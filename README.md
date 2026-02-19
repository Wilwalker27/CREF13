# Controle de Estoque TI

Aplicacao em Streamlit para cadastro de equipamentos, movimentacoes e relatorios.

## Rodar local

1. Criar/ativar ambiente virtual.
2. Instalar dependencias:
   `pip install -r requirements.txt`
3. Definir senha da aplicacao:
   `APP_PASSWORD=<sua_senha>`
4. Executar:
   `streamlit run estoque.py`

## Deploy no Streamlit Community Cloud

1. Suba este projeto para um repositorio no GitHub.
2. No Streamlit Community Cloud, clique em `Create app`.
3. Selecione:
   - Repositorio: o seu repositorio
   - Branch: a branch desejada (ex.: `main`)
   - Main file path: `estoque.py`
4. Em `Advanced settings` > `Secrets`, adicione:

```toml
APP_PASSWORD = "sua_senha_forte"
```

5. Clique em `Deploy`.

## Importante sobre banco de dados

Este projeto usa SQLite local (`estoque.db`). Em Streamlit Cloud, o disco local nao e persistente para longo prazo, entao dados podem ser perdidos em reinicios/redeploy.

Para uso em producao, recomenda-se migrar para banco externo (PostgreSQL, por exemplo).
