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

proc_of = composto ofensivo em escala equivalente a xG/gols
proc_def = composto defensivo em escala equivalente a xG/gols
GD_proc = proc_of − proc_def
surpresa_proc = GD_proc − GD_esp + actual_gd_influence · (gols_reais − gols_sofridos)

Resultado:

surpresa_res =
pontos_reais − pts_esp
Nota única do jogo
desempenho_bruto =
c_proc · surpresa_proc
+ c_res · surpresa_res

Parâmetros iniciais:

c_proc = 4.0
c_res  = 3.0
actual_gd_influence = 0.15

c_proc vem da aproximação:

d(GD)/d(ΔTSI) ≈ 2 · k · base

Na aproximação inicial do B3:

d(GD)/d(ΔTSI) ≈ 0.234 gols por ponto de TSI

Logo:

1 / 0.234 ≈ 4.0 pontos de TSI por gol de surpresa

c_res foi elevado para 3.0 para evitar que empates ou vitórias
claramente acima do esperado sejam anulados demais pelo processo.

Observação atual:

Para projeções futuras e mata-mata, o B4 usa a curva sublinear vigente:

d = TSI_A − TSI_B
V(d) = sign(d) * min(3.50, 1.25 * |d|^0.70)
k = 0.20

O B3 preserva a curva de base usada na auditoria dos jogos de grupo já avaliados para
evitar reescrever o esperado histórico quando uma curva futura é recalibrada.

Compressão e soma zero

O sinal bruto da partida é comprimido:

desempenho_comprimido =
4.0 · tanh(desempenho_bruto / 4.0)

Depois a média dos dois times no jogo é subtraída:

delta_partida =
desempenho_comprimido − média(desempenho_comprimido no jogo)

Assim, toda partida redistribui TSI entre os dois times:

Σ(delta_partida no jogo) = 0

Após aplicar peso de jogo, a mesma centralização é refeita para manter:

Σ(delta_partida_ponderado no jogo) = 0

Composto ofensivo
xG criado:            45%
chances claras:       25%
touches in opposition box: 10%
opposition half passes:   5%
ground duels:             7.5%
successful dribbles:      7.5%

Todas as métricas devem ser convertidas ou normalizadas para escala equivalente a xG/gols antes da combinação.

Fallback score-only

Se uma partida tem placar, mas não tem xG/stats de processo:

process_surprise = 0

Nesse caso o delta vem apenas de:

pontos_reais − pontos_esperados

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
Σ(delta_partida_ponderado)
/
Σ(peso_jogo)
Performance Grupo =
TSI_pré + ajuste_desempenho
