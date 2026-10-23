"""Read-only, bounded source snapshots. No imports, symlinks, secrets or git metadata."""

from pathlib import Path

EXCLUDED = {".git", ".venv", "node_modules", "__pycache__", ".gemini", "data"}
EXTENSIONS = {".py", ".js", ".ts", ".tsx", ".md", ".toml", ".yaml", ".yml"}


def resolve_target(root: Path, relative: str) -> Path:
    root = root.resolve()
    candidate = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("Target must be a relative path inside WORKSPACE_ROOT")
    for parent in [candidate, *candidate.parents]:
        if parent == root.parent:
            break
        if parent.is_symlink():
            raise ValueError("Symlinks are not accepted")
    target = candidate.resolve()
    if not target.is_relative_to(root) or not target.is_dir():
        raise ValueError("Target directory not found inside WORKSPACE_ROOT")
    return target


def source_snapshot(root: Path, relative: str) -> dict[str, str]:
    target, result, total = resolve_target(root, relative), {}, 0
    for path in sorted(target.rglob("*")):
        rel = path.relative_to(target)
        if any(p in EXCLUDED or p.startswith(".") for p in rel.parts):
            continue
        if path.is_symlink() or not path.is_file() or path.suffix not in EXTENSIONS:
            continue
        if path.name.upper() in {"GEMINI.MD", "AGENTS.MD"}:
            continue
        if path.stat().st_size > 50000 or len(result) >= 100:
            raise ValueError("Source exceeds snapshot limits")
        content = path.read_text(encoding="utf-8")
        total += len(content.encode())
        if total > 200000:
            raise ValueError("Source exceeds 200 KB snapshot limit")
        result[str(rel)] = content
    if not result:
        raise ValueError("No supported source files found")
    return result
