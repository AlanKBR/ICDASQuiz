# ICDASQuiz — instruções para agentes

Este repositório é o owner do **código da aplicação** ICDASQuiz. Em produção ele roda no servidor Zezin; não recrie infraestrutura de hospedagem dentro deste repo.

## Produção no Zezin

Antes de alterar deploy, rede, lifecycle, state, backup ou exposição:

1. rode `zezin where icdasquiz`;
2. leia `/srv/zezin/SERVICE-ARCHITECTURE.md`;
3. use `/srv/zezin/services/icdasquiz/service.toml` e o README daquele owner como fonte operacional;
4. valide estado vivo antes de mudar configuração.

Código fica aqui (`/srv/repos/owned/ICDASQuiz`). State, runtime e secrets ficam fora do Git nos planes V2 do Zezin. `icdas.db`, WAL/SHM, `.env`, secrets, backups e dados de usuários **nunca** pertencem ao repositório.

O serviço é stateful por causa do banco de pontuações e portanto não deve ser forçado no golden path stateless `zezin deploy`. Produção usa PostgreSQL; standalone/local usa SQLite embedded. Reutilize a borda compartilhada Cloudflare Tunnel -> Traefik -> CrowdSec; não instale proxy, firewall, scheduler ou sistema de backup paralelo.

## Aplicação

- Flask monolítico em `app.py`;
- SQLAlchemy 2 em `database.py`, com Alembic em `migrations/`; modelo atual `participants -> attempts -> answers`, mantendo `scores` apenas como legado/importação;
- `DATABASE_URL`/`POSTGRES_*` selecionam PostgreSQL; sem eles, `DB_PATH` usa SQLite embedded;
- não escreva SQL dependente de um dialeto sem necessidade; mudanças de schema entram como migration Alembic;
- produção exige `SECRET_KEY` e `FLASK_DEBUG=0`; `/dashboard` usa `ADMIN_PASSWORD` separado;
- produção usa `CF-Connecting-IP` validado para rate-limit/pseudônimo técnico; não confie diretamente em `X-Forwarded-For` nem reintroduza `ProxyFix` sem rever a cadeia efetiva;
- a coluna legada `ip` é mantida vazia; apenas `ip_hash` é retido por tentativa; não trate IP como identidade de pessoa;
- cada resposta registra imagem, códigos correto/respondido, acerto, ordem e tempo; não invente answers para scores históricos;
- `quiz_version` é derivada do conteúdo das imagens/descrições para preservar comparabilidade acadêmica;
- assets de quiz são `.webp` em `static/imagens/`;
- mudanças funcionais devem vir com testes em `tests.py`.

## Validação mínima

Após mudanças de aplicação: rode a suite pytest, construa a imagem, valide `/health`, fluxo principal do quiz e o modo SQLite standalone. Após mudança de banco/produção: valide também PostgreSQL, migrations, egress/exposição, backup+restore canary, restart e endpoint público.

Não execute `git push` sem ordem expressa do operador.
