// *******************************************************************
//  RCPSP (Resource-Constrained Project Scheduling Problem) para o RKO
//
//  Projeto: Otimizacao do Sequenciamento na Producao de Baterias (RCPSP)
//  Autores: Cristian Madeira, Otavio Novais, Thais Melo
//
//  Unico arquivo especifico do problema. O restante do framework RKO
//  (Chaves et al., 2025) permanece inalterado.
//
//  Vetor de chaves: uma chave por atividade REAL (n = J). As atividades
//  ficticias (inicio e fim) sao tratadas implicitamente.
//
//  Decoder:
//    1. Lista de prioridade: a cada passo escolhe, entre as atividades
//       elegiveis (todas as predecessoras ja na lista), a de MENOR chave.
//       Resultado: uma ordenacao topologica (sempre factivel).
//    2. SSGS (Serial Schedule Generation Scheme): cada atividade e
//       programada no menor instante >= fim das predecessoras em que ha
//       recurso suficiente durante toda a sua duracao.
//    3. (opcional) Forward-Backward Improvement / justificacao dupla
//       (Valls et al., 2005).
//
//  Formatos de instancia aceitos (detectados pela extensao):
//    .sm  -> formato original da PSPLIB (Kolisch & Sprecher, 1997)
//    .dzn -> formato MiniZinc (sem atividades ficticias)
// *******************************************************************
#ifndef _PROBLEM_H
#define _PROBLEM_H

#include "../Main/Data.h"
#include <fstream>
#include <sstream>
#include <string>
#include <queue>
#include <atomic>
#include <limits>
#include <omp.h>

// Global Variables
extern int n;                                       // size of the vector solution

// definida em MH/Method.h (incluido depois deste arquivo)
double get_time_in_seconds();

//------------------------------- CONFIGURACAO -----------------------------------

// 1 = aplica forward-backward improvement (justificacao dupla) no decoder
#ifndef RCPSP_FBI
#define RCPSP_FBI 1
#endif

// numero maximo de iteracoes de FBI por decodificacao (para quando nao melhora)
#ifndef RCPSP_FBI_MAXIT
#define RCPSP_FBI_MAXIT 5
#endif

// 1 = encerra a execucao quando o makespan atinge o alvo: max(lower bound,
//     valor do arquivo de alvos, se existir). Atingir o lower bound prova
//     otimalidade; atingir o alvo corresponde ao criterio "valor otimo
//     conhecido" da Etapa 4.
#ifndef RCPSP_STOP_AT_TARGET
#define RCPSP_STOP_AT_TARGET 1
#endif

// arquivo opcional com alvos (linhas "<instancia> <valor>"), relativo a Program/
#ifndef RCPSP_TARGET_FILE
#define RCPSP_TARGET_FILE "../Instances/RCPSP/targets.txt"
#endif

// 1 = adiciona ao makespan um termo de desempate < 1 (soma normalizada dos
//     instantes de termino). Ajuda a busca em platos; o makespan reportado
//     continua sendo floor(ofv).
#ifndef RCPSP_TIEBREAK
#define RCPSP_TIEBREAK 0
#endif

//---------------------- DADOS DA INSTANCIA (somente leitura no decoder) -----------

static int nAct = 0;                                 // J: atividades reais
static int nRes = 0;                                 // K: recursos renovaveis
static std::vector<int> cap;                         // R_k
static std::vector<int> dur;                         // p_j
static std::vector<std::vector<int>> req;            // r_jk
static std::vector<std::vector<int>> succ;           // sucessoras imediatas (reais)
static std::vector<std::vector<int>> pred;           // predecessoras imediatas (reais)
static std::vector<int> topoRank;                    // posicao numa ordem topologica fixa
static int horizonUB = 0;                            // soma das duracoes (horizonte trivial)
static int lbCPM = 0;                                // lower bound do caminho critico
static int lbRes = 0;                                // lower bound de recurso
static int lowerBound = 0;                           // max(lbCPM, lbRes)
static int stopTarget = 0;                           // alvo de parada

//---------------------- ESTATISTICAS POR EXECUCAO ---------------------------------

