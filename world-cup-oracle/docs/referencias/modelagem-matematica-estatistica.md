# Modelagem Matematica e Estatistica

Este documento detalha a parte quantitativa do World Cup Oracle: variaveis, formulas,
hipoteses, motivos das escolhas e pontos calibraveis.

---

## 1. Notacao geral

Para uma selecao `i`:

```text
F_i       pontos FIFA iniciais
E_i       Elo proprio
T_i       TSI
P_i       Perfil de jogo
A_i       Ataque
D_i       Defesa
lambda_i  gols esperados em 90 minutos
```

Para um confronto entre `i` e `j`:

```text
d_ij = T_i - T_j
```

---

## 2. Elo proprio do ciclo 2026

### Elo inicial

O ranking FIFA entra apenas como inicializador. Primeiro padronizamos os pontos FIFA:

```text
z_i = (F_i - media(F)) / desvio(F)
```

Depois:

```text
E_i,0 = clamp(1500 + 120 * z_i, 1100, 1900)
```

Motivo: os pontos FIFA ja contem informacao historica, mas o projeto quer um rating
proprio para o ciclo da Copa. Por isso FIFA so cria o estado inicial.

### Resultado esperado

Para o time A contra B:

```text
E_A* = E_A + mando
q_A = 1 / (1 + 10 ^ ((E_B - E_A*) / 400))
q_B = 1 - q_A
```

`mando = 50` Elo quando aplicavel.

### Resultado real

```text
vitoria = 1.00
empate = 0.50
derrota = 0.00
venceu nos penaltis = 0.55
perdeu nos penaltis = 0.45
```

Motivo: disputa de penaltis decide classificacao, mas nao deve valer como uma vitoria
normal no modelo de forca.

### Margem de gols

Para diferenca absoluta `g`:

```text
se g <= 1:
  M(g) = 1
se g > 1:
  x = g - 1
  M(g) = 1 + 0.4 * (1 - exp(-(0.277*x + 0.006*x^2.97)))
```

O multiplicador tem teto pratico perto de `1.4`.

Motivo: goleadas importam, mas uma goleada isolada nao pode explodir o rating.

### Atualizacao jogo a jogo

```text
E_A,t+1 = E_A,t + K * W * M(g) * (S_A - q_A)
```

Onde:

```text
K = 25
W = peso de importancia
S_A = resultado real
q_A = resultado esperado
```

Pesos:

```text
amistoso = 0.50
nations_league = 0.80
qualifier = 1.00
continental_group = 1.20
continental_knockout = 1.50
world_cup_group = 1.80
world_cup_knockout = 2.20
```

### Recencia

Cada delta de Elo recebe decaimento:

```text
w_rec = 0.5 ^ (meses_antes_da_copa / 24)
```

Media recente:

```text
media_recente = soma(delta_Elo_jogo * w_rec) / soma(w_rec)
```

Fator de amostra:

```text
f_amostra = min(1, soma(w_rec) / 8)
```

Ajuste:

```text
ajuste_recencia = clamp(10 * media_recente * f_amostra, -80, +80)
Elo_ajustado = Elo_base_final + ajuste_recencia
```

Motivo: forma recente importa, mas so com volume minimo de jogos.

---

## 3. TSI

### TSI_base

Nos outputs reais, o Elo ajustado e padronizado dentro do universo FIFA:

```text
zE_i = (Elo_ajustado_i - media(Elo_ajustado)) / desvio(Elo_ajustado)
TSI_base_i = clamp(10 + 2.25 * zE_i, 0, 20)
```

Motivo: evita que outliers encostem em 20 cedo demais e mantem uma escala interpretavel.

### Ajuste de calendario

Para cada selecao:

```text
opp_i = media(Elo_ajustado dos adversarios enfrentados)
baseline = media(opp_i das selecoes com TSI_base >= 13)
aj_cal_i = clamp(0.25 * (opp_i - baseline) / 100, -0.35, +0.35)
```

Motivo: jogar um ciclo muito fraco ou muito forte deixa rastro no Elo. Esse ajuste e
pequeno para nao substituir o proprio Elo.

### TSI_modelo e TSI_pre

```text
TSI_modelo_i = TSI_base_i + ajuste_calendario_i + ajuste_elenco_i
TSI_pre_i = TSI_modelo_i + ajuste_odds_i
```

Caps:

```text
ajuste_elenco em [-1.00, +1.00]
ajuste_odds em [-0.75, +0.75]
```

---

## 4. Elenco

Para cada jogador:

