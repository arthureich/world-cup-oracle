# Pendências e Riscos

Projeto: **Tactical Oracle**

---

## 1. Dados históricos do ciclo

### Risco

Não encontrar fonte completa e confiável.

### Impacto

Afeta Elo próprio.

### Mitigação

```text
priorizar competições oficiais
usar API-Football para spike/gaps
usar base aberta se encontrada
corrigir manualmente casos críticos
```

---

## 2. API-Football com 100 requests/dia

### Risco

Limite gratuito pode não permitir coleta ampla.

### Mitigação

```text
cache obrigatório
buscar por competição quando possível
não repetir requests
salvar JSON bruto
usar API só para validação/gaps se necessário
```

---

## 3. Pênaltis mal representados

### Risco

Fonte pode incluir shootout no placar.

### Mitigação

```text
goals_a/goals_b sem shootout
penalty_winner separado
corrigir manualmente mata-mata importante
```

---

## 4. Campo neutro / mando

### Risco

Fonte pode não distinguir mandante nominal e mando real.

### Mitigação

```text
neutral_site obrigatório
validar jogos em sede neutra
anfitrião da Copa por sede/país
```

---

## 5. Fonte única de xG

### Risco

xG/chances claras podem não estar disponíveis de forma consistente.

### Mitigação

```text
escolher fonte principal
não misturar provedores
se xG faltar, usar composto reduzido
```

---

## 6. Momentum indisponível

### Risco

Momentum pode ser visual e não exportável.

### Mitigação

```text
não depender de momentum no MVP
usar apenas se disponível de forma estruturada
```

---

## 7. Escalações e rotação

### Risco

Medir XI escalado vs XI provável pode ser difícil.

### Mitigação

```text
começar com heurística simples
usar minutagem/valor dos titulares
permitir ajuste manual em jogos críticos
```

---

## 8. Necessidade competitiva

### Risco

Difícil modelar “já classificado”, “precisa vencer” e “jogo morto”.

### Mitigação

```text
derivar da tabela antes da rodada
começar com regras simples
corrigir casos de borda manualmente
```

---

## 9. Anexo C

### Risco

Erro no chaveamento dos melhores terceiros.

### Mitigação

```text
tratar Anexo C como arquivo estático
testar todas as 495 combinações
criar testes unitários
```

---

## 10. Critérios de desempate

### Risco

Ordem errada de desempate.

### Mitigação

```text
documentar ordem oficial
criar testes com grupos sintéticos
usar fair play real durante a Copa se disponível
```

---

## 11. Poisson subestimar empates

### Risco

Poisson independente pode gerar poucos empates ou placares baixos.

### Mitigação

```text
validar no B9
ativar Dixon-Coles só se necessário
```

---

## 12. Parâmetros demais

### Risco

Overfitting.

### Mitigação

```text
calibrar poucos parâmetros por vez
preferir valores simples
documentar alterações
se melhora pouco, manter simples
```

---

## 13. Curvas de idade do B5

### Risco

Podem supervalorizar veteranos ou jovens.

### Mitigação

```text
inspecionar extremos
usar cap ±1.000
calibrar com distribuição das 48 seleções
```

---

## 14. Odds de passar de fase indisponíveis

### Risco

Nem todas as casas podem oferecer mercado completo.

### Mitigação

```text
usar agregador
usar odds de vencer grupo como alternativa
reduzir peso se mercado estiver incompleto
```

---

## 15. Simulação lenta

### Risco

200k+ simulações podem ficar lentas.

### Mitigação

```text
NumPy vetorizado
cache de probabilidades por confronto
rodar simulação pesada offline
dashboard lê outputs prontos
```

---

## 16. Dashboard recalculando tudo

### Risco

Interface lenta.

### Mitigação

```text
pré-computar outputs
dashboard consulta Parquet
simulador individual calcula sob demanda
```

---

## 17. B8 ainda não consolidado

### Pendência

Definir produto final:

```text
telas do dashboard
rankings
comparador de seleções
simulador de confronto
relatórios
exports
fluxo de atualização durante a Copa
```

---

## 18. B10 ainda precisa ser formalizado

### Pendência

A stack foi recomendada, mas falta consolidar:

```text
estrutura de pastas
CLI
orquestração
cache
versionamento
testes
deploy
```

---

### Status atual

```text
MVP local criado com pyproject, pacote Python, estrutura de dados,
schemas, Elo, TSI, ataque/defesa, simulação, validação e testes mínimos.
```

Ainda faltam:

```text
CLI/pipeline completo
cache de API
outputs Parquet processados
dashboard
```

---

## 19. Dependências locais não instaladas

### Risco

O ambiente de desenvolvimento pode não ter `pytest`, `polars`, `duckdb` e `scipy` instalados.

### Impacto

Afeta geração de Parquet mockado e execução formal dos testes.

### Mitigação

```text
instalar com pip install -e ".[dev]"
rodar pytest
rodar tactical-oracle-mocks
rodar tactical-oracle-mock-pipeline
```

---

## Próximos passos

```text
1. instalar dependências e rodar pytest
2. gerar Parquets mockados
3. implementar B3 — desempenho por jogo
4. completar B5 — elenco
5. completar B6 — odds de longo prazo
6. carregar Anexo C oficial como dado estático
7. criar pipeline que escreva outputs em data/processed/
8. consolidar B8 — Produto final
9. fazer data spike com API/base aberta
10. criar dataset mínimo do ciclo Copa 2026
```
