# syntax=docker/dockerfile:1

FROM python:3.13-slim AS builder

# build-essential is needed for any sdist-only deps (e.g. asyncmy's Cython build)
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

WORKDIR /app
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    pip install --upgrade pip \
    && pip install -r requirements.txt

FROM python:3.13-slim AS runtime

# libmediainfo0v5 provides the native library pymediainfo binds to on Linux
# (Linux wheels do not bundle it, unlike the Windows/macOS wheels)
# gosu lets the entrypoint drop from root to the runtime user after fixing ownership
RUN apt-get update \
    && apt-get install -y --no-install-recommends libmediainfo0v5 gosu \
    && rm -rf /var/lib/apt/lists/*

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1
COPY --from=builder "$VIRTUAL_ENV" "$VIRTUAL_ENV"

WORKDIR /app
COPY . .

# the UI is unzipped into web/ in the build context before `docker build` (see the release workflow);
# it lands at /app/web, which is config.web_dir. UI_VERSION is stamped for traceability only.
ARG UI_VERSION=unknown
LABEL org.saberr.ui-version=$UI_VERSION

RUN groupadd --gid 1000 saber \
    && useradd --uid 1000 --gid 1000 --create-home saber \
    && sed -i 's/\r$//' /app/scripts/docker/entrypoint.sh \
    && cp /app/scripts/docker/entrypoint.sh /usr/local/bin/docker-entrypoint.sh \
    && chmod +x /usr/local/bin/docker-entrypoint.sh

ENV PORT=8000
EXPOSE 8000

ENTRYPOINT ["docker-entrypoint.sh"]
CMD ["python", "main.py"]