static std::atomic<long long> nEvals(0);             // cronogramas gerados (todas as threads)
static int runBestCmax = std::numeric_limits<int>::max(); // melhor makespan visto no decoder
static std::atomic<double> runBestOfv(std::numeric_limits<double>::infinity()); // melhor ofv visto no decoder
static TSol bestDec;                                 // melhor solucao vista no decoder (chaves + ofv)
static std::atomic<bool> pendingSync(false);         // melhor solucao da criacao do pool ainda nao sincronizada
static long long evalsToBest = 0;                    // cronogramas ate o melhor
static double timeToBest = 0.0;                      // tempo ate o melhor (s)
static double runStart = 0.0;                        // inicio da execucao corrente
static std::atomic<double> lastEvalTime(0.0);        // instante aproximado da ultima decodificacao

//----------------------------- FUNCOES AUXILIARES ---------------------------------

static void RcpspError(const std::string &msg)
{
    printf("\nERROR (RCPSP): %s\n", msg.c_str());
    exit(1);
}

// extrai todos os inteiros de um trecho de texto
static std::vector<int> ExtractInts(const std::string &txt)
{
    std::vector<int> v;
    int sign = 1, val = 0;
    bool in = false;
    for (char c : txt)
    {
        if (c >= '0' && c <= '9') { val = val * 10 + (c - '0'); in = true; }
        else
        {
            if (in) { v.push_back(sign * val); val = 0; in = false; sign = 1; }
            sign = (c == '-') ? -1 : 1;
        }
    }
    if (in) v.push_back(sign * val);
    return v;
}

// texto entre "<key> =" e o ';' seguinte (formato .dzn)
static std::string DznBlock(const std::string &all, const std::string &key)
{
    size_t pos = 0;
    while ((pos = all.find(key, pos)) != std::string::npos)
    {
        size_t eq = all.find_first_not_of(" \t\r\n", pos + key.size());
        bool startOk = (pos == 0) || !(isalnum((unsigned char)all[pos - 1]) || all[pos - 1] == '_');
        if (startOk && eq != std::string::npos && all[eq] == '=')
        {
            size_t end = all.find(';', eq);
            if (end == std::string::npos) RcpspError("bloco .dzn sem ';' para " + key);
            return all.substr(eq + 1, end - eq - 1);
        }
        pos += key.size();
    }
    RcpspError("chave nao encontrada no .dzn: " + key);
    return "";
}

static void ReadDzn(const std::string &path)
{
    std::ifstream f(path);
    if (!f) RcpspError("arquivo nao encontrado: " + path);
    std::stringstream ss; ss << f.rdbuf();
    std::string all = ss.str();

    nRes = ExtractInts(DznBlock(all, "n_res"))[0];
    nAct = ExtractInts(DznBlock(all, "n_tasks"))[0];
    cap  = ExtractInts(DznBlock(all, "rc"));
    dur  = ExtractInts(DznBlock(all, "d"));
    std::vector<int> rr = ExtractInts(DznBlock(all, "rr"));

    if ((int)cap.size() != nRes || (int)dur.size() != nAct || (int)rr.size() != nRes * nAct)
        RcpspError("dimensoes inconsistentes no .dzn: " + path);

    req.assign(nAct, std::vector<int>(nRes, 0));
    for (int k = 0; k < nRes; k++)
        for (int j = 0; j < nAct; j++)
            req[j][k] = rr[k * nAct + j];               // rr e [recurso, tarefa]

    // suc = [ {..}, {..}, ... ] : um conjunto (1-based) por tarefa
    std::string sucTxt = DznBlock(all, "suc");
    succ.assign(nAct, {});
    int j = 0;
    size_t p = 0;
    while ((p = sucTxt.find('{', p)) != std::string::npos)
    {
        size_t q = sucTxt.find('}', p);
        if (j >= nAct) RcpspError("conjuntos 'suc' demais no .dzn");
        for (int s : ExtractInts(sucTxt.substr(p + 1, q - p - 1)))
            succ[j].push_back(s - 1);
        j++;
        p = q + 1;
    }
    if (j != nAct) RcpspError("numero de conjuntos 'suc' diferente de n_tasks");
}

