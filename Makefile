.PHONY: install test lint demo serve video
install:
	uv sync --frozen --extra dev --extra video
test:
	uv run --frozen --extra dev pytest -q --junitxml=artifacts/test-results.xml
lint:
	uv run --frozen ruff check src tests scripts
	uv run --frozen ruff format --check src tests scripts
demo:
	uv run --frozen agent-suite demo
serve:
	uv run --frozen agent-suite serve
video:
	uv run --frozen --extra video python scripts/render_video.py
