# Imagem de produção (SA-56): o uv monta o .venv no estágio de build; a imagem
# final leva só o .venv, o código e os estáticos, e roda sem privilégio.
FROM ghcr.io/astral-sh/uv:0.12.15 AS uv

FROM python:3.13.15-slim-trixie AS build
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never
WORKDIR /app
COPY pyproject.toml uv.lock .python-version ./
RUN uv sync --locked --no-dev --no-install-project
COPY manage.py ./
COPY src ./src
# O collectstatic importa os settings, que exigem as duas variáveis. Estas não
# são segredo, não conectam em banco nenhum e não chegam à imagem final.
RUN SECRET_KEY=build-sem-uso DATABASE_URL=sqlite:////tmp/build.db \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    .venv/bin/python manage.py collectstatic --noinput

FROM python:3.13.15-slim-trixie
RUN useradd --system --uid 10001 --no-create-home app
WORKDIR /app
COPY --from=build /app /app
USER app
ENV PATH="/app/.venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings.prod \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["gunicorn", "--pythonpath", "src", "config.wsgi", "--bind", "0.0.0.0:8000", "--workers", "2", "--no-control-socket", "--access-logfile", "-"]