static void ReadSm(const std::string &path)
{
    std::ifstream f(path);
    if (!f) RcpspError("arquivo nao encontrado: " + path);
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(f, line)) lines.push_back(line);

    int nJobs = -1;
    nRes = -1;
    for (const auto &l : lines)
    {
        if (l.find("jobs (incl. supersource/sink") != std::string::npos)
            nJobs = ExtractInts(l.substr(l.find(':') + 1))[0];
        if (l.find("- renewable") != std::string::npos)
            nRes = ExtractInts(l.substr(l.find(':') + 1))[0];
    }
    if (nJobs < 3 || nRes < 1) RcpspError("cabecalho .sm invalido: " + path);

    nAct = nJobs - 2;                                   // remove fonte e sumidouro
    dur.assign(nAct, 0);
    req.assign(nAct, std::vector<int>(nRes, 0));
    succ.assign(nAct, {});
    cap.assign(nRes, 0);

    auto findLine = [&](const std::string &tag) -> int {
        for (int i = 0; i < (int)lines.size(); i++)
            if (lines[i].find(tag) != std::string::npos) return i;
        RcpspError("secao nao encontrada no .sm: " + tag);
        return -1;
    };

    // PRECEDENCE RELATIONS: jobnr #modes #successors successors...
    int i0 = findLine("PRECEDENCE RELATIONS:") + 2;
    for (int r = 0; r < nJobs; r++)
    {
        std::vector<int> v = ExtractInts(lines[i0 + r]);
        int job = v[0], ns = v[2];
        if ((int)v.size() < 3 + ns) RcpspError("linha de precedencia invalida no .sm");
        if (job == 1 || job == nJobs) continue;         // fonte/sumidouro
        for (int t = 0; t < ns; t++)
        {
            int s = v[3 + t];
            if (s != nJobs) succ[job - 2].push_back(s - 2);
        }
    }

    // REQUESTS/DURATIONS: jobnr mode duration r1..rK
    i0 = findLine("REQUESTS/DURATIONS:") + 3;
    for (int r = 0; r < nJobs; r++)
    {
        std::vector<int> v = ExtractInts(lines[i0 + r]);
        if ((int)v.size() < 3 + nRes) RcpspError("linha de demandas invalida no .sm");
        int job = v[0];
        if (job == 1 || job == nJobs) continue;
        dur[job - 2] = v[2];
        for (int k = 0; k < nRes; k++) req[job - 2][k] = v[3 + k];
    }

    // RESOURCEAVAILABILITIES
    i0 = findLine("RESOURCEAVAILABILITIES:") + 2;
    std::vector<int> v = ExtractInts(lines[i0]);
    if ((int)v.size() < nRes) RcpspError("disponibilidades invalidas no .sm");
    for (int k = 0; k < nRes; k++) cap[k] = v[k];
}

// pre-processamento: predecessoras, ordem topologica, horizonte e lower bounds
static void Preprocess()
{
    pred.assign(nAct, {});
    for (int j = 0; j < nAct; j++)
        for (int s : succ[j])
        {
            if (s < 0 || s >= nAct) RcpspError("sucessora fora do intervalo");
            pred[s].push_back(j);
        }

    for (int j = 0; j < nAct; j++)
    {
        if (dur[j] < 0) RcpspError("duracao negativa");
        for (int k = 0; k < nRes; k++)
            if (req[j][k] > cap[k]) RcpspError("demanda maior que a capacidade (instancia infactivel)");
    }

    // ordem topologica (Kahn) + caminho critico
    std::vector<int> indeg(nAct), es(nAct, 0), order;
    for (int j = 0; j < nAct; j++) indeg[j] = (int)pred[j].size();
    for (int j = 0; j < nAct; j++) if (indeg[j] == 0) order.push_back(j);
    for (int h = 0; h < (int)order.size(); h++)
    {
        int j = order[h];
        for (int s : succ[j])
        {
            es[s] = std::max(es[s], es[j] + dur[j]);
            if (--indeg[s] == 0) order.push_back(s);
        }
    }
    if ((int)order.size() != nAct) RcpspError("rede de precedencia com ciclo");

    topoRank.assign(nAct, 0);
    for (int h = 0; h < nAct; h++) topoRank[order[h]] = h;

    horizonUB = 0;
    lbCPM = 0;
    for (int j = 0; j < nAct; j++)
    {
        horizonUB += dur[j];
        lbCPM = std::max(lbCPM, es[j] + dur[j]);
    }

    lbRes = 0;
    for (int k = 0; k < nRes; k++)
    {
        long long work = 0;
        for (int j = 0; j < nAct; j++) work += (long long)dur[j] * req[j][k];
        lbRes = std::max(lbRes, (int)((work + cap[k] - 1) / cap[k]));
    }
    lowerBound = std::max(lbCPM, lbRes);
}

