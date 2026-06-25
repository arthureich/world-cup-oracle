# Status do Projeto

## Projeto

**Nome:** Tactical Oracle  
**Tema:** modelo estatístico e simulador da Copa do Mundo 2026  
**Objetivo:** calcular força das seleções, probabilidades por jogo e probabilidades de avanço por fase.

---

## Legenda de status

```text
Consolidado:
  definido o suficiente para implementação inicial,
  mas ainda pode ser recalibrado depois.

Em desenho:
  já tem direção e decisões iniciais,
  mas ainda falta consolidar metodologia completa.

A consolidar:
  ainda precisa de definição formal.

A explorar:
  ainda não foi detalhado.
```

---

## Status geral dos blocos

| Bloco | Nome | Status |
|---|---|---|
| B0 | Dados | Consolidado |
| B1 | TSI — Team Strength Index | Consolidado em arquitetura |
| B2 | Elo próprio | Consolidado em metodologia |
| B3 | Desempenho por jogo | Consolidado em fórmula inicial |
| B4 | Ataque e Defesa | Consolidado em modelagem inicial |
| B5 | Elenco | Consolidado em ajuste estrutural |
| B6 | Odds | Consolidado em calibração leve de mercado |
| B7 | Simulação | Consolidado em engine de simulação inicial |
| B8 | Produto final | A consolidar |
| B9 | Validação / Calibração | Consolidado em protocolo de validação/calibração |
| B10 | Arquitetura, Framework e Estrutura de Dados | Em desenho / stack recomendada |

---

## Resumo executivo

```text
Consolidados:
B0, B1, B2, B3, B4, B5, B6, B7, B9

Em desenho:
B10

A consolidar:
B8
```

O projeto já tem metodologia central suficiente para implementação inicial.

O principal ponto ainda não consolidado é o **B8 — Produto final**, que deve definir exatamente o que será exibido no dashboard/app final.

---

## Status de implementação

Atualizado após o primeiro MVP local em Python.

| Bloco | Implementação atual |
|---|---|
| B0 — Dados | Parcial: dataclasses/schemas, IO Parquet com Polars, datasets mockados em código e writer para Parquet |
| B1 — TSI | Implementado MVP: mapeamento linear Elo ajustado → 0–20, TSI_base, TSI_modelo, TSI_pré e TSI_pós-grupos |
| B2 — Elo próprio | Implementado MVP: Elo inicial por pontos FIFA, esperado, real, pesos, margem, pênaltis, atualização jogo a jogo e recência |
| B3 — Desempenho por jogo | Implementado MVP: pontos reais, surpresa de processo, surpresa de resultado, peso do jogo e agregação ponderada |
| B4 — Ataque e Defesa | Implementado MVP: split reversível, Perfil pré por total de gols e λ com suporte a anfitrião |
| B5 — Elenco | Implementado MVP: valor efetivo por jogador, agregação por setor, penalidade de balanço, TSI implícito e ajuste com cap |
| B6 — Odds | Implementado MVP: devig binário/3-way, odds de longo prazo por linhas e ajuste leve de mercado persistível |
| B7 — Simulação | Implementado MVP: Poisson 90 min, probabilidades, placar provável, pontos esperados, ranking de grupos, melhores terceiros, prorrogação e pênaltis |
| B8 — Produto final | Não implementado |
| B9 — Validação | Implementado MVP: Brier Score, Log Loss, calibration bins, ECE e log-likelihood de placar |
| B10 — Arquitetura | Implementado MVP local: pacote Python, pyproject, estrutura de pastas, testes, cache JSON, normalização mock, pipeline mockado e outputs Parquet processados |

### Evidência técnica

```text
pytest
PASS 42 tests

ruff check .
PASS

pipeline mockado, normalização e outputs Parquet
8 seleções, 12 jogos, probabilidades, tabelas interim e tabelas processadas geradas
```

Observação:

```text
Dependências locais instaladas via `pip install -e ".[dev]"`.
Mocks gravados em `data/raw/`, normalizados em `data/interim/` e outputs processados
gravados em `data/processed/`.
```

---

## Próximas pendências de implementação

Ordem sugerida:

1. Substituir mocks por dados reais do ciclo Copa 2026.
2. Carregar o Anexo C oficial completo como dado estático para chaveamento dos melhores terceiros.
3. Validar/calibrar B3, B5 e B6 com dados reais e backtests.
4. Conectar cache de API e normalização a fontes reais.
5. Consolidar B8 — dashboard/relatórios/exports.

