# Política e Estado de Segurança

Auditoria de segurança de 14/08/2026, atualizada na segunda rodada de
06/09/2026. Descreve o que foi encontrado, o que foi corrigido e o que **você
precisa fazer manualmente** antes de considerar a aplicação segura em produção.

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
ENCRYPTION_KEY=<outra chave, DIFERENTE da SECRET_KEY>
DATABASE_URL=postgresql://...          # PostgreSQL; SQLite é recusado
CORS_ORIGINS=https://seu-app.com       # sem curinga, sempre https
TRUSTED_HOSTS=api.seu-app.com          # '*' é recusado
REDIS_URL=redis://...                  # obrigatório com WEB_CONCURRENCY > 1
WEB_CONCURRENCY=4
DOCS_ENABLED=false                     # não exponha /docs
COOKIE_SAMESITE=strict
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

A migração `0003` cifra os dados pessoais já gravados. Ela usa a mesma chave que
a aplicação usará, então defina a `ENCRYPTION_KEY` **definitiva antes** de
migrar: trocá-la depois torna os dados ilegíveis.

---

## 4. Verificação contínua

```bash
pytest                       # 132 testes: isolamento, JWT, sessões, MFA, cripto
pip-audit                    # CVEs nas dependências Python
bandit -r backend/           # análise estática
ruff check backend/ tests/   # lint

cd frontend
npm run lint                 # lint do frontend
npm audit                    # CVEs no frontend
```

---

## 5. Segunda rodada (06/09/2026)

Fecha os itens que a primeira rodada havia deixado em aberto.

| # | Item anterior | Resolução |
|---|---------------|-----------|
| 25 | Token em `localStorage`, exposto a XSS | Sessão em cookies `httpOnly` + `SameSite=Strict`, com CSRF por double-submit |
| 26 | Sem refresh token | Refresh token opaco, hasheado, com rotação a cada uso e revogação da família ao detectar reuso |
| 27 | Sem MFA | TOTP (RFC 6238) com códigos de recuperação de uso único |
| 28 | Rate limiting em memória com vários workers | Produção recusa iniciar com `WEB_CONCURRENCY > 1` sem `REDIS_URL` |
| 29 | Sem criptografia em repouso na aplicação | AES-256-GCM em nome, e-mail, observações e segredo TOTP, com índice cego para o e-mail |

### Detalhes das mudanças

**Cookies em vez de `localStorage`.** Um XSS ainda consegue agir em nome do
usuário enquanto a página está aberta, mas não consegue mais **exfiltrar** a
credencial para uso posterior — a diferença entre um incidente contido e uma
conta comprometida em definitivo. Como o navegador passa a enviar cookies
automaticamente, o CSRF é barrado por `SameSite=Strict` mais um token de
double-submit no cabeçalho `X-CSRF-Token`. O caminho `Authorization: Bearer`
segue disponível para clientes que não são navegadores, e é dispensado da
verificação de CSRF porque o navegador nunca envia esse cabeçalho sozinho.

**Rotação com detecção de reuso.** Cada renovação invalida o refresh token
apresentado e emite um sucessor na mesma família. Se um token já consumido
reaparece, a conclusão é que uma cópia vazou — o cliente legítimo já teria o
sucessor — e a família inteira é revogada, encerrando as duas sessões. É o
desfecho seguro: melhor derrubar a vítima junto do atacante do que manter as
duas ativas.

**Criptografia de campos.** Complementa, não substitui, a criptografia de disco
do provedor. As duas cobrem ameaças diferentes: a do provedor protege contra
alguém que leve o disco embora; esta protege contra quem obtém leitura do banco
— backup vazado, réplica mal configurada, dump em ticket de suporte, injeção de
SQL —, cenários em que o disco já foi descriptografado e os dados apareceriam em
claro. O e-mail continua pesquisável através de um índice cego (HMAC com chave
secreta), que preserva a restrição de unicidade sem guardar o endereço.

> **A `ENCRYPTION_KEY` não tem backup automático.** Perdê-la torna os dados
> cifrados irrecuperáveis. Guarde-a no cofre de segredos do provedor, não apenas
> na variável de ambiente.

### Bugs encontrados executando a aplicação

Três defeitos só apareceram ao rodar a interface de ponta a ponta, e não nos
testes:

1. **Laço de redirecionamento em `/login`.** A sondagem inicial de sessão recebe
   401 quando ninguém está logado; o interceptor tratava isso como sessão
   expirada, tentava renovar, falhava e redirecionava para `/login` — de onde a
   sondagem recomeçava.
2. **Preflight de CORS reprovado.** `X-CSRF-Token` não constava da allowlist de
   cabeçalhos, então toda escrita vinda do navegador era barrada antes de chegar
   à aplicação. Os testes não pegaram isso porque o `TestClient` não simula CORS;
   agora há um teste específico para o preflight.
3. **`App.css` nunca importado**, deixando o layout sem o contêiner de largura
   máxima.

## 6. Limitações conhecidas

- **Trilha de auditoria no mesmo banco da aplicação.** É uma escolha, não uma
  omissão: gravá-la na mesma transação da operação auditada garante que as duas
  existam ou nenhuma exista. Movê-la para outro banco daria isolamento contra as
  credenciais da aplicação, mas ao custo dessa atomicidade. Para conformidade
  estrita, o isolamento se obtém melhor na infraestrutura — réplica lógica
  append-only, papel de banco sem `DELETE`/`UPDATE` na tabela, ou backup WORM.
- **Sem WebAuthn/passkeys.** O TOTP é resistente a vazamento de senha, mas não a
  phishing em tempo real. Passkeys seriam o próximo passo.
- **Sem recuperação de senha por e-mail**, o que torna os códigos de recuperação
  o único caminho de volta caso o usuário perca o autenticador.
- **Categorização da importação é heurística.** Palavras-chave acertam os casos
  comuns de extrato brasileiro, mas não substituem revisão do usuário.

---

## 6. Como reportar uma vulnerabilidade

Abra um contato privado com o mantenedor. Não abra issue pública com detalhes de
exploração.
