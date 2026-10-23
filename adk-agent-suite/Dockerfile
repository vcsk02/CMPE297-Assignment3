FROM node:22-bookworm-slim AS cli
WORKDIR /cli
COPY integrations/gemini-cli/package*.json ./
RUN npm ci --omit=dev --ignore-scripts

FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PATH=/opt/gemini/node_modules/.bin:$PATH
WORKDIR /app
COPY --from=cli /usr/local/bin/node /usr/local/bin/node
COPY --from=cli /cli/node_modules /opt/gemini/node_modules
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN pip install --no-cache-dir uv==0.12.23 && uv sync --frozen --no-dev --no-editable \
    && groupadd -g 10001 app && useradd -u 10001 -g app -d /app app \
    && mkdir -p data && chown app:app data
COPY examples ./examples
USER 10001:10001
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s CMD ["/app/.venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=3)"]
CMD ["/app/.venv/bin/agent-suite", "serve", "--host", "0.0.0.0", "--port", "8080"]
