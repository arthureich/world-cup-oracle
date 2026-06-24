B0 — Dados
Objetivo

O B0 define quais dados o projeto precisa para calcular força das seleções, gerar probabilidades por jogo, simular a Copa e validar o modelo.

O B0 não define fórmulas de força. Ele define entradas, fontes e regras de dados.

Escopo histórico

O escopo foi simplificado para o ciclo da Copa 2026.

Ciclo Copa 2026 =
após a Copa 2022 até antes da Copa 2026

Uso principal:

Elo próprio
Perfil pré-Copa
base histórica recente

Prioridade de dados:

Eliminatórias da Copa 2026
Copas continentais
Nations League / competições oficiais similares
playoffs
amistosos, se disponíveis

O modelo não tenta reconstruir toda a história recente do futebol internacional. Ele mede a força das seleções dentro do ciclo competitivo da Copa 2026.

Partidas históricas do ciclo

Campos necessários:

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
Definição de placar
goals_a / goals_b =
placar ao fim do jogo, incluindo prorrogação,
mas excluindo disputa de pênaltis
penalty_winner =
seleção vencedora da disputa de pênaltis

Isso evita que a margem de gols do Elo conte gols de shootout.

Pontos FIFA iniciais

Os pontos FIFA são usados apenas para inicializar o Elo.

O z-score dos pontos FIFA deve ser calculado sobre todas as seleções FIFA, não apenas sobre as 48 classificadas.

z_score =
(pontos_fifa − média_pontos_fifa)
/
desvio_padrão_pontos_fifa
Estatísticas da Copa 2026

Para a Copa 2026, os dados são mais completos porque alimentam o desempenho por jogo e o Perfil de grupos.

Estatísticas essenciais:

gols
gols sofridos
xG
xG sofrido
chutes
chutes sofridos
chutes no alvo
chutes no alvo sofridos
chances claras
chances claras cedidas
posse de bola
cartão vermelho
minuto do cartão vermelho

Importantes se disponíveis:

momentum / attacking momentum
escalação titular
substituições relevantes
rotação/poupança
necessidade competitiva do jogo

Baixa relevância, mas armazenáveis:

escanteios
cartões amarelos
faltas
impedimentos

Fora do escopo:

mapa de chutes
kickoff_time
rest_days
travel_distance
Regra de fonte única para xG

xG e estatísticas avançadas da Copa devem vir de uma única fonte.

Não misturar provedores diferentes, porque xG muda por metodologia e isso bagunça a calibração.

Dados específicos da Copa 2026

Necessários:

grupos
jogos
placares
classificação dos grupos
chaveamento
regras dos melhores terceiros
anfitriões
sede/estádio, se necessário
Anexo C do chaveamento dos terceiros
Frequência de atualização
1. TSI inicial pré-Copa
2. Atualização após fase de grupos
3. Atualização após cada jogo do mata-mata
