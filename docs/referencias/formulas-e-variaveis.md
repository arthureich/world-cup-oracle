# Fórmulas e Variáveis

Projeto: **World Cup Oracle**

Referência técnica central das fórmulas, variáveis e saídas do sistema.

---

## Pipeline geral

```text
Pontos FIFA
→ Elo inicial
→ Elo próprio do ciclo Copa 2026
→ Elo ajustado por recência
→ TSI_base
→ ajuste_calendário
→ ajuste_elenco
→ TSI_modelo
→ ajuste_odds
→ TSI_pré
→ Perfil / Ataque / Defesa
→ λ por confronto
→ Poisson / Monte Carlo
→ probabilidades
→ Performance Grupo
→ TSI_pós
```

---

## B0 — Dados

### Janela histórica

```text
Ciclo Copa 2026 =
após a Copa 2022 até antes da Copa 2026
```

### Placar

```text
goals_a / goals_b =
placar ao fim do jogo, incluindo prorrogação,
mas excluindo disputa de pênaltis
```

```text
penalty_winner =
seleção vencedora da disputa de pênaltis
```

### Campos mínimos

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

---

## B1 — TSI

```text
TSI ∈ [0.000, 20.000]
```

```text
TSI_base = mapear_0_20(Elo_ajustado)
```

No pipeline real com o universo FIFA completo, o mapeamento inicial usa a distribuição
dos Elos ajustados para evitar saturar o teto da escala:

```text
TSI_base =
clamp(
  10.0 + 2.25 · z(Elo_ajustado),
  0.000,
  20.000
)
```

Onde:

```text
z(Elo_ajustado) =
(Elo_ajustado − média_Elo_FIFA)
/
desvio_Elo_FIFA
```

O mapeamento linear 0–20 permanece como referência MVP e teste unitário simples, mas
os outputs reais usam o mapeamento por coorte FIFA.

```text
média_adversários =
média(Elo_ajustado dos adversários enfrentados no ciclo)
```

```text
baseline_contender =
média(média_adversários das seleções com TSI_base >= 13.000)
```

```text
ajuste_calendário =
clamp(
  0.250 · (média_adversários − baseline_contender) / 100,
  -0.350,
  +0.350
)
```

```text
TSI_modelo = TSI_base + ajuste_calendário + ajuste_elenco
```

```text
TSI_pré = TSI_modelo + ajuste_odds
```

Pós-grupos:

```text
Performance Grupo = TSI_pré + ajuste_desempenho
```

```text
TSI_pós =
70% TSI_pré
+ 30% Performance Grupo
```

Equivalente:

```text
TSI_pós = TSI_pré + 0.15 · ajuste_desempenho
```

Limite:

```text
TSI_pós − TSI_pré ∈ [−2.000, +2.000]
```

---

## B2 — Elo próprio

### Elo inicial

O z-score dos pontos FIFA usa todas as seleções FIFA.

```text
z_score =
(pontos_fifa − média_pontos_fifa)
/
desvio_padrão_pontos_fifa
```

```text
Elo_inicial =
1500 + 120 · z_score
```

```text
Elo_inicial ∈ [1100, 1900]
```

### Mando

```text
Elo_mandante_ajustado =
Elo_mandante + 50
```

### Resultado esperado

```text
E_A =
1 / (1 + 10 ^ ((Elo_B − Elo_A_ajustado) / 400))
```

```text
E_B = 1 − E_A
```

### Resultado real

```text
vitória = 1.0
empate  = 0.5
derrota = 0.0
```

Pênaltis:

```text
venceu nos pênaltis = 0.55
perdeu nos pênaltis = 0.45
```

### Atualização

```text
novo_Elo =
Elo_atual
+ K
· peso_importância
· multiplicador_margem
· (resultado_real − resultado_esperado)
```

```text
K = 25
```

### Pesos por importância

```text
Amistoso:                 0.50
Nations League / similar: 0.80
Eliminatórias:            1.00
Continental grupos:       1.20
Continental mata-mata:    1.50
Copa do Mundo grupos:     1.80
Copa do Mundo mata-mata:  2.20
```

### Margem de gols

Empate ou vitória por 1 gol:

```text
multiplicador_margem = 1.00
```

Vitórias por mais gols:

```text
g = diferença absoluta de gols
x = g − 1
```

```text
multiplicador_margem =
1 + 0.4 · (1 − exp(−(0.277·x + 0.006·x^2.97)))
```

Teto:

```text
multiplicador_margem máximo ≈ 1.400
```

### Recência

```text
delta_Elo_jogo =
K
· peso_importância
· multiplicador_margem
· (resultado_real − resultado_esperado)
```

```text
peso_recência =
0.5 ^ (meses_antes_da_copa / 24)
```

```text
media_recente =
Σ(delta_Elo_jogo · peso_recência)
/
Σ(peso_recência)
```

```text
fator_amostra =
min(1, Σ(peso_recência) / 8)
```

```text
ajuste_recência =
10 · media_recente · fator_amostra
```