---

# B0 — Dados

## Status

```text
Consolidado
```

## O que está definido

O projeto usará como histórico principal o **ciclo da Copa 2026**.

```text
Ciclo Copa 2026 = após a Copa 2022 até antes da Copa 2026
```

Prioridades:

```text
Eliminatórias da Copa 2026
Copas continentais
Nations League / competições oficiais similares
playoffs
amistosos, se disponíveis
```

Para o histórico, os dados necessários são simples:

```text
match_id
date
team_a
team_b
goals_a
goals_b
competition
stage
match_type
home_team
neutral_site
went_to_penalties
penalty_winner
```

A definição de placar está consolidada:

```text
goals_a / goals_b = placar ao fim do jogo, incluindo prorrogação,
mas excluindo disputa de pênaltis
```

```text
penalty_winner = vencedor da disputa de pênaltis
```

Para a Copa 2026, serão usadas estatísticas completas:

```text
gols
xG
xG sofrido
chutes
chutes sofridos
chutes no alvo
chutes no alvo sofridos
chances claras
chances claras cedidas
posse
cartão vermelho
minuto do cartão vermelho
```

Também foi consolidado que xG e estatísticas avançadas da Copa devem vir de uma única fonte.

## Pendências

```text
definir fonte histórica/API
validar cobertura do ciclo da Copa 2026
escolher fonte única de xG/stats da Copa
obter Anexo C do chaveamento dos melhores terceiros
```

---

# B1 — TSI — Team Strength Index

## Status

```text
Consolidado em arquitetura
```

## O que está definido

O TSI mede a força geral da seleção.

```text
TSI ∈ [0.000, 20.000]
```

Fluxo consolidado:

```text
Pontos FIFA
→ Elo inicial
→ Elo próprio do ciclo da Copa 2026
→ Elo ajustado por recência
→ TSI_base
→ ajuste_elenco
→ TSI_modelo
→ ajuste_odds
→ TSI_pré
```

Fórmulas principais:

```text
TSI_base = mapear_0_20(Elo ajustado)
TSI_modelo = TSI_base + ajuste_elenco
TSI_pré = TSI_modelo + ajuste_odds
```

Atualização pós-grupos:

```text
Performance Grupo = TSI_pré + ajuste_desempenho
TSI_pós = 70% TSI_pré + 30% Performance Grupo
```

Equivalente:

```text
TSI_pós = TSI_pré + 0.30 · ajuste_desempenho
```

Limite:

```text
TSI_pós − TSI_pré ∈ [−2.000, +2.000]
```

## Pendências

```text
definir função exata de mapeamento Elo → escala 0–20
validar distribuição final das 48 seleções
```

---

# B2 — Elo próprio

## Status

```text
Consolidado em metodologia
```

## O que está definido

O Elo próprio mede força histórica recente no ciclo da Copa 2026.

Janela:

```text
pós-Copa 2022 até pré-Copa 2026
```

Elo inicial:

```text
Elo_inicial = 1500 + 120 · z_score(pontos_fifa)
```

Com limite:

```text
Elo_inicial ∈ [1100, 1900]
```

O z-score dos pontos FIFA usa todas as seleções FIFA.

Resultado esperado:

```text
E_A = 1 / (1 + 10 ^ ((Elo_B − Elo_A_ajustado) / 400))
```

Atualização:

```text
novo_Elo = Elo_atual
+ K · peso_importância · multiplicador_margem · (resultado_real − resultado_esperado)
```

Parâmetros:

```text
K = 25
mando = +50 Elo no cálculo do esperado
```

Pênaltis:

```text
venceu nos pênaltis = 0.55
perdeu nos pênaltis = 0.45
```

Recência:

```text
peso_recência = 0.5 ^ (meses_antes_da_copa / 24)
ajuste_recência = 10 · media_recente · fator_amostra
```

Limite:

```text
ajuste_recência ∈ [−80, +80] Elo
```

## Pendências

```text
validar cobertura dos jogos do ciclo
classificar corretamente importância das competições
identificar pênaltis e mando/campo neutro
```

---

# B3 — Desempenho por jogo

## Status

```text
Consolidado em fórmula inicial
```

## O que está definido

O B3 compara desempenho real vs esperado nos jogos da Copa.

Anti-circularidade:

```text
durante os grupos, o esperado usa TSI/Perfil pré-Copa
TSI e Perfil atualizados só existem após a terceira rodada
```

