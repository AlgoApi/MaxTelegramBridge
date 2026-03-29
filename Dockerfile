FROM ghcr.io/astral-sh/uv:python3.12-alpine AS builder

WORKDIR /app

RUN apk add --no-cache git build-base python3-dev libffi-dev
# --------------------------

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --frozen --no-install-project --no-dev

FROM python:3.12-alpine

WORKDIR /app

# Копируем виртуальное окружение из билдера
COPY --from=builder /app/.venv /app/.venv

# Устанавливаем переменную окружения, чтобы использовать пакеты из .venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

# Копируем исходный код проекта
COPY . .

# Создаем папки для сессий, чтобы Docker не ругался на права
RUN mkdir -p sessions redis_data

# Запуск моста
CMD ["python", "bridge.py"]