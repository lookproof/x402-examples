# Runs lookproof-mcp on stdio as a dry run, for automated checks such as Glama's: the server starts,
# lists its tools and answers each call with the price and no data. No API key, wallet or other secret
# is in the image or needed to run it. To get data, pass LOOKPROOF_API_KEY (or the x402 settings)
# with `docker run -e` at run time; never bake them into the image.
#
#   docker build -t lookproof-mcp mcp-server
#   docker run -i --rm lookproof-mcp
FROM python:3.12-slim

WORKDIR /app
COPY pyproject.toml README.md LICENSE CHANGELOG.md ./
COPY src ./src
RUN pip install --no-cache-dir . && useradd --create-home --uid 10001 mcp

USER mcp
WORKDIR /home/mcp
ENTRYPOINT ["lookproof-mcp"]