```text
ajuste_recência ∈ [−80, +80] Elo
```

```text
Elo_ajustado =
Elo_base_final + ajuste_recência
```

---

## B3 — Desempenho por jogo

```text
GD_esp =
λ_self − λ_opp
```

```text
pts_esp =
pontos esperados via Poisson
```

Processo:

```text
proc_of =
composto ofensivo em escala equivalente a xG/gols
```

```text
proc_def =
composto defensivo em escala equivalente a xG/gols
```

```text
GD_proc =
proc_of − proc_def
```

```text
surpresa_proc =
GD_proc − GD_esp
```

Resultado:

```text
surpresa_res =
pontos_reais − pts_esp
```

Nota do jogo:

```text
desempenho_bruto =
c_proc · surpresa_proc
+ c_res · surpresa_res
```

```text
c_proc = 4.0
c_res  = 3.0
```

Compressão:

```text
desempenho_comprimido =
4.0 · tanh(desempenho_bruto / 4.0)
```

Calibração zero-sum por partida:

```text
delta_partida =
desempenho_comprimido
− média(desempenho_comprimido no jogo)
```

```text
Σ(delta_partida no jogo) = 0
```

Aplicação do peso e nova centralização:

```text
delta_ponderado_pre =
delta_partida · peso_jogo
```

```text
delta_ponderado =
delta_ponderado_pre
− média(delta_ponderado_pre no jogo)
```

```text
Σ(delta_ponderado no jogo) = 0
```

Fallback sem processo:

```text
se não houver xG/stats de processo:
surpresa_proc = 0
```

Peso do jogo:

```text
peso_jogo =
peso_vermelho
· peso_rotacao
· peso_necessidade
```

```text
peso_jogo mínimo = 0.15
```

```text
peso_vermelho =
1 − 0.5 · (minutos_em_desequilíbrio_numérico / 90)
```

Agregação:

```text
ajuste_desempenho =
Σ(delta_ponderado)
/
Σ(peso_jogo)
```

---

## B4 — Ataque e Defesa

```text
Ataque = TSI + Perfil
Defesa = TSI − Perfil
```

```text
TSI =
(Ataque + Defesa) / 2
```

```text
Perfil =
(Ataque − Defesa) / 2
```

Perfil pré-Copa:

```text
total_time =
GF_por_jogo + GA_por_jogo
```

```text
r =
total_time − média_total_das_48
```

```text
z =
padronizar(r) entre as 48 seleções
```

```text
Perfil_pré =
clamp(0.8 · z, −2.000, +2.000)
```

Perfil de grupos:

```text
Perfil_grupos =
clamp(0.8 · padronizar(O − D), −2.000, +2.000)
```

Blend:

```text
peso_grupos =
0.40 · fator_qualidade
```

```text
peso_pré =
1 − peso_grupos
```

```text
Perfil_final =
peso_pré · Perfil_pré
+ peso_grupos · Perfil_grupos
```

Gols esperados:

```text
d = TSI_A − TSI_B
V(d) = sign(d) · min(V_max, a · |d|^p)
```

```text
profile_signal =
w_perfil · (Perfil_A + Perfil_B)
```

```text
λ_A =
base · exp(k · (V(d) + profile_signal))
```

```text
λ_B =
base · exp(k · (−V(d) + profile_signal))
```

Parâmetros atuais para jogos futuros/pós-grupos:

```text
base = 1.30
k = 0.20
a = 1.25
p = 0.70
V_max = 3.50
w_perfil = 0.25
```

Anfitrião:

```text
λ_host =
base · exp(k · (Ataque_host − Defesa_opp) + γ)
```

```text
λ_opp =
base · exp(k · (Ataque_opp − Defesa_host) − δ)
```

Observação:

```text
O B3 usa probabilidades de base preservadas para auditoria dos jogos de grupo.
A curva sublinear atual é usada para projeções futuras e mata-mata.
```

---

## B5 — Elenco

```text
valor_efetivo =
valor_mercado · nível_clube
```

Base: valor de mercado escalado pelo nível do clube, sem correção por idade/minutagem/
liga no jogador. O valor do elenco é então escalado por um multiplicador coletivo de
idade:

```text
valor_seleção ←
valor_seleção · mult_idade_seleção(idade_média)
```

```text
mult_idade_seleção =
1 + clamp((idade_média − 26) / 5, 0, 1) · 1.3
```

Chega a 2.30 com idade média de 31 anos. É uniforme dentro do time, então não altera a
comparação de equilíbrio entre setores.

Antes de agregar:

```text
valor_agregado_jogador =
log(1 + valor_efetivo)
```

Setores:

```text
GOL
DEF
MEI
ATA
```

```text
z_setor =
padronizar valor do setor entre as 48 seleções
```

```text
media_z =
média dos z dos 4 setores
```

```text
déficit_crítico =
Σ_setor máx(0, limiar_crítico − z_setor)
```

```text
squad_score =
media_z − λ · déficit_crítico
```

