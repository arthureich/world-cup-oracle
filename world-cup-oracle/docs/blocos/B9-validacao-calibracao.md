B9 — Validação / Calibração
Objetivo

O B9 verifica se o modelo está bem calibrado.

as probabilidades estão corretas?
os gols esperados fazem sentido?
o modelo compete com o mercado?
onde o modelo erra sistematicamente?
Níveis de validação
1. probabilidades de jogo
2. gols esperados e placares
3. probabilidades de grupo/fase
4. ranking TSI
5. comparação contra odds jogo a jogo
Métricas de jogo
Brier Score
Log Loss
Calibration Curve
Expected Calibration Error
acurácia por faixa de confiança

Brier Score:

Brier =
Σ_k (p_k − y_k)^2

Log Loss:

LogLoss =
− ln(probabilidade atribuída ao resultado que aconteceu)
Métricas de gols
log-likelihood do placar
erro absoluto médio dos gols esperados
RMSE dos gols esperados
taxa prevista vs real de empates
frequência de 0-0, 1-0, 0-1, 1-1
distribuição de total de gols
calibração de over/under gols

Para placar real i x j:

LL_placar =
ln(P(gols_A = i | λ_A))
+
ln(P(gols_B = j | λ_B))
Odds jogo a jogo

Separação:

B6 usa odds de longo prazo
B9 usa odds jogo a jogo

Devig jogo a jogo:

prob_A_bruta = 1 / odd_A
prob_E_bruta = 1 / odd_empate
prob_B_bruta = 1 / odd_B
prob_A_justa =
prob_A_bruta / (prob_A_bruta + prob_E_bruta + prob_B_bruta)
prob_E_justa =
prob_E_bruta / (prob_A_bruta + prob_E_bruta + prob_B_bruta)
prob_B_justa =
prob_B_bruta / (prob_A_bruta + prob_E_bruta + prob_B_bruta)

Comparações:

Brier Score modelo vs mercado
Log Loss modelo vs mercado
diferença média de probabilidade
maiores divergências modelo-mercado
calibração modelo vs calibração mercado
Backtest

Usar torneios históricos quando houver dados:

Copas do Mundo anteriores
Eurocopas
Copas América
Copas continentais relevantes

Separar:

calibração
teste
Parâmetros calibráveis

B3:

c_proc
c_res
pesos do composto de processo
peso do cartão vermelho
peso de rotação
peso de necessidade competitiva

B4:

base
k
γ
δ
limite do Perfil
pesos dos índices O e D

B5:

curva_mercado por idade
curva_habilidade por idade
β do balanço por setor
λ_e do ajuste de elenco
cap do ajuste de elenco

B6:

peso de campeão vs passar de fase
método de devig
cap do ajuste de odds

B7:

Dixon-Coles ρ
redução de λ na prorrogação
c_pen dos pênaltis
número de simulações
Anti-overfitting
não calibrar todos os parâmetros ao mesmo tempo
não mudar parâmetro por ganho pequeno em apenas um torneio
preferir fórmulas simples e estáveis
calibrar em um conjunto e testar em outro
documentar todo ajuste
manter Poisson puro se Dixon-Coles não melhorar claramente
Diagnósticos
modelo superestima favoritos
modelo subestima zebras
modelo subestima empates
modelo gera poucos 0-0
modelo gera muitos jogos com 4+ gols
modelo reage demais à fase de grupos
modelo reage pouco ao desempenho recente
modelo dá muita chance de título para zebras
modelo copia demais o mercado
modelo diverge demais do mercado sem justificativa
