# Tactical Oracle — Visão Geral

## O que é o projeto

**Tactical Oracle** é um projeto de modelagem estatística para a Copa do Mundo 2026.

O objetivo é estimar a força das seleções, calcular probabilidades por jogo e simular a Copa inteira para responder perguntas como:

- Qual seleção é mais forte antes da Copa?
- Qual é a chance de cada seleção passar de grupo?
- Qual é a chance de chegar às oitavas, quartas, semifinal, final e título?
- Qual é a probabilidade de vitória, empate e derrota em cada jogo?
- Qual é o placar mais provável?
- A seleção jogou melhor ou pior do que o esperado?
- Como a força muda após a fase de grupos e durante o mata-mata?

O projeto combina rating próprio, ajuste de elenco, calibração leve por odds, decomposição ataque/defesa, modelo de gols esperados, simulação Monte Carlo e validação probabilística.

---

## Ideia central

A métrica principal do sistema é o **TSI — Team Strength Index**.

```text
TSI = força geral da seleção
escala: 0.000 a 20.000
```

Interpretação aproximada:

```text
7.000–8.000   ≈ seleções mais fracas da Copa
14.000–16.000 ≈ seleções mais fortes da Copa
16.000+       ≈ seleção histórica/absurda
20.000        ≈ teto praticamente impossível
```

O TSI não é uma cópia do Ranking FIFA, do Elo ou das odds. Ele é uma força própria construída em etapas.

---

## Pipeline geral

```text
Pontos FIFA
→ Elo inicial
→ Elo próprio do ciclo da Copa 2026
→ Elo ajustado por recência
→ TSI_base
→ ajuste_elenco
→ TSI_modelo
→ ajuste_odds
→ TSI_pré-Copa
→ Ataque / Defesa
→ λ por confronto
→ simulação da Copa
→ Performance Grupo
→ TSI pós-grupos
```

Em termos intuitivos:

1. O Ranking FIFA ajuda a dar um ponto de partida.
2. O Elo próprio mede o desempenho recente no ciclo da Copa.
3. O elenco corrige diferenças entre resultados passados e força atual dos convocados.
4. As odds puxam levemente o modelo na direção do mercado, sem copiar o mercado.
5. O TSI final vira a força geral da seleção.
6. O TSI é dividido em Ataque e Defesa.
7. Ataque e Defesa viram gols esperados.
8. Gols esperados alimentam Poisson e Monte Carlo.
9. A simulação gera probabilidades por jogo e por fase.
10. Depois dos grupos, o desempenho real atualiza a força.

---

## Escopo de dados

O escopo histórico foi simplificado para o **ciclo da Copa 2026**.

```text
Ciclo Copa 2026 = após a Copa 2022 até antes da Copa 2026
```

Entram prioritariamente:

- Eliminatórias da Copa 2026;
- Copas continentais;
- Nations League e competições oficiais similares;
- playoffs;
- amistosos, se disponíveis.

A ideia é medir a força da seleção no ciclo competitivo que leva à Copa 2026, e não reconstruir toda a história recente do futebol internacional.

---

## Como o TSI é construído

O TSI pré-Copa nasce em três etapas principais.

### 1. Elo próprio

O Elo é calculado jogo a jogo no ciclo da Copa 2026.

Ele considera:

- resultado real;
- resultado esperado;
- importância da partida;
- mando/campo neutro;
- margem de gols, limitada para evitar exageros;
- pênaltis como empate com pequeno bônus;
- ajuste final por recência.

O Ranking FIFA não entra diretamente no TSI. Ele serve apenas para inicializar o Elo.

### 2. Ajuste de elenco

O elenco corrige o que o histórico ainda não mostrou.

Exemplos:

- uma geração nova explodiu recentemente;
- o valor de mercado já captura parte do envelhecimento da seleção;
- o time tem muitos jogadores fortes em um setor e buracos em outro;
- o valor de mercado cru ainda precisa ser agregado sem deixar estrelas isoladas dominarem.

O projeto usa valor de mercado como âncora direta, com minutagem recente, nível de
clube/liga e balanço entre setores quando essas fontes estiverem disponíveis.

### 3. Ajuste de odds

As odds entram como calibração leve.

O mercado usado no ajuste pré-Copa é de longo prazo:

- passar da fase de grupos;
- campeão, para afinar o topo.

Odds jogo a jogo ficam reservadas para validação, evitando circularidade.

---

## Ataque, Defesa e Perfil

Depois de calcular o TSI, o projeto separa a força em dois componentes:

```text
Ataque = TSI + Perfil
Defesa = TSI − Perfil
```

O **Perfil** não mede força. Ele mede tendência de jogo:

```text
saldo de gols  → eixo de força  → TSI/Elo
total de gols  → eixo de perfil → Ataque/Defesa
```

Perfil positivo indica seleção mais associada a jogos abertos.  
Perfil negativo indica seleção mais associada a jogos travados.

Isso permite diferenciar dois times de força parecida:

- um forte e ofensivo;
- outro forte e defensivo.

---

## Gols esperados

Para cada confronto, Ataque e Defesa viram gols esperados.

