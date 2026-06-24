B6 — Odds
Objetivo

O B6 faz uma calibração leve de mercado.

B6 = calibração leve
não é copiar o mercado
Mercados usados
principal: passar da fase de grupos
afinação: campeão

Odds jogo a jogo ficam reservadas para o B9.

Devig — campeão

Mercado mutuamente exclusivo entre as 48 seleções.

prob_bruta_i =
1 / odd_i
prob_justa_i =
prob_bruta_i
/
Σ(prob_bruta das 48 seleções)
Devig — passar de fase

Mercado binário por seleção.

prob_passar_bruta =
1 / odd_passar
prob_nao_passar_bruta =
1 / odd_nao_passar
prob_passar_justa =
prob_passar_bruta
/
(prob_passar_bruta + prob_nao_passar_bruta)
Força de mercado

Base:

força_base =
logit(prob_passar_de_fase)

Onde:

logit(p) =
ln(p / (1 − p))

Topo:

força_topo =
ln(prob_campeão_com_piso)

Combinação:

força_mercado =
combinação(força_base, força_topo)

O peso exato entre campeão e passar de fase é recalibrável.

TSI de mercado
TSI_mercado =
padronizar força_mercado
para média e desvio do TSI_modelo
Ajuste de odds
ajuste_odds =
clamp(
  TSI_mercado − TSI_modelo,
  −0.750,
  +0.750
)
TSI_pré =
TSI_modelo + ajuste_odds
