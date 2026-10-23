"""Deterministic review checks are preserved independently of the LLM summary."""

import ast
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.genai import types

from agent_suite.config import Settings
from agent_suite.paths import resolve_target, source_snapshot
from agent_suite.process import run_process


def ast_findings(files: dict[str, str]) -> list[dict]:
    findings = []
    for filename, source in files.items():
        if not filename.endswith(".py"):
            continue

        def add(node, rule, severity, message, filename=filename):
            findings.append(
                {
                    "file": filename,
                    "line": node.lineno,
                    "rule": rule,
                    "severity": severity,
                    "message": message,
                    "source": "python_ast",
                }
            )

        try:
            tree = ast.parse(source, filename=filename)
        except SyntaxError as error:
            findings.append(
                {
                    "file": filename,
                    "line": error.lineno or 1,
                    "rule": "syntax",
                    "severity": "high",
                    "message": error.msg,
                    "source": "python_ast",
                }
            )
            continue
        pop_names = {
            n.func.value.id
            for n in ast.walk(tree)
            if isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "pop"
            and isinstance(n.func.value, ast.Name)
        }
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"}:
                    add(
                        node,
                        "dynamic-execution",
                        "high",
                        "Avoid executing dynamically supplied code.",
                    )
                if any(
                    k.arg == "shell" and isinstance(k.value, ast.Constant) and k.value.value is True
                    for k in node.keywords
                ):
                    add(node, "shell-true", "high", "Use an argument list with shell=False.")
                if (
                    isinstance(node.func, ast.Attribute)
                    and node.func.attr == "execute"
                    and node.args
                ):
                    if isinstance(node.args[0], (ast.JoinedStr, ast.BinOp)):
                        add(node, "sql-interpolation", "high", "Bind SQL values with parameters.")
            if isinstance(node, ast.ExceptHandler) and node.type is None:
                add(
                    node,
                    "bare-except",
                    "medium",
                    "Catch a specific exception and preserve cancellation.",
                )
            if isinstance(node, ast.Assign) and isinstance(node.value, ast.Name):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id in pop_names:
                        add(
                            node,
                            "stack-initialization",
                            "medium",
                            "Container later uses pop(); verify initialization. For DFS use [start].",
                        )
    return findings


async def lint_snapshot(files: dict[str, str]) -> dict:
    with tempfile.TemporaryDirectory(prefix="adk-lint-") as temp:
        for filename, content in files.items():
            destination = Path(temp) / filename
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(content)
        result = await run_process(
            [
                sys.executable,
                "-m",
                "ruff",
                "check",
                "--isolated",
                "--output-format",
                "json",
                "--select",
                "E9,F63,F7,F82",
                temp,
            ],
            cwd=temp,
            env={"PATH": os.environ.get("PATH", "")},
            timeout=20,
        )
        if result["exit_code"] not in {0, 1}:
            raise ValueError("Linter failed")
        findings = json.loads(result["stdout"])
        for finding in findings:
            finding["filename"] = str(Path(finding["filename"]).relative_to(temp))
        return {
            "status": "passed" if not findings else "findings",
            "findings": findings,
            "exit_code": result["exit_code"],
        }


async def test_target(settings: Settings, target: str) -> dict:
    path = resolve_target(settings.workspace_root, target)
    if settings.review_test_mode == "skip":
        return {
            "status": "skipped",
            "reason": "Execution requires an explicit trusted or docker mode",
        }
    if settings.review_test_mode == "docker":
        docker = shutil.which("docker")
        if not docker:
            raise ValueError("Docker test isolation requested, but Docker is unavailable")
        argv = [
            docker,
            "run",
            "--rm",
            "--network",
            "none",
            "--read-only",
            "--cap-drop",
            "ALL",
            "--security-opt",
            "no-new-privileges",
            "--cpus",
            "1",
            "--memory",
            "256m",
            "--pids-limit",
            "64",
            "--user",
            "65532:65532",
            "--tmpfs",
            "/tmp:rw,nosuid,size=16m",
            "--mount",
            f"type=bind,src={path},dst=/work,readonly",
            "python:3.12-slim",
            "python",
            "-I",
            "-B",
            "-m",
            "unittest",
            "discover",
            "-s",
            "/work",
        ]
    else:
        argv = [sys.executable, "-I", "-B", "-m", "unittest", "discover", "-s", str(path)]
    result = await run_process(
        argv, cwd=str(path), env={"PATH": os.environ.get("PATH", "")}, timeout=30
    )
    output = result["stdout"] + result["stderr"]
    if "Ran 0 tests" in output:
        status = "no_tests"
    else:
        status = "passed" if result["exit_code"] == 0 else "failed"
    return {"status": status, **result, "isolation": settings.review_test_mode}


class ReviewCheck(BaseAgent):
    settings: Settings
    check: str

    async def _run_async_impl(self, ctx):
        target = ctx.session.state.get("review_target", "review_target")
        if self.check == "ast":
            result = {
                "findings": ast_findings(source_snapshot(self.settings.workspace_root, target))
            }
        elif self.check == "lint":
            result = await lint_snapshot(source_snapshot(self.settings.workspace_root, target))
        elif self.check == "tests":
            result = await test_target(self.settings, target)
        else:
            raise ValueError("Unknown review check")
        yield Event(
            author=self.name,
            content=types.Content(
                role="model", parts=[types.Part.from_text(text=json.dumps(result))]
            ),
            actions=EventActions(state_delta={"review_" + self.check: result}),
        )


def final_review(state: dict, narrative: dict | str) -> dict:
    if isinstance(narrative, str):
        narrative = json.loads(narrative)
    findings = list(state.get("review_ast", {}).get("findings", []))
    for item in state.get("review_lint", {}).get("findings", []):
        findings.append(
            {
                "file": item["filename"],
                "line": item["location"]["row"],
                "rule": item["code"],
                "severity": "medium",
                "message": item["message"],
                "source": "ruff",
            }
        )
    tests = state.get("review_tests", {"status": "skipped"})
    verdict = (
        "changes_requested" if findings or tests["status"] == "failed" else "needs_human_review"
    )
    return {
        "verdict": verdict,
        **narrative,
        "findings": findings,
        "test_execution": tests,
        "limitations": [
            "AST checks cover a small Python rule set, not complete security analysis.",
            "This assistant never approves or merges a pull request.",
        ],
    }
