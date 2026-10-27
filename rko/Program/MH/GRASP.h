#ifndef _GRASP_H
#define _GRASP_H

/************************************************************************************
 Method: LineSearch
 Description: Consider the line search in direction ei , where vector ei has zeros 
 in all components except the i-th, where it has value one. The objective function 
 is evaluated at points x + k·h·ei for k = 0,1,−1,2,−2,... such that li≤xi+k·h≤ui.
 Let k∗ the value of k that minimizes f(x+k·h·ei) subject to li ≤ xi +k·h ≤ ui
*************************************************************************************/
static void LineSearch(TSol s, float h, int i, double &bestZ, double &bestF)
{
    std::vector<double> rk;

    // encontrar a melhor solucao na linha
    bestZ = 0;
    bestF = INFINITY;

    // encontrar a melhor solucao na linha (partindo do ponto corrente)
    // bestZ = s.vec[i].rk;
    // bestF = s.ofv;

    // gerar k como sendo as possiveis random keys do gene i, k = rk_i * tau | tau = {0, 1, -1, 2, -2, ...}
    double tau = 0;
    rk.push_back(s.rk[i] + tau * h);
    for (int j=0; j<(int)(1.0/h)+1; j+=2){
        tau++;

        if (((s.rk[i] + tau * h) >= 0) && ((s.rk[i] + tau * h) < 1))
            rk.push_back(s.rk[i] + tau * h);

        if (((s.rk[i] + (-1*tau) * h) >= 0) && ((s.rk[i] + (-1*tau) * h) < 1))
            rk.push_back(s.rk[i] + (-1*tau) * h);
    }

    // (sample greedy) This method is similar to the greedy algorithm, but instead of selecting the best among all possible options, 
    // it only considers q < m possible insertions (chosen uniformly at random) in each iteration. The most profitable among those is selected. 
    int q = ceil(log2((int)(1.0/h))) + 1; 

    if (q > (int)rk.size())
        q = rk.size();

    // escolher um subconjunto com q rks para calcular o decoder
    std::shuffle(rk.begin(), rk.end(), std::mt19937(std::random_device()()));

    // calcular a qualidade da solucao s com a rk j
    for (int j=0; j<q; j++)
    {  
        if (stop_execution.load()) return;      
        
        s.rk[i] = rk[j];   
        s.ofv = Decoder(s);

        if (s.ofv < bestF){
            bestZ = s.rk[i];
            bestF = s.ofv;
        }
    }

    rk.clear();
}