Esperado:

```text
GD_esp = λ_self − λ_opp
pts_esp = pontos esperados via Poisson
```

Dois canais:

```text
PROCESSO  → xG e métricas de desempenho
RESULTADO → pontos reais vs pontos esperados
```

Processo:

```text
GD_proc = proc_of − proc_def
surpresa_proc = GD_proc − GD_esp
```

Resultado:

```text
surpresa_res = pontos_reais − pts_esp
```

Nota:

```text
desempenho_jogo = c_proc · surpresa_proc + c_res · surpresa_res
```

Parâmetros:

```text
c_proc = 4.0
c_res = 1.0
```

Peso do jogo:

```text
peso_jogo = peso_vermelho · peso_rotacao · peso_necessidade
peso_jogo mínimo = 0.15
```

Agregação:

```text
ajuste_desempenho = Σ(peso_jogo · desempenho_jogo) / Σ(peso_jogo)
Performance Grupo = TSI_pré + ajuste_desempenho
```

## Pendências

```text
calibrar c_proc e c_res no B9
confirmar disponibilidade das estatísticas da Copa
operacionalizar rotação e necessidade competitiva
```

---

# B4 — Ataque e Defesa

## Status

```text
Consolidado em modelagem inicial
```

## O que está definido

O B4 separa TSI em Ataque e Defesa.

```text
Ataque = TSI + Perfil
Defesa = TSI − Perfil
```

Reversível:

```text
TSI = (Ataque + Defesa) / 2
Perfil = (Ataque − Defesa) / 2
```

O Perfil mede abertura/ofensividade, não força.

Perfil pré-Copa:

```text
total_time = GF_por_jogo + GA_por_jogo
r = total_time − média_total_das_48
z = padronizar(r) entre as 48 seleções
Perfil_pré = clamp(0.8 · z, −2.000, +2.000)
```

Perfil de grupos:

```text
Perfil_grupos = clamp(0.8 · padronizar(O − D), −2.000, +2.000)
```

Blend:

```text
peso_grupos = 0.40 · fator_qualidade
peso_pré = 1 − peso_grupos
Perfil_final = peso_pré · Perfil_pré + peso_grupos · Perfil_grupos
```

Gols esperados:

```text
λ_A = base · exp(k · (Ataque_A − Defesa_B))
λ_B = base · exp(k · (Ataque_B − Defesa_A))
```

Parâmetros:

```text
base = 1.30
k = 0.09
γ = 0.15
δ = 0.00
```

## Pendências

```text
calibrar base, k, γ e δ no B9
validar limite ±2.000 do Perfil
confirmar pesos dos índices O e D
```

---

# B5 — Elenco

## Status

```text
Consolidado em ajuste estrutural
```

## O que está definido

O B5 ajusta o TSI pela qualidade atual do elenco convocado.

Fontes:

```text
valor de mercado: Transfermarkt
minutagem / nível de clube: FotMob ou FBref
```

Escopo:

```text
somente os 26 convocados
roda após convocação
funcionamento automático
```

Valor do jogador:

```text
valor_efetivo = valor_mercado · nível_clube
valor_seleção ← valor_seleção · mult_idade_seleção(idade_média)
```

No MVP real, o valor de mercado é escalado pelo nível do clube; o valor da seleção é
então escalado por um multiplicador coletivo que cresce com a idade média (teto 2.30
aos 31). Sem correção de idade por jogador; o desequilíbrio é tratado no score por
setor.

Antes de agregar:

```text
valor_agregado_jogador = log(1 + valor_efetivo)
```

Setores:

```text
GOL, DEF, MEI, ATA
```

Score:

```text
déficit_crítico = Σ_setor máx(0, limiar_crítico − z_setor)
squad_score = media_z − λ · déficit_crítico
```

Parâmetros:

```text
limiar_crítico = −1.0
λ = 0.50
λ_e (encolhimento) = 0.35
cap ajuste_elenco = ±1.000
```

Ajuste:

```text
ajuste_elenco = clamp(
  λ_e · (TSI_elenco_implícito − TSI_base),
  −1.000,
  +1.000
)
```

## Pendências

```text
validar pesos por setor
calibrar limiar_crítico, λ e λ_e
```

---

# B6 — Odds

## Status

```text
Consolidado em calibração leve de mercado
```

## O que está definido

O B6 faz ajuste leve de mercado.

