# rcpsp-baterias

Projeto da disciplina de Otimização Discreta: **Otimização do Sequenciamento de Atividades na Produção de Baterias para Veículos Elétricos — uma abordagem via RCPSP**.

Autores: Cristian Madeira, Otávio Novais, Thaís Melo.

O problema é resolvido de duas formas, aplicadas às mesmas instâncias da PSPLIB:

1. **Método exato:** modelo PLIM tempo-indexado (Pritsker et al., 1969), em AMPL + CPLEX/Gurobi *(a implementar em `ampl/`)*.
2. **Metaheurística:** **RKO — Random-Key Optimizer** (Chaves et al., 2025), com um decoder específico para o RCPSP.

## Estrutura

```
rko/                         framework RKO (C++), copiado de RKO-solver/RKO_Cpp_v1.0 (licença MIT)
  Program/Problem/Problem.h  <- ÚNICO arquivo específico do problema (RCPSP)
  Program/Problem/Problem_TSP_original.h.txt   arquivo original do TSP, só para referência
  Instances/RCPSP/j30/       480 instâncias J30 (.dzn) + j301_1.sm (formato original PSPLIB)
  Instances/RCPSP/j60/       480 instâncias J60 (.dzn)
  Instances/RCPSP/targets.txt  alvos de parada (ótimos de referência), gerado por tools/
  Results/                   saídas do RKO (não versionadas)
tools/
  psplib.py                  leitura .sm/.dzn, lower bounds, parâmetros do ProGen
  reference_cpsat.py         valores de referência via OR-Tools CP-SAT (validação)
  experiments.py             gera alvos e cenários; resume resultados (RPD)
results/
  reference_j30.csv          ótimos/limitantes de referência das 480 J30
  reference_j60.csv          idem para as 480 J60 (409 ótimos provados; 71 só com limitantes)
```

O restante do framework RKO **não foi alterado**: a implementação do RCPSP está toda em `Problem.h`.

## O decoder do RCPSP

O vetor de chaves tem **uma chave por atividade real** (n = 30 no J30). As atividades fictícias de início e fim são implícitas.

1. **Lista de prioridade:** a cada passo, entre as atividades elegíveis (todas as predecessoras já na lista), escolhe a de **menor chave**. O resultado é sempre uma ordenação topológica.
2. **SSGS:** cada atividade é programada no menor instante ≥ término das predecessoras em que há recurso suficiente durante toda a duração. Gera cronogramas ativos, sempre factíveis.
3. **FBI (opcional, ligado por padrão):** justificação dupla — passo para trás na rede invertida e passo para frente —, repetida enquanto o makespan melhora (Valls et al., 2005).

Opções de compilação (no topo de `Problem.h`, ou via `-D` no compilador):

| Macro | Padrão | Efeito |
|---|---|---|
| `RCPSP_FBI` | 1 | aplica forward-backward improvement no decoder |
| `RCPSP_FBI_MAXIT` | 5 | máximo de iterações de FBI por decodificação |
| `RCPSP_STOP_AT_TARGET` | 1 | encerra a execução ao atingir max(lower bound, alvo de `targets.txt`) |
| `RCPSP_TIEBREAK` | 0 | soma ao makespan um termo de desempate < 1 (soma normalizada dos términos) |

## Como compilar e rodar

Requisitos: `g++` com suporte a C++20 e OpenMP.

- **Linux / WSL:** `sudo apt install g++ make`
- **macOS:** o clang da Apple não traz OpenMP; use `brew install gcc` e compile com `make CCC=g++-14` (ajuste a versão).
- **Windows:** use o WSL, ou MinGW-w64 com OpenMP.

```bash
cd rko/Program
make rebuild
./runTest ../Instances/RCPSP/test-debug.csv 9 0 1     # RKO completo, modo debug (imprime na tela)
```

Argumentos: `./runTest <cenario.csv> <K> <T> <D>`

- `K`: metaheurística — 0 BRKGA, 1 SA, 2 GRASP, 3 ILS, 4 VNS, 5 PSO, 6 GA, 7 LNS, 8 BRKGA-CS, **9 RKO (todas em paralelo)**
- `T`: 0 = parâmetros fixos (`ParametersOffline.txt`), 1 = ajuste online por Q-Learning (`ParametersOnline.txt`)
- `D`: 1 = debug (tela, semente fixa), 0 = execução (arquivos em `Results/`, semente pelo relógio)

O cenário é um CSV com cabeçalho e uma linha por instância: `caminho relativo a Instances/`, `tempo máximo (s)`, `nº de execuções`. **O arquivo não pode terminar com quebra de linha**: o laço `while (!feof(...))` do `main.cpp` executaria a última instância duas vezes. O `tools/experiments.py scenario` já gera no formato certo.