/************************************************************************************
 Method: ConstrutiveGreedyRandomized
 Description: It takes as input a solution vector s. Initially, the procedure allows 
 all coordinates of s to change (i.e. they are called unfixed). In turn, a discrete 
 line search is performed in each unfixed coordinate direction i of s with the other 
 n − 1 coordinates of s held at their current values.
*************************************************************************************/
static void ConstrutiveGreedyRandomized(TSol &s, float h, float alpha)
{
    std::vector<int> UnFixed(n);                // armazena as random-keys ainda nao fixadas
    std::vector<int> chosenRK;                  // armazena as random-keys que serao pesquisadas no line search
    std::vector<int> RCL;                       // armazena as melhores solucoes candidatas
    std::vector<double> z(n);                   // armazena o melhor valor da random-key i
    std::vector<double> g(n,INFINITY);          // armazena o valor da fo com a random-key z_i

    double min, max;
    double betaMin = 0.3, 
           betaMax = 0.7;

    // inicializar os pontos do cromossomo que podem ser alterados
    for (int i = 0; i < n; i++) {
        UnFixed[i] = i;
    }

    // construir uma solucao por meio de perturbacoes na solucao corrente e escolha de uma das melhores
    double intensity = randomico(betaMin, betaMax);
    
    // while (!UnFixed.empty())
    for (int j=0; j<n*intensity; j++)
    {
        // criar uma lista de solucoes candidatas perturbando uma rk (ainda não 'fixada') da solucao corrente
        min = INFINITY;
        max = -INFINITY;

        // escolher o subconjunto de random keys que serao pesquisadas
        chosenRK.clear();
        int kMax = UnFixed.size() * 0.1;
        if (kMax < 2) 
            kMax = UnFixed.size();

        chosenRK = UnFixed;
        std::shuffle(chosenRK.begin(), chosenRK.end(), rng);
        chosenRK.resize(kMax);

        // line search
        z.clear();
        z.resize(n);
        g.clear();
        g.resize(n,INFINITY);

        for (int k=0; k<kMax; k++) 
        {
            int i = chosenRK[k];

            TSol sAux = s;
            
            // linear search
            LineSearch(sAux, h, i, z[i], g[i]);
        }

        for(int i=0; i<n; i++)
        {
            if (min > g[i])
                min = g[i];

            if (max < g[i] && g[i] != INFINITY)
                max = g[i];
        }

        // criar a RCL
        RCL.clear();
        double threshold = min + alpha * (max - min);

        for (int i=0; i<n; i++)
        { 
            if (g[i] <= threshold)
            {
                RCL.push_back(i);
            }
        }

        // selecionar aleatoriamente um dos melhores candidatos para continuar a construcao
        if (!RCL.empty()){
            int x = irandomico(0, (int)(RCL.size())-1);
            int kCurrent = RCL[x];  // indice da random key que sera fixado
            
            // atualizar a solucao corrente
            s.rk[kCurrent] = z[kCurrent];
            s.ofv = g[kCurrent];
            // printf("\tFoViz %d = %lf (%d, %lf)\n", j, s.ofv, k, z[k]);

            // retirar a rk k do conjunto UnFixed
            for (int i=0; i<(int)UnFixed.size(); i++)
            {
                if (UnFixed[i] == kCurrent) 
                {
                    UnFixed.erase(UnFixed.begin()+i);
                    break;
                }
            }
        }
    }

    // update the solution found in the constructive phase
    s.ofv = Decoder(s);
}

