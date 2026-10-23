"""Offline CLI test double. It is deliberately NOT presented as Gemini inference."""

import ast
import json
import sys
from pathlib import Path


def main():
    files, functions = [], []
    for path in sorted(Path(sys.argv[1]).rglob("*.py")):
        files.append(path.name)
        tree = ast.parse(path.read_text())
        functions.extend(n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef))
    print(
        json.dumps(
            {
                "response": "OFFLINE FIXTURE: Analyze stack initialization and duplicate checkout.",
                "files": files,
                "functions": functions,
                "test_plan": [
                    "DFS handles a start node that is an integer",
                    "Repeated checkout keys return one order",
                    "Stock never becomes negative",
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
