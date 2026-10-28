# Decisões técnicas

- **SA-1** — Settings particionados (`base`/`dev`/`prod`) em vez de um arquivo único: dev e produção divergem em `DEBUG`, hosts e banco, e um `if DEBUG` espalhado é onde erro de produção se esconde.
- **SA-2** — `/healthz/` como view no pacote `config` em vez de app própria: é infraestrutura, não domínio. Faz `SELECT 1` e prova app de pé e banco alcançável; sem `try/except`, porque banco fora **deve** derrubar o health check.
- **SA-3** — Só as dependências que o passo usa, com versões travadas no `uv.lock` (`uv sync --locked` no CI): o lock versionado é o contrato do ambiente.
- **SA-4** — Configuração por variável de ambiente (`django-environ`, `DATABASE_URL`) em vez de valores no código: o mesmo settings serve dev, CI e produção; `.env` fora do git, `.env.example` sem valores.
- **SA-5** — Cobertura omite `wsgi.py`, `asgi.py` e `settings/prod.py`: boilerplate que só executa em produção; regra de negócio é 100% medida.
- **SA-6** — `SECRET_KEY` fixa e não-secreta no CI em vez de segredo do repositório: o CI não serve tráfego; ali ela é parâmetro, não segredo.
- **SA-7** — Postgres local publicado em `5433` em vez de `5432`: evita colisão com um Postgres nativo na máquina de desenvolvimento e torna o `docker compose up` robusto em máquina alheia. No CI a porta segue 5432 (runner limpo).
- Imagem do Postgres no CI pelo espelho `mirror.gcr.io/library` em vez do Docker Hub: CI público compartilha IP e estoura o rate limit anônimo do Hub.
