B4 — Ataque e Defesa
Objetivo

O B4 separa o TSI em Ataque e Defesa e define a função de gols esperados.

Fórmula central
Ataque = TSI + Perfil
Defesa = TSI − Perfil

Reversível:

TSI =
(Ataque + Defesa) / 2
Perfil =
(Ataque − Defesa) / 2
O que o Perfil mede

O Perfil mede abertura/ofensividade, não força.

saldo de gols  → eixo de força  → TSI/Elo
total de gols  → eixo de perfil → B4

Perfil positivo indica tendência a jogos mais abertos.
Perfil negativo indica tendência a jogos mais travados.

Perfil pré-Copa

Usa jogos do ciclo da Copa 2026.

total_time =
GF_por_jogo + GA_por_jogo
r =
total_time − média_total_das_48
z =
padronizar(r) entre as 48 seleções
Perfil_pré =
clamp(0.8 · z, −2.000, +2.000)
Perfil de grupos
Perfil_grupos =
clamp(0.8 · padronizar(O − D), −2.000, +2.000)

Índice ofensivo O:

xG criado:            35%
chances claras:       20%
finalizações no alvo: 15%
gols feitos:          15%
finalizações:         10%
posse de bola:         5%

Índice defensivo D, onde D alto = concede pouco:

xG sofrido:                     ~40%
chances claras cedidas:         ~23%
finalizações no alvo sofridas:  ~17%
gols sofridos:                  ~17%
finalizações sofridas:           ~3%
Blend
peso_grupos =
0.40 · fator_qualidade
peso_pré =
1 − peso_grupos
Perfil_final =
peso_pré · Perfil_pré
+ peso_grupos · Perfil_grupos

Com amostra limpa:

Perfil_final =
60% Perfil_pré
+ 40% Perfil_grupos
Limite
Perfil ∈ [−2.000, +2.000]
Gols esperados
λ_A =
base · exp(k · (Ataque_A − Defesa_B))
λ_B =
base · exp(k · (Ataque_B − Defesa_A))

Parâmetros iniciais:

base = 1.30
k    = 0.09
γ    = 0.15
δ    = 0.00
Anfitrião
λ_host =
base · exp(k · (Ataque_host − Defesa_opp) + γ)
λ_opp =
base · exp(k · (Ataque_opp − Defesa_host) − δ)

Jogo neutro:

γ = 0
δ = 0