```text
valor_efetivo = market_value * nivel_clube
valor_agregado = log(1 + valor_efetivo)
```

O valor e somado por setor:

```text
GOL, DEF, MEI, ATA
```

Cada setor e padronizado contra as outras selecoes:

```text
z_setor = (valor_setor - media_setor) / desvio_setor
```

Score:

```text
media_z = media(z_GOL, z_DEF, z_MEI, z_ATA)
deficit_critico = soma(max(0, limiar_critico - z_setor))
squad_score = media_z - 0.50 * deficit_critico
```

Com:

```text
limiar_critico = -1.0
```

Depois:

```text
TSI_elenco_implicito = padronizar(squad_score para media/desvio do TSI_base)
ajuste_elenco = clamp(lambda_e * (TSI_elenco_implicito - TSI_base), -1, +1)
```

Motivo: elenco deve corrigir o historico, nao substituir todos os sinais de campo.

---

## 5. Odds de longo prazo

Odds de campeao:

```text
p_bruta_i = 1 / odd_i
p_justa_i = p_bruta_i / soma(p_bruta)
```

Odds binarias de passagem:

```text
p_passar = (1 / odd_passar) / ((1 / odd_passar) + (1 / odd_nao_passar))
```

Forca de mercado:

```text
forca_base = logit(p_passar)
forca_topo = ln(max(p_campeao, piso))
forca_mercado = combinacao(forca_base, forca_topo)
```

Depois:

```text
TSI_mercado = padronizar(forca_mercado para media/desvio do TSI_modelo)
ajuste_odds = clamp(TSI_mercado - TSI_modelo, -0.75, +0.75)
```

Motivo: mercado agrega informacao externa, mas o modelo nao deve virar copia das odds.

---

## 6. Ataque, Defesa e Perfil

Split reversivel:

```text
Ataque_i = T_i + P_i
Defesa_i = T_i - P_i
T_i = (Ataque_i + Defesa_i) / 2
P_i = (Ataque_i - Defesa_i) / 2
```

O perfil mede abertura, nao qualidade. Uma selecao pode ser forte e defensiva ou forte e
ofensiva.

Pre-Copa:

```text
total_i = gols_feitos_por_jogo_i + gols_sofridos_por_jogo_i
P_i = clamp(0.8 * z(total_i), -2, +2)
```

Pos-grupos, o perfil usa processo ofensivo/defensivo observado e faz blend com o perfil
pre-Copa.

---

## 7. Gols esperados

O modelo atual usa uma transformacao sublinear limitada no gap de TSI.

Gap bruto:

```text
d = T_A - T_B
```

Transformacao:

```text
V(d) = sign(d) * min(V_max, a * |d|^p)
```

Parametros:

```text
a = 1.25
p = 0.60
V_max = 3.00
k = 0.18
base_goals = 1.30
```

Sinal de perfil:

```text
profile_signal = 0.25 * (P_A + P_B)
```

Gols esperados:

```text
lambda_A = base_goals * exp(k * ( V(d) + profile_signal))
lambda_B = base_goals * exp(k * (-V(d) + profile_signal))
```

Com anfitriao:

```text
lambda_host = lambda_host * exp(gamma)
lambda_opp = lambda_opp * exp(-delta)
```

```text
gamma = 0.15
delta = 0.00
```

Motivo da curva sublinear:

- em jogos equilibrados, pequenas diferencas de TSI devem aparecer melhor na probabilidade;
- em jogos muito desiguais, o xG nao deve crescer sem controle;
- o cap `V_max` estabiliza extremos.

---

## 8. Poisson para placares

Para 90 minutos:

```text
G_A ~ Poisson(lambda_A)
G_B ~ Poisson(lambda_B)
```

Probabilidade de placar:

```text
P(G_A = x, G_B = y) = Pois(x; lambda_A) * Pois(y; lambda_B)
```

Resultado:

```text
P(vitoria A) = soma P(x,y), x > y
P(empate) = soma P(x,y), x = y
P(vitoria B) = soma P(x,y), x < y
```

Pontos esperados:

```text
EP_A = 3 * P(vitoria A) + P(empate)
EP_B = 3 * P(vitoria B) + P(empate)
```

---

## 9. Mata-mata

O avanco em mata-mata nao e igual a vencer em 90 minutos.

Fluxo:

```text
1. simula 90 minutos com Poisson
2. se empatar, simula prorrogacao
3. se continuar empatado, decide nos penaltis
```

Prorrogacao:

```text
lambda_ET_A = lambda_A / 3
lambda_ET_B = lambda_B / 3
```

