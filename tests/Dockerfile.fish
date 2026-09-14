FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

RUN apt-get update \
    && apt-get install --no-install-recommends --yes fish git \
    && rm -rf /var/lib/apt/lists/*

RUN uv pip install --system invoke-toolkit

ENV PYTHONPATH=/workspace/src
WORKDIR /workspace

COPY tests/fish.config.fish /root/.config/fish/config.fish

ENTRYPOINT ["fish"]
CMD ["--interactive"]
