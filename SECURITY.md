# Política e Estado de Segurança

Documento gerado pela auditoria de segurança de 14/08/2026. Descreve o que foi
encontrado, o que foi corrigido e o que **você precisa fazer manualmente** antes
de considerar a aplicação segura em produção.

---

## 1. AÇÃO OBRIGATÓRIA: rotação da chave de assinatura

### O que aconteceu

O histórico do Git contém, desde o commit inicial até `9211ad0`, um README que
instruía o desenvolvedor a executar:

```
echo "SECRET_KEY=09d25e09...e8d3e7" > .env
```

Esse valor é a **chave de exemplo da documentação oficial do FastAPI**. Ela é
pública, aparece em milhares de repositórios e está em qualquer wordlist de
atacante.

### Por que isso é grave

A `SECRET_KEY` assina os tokens JWT. Quem conhece a chave consegue **forjar um
token válido para qualquer usuário**, sem senha, sem tentativa de login e sem
deixar rastro de falha de autenticação. É comprometimento total da autenticação.

Qualquer implantação criada seguindo aquele README está afetada.

### Correções já aplicadas

- A aplicação agora **recusa iniciar** se a `SECRET_KEY` for essa chave, um
  placeholder conhecido, curta demais ou de baixa entropia
  (`backend/core/config.py`).
- A denylist guarda o hash SHA-256 do segredo, não o segredo em si.

### O que você precisa fazer

```bash
# 1. Gere uma chave nova, exclusiva por ambiente
python -c "import secrets; print(secrets.token_urlsafe(64))"

# 2. Atualize a variável SECRET_KEY no provedor (Render, Vercel, etc.)
# 3. Reinicie o serviço
```

Trocar a chave invalida todos os tokens existentes — os usuários farão login de
novo. Isso é o comportamento desejado.

### Sobre a limpeza do histórico

**Não é necessário reescrever o histórico do Git.** Foi verificado que os
arquivos `.env` e `frontend/.env` **nunca chegaram a ser versionados**:

```bash
git log --all --full-history -- .env frontend/.env   # retorna vazio
```

O plano de rotação anterior (`SECURITY_ROTATION_PLAN.md`) partia da premissa de
que arquivos de ambiente tinham sido commitados. Isso não ocorreu. O que vazou
foi a chave de exemplo escrita no corpo do README — e para essa, rotacionar
resolve, já que o valor é público de qualquer forma. Um `git filter-repo`
seguido de force push traria o custo de reescrever o histórico sem benefício de
segurança correspondente.

---

## 2. Vulnerabilidades corrigidas

| # | Severidade | Problema | Correção |
|---|-----------|----------|----------|
| 1 | **Crítica** | Chave JWT pública no histórico do README | Denylist que impede a inicialização + rotação obrigatória |
| 2 | **Crítica** | **IDOR**: categorias eram globais — qualquer usuário autenticado podia listar, renomear e apagar as de todos | `usuario_id` obrigatório e filtro de posse em todo acesso |
| 3 | **Crítica** | CORS `.*\.vercel\.app` com `allow_credentials=True`: qualquer pessoa podia publicar um site na Vercel e ler os dados da vítima | Allowlist explícita, curinga rejeitado em produção |
| 4 | **Crítica** | `python-jose` com CVE-2024-33663 (confusão de algoritmo) e CVE-2024-33664 (DoS) | Migrado para PyJWT com allowlist de algoritmo |
| 5 | **Alta** | Transação podia referenciar categoria de outro usuário | Categoria resolvida dentro do escopo do usuário |
| 6 | **Alta** | Sem rate limiting: força bruta ilimitada no login | Janela deslizante por IP, com backend Redis opcional |
| 7 | **Alta** | Enumeração de usuários por tempo de resposta | Hash descartável equaliza o tempo |
| 8 | **Alta** | Troca de senha não encerrava as sessões ativas | `token_version` revoga todos os tokens |
| 9 | **Alta** | PWA guardava saldos e extrato em disco por 7 dias, sem limpar no logout | Cache de API removido; limpeza no logout e no 401 |
| 10 | **Alta** | 21 CVEs conhecidas nas dependências Python; 22 no frontend | Todas atualizadas — `pip-audit` e `npm audit` limpos |
| 11 | **Alta** | Sem migrações: `create_all` em produção | Alembic com backfill validado |
| 12 | **Média** | Sem política de senha | Mínimo de 12 caracteres, denylist, limite de tamanho |
| 13 | **Média** | Erros 500 expunham mensagens do driver de banco | Tratador genérico |
| 14 | **Média** | Erros de validação refletiam a senha enviada | Tratador que omite os valores |
| 15 | **Média** | Ausência de headers de segurança | HSTS, CSP, `no-store`, anti-clickjacking |
| 16 | **Média** | `limit` sem teto e intervalos de data ilimitados | Teto de 200 registros e de ~5 anos |
| 17 | **Média** | Corrida entre verificação e inserção no cadastro | Unicidade garantida pela constraint |
| 18 | **Média** | Retry de rede duplicava lançamentos financeiros | `Idempotency-Key` com índice único |
| 19 | **Média** | Sem trilha de auditoria | Tabela `logs_auditoria` append-only |
| 20 | **Média** | `avatar_url` aceitava `javascript:` (XSS armazenado) | Apenas `https:` e `data:image/` |
| 21 | **Média** | Mass assignment via campos extras no payload | `extra="forbid"` nos schemas |
| 22 | **Média** | Segredos podiam vazar em log via traceback | Filtro de redação no logger raiz |
| 23 | **Baixa** | Artefatos `.vs/` versionados (índice SQLite com conteúdo dos arquivos) | Removidos e ignorados |
| 24 | **Baixa** | `worker.py`/`tasks.py` importavam Celery, ausente das dependências | Removidos |

