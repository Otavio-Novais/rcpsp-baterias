#ifndef _PSO_H
#define _PSO_H

/************************************************************************************
 Method: UpdatePopulationSize
 Description: update the size of the population according the current state
*************************************************************************************/
static void UpdateParticleSize(std::vector <TSol> &X, std::vector <TSol> &Pbest, std::vector <std::vector <float> > &V, TSol Gbest, int Psize,  
                              float c1, float c2, float w)
{
    // size of the current population
    int oldPsize = X.size();

    // pruning 
    if (oldPsize > Psize){
        X.resize(Psize);
        Pbest.resize(Psize);
        V.resize(Psize);
    }

    // generate new particles 
    else if (oldPsize < Psize){
        X.resize(Psize);
        Pbest.resize(Psize);
        V.resize(Psize, std::vector<float>(n));

        // Create the initial particles with random keys 
        for (int i=oldPsize; i<Psize; i++)
        {
            // initialize X[i]
            CreateInitialSolutions(X[i]); 

            // initialize Pbest
            Pbest[i] = X[i];    

            // initialize V[i][j]
            for (int j=0; j<n; j++)
                V[i][j] = randomico(0,1);

            for (int j=0; j<n; j++)
            {
                float r1 = randomico(0,1);
                float r2 = randomico(0,1);

                // update v[i][j] com fator de constricao
                V[i][j] = w * (V[i][j] + (c1 * r1 * (Pbest[i].rk[j] - X[i].rk[j])) + 
                                         (c2 * r2 * (Gbest.rk[j] - X[i].rk[j])));
                
                // update X[i][j]
                double oldrk = X[i].rk[j];
                X[i].rk[j] = X[i].rk[j] + V[i][j];  

                if (X[i].rk[j] < 0.0 || X[i].rk[j] >= 1.0) {
                    X[i].rk[j] = oldrk; 
                    V[i][j] = 0;
                }
            }

            // fitness of X[i]
            X[i].ofv = Decoder(X[i]);

            // update Pbest
            Pbest[i] = X[i];    
        }
    }
}