Cenários prontos em `rko/Instances/RCPSP/`:

| Arquivo | Uso |
|---|---|
| `test-debug.csv` | teste rápido: `j301_1.sm` e a mesma instância em `.dzn` (2 s cada) |
| `valid-j30.csv` | validação: seleção de 10 instâncias, 5 s, 3 execuções |
| `exp-j30.csv` | proposta para o experimento final: seleção de 10 instâncias, 10 s, 10 execuções |

### Saídas (modo `D = 0`)

| Arquivo | Conteúdo |
|---|---|
| `Results/Results_<MH>.csv` | gerado pelo RKO: makespan de cada execução, melhor, média, tempos |
| `Results/Solutions_<MH>.txt` | melhor cronograma (instantes de início) e verificação de factibilidade |
| `Results/Stats_<MH>.csv` | **gerado pelo `Problem.h`**: por execução, `cmax`, `lb`, `alvo`, nº de cronogramas gerados, **cronogramas até o melhor**, tempo até o melhor e tempo total |

O `tools/experiments.py summary` também **confere a consistência** entre os três arquivos: makespan por execução em `Results_` vs `Stats_`, e melhor makespan vs cronograma salvo em `Solutions_`. Qualquer divergência aparece como `INCONSISTENTE` e invalida o resultado.

`schedules_to_best` permite comparar com a literatura, que usa orçamento em número de cronogramas (1.000 / 5.000 / 50.000), mesmo com o RKO parando por tempo.

## Fluxo de experimentos

```bash
# 1) referência (já gerada em results/; refazer só se necessário)
python3 tools/reference_cpsat.py rko/Instances/RCPSP/j30 --time 20 --out results/reference_j30.csv

# 2) alvos de parada
python3 tools/experiments.py targets results/reference_j30.csv results/reference_j60.csv

# 3) cenário (seleção de 10 instâncias J30, 10 s, 10 execuções)
python3 tools/experiments.py scenario --set selecao_j30 --time 10 --runs 10 --out rko/Instances/RCPSP/exp-j30.csv

# 4) rodar (a partir de rko/Program)
./runTest ../Instances/RCPSP/exp-j30.csv 9 0 0      # RKO
./runTest ../Instances/RCPSP/exp-j30.csv 0 0 0      # BRKGA

# 5) resumo com RPD
python3 tools/experiments.py summary --ref results/reference_j30.csv \
    --stats "rko/Results/Stats_*.csv" --out results/summary_j30.csv
```

`pip install ortools` é necessário apenas para o passo 1.

## Seleção de instâncias (J30)

`selecao_j30` (em `tools/experiments.py`) = `j301_1` (exemplo da Etapa 3) + 9 instâncias dos grupos mais difíceis do J30, uma por grupo: a de maior tempo de prova no CP-SAT entre as com ótimo provado.

| Instância | NC | RF | RS | Ótimo | LB trivial |
|---|---|---|---|---|---|
| j301_1 | 1,5 | 0,25 | 0,2 | 43 | 38 |
| j309_2 | 1,5 | 0,75 | 0,2 | 92 | 63 |
| j3013_1 | 1,5 | 1,00 | 0,2 | 58 | 48 |
| j3025_4 | 1,8 | 0,75 | 0,2 | 81 | 53 |
| j3029_8 | 1,8 | 1,00 | 0,2 | 80 | 65 |
| j3037_7 | 2,1 | 0,50 | 0,2 | 92 | 54 |
| j3041_10 | 2,1 | 0,75 | 0,2 | 99 | 67 |
| j3045_6 | 2,1 | 1,00 | 0,2 | 129 | 89 |
| j3014_2 | 1,5 | 1,00 | 0,5 | 53 | 46 |
| j3030_2 | 1,8 | 1,00 | 0,5 | 68 | 65 |

Justificativa: nas 120 instâncias com RS = 1,0, o ótimo coincide com o lower bound trivial (caminho crítico / recurso); com RS = 0,7, a diferença média por grupo fica entre 0,3 e 2,5 unidades. Nesses casos todos os métodos atingem o ótimo de imediato, sem contraste. Com RS = 0,2, a diferença média vai de 5 a 29 unidades. A diferença entre ótimo e LB trivial por grupo está em `results/reference_j30.csv`.

## Validação (feita em 2 núcleos, tempos apenas indicativos)