Mercados usados:

```text
principal: passar da fase de grupos
afinação: campeão
```

Odds jogo a jogo não entram no B6; ficam para o B9.

Devig campeão:

```text
prob_justa_i = prob_bruta_i / Σ(prob_bruta das 48 seleções)
```

Devig passar de fase:

```text
prob_passar_justa =
prob_passar_bruta /
(prob_passar_bruta + prob_nao_passar_bruta)
```

Força de mercado:

```text
força_base = logit(prob_passar_de_fase)
força_topo = ln(prob_campeão_com_piso)
força_mercado = combinação(força_base, força_topo)
```

TSI mercado:

```text
TSI_mercado = padronizar força_mercado para média/desvio do TSI_modelo
```

Ajuste:

```text
ajuste_odds = clamp(TSI_mercado − TSI_modelo, −0.750, +0.750)
TSI_pré = TSI_modelo + ajuste_odds
```

## Pendências

```text
definir fonte de odds
calibrar peso campeão vs passar de fase
avaliar método de devig alternativo se necessário
```

---

# B7 — Simulação

## Status

```text
Consolidado em engine de simulação inicial
```

## O que está definido

λ representa gols esperados nos 90 minutos.

```text
gols_A ~ Poisson(λ_A)
gols_B ~ Poisson(λ_B)
```

Probabilidades:

```text
P(vitória A) = Σ P(i, j), i > j
P(empate) = Σ P(i, j), i = j
P(vitória B) = Σ P(i, j), i < j
```

Pontos esperados:

```text
pts_esp_A = 3 · P(vitória A) + 1 · P(empate)
pts_esp_B = 3 · P(vitória B) + 1 · P(empate)
```

Formato:

```text
12 grupos de 4
top 2 de cada grupo
+ 8 melhores terceiros
→ Round of 32
```

Mata-mata:

```text
90 min: Poisson normal
prorrogação: λ/3 por lado
pênaltis: clamp(0.5 + c_pen · ΔTSI, 0.40, 0.60)
```

Parâmetro:

```text
c_pen = 0.010
```

Simulações:

```text
50.000 rápido
200.000+ estável
```

## Pendências

```text
obter Anexo C do chaveamento
validar critérios oficiais no código
calibrar pênaltis e possível Dixon-Coles no B9
```

---

# B8 — Produto final

## Status

```text
A consolidar
```

## O que falta definir

```text
dashboard final
páginas/telas
rankings exibidos
probabilidades por fase
simulador de confronto
comparador de seleções
relatórios
exports
atualização durante a Copa
experiência do usuário
```

---

# B9 — Validação / Calibração

## Status

```text
Consolidado em protocolo de validação/calibração
```

## O que está definido

Níveis de validação:

```text
probabilidades de jogo
gols esperados e placares
probabilidades de grupo/fase
ranking TSI
odds jogo a jogo
```

Métricas:

```text
Brier Score
Log Loss
Calibration Curve
Expected Calibration Error
log-likelihood do placar
erro dos gols esperados
taxa de empates
placares baixos
comparação contra mercado
```

Odds jogo a jogo:

```text
B6 usa odds de longo prazo
B9 usa odds jogo a jogo
```

Anti-overfitting:

```text
não calibrar tudo ao mesmo tempo
preferir versão simples se melhora pouco
calibrar em um conjunto e testar em outro
documentar mudanças
ativar Dixon-Coles só se necessário
```

## Pendências

```text
definir torneios de backtest
definir critérios mínimos para aceitar mudança de parâmetro
coletar odds jogo a jogo para validação
```

---

# B10 — Arquitetura, Framework e Estrutura de Dados

## Status

```text
Em desenho / stack recomendada
```

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

Arquitetura:

```text
Parquet raw data
↓
Polars / DuckDB normalization
↓
ratings pipeline
↓
simulation engine
↓
validation engine
↓
outputs Parquet
↓
Streamlit dashboard
```

## Decisão importante

Como API-Football grátis tem limite de 100 requests/dia, o pipeline precisa de cache local obrigatório.

```text
se já baixou uma resposta, não chama a API de novo
```

Estratégia de dados:

```text
base aberta histórica, se encontrada
+ API-Football para validação/gaps
+ correções manuais pontuais
+ Parquet final para o modelo
```

## Pendências

```text
formalizar estrutura de pastas
formalizar comandos do pipeline
formalizar esquema de tabelas
consolidar B10 como documentação técnica
```