// procura o alvo da instancia no arquivo opcional de alvos
static int ReadTarget(const char *inst)
{
    std::ifstream f(RCPSP_TARGET_FILE);
    if (!f) return 0;
    std::string name, line;
    int val;
    while (std::getline(f, line))
    {
        std::istringstream is(line);
        if (!(is >> name >> val)) continue;
        if (name[0] == '#') continue;
        std::string a(inst), b(name);
        // aceita caminho completo ou apenas o nome do arquivo
        auto base = [](const std::string &s) { size_t p = s.find_last_of('/'); return p == std::string::npos ? s : s.substr(p + 1); };
        if (a == b || base(a) == base(b)) return val;
    }
    return 0;
}

/************************************************************************************
 SSGS generico.
   order : lista de prioridade (deve respeitar a rede P)
   P     : listas de "predecessoras" na direcao do escalonamento
           (pred no sentido direto; succ no sentido reverso)
   st    : instantes de inicio resultantes
   usage : buffer de uso de recursos (horizonUB+1) x K, reutilizado
   retorna o makespan
*************************************************************************************/
static int SSGS(const std::vector<int> &order, const std::vector<std::vector<int>> &P,
                std::vector<int> &st, std::vector<int> &usage)
{
    const int H = horizonUB + 1;
    usage.assign((size_t)H * nRes, 0);
    st.assign(nAct, 0);
    std::vector<char> done(nAct, 0);
    int cmax = 0;

    for (int j : order)
    {
        int t = 0;
        for (int i : P[j])
        {
            if (!done[i]) RcpspError("lista de prioridade viola a precedencia");
            t = std::max(t, st[i] + dur[i]);
        }

        // menor t >= ES_j com recurso suficiente em [t, t+p_j)
        const int pj = dur[j];
        bool ok = false;
        while (!ok)
        {
            ok = true;
            for (int tau = t; tau < t + pj && ok; tau++)
                for (int k = 0; k < nRes; k++)
                    if (usage[(size_t)tau * nRes + k] + req[j][k] > cap[k])
                    {
                        ok = false;
                        t = tau + 1;                    // salta para depois do conflito
                        break;
                    }
        }

        st[j] = t;
        done[j] = 1;
        for (int tau = t; tau < t + pj; tau++)
            for (int k = 0; k < nRes; k++)
                usage[(size_t)tau * nRes + k] += req[j][k];
        cmax = std::max(cmax, t + pj);
    }
    return cmax;
}

/************************************************************************************
 Forward-Backward Improvement (justificacao dupla, Valls et al., 2005).
 Recebe um cronograma factivel e devolve outro com makespan <= ao original.
*************************************************************************************/
static int FBI(std::vector<int> &st, int cmax, std::vector<int> &usage)
{
    std::vector<int> order(nAct), stB, stF;
    for (int it = 0; it < RCPSP_FBI_MAXIT; it++)
    {
        // passo para tras: ordem decrescente de termino, rede invertida
        for (int j = 0; j < nAct; j++) order[j] = j;
        std::sort(order.begin(), order.end(), [&](int a, int b) {
            int fa = st[a] + dur[a], fb = st[b] + dur[b];
            if (fa != fb) return fa > fb;
            return topoRank[a] > topoRank[b];
        });
        int cB = SSGS(order, succ, stB, usage);
        for (int j = 0; j < nAct; j++) stB[j] = cB - (stB[j] + dur[j]);   // volta ao tempo direto

        // passo para frente: ordem crescente de inicio
        for (int j = 0; j < nAct; j++) order[j] = j;
        std::sort(order.begin(), order.end(), [&](int a, int b) {
            if (stB[a] != stB[b]) return stB[a] < stB[b];
            return topoRank[a] < topoRank[b];
        });
        int cF = SSGS(order, pred, stF, usage);

        if (cF < cmax) { st = stF; cmax = cF; }
        else break;
    }
    return cmax;
}

// verifica precedencia e recursos de um cronograma (usado na impressao final)
static bool CheckSchedule(const std::vector<int> &st, int cmax)
{
    for (int j = 0; j < nAct; j++)
    {
        if (st[j] < 0 || st[j] + dur[j] > cmax) return false;
        for (int s : succ[j]) if (st[j] + dur[j] > st[s]) return false;
    }
    for (int t = 0; t < cmax; t++)
        for (int k = 0; k < nRes; k++)
        {
            int u = 0;
            for (int j = 0; j < nAct; j++)
                if (st[j] <= t && t < st[j] + dur[j]) u += req[j][k];
            if (u > cap[k]) return false;
        }
    return true;
}