### Bug de integridade contábil (não é falha de segurança, mas some com dinheiro)

O campo `tipo` da categoria era texto livre, mas o dashboard só somava
`'Gasto'` e `'Receita'`. Uma categoria cadastrada como `'Despesa'` — termo
usado na própria documentação do projeto e nos schemas — era aceita pela API e
**desaparecia silenciosamente de todos os totais**. O dinheiro não aparecia em
lugar nenhum, sem erro.

Correções: `Literal["Gasto", "Receita"]` no schema, CHECK constraint no banco, e
a migração `0002` normaliza os registros existentes (`Despesa` → `Gasto`),
trazendo de volta os valores que estavam invisíveis.

---

## 3. Checklist de implantação em produção

```bash
ENVIRONMENT=production
SECRET_KEY=<nova, 64+ caracteres, exclusiva>
DATABASE_URL=postgresql://...          # PostgreSQL; SQLite é recusado
CORS_ORIGINS=https://seu-app.com       # sem curinga, sempre https
TRUSTED_HOSTS=api.seu-app.com          # '*' é recusado
REDIS_URL=redis://...                  # necessário com mais de um worker
DOCS_ENABLED=false                     # não exponha /docs
LOG_LEVEL=INFO
```

A aplicação **falha ao iniciar** se qualquer um desses itens estiver inseguro.
Isso é intencional: é preferível não subir a subir vulnerável.

### Migrações

```bash
# Instalação nova
alembic upgrade head

# Base existente, criada pelo antigo create_all
alembic stamp 0001
alembic upgrade head
```

A migração `0002` **aborta** se encontrar transações com valor ≤ 0, pedindo
revisão manual. Corrigir valores financeiros automaticamente seria pior do que
falhar.

---

## 4. Verificação contínua

```bash
pytest                      # 70 testes, incluindo isolamento entre usuários
pip-audit                   # CVEs nas dependências Python
bandit -r backend/          # análise estática
npm audit --prefix frontend # CVEs no frontend
```

---

## 5. Limitações conhecidas

Itens que exigem decisão de produto ou infraestrutura e ficaram fora do escopo
desta auditoria:

- **Token em `localStorage`.** Continua exposto a XSS. A mitigação adequada é
  cookie `httpOnly` + `SameSite=Strict` com proteção CSRF, o que muda o contrato
  entre frontend e backend. O risco atual está reduzido (CSP restritiva, nenhum
  `dangerouslySetInnerHTML` no código, validação de `avatar_url`), mas não
  eliminado.
- **Sem refresh token.** A sessão expira em 30 minutos e exige novo login.
- **Sem MFA.**
- **Rate limiting em memória** quando `REDIS_URL` não está configurado: o limite
  passa a valer por processo.
- **Trilha de auditoria no mesmo banco** da aplicação. Para conformidade estrita,
  ela deveria ir para armazenamento append-only separado, fora do alcance das
  credenciais da aplicação.
- **Sem criptografia em repouso** no nível da aplicação; depende do provedor.

---

## 6. Como reportar uma vulnerabilidade

Abra um contato privado com o mantenedor. Não abra issue pública com detalhes de
exploração.