Só setores abaixo de `limiar_crítico` (−1.0, ≈ 16% pior do torneio) são punidos, na
profundidade abaixo da linha. Sem setor crítico, `déficit_crítico = 0` e o score é o
talento total (`media_z`) — concentração não é penalizada.

```text
TSI_elenco_implícito =
padronizar squad_score
para média e desvio do TSI_base
```

```text
ajuste_elenco =
clamp(
  λ_e · (TSI_elenco_implícito − TSI_base),
  −1.000,
  +1.000
)
```

---

## B6 — Odds

Campeão:

```text
prob_bruta_i =
1 / odd_i
```

```text
prob_justa_i =
prob_bruta_i
/
Σ(prob_bruta das 48 seleções)
```

Passar de fase:

```text
prob_passar_bruta =
1 / odd_passar
```

```text
prob_nao_passar_bruta =
1 / odd_nao_passar
```

```text
prob_passar_justa =
prob_passar_bruta
/
(prob_passar_bruta + prob_nao_passar_bruta)
```

Força de mercado:

```text
força_base =
logit(prob_passar_de_fase)
```

```text
logit(p) =
ln(p / (1 − p))
```

```text
força_topo =
ln(prob_campeão_com_piso)
```

```text
força_mercado =
combinação(força_base, força_topo)
```

```text
TSI_mercado =
padronizar força_mercado
para média e desvio do TSI_modelo
```

```text
ajuste_odds =
clamp(
  TSI_mercado − TSI_modelo,
  −0.750,
  +0.750
)
```

---

## B7 — Simulação

```text
gols_A ~ Poisson(λ_A)
gols_B ~ Poisson(λ_B)
```

```text
P(vitória A) =
Σ P(i, j), para i > j
```

```text
P(empate) =
Σ P(i, j), para i = j
```

```text
P(vitória B) =
Σ P(i, j), para i < j
```

```text
pts_esp_A =
3 · P(vitória A)
+ 1 · P(empate)
```

```text
pts_esp_B =
3 · P(vitória B)
+ 1 · P(empate)
```

Prorrogação:

```text
λ_prorrogação_A =
λ_A / 3
```

```text
λ_prorrogação_B =
λ_B / 3
```

Pênaltis:

```text
P(A vence nos pênaltis) =
clamp(
  0.5 + c_pen · (TSI_A − TSI_B),
  0.40,
  0.60
)
```

---

## B9 — Validação

```text
Brier =
Σ_k (p_k − y_k)^2
```

```text
LogLoss =
− ln(probabilidade atribuída ao resultado que aconteceu)
```

Para placar real `i x j`:

```text
LL_placar =
ln(P(gols_A = i | λ_A))
+
ln(P(gols_B = j | λ_B))
```

Expected Calibration Error:

```text
ECE =
Σ_bins (n_bin / n_total) ·
|media_prob_prevista_bin − frequencia_observada_bin|
```

Comparação contra odds jogo a jogo:

```text
odds americanas/decimais
→ probabilidades implícitas
→ normalização para remover margem
→ Brier/Log Loss modelo vs mercado
```

---

## Variáveis principais

| Variável | Significado | Bloco |
|---|---|---|
| `pontos_fifa` | pontos FIFA usados para inicializar Elo | B0/B2 |
| `z_score` | padronização dos pontos FIFA | B2 |
| `Elo_inicial` | rating inicial da seleção | B2 |
| `Elo_base_final` | Elo após jogos do ciclo | B2 |
| `ajuste_recência` | ajuste final por forma recente | B2 |
| `Elo_ajustado` | Elo final pré-mapeamento | B2 |
| `TSI_base` | TSI derivado do Elo | B1 |
| `ajuste_calendário` | ajuste leve por força média dos adversários no ciclo | B1 |
| `ajuste_elenco` | ajuste estrutural por elenco | B5 |
| `TSI_modelo` | TSI após calendário e elenco | B1/B5 |
| `ajuste_odds` | ajuste leve de mercado | B6 |
| `TSI_pré` | TSI final antes da Copa | B1 |
| `Perfil` | eixo abertura/ofensividade | B4 |
| `Ataque` | TSI deslocado pelo Perfil | B4 |
| `Defesa` | TSI deslocado pelo Perfil | B4 |
| `λ_A`, `λ_B` | gols esperados no confronto | B4/B7 |
| `GD_esp` | diferença de gols esperada | B3 |
| `GD_proc` | diferença de processo | B3 |
| `desempenho_bruto` | nota pré-soft-cap do jogo | B3 |
| `delta_ponderado` | delta do jogo após soft cap, peso e soma zero | B3 |
| `peso_jogo` | confiabilidade do jogo | B3 |
| `ajuste_desempenho` | média ponderada dos jogos de grupo | B3 |
| `Performance Grupo` | TSI_pré + ajuste_desempenho | B3/B1 |
| `TSI_pós` | TSI atualizado pós-grupos | B1 |
| `valor_efetivo` | valor atual ajustado do jogador | B5 |
| `squad_score` | força agregada do elenco | B5 |
| `TSI_mercado` | força implícita nas odds | B6 |
