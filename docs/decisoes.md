# Decisões técnicas

A numeração acompanha os nomes dos testes (`test_sa_N_…`, `test_l_N_…`). **SA-** são decisões técnicas; **L-** são lacunas da ficha do projeto, decididas. Números SA ausentes são decisões de processo, sem efeito no código, exceto a SA-18, substituída pela L-3 e pela L-4.

- **SA-1** — Settings particionados (`base`/`dev`/`prod`) em vez de um arquivo único: dev e produção divergem em `DEBUG`, hosts e banco, e um `if DEBUG` espalhado é onde erro de produção se esconde.
- **SA-2** — `/healthz/` como view no pacote `config` em vez de app própria: é infraestrutura, não domínio. Faz `SELECT 1` e prova app de pé e banco alcançável; sem `try/except`, porque banco fora **deve** derrubar o health check.
- **SA-3** — Só as dependências que o passo usa, com versões travadas no `uv.lock` (`uv sync --locked` no CI): o lock versionado é o contrato do ambiente.
- **SA-4** — Configuração por variável de ambiente (`django-environ`, `DATABASE_URL`) em vez de valores no código: o mesmo settings serve dev, CI e produção; `.env` fora do git; `.env.example` sem segredos, só com a URL do Postgres local do compose (credencial de desenvolvimento, a mesma do `docker-compose.yml`), para o projeto rodar depois de um `cp`.
- **SA-5** — Cobertura omite `wsgi.py`, `asgi.py` e `settings/prod.py`: boilerplate que só executa em produção; regra de negócio é 100% medida.
- **SA-6** — `SECRET_KEY` fixa e não-secreta no CI em vez de segredo do repositório: o CI não serve tráfego; ali ela é parâmetro, não segredo.
- **SA-7** — Postgres local publicado em `5433` em vez de `5432`: evita colisão com um Postgres nativo na máquina de desenvolvimento e torna o `docker compose up` robusto em máquina alheia. No CI a porta segue 5432 (runner limpo).
- Imagem do Postgres no CI pelo espelho `mirror.gcr.io/library` em vez do Docker Hub: CI público compartilha IP e estoura o rate limit anônimo do Hub.
- **SA-9** — Usuário customizado (`users.User`) desde a primeira migração em vez do `auth.User`: trocar `AUTH_USER_MODEL` com tabelas já criadas exige reescrever migrações à mão. E-mail obrigatório no registro.
- **SA-10** — Registro público em `POST /api/auth/registro/`, com os validadores de senha do Django (inclusive o de similaridade com username e e-mail); a resposta nunca devolve a senha.
- **SA-11** — Login por username em `POST /api/auth/token/` com a `TokenAuthentication` nativa em vez de JWT: o token vive no banco, e revogar é apagar uma linha, sem lista de bloqueio. Credencial inválida responde 401 com a mesma mensagem para senha errada e usuário inexistente, para que o login não confirme quais usuários existem; corpo malformado ou campo ausente continua 400.
- **SA-12** — `TokenAuthentication` e `IsAuthenticated` como padrão global em vez de liberar rota por rota: rota nova nasce fechada. Só `TokenAuthentication`, sem `SessionAuthentication`: o DRF responde 401 (e não 403) apenas quando a primeira classe de autenticação monta o cabeçalho `WWW-Authenticate`, e a `SessionAuthentication` não monta; com uma classe só, não há ordem a errar.
- **SA-13** — Ruff fora das migrações (código gerado pelo Django) e sem a RUF012: Django e DRF declaram configuração como atributo de classe por convenção (`Meta.fields`, `permission_classes`), e a regra acusava a forma idiomática.
- **SA-14** — E-mail único sem diferenciar maiúsculas, garantido no banco por `UniqueConstraint(Lower("email"))` em vez de só no serializer: o validador dá a mensagem amigável, o índice dá a garantia. Numa corrida entre duas requisições, o índice decide e o `IntegrityError` vira o mesmo 400.
- **SA-15** — Senha aceita como digitada em vez de aparada: o login não apara espaços, e aparar só no registro trancaria para fora quem usa espaço nas bordas. Limite de 128 caracteres na entrada, folgado para gerenciadores de senha.
- **SA-16** — Admin é `is_staff` (`IsAdminUser` do DRF) em vez de um papel próprio: o sistema tem só dois perfis, e o flag nativo é o mesmo do admin do Django, sem campo nem migração a mais.
- **SA-17** — Em `/api/salas/`, leitura para qualquer autenticado e escrita (`POST`, `PATCH`, `DELETE`) só para admin, pelo `get_permissions` do viewset; `PUT` fora (`http_method_names`), porque a ficha só prevê alteração parcial. A permissão é conferida antes do método: usuário comum recebe 403 em qualquer verbo de escrita, e só o admin vê o 405 do `PUT`.
- **SA-19** — `DELETE` apaga a sala de fato em vez de desativá-la: o verbo faz o que diz, e desativar é `PATCH` com `"ativa": false`.
- **SA-20** — Capacidade mínima 1 em dois lugares em vez de um: o serializer dá a mensagem em português e a `CheckConstraint` `sala_capacidade_minima` garante no banco. Validador no modelo ficou de fora: nenhum caminho do projeto o executaria, e o `full_clean()` já valida a constraint. O teto de 32767 vem do `PositiveSmallIntegerField` e o DRF o leva ao serializer, então um valor acima dele dá 400, não 500.
- **SA-21** — Nome de sala único sem diferenciar maiúsculas, garantido por `UniqueConstraint(Lower("nome"))` em vez do `unique=True` da ficha: "Sala A" e "sala a" seriam a mesma sala para quem reserva. Mesmo padrão da SA-14: o validador dá a mensagem, o índice dá a garantia.
- **SA-22** — Listagem de salas ordenada por nome (`Meta.ordering`) em vez da ordem de inserção: resposta determinística e testes estáveis.
- **SA-23** — `SimpleRouter` em vez de `DefaultRouter`: o `DefaultRouter` publica uma raiz navegável em `/api/` que ninguém usa e que seria mais uma rota a fechar.
- **SA-24** — Um app só (`reservas`) para salas e reservas em vez de um por modelo: o serviço, as permissões e os filtros da ficha formam uma camada só, e a `Reserva` depende da `Sala`.

## Lacunas da ficha

- **L-1** — O teste de rota protegida sem token (401 com `WWW-Authenticate: Token`) entrou na primeira rota protegida, `GET /api/salas/`.
- **L-2** — Sem endpoint de logout: o token vive no banco, e revogar é apagar a linha (SA-11).
- **L-3** — `GET /api/salas/{id}/` existe, embora a ficha só liste a coleção: vem com o viewset e usa o mesmo filtro da listagem, então sala inativa dá 404 para usuário comum sem revelar que existe.
- **L-4** — Admin vê as salas inativas na listagem; usuário comum, só as ativas: sem isso, uma sala desativada sumiria da API para quem pode reativá-la.