Penaltis:

```text
P(A vence penaltis) =
clamp(0.5 + c_pen * (T_A - T_B), 0.40, 0.60)
```

```text
c_pen = 0.010
```

Motivo: o melhor time tem vantagem, mas disputa de penaltis continua altamente ruidosa.

---

## 10. Desempenho por jogo

Para atualizar TSI depois dos grupos, o modelo compara o que era esperado com o que
aconteceu.

Esperado:

```text
GD_esp = lambda_self - lambda_opp
pts_esp = pontos esperados via Poisson
```

Processo:

```text
proc_of = composto ofensivo em escala de xG
proc_def = composto defensivo em escala de xG
GD_proc = proc_of - proc_def
surpresa_proc = GD_proc - GD_esp
```

Resultado:

```text
surpresa_res = pontos_reais - pts_esp
```

Nota:

```text
desempenho_bruto =
4.0 * surpresa_proc + 3.0 * surpresa_res
```

Soft cap:

```text
desempenho_comprimido =
4.0 * tanh(desempenho_bruto / 4.0)
```

Soma zero por partida:

```text
delta_partida = desempenho_comprimido - media_do_jogo
```

Peso do jogo:

```text
peso_jogo = peso_vermelho * peso_rotacao * peso_necessidade
peso_jogo >= 0.15
```

Agregacao:

```text
ajuste_desempenho = soma(delta_ponderado) / soma(peso_jogo)
TSI_pos = TSI_pre + 0.30 * ajuste_desempenho
```

Cap:

```text
TSI_pos - TSI_pre em [-2, +2]
```

Motivo: xG/processo e resultado entram juntos. O processo reduz ruido, mas o placar e os
pontos tambem sao informacao real.

---

## 11. Simulacao Monte Carlo

Cada simulacao sorteia todos os jogos restantes:

```text
for s in 1..N:
  simular grupos
  aplicar criterios de desempate
  selecionar melhores terceiros
  aplicar Anexo C
  simular mata-mata
  acumular fases alcancadas
```

Probabilidade por fase:

```text
P(fase_i) = contagem_i / N
```

No dashboard, o bracket mais provavel e uma visualizacao deterministica baseada nas
probabilidades calculadas, nao uma promessa de que aquele e o unico caminho provavel.

---

## 12. Validacao

### Brier Score

Para uma partida com tres classes:

```text
Brier = soma_k (p_k - y_k)^2
```

Onde `y_k = 1` para o resultado real e `0` para os outros.

### Log Loss

```text
LogLoss = -ln(p_resultado_real)
```

Pune muito previsoes confiantes que erram.

### Log-likelihood do placar

Para placar real `x-y`:

```text
LL_score =
ln(Pois(x; lambda_A)) + ln(Pois(y; lambda_B))
```

Tambem e reportado:

```text
NLL_score = -LL_score
```

### Calibracao

O modelo cria bins de probabilidade por classe:

```text
bin 0: 0.0-0.1
bin 1: 0.1-0.2
...
bin 9: 0.9-1.0
```

Em cada bin:

```text
erro_bin = |media_prob_prevista - frequencia_observada|
```

Expected Calibration Error:

```text
ECE = media ponderada dos erros dos bins
```

### Odds jogo a jogo

Se `data/interim/odds_match_by_match.parquet` existir:

```text
odds -> probabilidades implicitas
normalizar para remover margem
comparar Brier e Log Loss do modelo contra mercado
```

---

## 13. Comandos operacionais

Atualizar depois de novas partidas:

```bash
python -m world_cup_oracle.pipeline.update_after_matches
```

Buscar novos detalhes via API/cache:

```bash
python -m world_cup_oracle.pipeline.update_after_matches --fetch-fotmob
```

Rodar validacao:

```bash
python -m world_cup_oracle.pipeline.validation_report
```

Rodar testes:

```bash
pytest
```

---

## 14. Hipoteses e limites

Hipoteses atuais:

- Poisson independente e o MVP;
- Dixon-Coles fica opcional;
- odds sao ajuste leve e validacao, nao verdade absoluta;
- TSI e atualizado por evidencia observada, com caps;
- penaltis sao tratados separadamente do placar;
- Anexo C e dado oficial carregado, nao regra inferida.

Limites atuais:

- xG depende da fonte escolhida;
- odds historicas gratuitas sao limitadas;
- rotacao e contexto competitivo ainda exigem flags manuais;
- calibracao fica melhor conforme mais partidas reais entram.