// Atualiza SOMENTE bestSolution (chaves + ofv coerentes), se melhor.
// Nao mexer no pool aqui: UpdatePoolSolutions reordena o pool e, durante
// CretePoolSolutions, a busca local FareyLS segura uma referencia a pool[i]
// -> chaves e ofv ficariam trocados. Usa a mesma secao critica (sem nome) de
// UpdatePoolSolutions; o Decoder nunca e chamado de dentro dela (sem deadlock).
static void SetBestSolution(const TSol &s)
{
    #pragma omp critical
    {
        if (s.ofv < bestSolution.ofv)
        {
            bestSolution = s;
            best_time = start_time + timeToBest;
        }
    }
}

// repoe em bestSolution a melhor solucao vista na criacao do pool
static void SyncBestSolution()
{
    TSol tmp;
    bool doIt = false;
    #pragma omp critical(rcpsp_stats)
    {
        if (pendingSync.load())
        {
            tmp = bestDec;
            pendingSync.store(false);
            doIt = true;
        }
    }
    if (!doIt) return;
    SetBestSolution(tmp);
#if RCPSP_STOP_AT_TARGET
    if (runBestCmax <= stopTarget && !stop_execution.load())
    {
        lastEvalTime.store(get_time_in_seconds());
        stop_execution.store(true);
    }
#endif
}

//----------------------- IMPLEMENTATION OF FUNCTIONS  -------------------------------

/************************************************************************************
 Method: ReadData
 Description: read input data of the problem
*************************************************************************************/
void ReadData(char nameTable[])
{
    std::string path = std::string("../Instances/") + nameTable;
    std::string ext = path.substr(path.find_last_of('.') + 1);

    if (ext == "sm" || ext == "SM") ReadSm(path);
    else if (ext == "dzn") ReadDzn(path);
    else RcpspError("extensao nao suportada (use .sm ou .dzn): " + path);

    Preprocess();

    stopTarget = std::max(lowerBound, ReadTarget(nameTable));

    // estatisticas da execucao
    nEvals.store(0);
    runBestCmax = std::numeric_limits<int>::max();
    runBestOfv.store(std::numeric_limits<double>::infinity());
    pendingSync.store(false);
    bestDec.rk.clear();
    evalsToBest = 0;
    timeToBest = 0.0;
    runStart = start_time;
    lastEvalTime.store(start_time);

    if (debug && run == 0)
        printf("\n[RCPSP] J=%d K=%d horizonte=%d LB_CPM=%d LB_rec=%d alvo=%d",
               nAct, nRes, horizonUB, lbCPM, lbRes, stopTarget);

    n = nAct;
}

