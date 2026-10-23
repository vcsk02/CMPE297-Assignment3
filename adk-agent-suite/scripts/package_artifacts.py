"""Create the complete handoff archive, excluding credentials and reproducible scratch data."""

import hashlib
import json
import os
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDE_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "data",
}


def main():
    paths = []
    for directory, dirs, files in os.walk(ROOT):
        relative = Path(directory).relative_to(ROOT)
        dirs[:] = [
            d
            for d in dirs
            if d not in EXCLUDE_DIRS and not (relative == Path("video") and d == "build")
        ]
        for name in files:
            path = Path(directory) / name
            if (
                path.is_symlink()
                or name == ".env"
                or (name.startswith(".env.") and name != ".env.example")
            ):
                continue
            if name.endswith((".db", ".db-shm", ".db-wal", ".sqlite", ".pyc")):
                continue
            if name.startswith("client_secret") or name.endswith("token.json"):
                continue
            if name == "manifest.json" and relative == Path("artifacts"):
                continue
            paths.append(path)
    manifest = {
        "files": [
            {
                "path": str(path.relative_to(ROOT)),
                "size": path.stat().st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            for path in sorted(paths)
        ]
    }
    manifest_path = ROOT / "artifacts/manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    paths.append(manifest_path)
    destination = ROOT / "dist/adk-agent-suite.zip"
    destination.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(paths):
            archive.write(path, ROOT.name + "/" + str(path.relative_to(ROOT)))
    print(f"{destination}: {len(paths)} files, {destination.stat().st_size / 1048576:.1f} MiB")


if __name__ == "__main__":
    main()
