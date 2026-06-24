B3 — Desempenho por jogo
Objetivo

O B3 transforma cada partida da Copa em uma nota de desempenho: a seleção jogou melhor ou pior do que o esperado?

Saídas:

Performance Grupo  → atualiza TSI pós-grupos
insumos de Perfil  → alimentam B4
Anti-circularidade

Durante a fase de grupos, o esperado usa apenas TSI/Perfil pré-Copa.

O TSI atualizado e o Perfil de grupos só passam a existir depois da terceira rodada.

Esperado antes do jogo

Vem do B4:

λ_self, λ_opp =
gols esperados a favor e contra
GD_esp =
λ_self − λ_opp
pts_esp =
pontos esperados via Poisson
Dois canais

Processo:

proc_of =
composto ofensivo em escala equivalente a xG/gols
proc_def =
composto defensivo em escala equivalente a xG/gols
GD_proc =
proc_of − proc_def
surpresa_proc =
GD_proc − GD_esp

Resultado:

surpresa_res =
pontos_reais − pts_esp
Nota única do jogo
desempenho_jogo =
c_proc · surpresa_proc
+ c_res · surpresa_res

Parâmetros iniciais:

c_proc = 4.0
c_res  = 1.0

c_proc vem da aproximação:

d(GD)/d(ΔTSI) ≈ 2 · k · base

Com k = 0.09 e base = 1.30:

2 · 0.09 · 1.30 ≈ 0.234 gols por ponto de TSI

Logo:

1 / 0.234 ≈ 4.0 pontos de TSI por gol de surpresa
Composto ofensivo
xG criado:            45%
chances claras:       25%
finalizações no alvo: 20%
finalizações:         10%

Todas as métricas devem ser convertidas ou normalizadas para escala equivalente a xG/gols antes da combinação.

Peso do jogo
peso_jogo =
peso_vermelho
· peso_rotacao
· peso_necessidade

Com piso:

peso_jogo mínimo = 0.15

Vermelho:

peso_vermelho =
1 − 0.5 · (minutos_em_desequilíbrio_numérico / 90)

Usa minutos de desequilíbrio numérico relevante, não apenas existência de cartão vermelho.

Rotação:

peso_rotacao =
força do XI escalado / força do XI provável

Aproximação:

XI cheio:        1.00
rotação pesada: ~0.40

Necessidade competitiva:

1.00 para jogo decisivo
menor para jogo irrelevante / time já classificado poupando
Agregação da fase de grupos
ajuste_desempenho =
Σ(peso_jogo · desempenho_jogo)
/
Σ(peso_jogo)
Performance Grupo =
TSI_pré + ajuste_desempenho
