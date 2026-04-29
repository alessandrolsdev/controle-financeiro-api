# SECURITY_ROTATION_PLAN.md

## Contexto

Arquivos de ambiente foram versionados anteriormente e a `SECRET_KEY` deve ser considerada comprometida.

## Ações obrigatórias

1. Gerar uma nova `SECRET_KEY` forte.
2. Atualizar a `SECRET_KEY` nos ambientes reais.
3. Reiniciar serviços que dependem da `SECRET_KEY`.
4. Invalidar tokens/sessões antigas, se aplicável.
5. Confirmar que `.env` e `frontend/.env` não estão mais rastreados.
6. Limpar o histórico Git para remover os arquivos sensíveis antigos.
7. Fazer force push coordenado após a limpeza de histórico.
8. Avisar qualquer colaborador para reclonar o repositório ou resetar o clone local.

## Geração sugerida de SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

## Limpeza de histórico

Ferramenta recomendada:

```bash
git filter-repo --invert-paths --path .env --path frontend/.env
```

## Aviso

Este procedimento reescreve o histórico Git. O force push deve ser feito somente após aprovação explícita.