/************************************************************************************
 Method: PSO
 Description: search process of the Particle Swarm Optimization
*************************************************************************************/
void PSO(int method, int control)
{
    int Psize = 0;                           // number of particles
    float c1 = 0.0;
    float c2 = 0.0;
    float w = 0.0;

    std::vector <TSol> X;                    // current solutions
    std::vector <TSol> Pbest;                // best solutions 
    std::vector <std::vector <float> > V;    // particle velocity

    TSol Gbest;                              // global best solution
    double bestOFcurrent = 0;                // best ofv found in the current generation

    // local variables
    int numGenerations = 0;                  // number of generations
    float currentTime = 0;                   // computational time of the search process
    int bestGeneration = 0;                  // number of generation that found the best solution
    int improv = 0;                          // improvement flag

    double start_timeMH = get_time_in_seconds();    // start computational time
    double end_timeMH = get_time_in_seconds();      // end computational time

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

    // ** read file with parameter values
    numPar = 4;
    std::vector<std::vector<double>> parameters;
    parameters.resize(numPar);

    readParameters(method, control, parameters, numPar);

    // offline control
    if (control == 0){
        // define parameters of PSO (offline)
        Psize = parameters[0][0];
        c1    = parameters[1][0];
        c2    = parameters[2][0];
        w     = parameters[3][0];
    }

    // online control
    else{
        // Q-Learning 
        if (control == 1){
            // create possible states of the Markov chain
            CreateStates(parameters, method, numStates, numPar, S);

            // number of restart epsilon
            restartEpsilon = 1;  

            // maximum epsilon  
            epsilon_max = 1.0;  

            // current state
            iCurr = irandomico(0,numStates-1);

            // define parameters of PSO
            Psize = (int)S[iCurr].par[0];
            c1 = S[iCurr].par[1];
            c2 = S[iCurr].par[2];
            w  = S[iCurr].par[3];
        }
    }  

    // initialize population
    X.clear(); 
    Pbest.clear();
    V.clear(); 

    X.resize(Psize);
    Pbest.resize(Psize);
    V.resize(Psize, std::vector<float>(n));

    // Create the initial chromosomes with random keys 
    Gbest.ofv = INFINITY;
    for (int i=0; i<Psize; i++)
    {
        // initialize X[i]
        CreateInitialSolutions(X[i]); 

        // fitness of X[i]
        X[i].ofv = Decoder(X[i]);

        // initialize V[i][j]
        for (int j=0; j<n; j++)
            V[i][j] = randomico(0,1);

        // initialize Gbest
        if (X[i].ofv < Gbest.ofv)
            Gbest = X[i];

        // initialize Pbest
        Pbest[i] = X[i];    
    }
    
    // run the evolutionary process until stop criterion
    while (currentTime < MAXTIME)
    {
    	// number of generations
        numGenerations++;

        // define the parameters considering the current state and evolve a new iteration of the PSO
        // Q-Learning 
        if (control == 1){
            // set Q-Learning parameters  
            SetQLParameter(currentTime, Ti, restartEpsilon, epsilon_max, epsilon_min, epsilon, lf, df); 

            // choose a action at for current state st
            at = ChooseAction(S, st, epsilon);

            // execute action at of st
            iCurr = S[st].Ai[at];

            // define the parameters according of the current state
            Psize = (int)S[iCurr].par[0];
            c1 = S[iCurr].par[1];
            c2 = S[iCurr].par[2];
            w  = S[iCurr].par[3];         

            UpdateParticleSize(X, Pbest, V, Gbest, Psize, c1, c2, w);
        }

        // generate new population
        bestOFcurrent = INFINITY;
        double media = 0;
        for (int i=0; i<Psize; i++)
        {
            if (stop_execution.load()) return;      

            double probUpdate = 1.0; 

            // update particles X[i]
            for (int j=0; j<n; j++)
            {
                float r1 = randomico(0,1);
                float r2 = randomico(0,1);

                // update v[i][j] com fator de constricao
                V[i][j] = w * (V[i][j] + (c1 * r1 * (Pbest[i].rk[j] - X[i].rk[j])) + 
                                         (c2 * r2 * (Gbest.rk[j] - X[i].rk[j])));
                
                if (randomico(0,1) < probUpdate){
                    // update X[i][j]
                    double oldrk = X[i].rk[j];
                    X[i].rk[j] = X[i].rk[j] + V[i][j];  

                    if (X[i].rk[j] < 0.0 || X[i].rk[j] >= 1.0) {
                        X[i].rk[j] = oldrk; 
                        V[i][j] = 0;
                    }
                }
            }

            // fitness
            X[i].ofv = Decoder(X[i]);

            // set the best ofv found in this generation
            if (X[i].ofv < bestOFcurrent){
                bestOFcurrent = X[i].ofv;
            }

            // set Pbest
            if (X[i].ofv < Pbest[i].ofv){
                Pbest[i] = X[i];
            }

            // set Gbest 
            if (X[i].ofv < Gbest.ofv){
                Gbest = X[i];
                bestGeneration = numGenerations;    
                improv = 1;
            }

            media += X[i].ofv;
        } 

        // local search
        double oldGbest = Gbest.ofv;
        int chosen = irandomico(0,Psize-1);
        if (randomico(0,1)<0.95)
            NelderMeadSearch(Pbest[chosen]);
        else 
            RVND(Pbest[chosen]);

        if (Pbest[chosen].ofv < Gbest.ofv){
            Gbest = Pbest[chosen];
            bestGeneration = numGenerations; 
            improv = 1;   
        }

        // if (debug && method == 5) printf("\nGen: %d \t sBest: %lf \t media: %lf", numGenerations, Gbest.ofv, media/Psize);

        if (bestGeneration == numGenerations || Gbest.ofv < oldGbest){
            // update the pool of solutions
            UpdatePoolSolutions(Gbest, method);
        }

        // Q-Learning 
        if (control == 1){
            // The reward function is based on improvement of the current best fitness and binary reward
            if (improv){
                R = 1;
                improv = 0;
            }
            else{
                R = (Gbest.ofv - bestOFcurrent)/bestOFcurrent;
            }

            // if (debug) printf("\t [%.4lf, %d, %d] \t [%d]", R, st, at, Psize);

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


        // Reset
        if ((numGenerations - bestGeneration) > 1000) {
            X.clear(); 
            X.resize(Psize);

            Gbest.ofv = INFINITY;
            for (int i=0; i<Psize; i++){
                if (stop_execution.load()) return;      
                
                CreateInitialSolutions(X[i]);
                X[i].ofv = Decoder(X[i]);

                if (X[i].ofv < Gbest.ofv)
                    Gbest = X[i];

                Pbest[i] = X[i];
            }

            bestGeneration = numGenerations;
        }
        
        // terminate the evolutionary process in MAXTIME
        end_timeMH = get_time_in_seconds();
        currentTime = end_timeMH - start_timeMH;
    }

    // free memory of PSO components
    X.clear();
    V.clear();
    Pbest.clear();

    // print policy
    // if (debug and control == 1)
    //     PrintPolicy(S, st);
}

#endif