```text
λ_A = base · exp(k · (Ataque_A − Defesa_B))
λ_B = base · exp(k · (Ataque_B − Defesa_A))
```

Onde:

```text
λ_A = gols esperados do time A em 90 minutos
λ_B = gols esperados do time B em 90 minutos
```

Parâmetros iniciais:

```text
base = 1.30
k    = 0.09
γ    = 0.15
δ    = 0.00
```

Também existe bônus de anfitrião para jogos disputados no país daquela seleção.

---

## Simulação da Copa

O B7 usa Poisson independente:

```text
gols_A ~ Poisson(λ_A)
gols_B ~ Poisson(λ_B)
```

Isso gera:

- probabilidade de vitória A;
- probabilidade de empate;
- probabilidade de vitória B;
- placar mais provável;
- gols esperados.

Na fase de grupos, o sistema simula:

```text
12 grupos de 4
classificam 1º e 2º de cada grupo
+ 8 melhores terceiros
→ Round of 32
```

No mata-mata:

1. simula os 90 minutos;
2. se empatar, simula prorrogação com λ proporcional a 30 minutos;
3. se continuar empatado, simula pênaltis com vantagem limitada pela diferença de TSI.

Volume de simulações:

```text
50.000  → dashboard rápido
200.000+ → resultado mais estável
```

---

## Atualização durante a Copa

O projeto roda em três momentos principais.

### 1. Pré-Copa

Calcula:

- Elo ajustado;
- TSI_base;
- ajuste de elenco;
- ajuste de odds;
- TSI_pré;
- Ataque e Defesa;
- probabilidades iniciais.

### 2. Após a fase de grupos

Calcula:

- desempenho real vs esperado;
- Performance Grupo;
- TSI pós-grupos;
- Perfil de grupos;
- Ataque e Defesa atualizados;
- probabilidades do mata-mata real.

A atualização do TSI é:

```text
TSI_pós = TSI_pré + 0.30 · ajuste_desempenho
```

Com limite:

```text
TSI_pós − TSI_pré ∈ [−2.000, +2.000]
```

### 3. Após cada jogo do mata-mata

O sistema atualiza ratings e re-simula o restante da competição.

Seleções eliminadas recebem probabilidade zero nas fases futuras.

---

## Desempenho por jogo

O B3 mede se uma seleção jogou melhor ou pior do que o esperado.

O esperado vem dos λ pré-jogo.

O real é separado em dois canais:

```text
PROCESSO  → como o time jogou
RESULTADO → o que o time conseguiu no placar/tabela
```

O processo usa xG, chances claras e métricas FotMob de território/duelos,
sempre em escala equivalente a gols/xG.

As métricas FotMob atualmente usadas são:

- touches in opposition box;
- opposition half passes;
- ground duels won e %;
- successful dribbles e %.

O resultado usa pontos reais menos pontos esperados.

A nota final é:

```text
desempenho_bruto = c_proc · surpresa_proc + c_res · surpresa_res
```

Com parâmetros iniciais:

```text
c_proc = 4.0
c_res  = 3.0
```

O sinal bruto é comprimido por soft cap e calibrado por partida para soma zero:

```text
delta_partida = 4.0 · tanh(desempenho_bruto / 4.0) − média_do_jogo
```

Se só houver placar, sem xG/stats de processo, o jogo entra como score-only:

```text
surpresa_proc = 0
```

Também há peso por qualidade da amostra:

- cartão vermelho e minuto da expulsão;
- rotação/poupança;
- necessidade competitiva.

---

## Validação e calibração

O B9 mede se o modelo está calibrado.

Ele valida:

- probabilidades de vitória/empate/derrota;
- gols esperados;
- distribuição de placares;
- empates e placares baixos;
- probabilidades por fase;
- comparação com odds jogo a jogo.

Métricas principais:

- Brier Score;
- Log Loss;
- Calibration Curve;
- Expected Calibration Error;
- log-likelihood do placar;
- erro dos gols esperados;
- comparação contra mercado.

A regra é evitar overfitting: o modelo só fica mais complexo se a validação mostrar ganho claro.

---

## Stack recomendada

Stack inicial recomendada:

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

Arquitetura geral:

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

Como a obtenção de dados históricos é o maior risco, o pipeline deve ter cache local obrigatório para respostas de API.

---

## Resultado esperado

O produto final deve permitir visualizar:

- ranking TSI;
- força ofensiva e defensiva;
- probabilidade por fase;
- probabilidade por jogo;
- gols esperados;
- placar mais provável;
- evolução da força durante a Copa;
- comparação entre seleções;
- diagnóstico de calibração.

---

## Filosofia do projeto

O Tactical Oracle não tenta prever futebol como se fosse determinístico.

Ele tenta estimar probabilidades bem calibradas.

A pergunta principal não é:

```text
quem vai ganhar?
```

A pergunta correta é:

```text
qual é a distribuição mais realista de resultados possíveis?
```

O sistema combina força histórica, qualidade atual do elenco, sinal do mercado, estilo de jogo, gols esperados e simulação para produzir essa distribuição.
