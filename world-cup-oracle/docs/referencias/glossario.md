# Glossário

Projeto: **World Cup Oracle**

---

## Ajuste de desempenho

Média ponderada das notas dos três jogos da fase de grupos.

```text
ajuste_desempenho =
Σ(delta_ponderado)
/
Σ(peso_jogo)
```

---

## Ajuste de elenco

Correção estrutural do TSI baseada nos convocados.

---

## Ajuste de odds

Correção leve do TSI baseada no mercado de longo prazo.

---

## Ataque

Componente derivado do TSI.

```text
Ataque = TSI + Perfil
```

---

## Brier Score

Métrica de qualidade de previsão probabilística.

```text
Brier =
Σ_k (p_k − y_k)^2
```

Quanto menor, melhor.

---

## Calibration Curve

Curva que compara probabilidade prevista com frequência real observada.

---

## Ciclo Copa 2026

Janela histórica do projeto.

```text
após Copa 2022 até antes da Copa 2026
```

---

## Clamp

Operação que limita um valor dentro de intervalo.

```text
clamp(x, min, max)
```

---

## Defesa

Componente derivado do TSI.

```text
Defesa = TSI − Perfil
```

---

## Desempenho bruto

Nota de uma seleção em uma partida.

```text
desempenho_bruto =
c_proc · surpresa_proc
+ c_res · surpresa_res
```

O valor bruto ainda passa por soft cap e centralização zero-sum por partida
antes de virar `delta_ponderado`.

---

## Devig

Remoção da margem da casa de apostas das odds.

---

## Dixon-Coles

Correção opcional do Poisson para empates e placares baixos.

---

## Elo ajustado

Elo final após ciclo da Copa e recência.

```text
Elo_ajustado =
Elo_base_final + ajuste_recência
```

---

## Elo inicial

Rating inicial derivado dos pontos FIFA.

```text
Elo_inicial =
1500 + 120 · z_score
```

---

## Fator de qualidade

Valor entre 0 e 1 que mede a confiabilidade dos dados de grupos para atualizar Perfil.

---

## Força de mercado

Sinal extraído das odds de longo prazo.

---

## GD_esp

Diferença de gols esperada.

```text
GD_esp = λ_self − λ_opp
```

---

## GD_proc

Diferença de processo observada.

```text
GD_proc = proc_of − proc_def
```

---

## Log Loss

Métrica que pune excesso de confiança.

```text
LogLoss =
− ln(probabilidade atribuída ao resultado que aconteceu)
```

---

## Logit

Transformação de probabilidade.

```text
logit(p) =
ln(p / (1 − p))
```

---

## λ

Gols esperados.

```text
λ_A =
base · exp(k · (Ataque_A − Defesa_B))
```

No B7, λ representa gols esperados nos 90 minutos.

---

## Monte Carlo

Simulação repetida milhares de vezes para estimar probabilidades.

---

## Perfil

Eixo de abertura/ofensividade da seleção.

```text
Perfil =
(Ataque − Defesa) / 2
```

Perfil não mede força. Força é TSI.

---

## Performance Grupo

TSI implícito gerado pelos três jogos de grupo.

```text
Performance Grupo =
TSI_pré + ajuste_desempenho
```

---

## Peso_jogo

Confiabilidade de uma partida.

```text
peso_jogo =
peso_vermelho · peso_rotacao · peso_necessidade
```

---

## Poisson

Distribuição usada para modelar gols.

```text
gols_A ~ Poisson(λ_A)
gols_B ~ Poisson(λ_B)
```

---

## Proc_of / Proc_def

Compostos ofensivo e defensivo em escala equivalente a xG/gols.

---

## Squad_score

Score agregado do elenco após correção de valor, setores e balanço.

---

## Surpresa_proc

```text
surpresa_proc =
GD_proc − GD_esp
```

---

## Surpresa_res

```text
surpresa_res =
pontos_reais − pts_esp
```

---

## TSI

Team Strength Index. Métrica central de força.

```text
TSI ∈ [0.000, 20.000]
```

---

## TSI_base

TSI derivado do Elo ajustado.

---

## TSI_modelo

TSI após ajuste de elenco.

```text
TSI_modelo =
TSI_base + ajuste_elenco
```

---

## TSI_pré

TSI final antes da Copa.

```text
TSI_pré =
TSI_modelo + ajuste_odds
```

---

## TSI_pós

TSI atualizado após fase de grupos.

```text
TSI_pós =
TSI_pré + 0.30 · ajuste_desempenho
```

---

## Valor efetivo

Valor de mercado ajustado para habilidade atual.

---

## Z-score

```text
z =
(x − média) / desvio_padrão
```
