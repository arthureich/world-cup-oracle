# B10 — Arquitetura / Stack

## Status

```text
MVP local implementado
```

Ainda existem partes em desenho, principalmente CLI completa, cache de API, outputs finais e dashboard.

---

## Stack recomendada

```text
Python
Polars
DuckDB
Parquet
NumPy / SciPy
Streamlit
pytest
Markdown / MkDocs
Git
```

---

## Estrutura implementada

```text
pyproject.toml
README.md

data/
  raw/
  interim/
  processed/
  snapshots/

src/
  tactical_oracle/
    config/
    data/
    elo/
    tsi/
    squad/
    odds/
    attack_defense/
    simulation/
    validation/
    pipeline/

tests/
  test_elo.py
  test_tsi.py
  test_attack_defense.py
  test_simulation.py
  test_validation.py
```

---

## Comandos implementados

```text
tactical-oracle-mocks
tactical-oracle-mock-pipeline
```

O primeiro grava datasets mockados em Parquet.

O segundo executa um fluxo local:

```text
pontos FIFA mockados
→ Elo
→ TSI
→ Ataque/Defesa
→ λ por jogo
→ probabilidades Poisson
```

---

## Arquitetura alvo

```text
Parquet raw data
↓
Polars / DuckDB normalization
↓
ratings pipeline
  Elo
  TSI
  elenco
  odds
  ataque/defesa
↓
simulation engine
  Poisson
  grupos
  mata-mata
  Monte Carlo
↓
validation engine
  Brier
  Log Loss
  calibration curves
↓
outputs Parquet
↓
Streamlit dashboard
```

---

## Decisão de dados

Como API-Football free tem limite de 100 requests/dia, o pipeline deve usar cache local obrigatório.

Estratégia:

```text
base aberta histórica, se encontrada
+ API-Football para validação/gaps
+ correções manuais pontuais
+ Parquet final para o modelo
```

Toda resposta de API deve ser salva crua:

```text
data/raw/api_football/endpoint/params_hash/date.json
```

Regra:

```text
se já baixou, não chama a API de novo
```

---

## Pendências técnicas

```text
instalar dependências e validar com pytest
gerar Parquets mockados em data/raw/
criar pipeline de escrita em data/processed/
implementar cache de API
implementar B3 completo
implementar B5 completo
implementar B6 com dados reais de odds
carregar Anexo C como arquivo estático
definir dashboard B8
```
