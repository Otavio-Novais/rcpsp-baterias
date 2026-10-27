# =============================================================================
#  RCPSP - formulacao tempo-indexada (Pritsker et al., 1969)
#  Projeto: Otimizacao do Sequenciamento na Producao de Baterias
#  Notacao da Etapa 4: J = {1..n}, 1 e n atividades ficticias (inicio/fim).
#
#  Diferencas em relacao ao texto da Etapa 4 (ambas reduzem/fortalecem o
#  modelo sem mudar o conjunto de solucoes otimas):
#   - x[j,t] so existe na janela [ES[j], LS[j]] (CPM com horizonte H);
#   - precedencia DESAGREGADA por padrao (formul = "D"; Christofides et al.,
#     1987), com relaxacao linear mais forte. formul = "A" usa a versao
#     agregada da Etapa 4, restricao (3).
# =============================================================================

param n integer > 2;                         # numero de atividades (com as ficticias)
set J := 1..n;                               # atividades; n = fim do projeto
set K;                                       # recursos renovaveis

param p {J} integer >= 0;                    # duracao
param r {J, K} integer >= 0 default 0;       # demanda da atividade pelo recurso
param R {K} integer >= 0;                    # capacidade do recurso
set P {J} within J default {};               # predecessoras imediatas

param H integer >= 0;                        # horizonte (makespan de uma heuristica)
param ES {J} integer >= 0;                   # inicio mais cedo (CPM)
param LS {j in J} integer >= ES[j];          # inicio mais tarde (CPM com horizonte H)

param formul symbolic in {"D", "A"} default "D";

# x[j,t] = 1 se a atividade j comeca no periodo t
var x {j in J, t in ES[j]..LS[j]} binary;

# (1) makespan = instante de inicio da atividade ficticia final
minimize Makespan:
    sum {t in ES[n]..LS[n]} t * x[n,t];

# (2) cada atividade comeca exatamente uma vez
subject to InicioUnico {j in J}:
    sum {t in ES[j]..LS[j]} x[j,t] = 1;

# (3a) precedencia agregada (Etapa 4): S_j >= S_i + p_i
subject to PrecAgregada {j in J, i in P[j]: formul = "A"}:
    sum {t in ES[j]..LS[j]} t * x[j,t] >= sum {t in ES[i]..LS[i]} t * x[i,t] + p[i];

# (3b) precedencia desagregada: se j comecou ate t, i comecou ate t - p_i
subject to PrecDesagregada {j in J, i in P[j], t in ES[j]..LS[j]: formul = "D"}:
    sum {s in ES[j]..t} x[j,s] <= sum {s in ES[i]..min(LS[i], t - p[i])} x[i,s];

# (4) capacidade: atividades em execucao no periodo tau (iniciadas em [tau-p_j+1, tau])
subject to Capacidade {k in K, tau in 0..H-1}:
    sum {j in J, t in max(ES[j], tau - p[j] + 1)..min(LS[j], tau): r[j,k] > 0} r[j,k] * x[j,t] <= R[k];
