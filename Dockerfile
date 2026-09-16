# Karst research data service. Deployment notes: zeabur.md
# Nothing here bakes in a ticker, a data set or a credential; /data is a mounted volume.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONUTF8=1 PYTHONPATH=/app KARST_DATA_DIR=/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# The package runs from the source tree (not site-packages) so that the versioned
# method sources under strategy/ stay where karst.pipeline looks for them.
COPY pyproject.toml ./
COPY karst/ ./karst/
COPY strategy/ ./strategy/

EXPOSE 8080
VOLUME ["/data"]

# KARST_MCP_TOKEN must be set, or the server refuses to serve HTTP.
CMD ["python", "-m", "karst.mcp_server", "--http", "--host", "0.0.0.0", "--port", "8080", "--data-dir", "/data"]
