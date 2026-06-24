B2 — Elo próprio
Objetivo

O B2 calcula um Elo próprio para medir força histórica recente das seleções dentro do ciclo da Copa 2026.

Janela
Ciclo Copa 2026 =
pós-Copa 2022 até pré-Copa 2026
Elo inicial
Elo_inicial =
1500 + 120 · z_score(pontos_fifa)

Com limite:

Elo_inicial ∈ [1100, 1900]

O z-score usa todas as seleções FIFA.

Mando
Elo_mandante_ajustado =
Elo_mandante + 50

O bônus de mando entra apenas no cálculo do resultado esperado, não soma diretamente ao Elo.

Resultado esperado
E_A =
1 / (1 + 10 ^ ((Elo_B − Elo_A_ajustado) / 400))
E_B = 1 − E_A
Resultado real
vitória = 1.0
empate  = 0.5
derrota = 0.0

Pênaltis:

venceu nos pênaltis = 0.55
perdeu nos pênaltis = 0.45
Atualização
novo_Elo =
Elo_atual
+ K
· peso_importância
· multiplicador_margem
· (resultado_real − resultado_esperado)
K = 25
Pesos por importância
Amistoso:                 0.50
Nations League / similar: 0.80
Eliminatórias:            1.00
Continental grupos:       1.20
Continental mata-mata:    1.50
Copa do Mundo grupos:     1.80
Copa do Mundo mata-mata:  2.20
Margem de gols

Empate ou vitória por 1 gol:

multiplicador_margem = 1.00

Vitórias por mais gols:

g = diferença absoluta de gols
x = g − 1
multiplicador_margem =
1 + 0.4 · (1 − exp(−(0.277·x + 0.006·x^2.97)))

Teto assintótico:

multiplicador_margem máximo ≈ 1.400
Recência
delta_Elo_jogo =
K
· peso_importância
· multiplicador_margem
· (resultado_real − resultado_esperado)
peso_recência =
0.5 ^ (meses_antes_da_copa / 24)
media_recente =
Σ(delta_Elo_jogo · peso_recência)
/
Σ(peso_recência)
fator_amostra =
min(1, Σ(peso_recência) / 8)
ajuste_recência =
10 · media_recente · fator_amostra

Limite:

ajuste_recência ∈ [−80, +80] Elo
Elo_ajustado =
Elo_base_final + ajuste_recência