- **Parser:** `j301_1.sm` e `J30_1_1.dzn` produzem dados idênticos (C++ e Python); o LB de caminho crítico (38) bate com o `MPM-Time` do cabeçalho da PSPLIB.
- **Referência:** o CP-SAT provou o ótimo de 475 das 480 instâncias J30 e de 409 das 480 J60 em ≤ 20 s cada; os 10 ótimos do grupo 1 do J30 conferem com os valores publicados na PSPLIB. Nas 71 J60 sem prova, a diferença média entre o limitante superior e o inferior é de 17 unidades; para elas, usar como referência o melhor valor conhecido da PSPLIB (`j60hrs.sm`). O `targets.txt` só contém ótimos provados, então a parada por alvo nunca encerra uma execução num valor não ótimo.
- **Decoder:** em 120 execuções (RKO, BRKGA, ILS e GA × 10 instâncias × 3, 3 s cada), todos os cronogramas passaram na verificação de precedência e recurso, nenhum makespan ficou abaixo do ótimo, e o makespan reportado pelo RKO, o registrado pelo decoder e o da solução final salva coincidiram em todos os casos. Nesse hardware (2 núcleos), os quatro métodos empataram: ótimo em 19–21 das 30 execuções, RPD médio de 0,46% a 0,56%; as diferenças só devem aparecer com mais tempo/núcleos e no J60.
- **Variantes do decoder** (FBI e desempate, 3 instâncias difíceis × 3 execuções): resultado inconclusivo nessa escala. O FBI chega ao melhor com menos cronogramas, mas cada cronograma custa cerca de 3× mais. Vale repetir com 10 execuções na máquina final — é um resultado que pode entrar no artigo.
- **Custo fixo do framework:** a criação do pool inicial (20 soluções + busca local) consome cerca de 20 mil decodificações antes das metaheurísticas começarem, mesmo quando o alvo é atingido logo no início.

## Como o `Problem.h` interage com o framework

- **Melhor solução:** toda melhoria vista pelo decoder vira a `bestSolution` do RKO, com chaves e makespan coerentes. Sem isso, uma metaheurística podia avaliar uma solução melhor e ser interrompida (fim do tempo ou alvo) antes de registrá-la, e o RKO reportava um valor pior do que o melhor cronograma encontrado.
- **Pool:** o decoder **nunca** altera o pool de soluções. Uma versão anterior inseria a solução no pool ao atingir o alvo; isso reordenava o pool enquanto a busca local da criação do pool segurava uma referência a uma posição, deixando chaves e makespan trocados (corrigido).
- **Criação do pool:** roda fora da região paralela, e ao final o `main` faz `bestSolution = pool[0]`. Por isso, melhorias dessa fase ficam pendentes e são sincronizadas na primeira decodificação das metaheurísticas, onde também se aplica a parada por alvo.

## Cuidados metodológicos

- **Threads:** o RKO usa **9 threads** mesmo com uma só metaheurística (K < 9 roda 9 cópias dela, compartilhando o pool de soluções). Rodem todos os experimentos finais **na mesma máquina** e reportem CPU e nº de threads — inclusive as threads do CPLEX/Gurobi.
- **Sementes:** no modo `D = 0`, a semente vem do relógio, e o paralelismo torna as execuções não determinísticas. As "sementes fixas" da Etapa 4 não se aplicam ao RKO como está; reportem média, desvio-padrão e nº de execuções.
- **Parada por alvo:** com `RCPSP_STOP_AT_TARGET`, o "tempo até o melhor" passa a ser *tempo até o ótimo*. É um critério padrão (time-to-target), mas deve ser declarado no artigo.
- **Valores de referência:** `results/reference_*.csv` vêm do CP-SAT. Os ótimos `OPTIMAL` são provados; mesmo assim, conferir com `j30opt.sm` / `j60hrs.sm` da PSPLIB antes do artigo.
- **Nome das instâncias:** o "j30_17" da Etapa 3 é o arquivo `j301_1.sm` (`j30_17.bas` é o nome da base geradora). Usar `j301_1` no artigo.

## Créditos e licenças

- **RKO:** Chaves, A.A.; Resende, M.G.C.; Schuetz, M.J.A.; Brubaker, J.K.; Katzgraber, H.G.; Arruda, E.F.; Silva, R.M.A. *A Random-Key Optimizer for Combinatorial Optimization*. Journal of Heuristics, 31(4), 2025. Código: <https://github.com/RKO-solver/RKO_Cpp_v1.0> (MIT, ver `rko/LICENSE`).
- **Instâncias:** PSPLIB (Kolisch & Sprecher, 1997). Os arquivos `.dzn` vêm de <https://github.com/MiniZinc/minizinc-benchmarks> (MIT, ver `rko/Instances/RCPSP/LICENSE-minizinc-benchmarks`); `j301_1.sm` vem de <https://github.com/PyJobShop/PSPLIB> (MIT).
- **FBI:** Valls, V.; Ballestín, F.; Quintanilla, S. *Justification and RCPSP: A technique that pays*. EJOR, 165(2), 2005.