/************************************************************************************
 Method: GRASP
 Description: Metaheurist Greedy Randomized Adpative Search Procedura.
*************************************************************************************/
void GRASP(int method, int control)
{
    // GRASP parameters
    TSol s;                                     // current solution
    TSol sLine;                                 // constructive solution
    TSol sLineBest;                             // local search solution
    TSol sBest;                                 // best solution of GRASP

    float currentTime = 0;                      // computational time of the search process
    int improv = 0;                             // improvement flag
    
    double start_timeMH = get_time_in_seconds();// start computational time
    double end_timeMH = get_time_in_seconds();  // end computational time

    float alphaGrasp = 0.1;                     // greedy rate
    float h;                                    // grid dense
    float hs = 0;                               // start grid dense
    float he = 0;                               // end grid dense

    // Q-Learning parameters
    std::vector<TState> S;                      // finite state space
    int numPar = 0;                             // number of parameters
    int numStates = 0;                          // number of states
    int iCurr = 0;                              // current (initial) state
    double epsilon=0;                           // greed choice possibility
    double lf=0;                                // learning factor
    double df=0;                                // discount factor
    double R=0;                                 // reward
    std::vector <std::vector <TQ> > Q;          // Q-Table
    std::vector<int> ai;                        // actions
    float epsilon_max = 1.0;                    // maximum epsilon 
    float epsilon_min = 0.1;                    // minimum epsilon
    int Ti = 1;                                 // number of epochs performed
    int restartEpsilon = 1;                     // number of restart epsilon
    int st = 0;                                 // current state
    int at = 0;                                 // current action

    /*  h	    1/h	    log2(1/h)
    1.00000	1	    0.00
    0.50000	2	    1.00
    0.25000	4	    2.00
    0.12500	8	    3.00
    0.06250	16	    4.00
    0.03125	32	    5.00
    0.01563	64	    6.00
    0.00781	128	    7.00
    0.00391	256	    8.00
    0.00195	512	    9.00
    0.00098	1,024	10.00
    0.00049	2,048	11.00
    0.00024	4,096	12.00
    0.00012	8,192	13.00 */      

    // ** read file with parameter values
    numPar = 3;
    std::vector<std::vector<double>> parameters;
    parameters.resize(numPar);

    readParameters(method, control, parameters, numPar);

    // offline control
    if (control == 0){
        // define parameters of GRASP
        alphaGrasp = parameters[0][0];
        hs         = parameters[1][0];
        he         = parameters[2][0];
    }

    // online control
    else {
        if (control == 1){
            // create possible states of the Markov chain
            CreateStates(parameters, method, numStates, numPar, S);

            // number of restart epsilon
            restartEpsilon = 1;  

            // maximum epsilon  
            epsilon_max = 1.0;  

            // current state
            iCurr = irandomico(0,numStates-1);

            // define parameters of GRASP
            alphaGrasp = S[iCurr].par[0];
            hs = S[iCurr].par[1];
            he = S[iCurr].par[2];
        }
    }

    int iter = 0;

    // create an initial solution
    CreateInitialSolutions(s);
    s.ofv = Decoder(s);
    sBest = s;

    // run the search process until stop criterion (maxTime)
    while (currentTime < MAXTIME)
    {
        // Q-Learning 
        if (control == 1){
            // set Q-Learning parameters  
            SetQLParameter(currentTime, Ti, restartEpsilon, epsilon_max, epsilon_min, epsilon, lf, df); 

            // choose a action at for current state st
            at = ChooseAction(S, st, epsilon);

            // execute action at of st
            iCurr = S[st].Ai[at];

            // define the parameters according of the current state
            alphaGrasp = S[iCurr].par[0];  
            hs = S[iCurr].par[1];
            he = S[iCurr].par[2];         
        }

        h = hs;
        // noImprov = 0;
        while (h >= he)
        {
            if (stop_execution.load()) return; 

            iter++;

            // offline control
            if (control == 0){
                alphaGrasp = randomico(0.1, 0.9);
            }

            // construct a greedy randomized solution
            sLine = s;
            ConstrutiveGreedyRandomized(sLine, h, alphaGrasp);
            
            // apply local search in current solution
            sLineBest = sLine;
            RVND(sLineBest);

            // update the best solution found by GRASP
            if (sLineBest.ofv < sBest.ofv){
                sBest = sLineBest;
                improv = 1;

                // update the pool of solutions
                UpdatePoolSolutions(sLineBest, method);
            }
            // make grid more dense
            else{
                h = h/2;
            }

            // accept criterion
            if (sLineBest.ofv < s.ofv){
                s = sLineBest;
            }
            else{
                // Metropolis criterion
                if ( randomico(0.0,1.0) < (exp(-(sLineBest.ofv - s.ofv)/(1000 - 1000*(currentTime / MAXTIME)))) ){ 
                    s = sLineBest;
                }
            }

            // if (debug && method == 2) printf("\nIter: %d \t s': %lf \t s'best: %lf \t sBest: %lf", iter, sLine.ofv, sLineBest.ofv, sBest.ofv);

            // terminate the evolutionary process in MAXTIME
            end_timeMH = get_time_in_seconds();
            currentTime = end_timeMH - start_timeMH;
        } 

        // Q-Learning 
        if (control == 1){
            // The reward function is based on improvement of the current best fitness and binary reward
            if (improv){
                R = 1;
                improv = 0;
            }
            else{
                R = (sBest.ofv - sLineBest.ofv)/sLineBest.ofv;
            }

            // if (debug) printf("\t [%.4lf, %d, %d] \t [%.2lf, %lf, %lf]", R, st, at, alphaGrasp, hs, he);

            // index of the next state
            int st_1 = S[st].Ai[at];

            // Update the Q-Table value
            S[st].Qa[at] = S[st].Qa[at] + lf*(R + df*S[st_1].maxQ - S[st].Qa[at]); 

            if (S[st].Qa[at] > S[st].maxQ)
            {
                S[st].maxQ = S[st].Qa[at];
                S[st].maxA = at;
            }

            // Define the new current state st
            st = st_1;
        }

        // restart the current solution 
        CreateInitialSolutions(s); 

        // decode the new solution
        s.ofv = Decoder(s);

        // terminate the search process in MAXTIME
        end_timeMH = get_time_in_seconds();
        currentTime = end_timeMH - start_timeMH;
    }

    // print policy
    // if (debug and control == 1)
    //     PrintPolicy(S, st);
}

#endif