/************************************************************************************
 Method: Decoders
 Description: mapping the random-key solutions into problem solutions
*************************************************************************************/
double Decoder(TSol s)
{
    // 1. lista de prioridade: elegivel com menor chave (ordenacao topologica)
    std::vector<int> indeg(nAct), order;
    order.reserve(nAct);
    std::priority_queue<std::pair<double, int>, std::vector<std::pair<double, int>>,
                        std::greater<std::pair<double, int>>> elig;
    for (int j = 0; j < nAct; j++)
    {
        indeg[j] = (int)pred[j].size();
        if (indeg[j] == 0) elig.push({s.rk[j], j});
    }
    while (!elig.empty())
    {
        int j = elig.top().second;
        elig.pop();
        order.push_back(j);
        for (int q : succ[j])
            if (--indeg[q] == 0) elig.push({s.rk[q], q});
    }

    // 2. SSGS
    std::vector<int> st, usage;
    int cmax = SSGS(order, pred, st, usage);

    // 3. forward-backward improvement
#if RCPSP_FBI
    cmax = FBI(st, cmax, usage);
#endif

    double ofv = cmax;
#if RCPSP_TIEBREAK
    double sumF = 0.0;
    for (int j = 0; j < nAct; j++) sumF += st[j] + dur[j];
    ofv += 0.5 * sumF / ((double)nAct * (double)(horizonUB + 1));
#endif

    if (!print)
    {
        // estatisticas (cronogramas gerados e cronogramas ate o melhor)
        long long c = ++nEvals;
        if ((c & 255) == 0) lastEvalTime.store(get_time_in_seconds());

        // Fases do RKO: (1) criacao do pool, no thread principal, FORA da
        // regiao paralela; ao fim dela o main faz bestSolution = pool[0];
        // (2) metaheuristicas, DENTRO da regiao paralela.
        const bool inMH = omp_in_parallel();

        // primeira decodificacao da fase (2): repoe a melhor solucao vista
        // na fase (1), caso pool[0] nao seja ela, e aplica a parada por alvo
        if (inMH && pendingSync.load()) SyncBestSolution();

        // Toda melhoria vista pelo decoder vira a melhor solucao global.
        // Sem isso, uma metaheuristica pode avaliar uma solucao melhor e
        // ser interrompida (fim do tempo/alvo) antes de registra-la, e o RKO
        // reportaria um makespan pior do que o melhor cronograma encontrado.
        if (ofv < runBestOfv.load())
        {
            bool improved = false;
            s.ofv = ofv;
            #pragma omp critical(rcpsp_stats)
            {
                if (ofv < runBestOfv.load())
                {
                    runBestOfv.store(ofv);
                    runBestCmax = cmax;
                    evalsToBest = c;
                    timeToBest = get_time_in_seconds() - start_time;
                    bestDec = s;
                    improved = true;
                }
            }
            if (improved)
            {
                if (inMH) SetBestSolution(s);
                else pendingSync.store(true);
            }
        }

#if RCPSP_STOP_AT_TARGET
        // alvo atingido (solucao ja registrada acima): encerra a execucao.
        // Na fase (1) a parada fica para a sincronizacao, para nao perder
        // a solucao quando o main sobrescrever bestSolution.
        if (inMH && cmax <= stopTarget && !stop_execution.load())
        {
            lastEvalTime.store(get_time_in_seconds());
            stop_execution.store(true);
        }
#endif
    }
    else
    {
        bool feas = CheckSchedule(st, cmax);
        if (debug)
        {
            printf("\nCmax = %d (LB = %d) | cronograma %s", cmax, lowerBound, feas ? "FACTIVEL" : "INFACTIVEL");
            printf("\nInicio (atividades reais 1..%d): ", nAct);
            for (int j = 0; j < nAct; j++) printf("%d ", st[j]);
        }
        else
        {
            fprintf(arqSol, "Cmax=%d LB=%d %s | S=", cmax, lowerBound, feas ? "FACTIVEL" : "INFACTIVEL");
            for (int j = 0; j < nAct; j++) fprintf(arqSol, "%d ", st[j]);
        }
    }

    return ofv;
}

/************************************************************************************
 Method: FreeMemoryProblem
 Description: Free local memory allocate by Problem
 (antes de limpar, grava as estatisticas da execucao anterior, se houver)
*************************************************************************************/
void FreeMemoryProblem()
{
    if (nEvals.load() > 0 && nAct > 0)
    {
        double tTotal = lastEvalTime.load() - runStart;
        if (debug)
        {
            printf("\n[RCPSP] execucao %d: Cmax=%d LB=%d cronogramas=%lld ate_melhor=%lld t_melhor=%.3fs t_total=%.3fs",
                   run, runBestCmax, lowerBound, nEvals.load(), evalsToBest, timeToBest, tTotal);
        }
        else
        {
            char name[256] = "../Results/Stats_";
            strcat(name, nameMH);
            strcat(name, ".csv");
            FILE *f = fopen(name, "r");
            bool exists = (f != NULL);
            if (f) fclose(f);
            f = fopen(name, "a");
            if (f)
            {
                if (!exists)
                    fprintf(f, "instance,mh,run,cmax,lb,target,schedules,schedules_to_best,time_to_best,time_total\n");
                fprintf(f, "%s,%s,%d,%d,%d,%d,%lld,%lld,%.3f,%.3f\n", instance, nameMH, run,
                        runBestCmax, lowerBound, stopTarget, nEvals.load(), evalsToBest, timeToBest, tTotal);
                fclose(f);
            }
        }
        nEvals.store(0);
    }

    cap.clear(); dur.clear(); req.clear(); succ.clear(); pred.clear(); topoRank.clear();
}

#endif
