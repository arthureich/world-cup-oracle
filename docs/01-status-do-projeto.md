# Status do Projeto

## Projeto

**Nome:** World Cup Oracle  
**Tema:** modelo estatistico e simulador da Copa do Mundo 2026  
**Objetivo:** calcular forca das selecoes, probabilidades por jogo, probabilidades por
fase e atualizar o torneio conforme novos resultados entram.

---

## Status geral

O projeto ja tem um MVP local funcional:

- pipeline em Python;
- dados em Parquet;
- Elo proprio;
- TSI pre-Copa e TSI atual;
- ajuste de calendario, elenco e odds;
- ataque/defesa;
- gols esperados;
- Poisson para placares;
- simulacao de grupos e mata-mata;
- bracket projetado;
- dashboard Streamlit com bracket, proximas partidas/mata-mata e tabela geral das 48
  selecoes;
- atualizacao pos-partida;
- validacao com Brier, Log Loss, calibracao e likelihood de placar.

---

## Status dos blocos

| Bloco | Nome | Status |
|---|---|---|
| B0 | Dados | Implementado com dados locais/cache e normalizacao Parquet |
| B1 | TSI - Team Strength Index | Implementado e recalibravel |
| B2 | Elo proprio | Implementado |
| B3 | Desempenho por jogo | Implementado com processo, resultado, soft cap e pesos manuais |
| B4 | Ataque e Defesa | Implementado com transformacao sublinear do gap de TSI |
| B5 | Elenco | Implementado como ajuste estrutural com cap |
| B6 | Odds | Implementado para odds de longo prazo; odds jogo a jogo pendentes para validacao |
| B7 | Simulacao | Implementado para grupos, melhores terceiros e mata-mata |
| B8 | Produto final | MVP Streamlit implementado |
| B9 | Validacao / Calibracao | Implementado com relatorio local |
| B10 | Arquitetura | Implementado como MVP local analitico |

---

## Evidencia tecnica

Ultima bateria registrada:

```text
ruff check app src tests
All checks passed

pytest tests/test_tournament_projection.py tests/test_match_performance_pipeline.py -q
11 passed
```

Relatorio de validacao atual:

```text
docs/reports/validation-2026-07-12.md
```

Metricas registradas no ultimo run:

```text
partidas avaliadas na validacao 1X2: 72
partidas completadas no operacional: 100
jogos de mata-mata auditados: 28
Brier Score: 0.509684
Log Loss: 0.874943
Expected Calibration Error: 0.142348
```

Observacao:

```text
A comparacao contra odds jogo a jogo ainda fica como missing_odds_file enquanto
data/interim/odds_match_by_match.parquet nao existir.
```

---

## Comandos principais

Atualizar o pipeline depois de novas partidas locais/cacheadas:

```bash
python -m world_cup_oracle.pipeline.update_after_matches
```

Buscar novos dados FotMob/API e depois recalcular:

```bash
python -m world_cup_oracle.pipeline.update_after_matches --fetch-fotmob
```

Gerar relatorio de validacao:

```bash
python -m world_cup_oracle.pipeline.validation_report
```

Rodar testes:

```bash
pytest
```

---

## O que esta completo o suficiente

O nucleo estatistico esta pronto para iterar:

- calcular TSI;
- comparar selecoes;
- calcular xG por confronto;
- calcular vitoria/empate/derrota em 90 minutos;
- calcular avanco em mata-mata com prorrogacao e penaltis;
- simular o torneio;
- apresentar probabilidades por fase;
- apresentar a tabela geral das 48 selecoes com status, campanha, Elo, elenco, odds,
  delta de partidas, TSI atual e probabilidades por fase;
- auditar performance das partidas;
- atualizar dados ja jogados;
- validar probabilidades.

---

## Checkpoint de torneio

Atualizado em 2026-07-12, com todas as oitavas concluidas.

Semifinais atuais:

```text
France x Spain
Argentina x England
```

Top probabilidades de titulo no run atual:

```text
Spain 30.1%
France 28.1%
Argentina 24.2%
England 17.6%
```

O pipeline agora usa `team_current_strength.parquet` e `attack_defense_current.parquet`
para simular o restante do mata-mata com TSI atualizado iterativamente.

---

## Pendencias reais

As pendencias agora sao mais de produto, dados e calibracao fina do que de estrutura.

1. Coletar `odds_match_by_match.parquet` para comparar modelo vs mercado jogo a jogo.
2. Substituir entradas manuais por JSON bruto/cache quando houver fonte disponivel.
3. Continuar calibrando B3/B4/B7 conforme mais partidas reais entram.
4. Adicionar graficos de calibracao no dashboard.
5. Criar uma pagina de auditoria por partida no Streamlit.
6. Definir criterio formal para aceitar mudancas de parametro.
7. Melhorar layout e leitura do bracket em telas pequenas.

---

## Decisoes importantes mantidas

- O MVP continua local, analitico e simples.
- Dados ficam em Parquet.
- Poisson puro e o motor principal de placar.
- Dixon-Coles segue opcional.
- FIFA so inicializa Elo.
- Odds de longo prazo ajustam TSI com cap.
- Odds jogo a jogo sao validacao, nao insumo direto da previsao do proprio jogo.
- Penaltis ficam separados do placar.
- Anexo C dos melhores terceiros e dado carregado, nao inferido.
- Flags de rotacao/garantia de primeiro lugar sao manuais no MVP.


