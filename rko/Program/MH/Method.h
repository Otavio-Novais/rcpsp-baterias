#ifndef _Method_H
#define _Method_H

/************************************************************************************
 Method: sortByFitness
 Description: Sort TSol by objective function
*************************************************************************************/
bool sortByFitness(const TSol &lhs, const TSol &rhs) { return lhs.ofv < rhs.ofv; }

/************************************************************************************
 Method: RANDOMICO
 Description: Generate a double random number between min and max => [min, max)
*************************************************************************************/
double randomico(double min, double max)
{
    return std::uniform_real_distribution<double>(min, max)(rng);
}

/************************************************************************************
 Method: IRANDOMICO
 Description: Generate a int random number between min and max => [min, max]
*************************************************************************************/
int irandomico(int min, int max)
{
    return (int)randomico(0,max-min+1) + min;
}

/************************************************************************************
 Method: get_time_in_seconds
 Description: measure time on Linux/macOS and Windows
*************************************************************************************/
double get_time_in_seconds() {
    #if defined(_WIN32) || defined(_WIN64)
        LARGE_INTEGER frequency, timeCur;
        QueryPerformanceFrequency(&frequency);
        QueryPerformanceCounter(&timeCur);
        return static_cast<double>(timeCur.QuadPart) / frequency.QuadPart;
    #else
        struct timespec timeCur;
        clock_gettime(CLOCK_MONOTONIC, &timeCur);
        return timeCur.tv_sec + timeCur.tv_nsec / 1e9;
    #endif
}

/************************************************************************************
 Method: TTT
 Description: Create the TTT file
*************************************************************************************/
void TTT(TSol s, int mh)
{
    // TTT plot
    if (s.ofv < 7542)  // target = 7542 TSP
    {
        char name[256]="../Results/TTT_";
        strcat(name,nameMH);
        strcat(name,".txt");
        FILE *tttFile;
        tttFile = fopen(name, "a");
        if (tttFile == NULL) {
            printf("Error opening the file %s.\n", "TTT.txt");
            return;
        }
        fprintf(tttFile, "%lf\n", best_time);
        fclose(tttFile);
        exit(1);
    }
}

/************************************************************************************
 Method: STN
 Description: Create the STN file
*************************************************************************************/
void STN(TSol s, int mh)
{
    char name[256]="../Results/STN_";
    strcat(name,nameMH);
    strcat(name,".txt");
    FILE *stnFile;
    stnFile = fopen(name, "a");
    if (stnFile == NULL) {
        printf("Error opening the file %s.\n", name);
        return;
    }
    fprintf(stnFile, "%d \t %.3lf \t ", run+1, s.ofv);
    for (int i = 0; i < n; i++)
    {
        if (i == n - 1)
            fprintf(stnFile, "%.3lf\n", s.rk[i]);
        else
            fprintf(stnFile, "%.3lf, ", s.rk[i]);
    }
    fclose(stnFile);
}

/************************************************************************************
 Method: updateBestSolution
 Description: Update the best solution found during the search process
*************************************************************************************/
void updateBestSolution(TSol s, int mh)
{
    // save the best solution found 
    if (s.ofv < bestSolution.ofv)
    {
        // update best solution found
        bestSolution = s;

        // update best time
        best_time = get_time_in_seconds();

        if (debug) {
            // get the current thread ID
            int thread_id = omp_get_thread_num();   
            printf("\nBest solution: %.2lf (MH: %d - Thread: %d)", s.ofv, mh, thread_id);
        }
        
        // STN plot
        // STN(s, mh);
    }
    // TTT plot
    // TTT(s, mh);
}

/************************************************************************************
 Method: CreateInitialSolutions
 Description: Create a initial random solution
*************************************************************************************/
void CreateInitialSolutions(TSol &s)
{
    s.rk.clear();
    s.rk.resize(n);

    // create a random-key solution
    for (int j = 0; j < n; j++){
        s.rk[j] = randomico(0,1);  // random value between [0,1)
    }

    s.flag = 0;
    s.label = 0;
    s.ofv = 0;
    s.promising = 0;
    s.similar = 0;
}

/************************************************************************************
 Method: ShakeSolution
 Description: shake the current solution
*************************************************************************************/
void ShakeSolution(TSol &s, float betaMin, float betaMax)
{
    int shaking_type = 0;
    int intensity = (int)(n * randomico(betaMin, betaMax)) + 1;
    if (intensity < 1) intensity = 1;
    for(int k = 0; k < intensity; k++) {
        shaking_type = irandomico(1,4);
        int i = irandomico(0, n-1);
        
        if(shaking_type == 1){
            // Change to random value
            s.rk[i] = randomico(0,1);
        }
        else
        if(shaking_type == 2){
            // Invert value
            if (s.rk[i] > 0.0001)
                s.rk[i] = 1.0 - s.rk[i];
            else
                s.rk[i] = 0.9999;
        }
        else 
        if (shaking_type == 3){
            // Swap two random positions
            int j = irandomico(0, n - 1);
            double temp = s.rk[i];
            s.rk[i] = s.rk[j];
            s.rk[j] = temp;
        }
        i = irandomico(0, n - 2);
        if(shaking_type == 4){
            // Swap with neighbor
            double temp = s.rk[i];
            s.rk[i]   = s.rk[i+1];
            s.rk[i+1] = temp;
        }
    }
}

/************************************************************************************
 Method: Blending
 Description: uniform crossover
*************************************************************************************/
TSol Blending(TSol &s1, TSol &s2, double factor)
{   
    TSol s;

    // create a new solution
    s.rk.resize(n);

    // Mate: including decoder gene in the n-th rk 
    for(int j = 0; j < n; j++)
    {
        // mutation
        if (randomico(0,1) < 0.02){
            s.rk[j] = randomico(0,1);
        }

        //copy alelos of top chromossom of the new generation
        else{
            if (randomico(0,1) < 0.5){
                s.rk[j] = s1.rk[j];
            }
            else{
                if (factor == -1){
                    s.rk[j] = 1.0 - s2.rk[j];
                    if (s.rk[j] == 1.0) s.rk[j] = 0.9999999;
                }
                else{
                    s.rk[j] = s2.rk[j];
                }
            }
        }
    }

    // set the flag of local search as zero
    s.flag = 0;
    return s;
}

/************************************************************************************
 Method: NelderMeadSearch
 Description: The Nelder–Mead method is a numerical method used to find the minimum 
 of an objective function in a multidimensional space. It is a direct search method 
 based on function comparison.
*************************************************************************************/
void NelderMeadSearch(TSol &x1)
{
    // elite points
    int k1, k2;
    do {
        k1 = irandomico(0,pool.size()-1);
        k2 = irandomico(0,pool.size()-1);
    }
    while (k1 == k2);

    // TSol x1 = x;
    TSol x2 = pool[k1];
    TSol x3 = pool[k2];

    // internal points
    TSol x_r;
    TSol x_e;
    TSol x_c;
    TSol x0;

    TSol xBest = x1;

    int iter_count = 0;
    int eval_count = 0;

    // sort points in the simplex so that x1 is the point having
    // minimum fx and x3 is the one having the maximum fx
    if (x1.ofv > x2.ofv) {
        TSol temp = x1;
        x1 = x2;
        x2 = temp;
    }

    if (x1.ofv > x3.ofv) {
        TSol temp = x1;
        x1 = x3;
        x3 = temp;
    }

    if (x2.ofv > x3.ofv) {
        TSol temp = x2;
        x2 = x3;
        x3 = temp;
    }
    
    // compute the simplex centroid
    x0 = Blending(x1, x2, 1);
    x0.ofv = Decoder(x0);
    if (x0.ofv < xBest.ofv) xBest = x0;

    iter_count++; 

    // continue minimization until stop conditions are met
    int maxIter = n*exp(-2);
    while (iter_count <= maxIter) 
    {
        int shrink = 0;

        // reflection point (r)
        x_r = Blending(x0, x3, -1);
        x_r.ofv = Decoder(x_r);
        if (x_r.ofv < xBest.ofv) xBest = x_r;
        eval_count++;

        // point_r is better than the x1
        if (x_r.ofv < x1.ofv) 
        {
            // expansion point (e)
            x_e = Blending(x_r, x0, -1);
            x_e.ofv = Decoder(x_e);
            if (x_e.ofv < xBest.ofv) xBest = x_e;
            eval_count++;

            if (x_e.ofv < x_r.ofv) 
            {
                // expand
                x3 = x_e;
            } 
            else 
            {
                // reflect
                x3 = x_r;
            }
        } 
        // x_r is NOT better than the x1
        else 
        {    
            // point_r is better than the second best solution
            if (x_r.ofv < x2.ofv) 
            {
                // reflect
                x3 = x_r;
            } 
            else 
            {
                // point_r is better than the worst solution
                if (x_r.ofv < x3.ofv) 
                {
                    // contraction point (c)
                    x_c = Blending(x_r, x0, 1);
                    x_c.ofv = Decoder(x_c);
                    if (x_c.ofv < xBest.ofv) xBest = x_c;
                    eval_count++;

                    if (x_c.ofv < x_r.ofv) 
                    {
                        // contract outside
                        x3 = x_c;
                    } 
                    else 
                    {
                        // shrink
                        shrink = 1;
                    }
                } 
                else 
                {
                    // contraction point (c)
                    x_c = Blending(x0, x3, 1);
                    x_c.ofv = Decoder(x_c);
                    if (x_c.ofv < xBest.ofv) xBest = x_c;
                    eval_count++;

                    if (x_c.ofv < x3.ofv) 
                    {
                        // contract inside
                        x3 = x_c;
                    } 
                    else {
                        // shrink
                        shrink = 1;
                    }
                }
            }
        }
        if (shrink) {
            x2 = Blending(x1, x2, 1);
            x2.ofv = Decoder(x2);
            if (x2.ofv < xBest.ofv) xBest = x2;
            eval_count++;

            x3 = Blending(x1, x3, 1);
            x3.ofv = Decoder(x3);
            if (x3.ofv < xBest.ofv) xBest = x3;
            eval_count++;
        }

        // sort
        if (x1.ofv > x2.ofv) {
            TSol temp = x1;
            x1 = x2;
            x2 = temp;
        }

        if (x1.ofv > x3.ofv) {
            TSol temp = x1;
            x1 = x3;
            x3 = temp;
        }

        if (x2.ofv > x3.ofv) {
            TSol temp = x2;
            x2 = x3;
            x3 = temp;
        }

        // compute the simplex centroid
        x0 = Blending(x1, x2, 1);
        x0.ofv = Decoder(x0);
        if (x0.ofv < xBest.ofv) xBest = x0;

        iter_count++;
    }

    // return the best solution found
    x1 = xBest;
}

/************************************************************************************
 Method: SwapLS
 Description: swap local search
*************************************************************************************/
void SwapLS(TSol &s)
{
    // // define a random order for the neighors
    std::shuffle(RKorder.begin(), RKorder.end(),rng);
    
    TSol sBest = s;
    for(int i = 0; i < n-1; i++) {
        for(int j = i+1; j < n; j++) {        
            // Swap positions i and j
            double temp = s.rk[RKorder[i]];
            s.rk[RKorder[i]] = s.rk[RKorder[j]];
            s.rk[RKorder[j]] = temp;

            s.ofv = Decoder(s);

            if (s.ofv < sBest.ofv){
                sBest = s;
                // return;
            }
            else{
                s = sBest;
            }
        }
    }
}

/************************************************************************************
 Method: InvertLS
 Description: Invert local search
*************************************************************************************/
void InvertLS(TSol &s)
{
    // define a random order for the neighors
    std::shuffle(RKorder.begin(), RKorder.end(),rng);

    TSol sBest = s;
    for(int i = 0; i < n; i++) {
        // invert the random-key value
        if (s.rk[RKorder[i]] > 0.00001)
            s.rk[RKorder[i]] = 1.0 - s.rk[RKorder[i]];
        else
            s.rk[RKorder[i]] = 0.99999;

        s.ofv = Decoder(s);

        if (s.ofv < sBest.ofv){
            sBest = s;
            // return;
        }
        else{
            s = sBest;
        }
    }
}

/************************************************************************************
 Method: Farey LS
 Description: Farey local search
*************************************************************************************/
void FareyLS(TSol &s)
{
    // define a random order for the neighors
    std::shuffle (RKorder.begin(), RKorder.end(),rng);

    std::vector<double> F = {0.00, 0.142857, 0.166667, 0.20, 0.25, 0.285714, 0.333333, 0.40, 0.428571, 0.50, 
                             0.571429, 0.60, 0.666667, 0.714286, 0.75, 0.80, 0.833333, 0.857143, 1.0};
    TSol sBest = s;
    for(int i = 0; i < n; i++) {
        for (int j=0; j<(int)F.size()-1; j++){
            // generate a random value between two intervals of the Farey sequence
            s.rk[RKorder[i]] = randomico(F[j], F[j+1]);

            s.ofv = Decoder(s);

            if (s.ofv < sBest.ofv){
                sBest = s;
                // return;
            }
            else{
                s = sBest;
            }
        }
    }
}

/************************************************************************************
 Method: Fribonacci LS
 Description: Fibonacci local search
*************************************************************************************/
void FibonacciLS(TSol &s)
{
    // define a random order for the neighors
    std::shuffle (RKorder.begin(), RKorder.end(),rng);

    std::vector<double> Fibonacci = {0.01,
                                     0.02,
                                     0.03,
                                     0.05,
                                     0.08,
                                     0.13,
                                     0.21,
                                     0.34,
                                     0.55,
                                     0.89};
    TSol sBest = s;
    for(int i = 0; i < n; i++) {
        double rk = s.rk[RKorder[i]];
        for (int j=0; j<(int)Fibonacci.size(); j++){
            // generate a random value between actual value and fibonacci j
            double newrk = randomico(rk, rk+Fibonacci[j]);
            
            if (newrk < 1.0)
            {
                s.rk[RKorder[i]] = newrk;
                s.ofv = Decoder(s);

                if (s.ofv < sBest.ofv){
                    sBest = s;
                    // return;
                }
                else{
                    s = sBest;
                }
            }

            newrk = randomico(rk, rk-Fibonacci[j]);
            if (newrk >= 0)
            {
                s.rk[RKorder[i]] = newrk;
                s.ofv = Decoder(s);

                if (s.ofv < sBest.ofv){
                    sBest = s;
                    return;
                }
                else{
                    s = sBest;
                }
            }
        }
    }
}

/************************************************************************************
 Method: 2-Opt LS
 Description: 2-Opt local search
*************************************************************************************/
void TwoOptLS(TSol &s)
{
    TSol sBest = s;

    for(int i = 0; i < n-2; i++) {
        for(int j = i+2; j < n; j++) {        
            // invert sequence between i and j
            std::reverse(s.rk.begin()+i,s.rk.begin()+j);

            s.ofv = Decoder(s);

            if (s.ofv < sBest.ofv){
                sBest = s;
                // return;
            }
            else{
                s = sBest;
            }
        }
    }
}

/************************************************************************************
 Method: RVND
 Description: Random Variable Neighborhood Descent
*************************************************************************************/
void RVND(TSol &s)
{
    // ***** we use a Random Variable Neighborhood Descent (RVND) as local search ****
    int numLS = 4;

    // current neighborhood
    int k = 1;

    // predefined number of neighborhood moves
    std::vector <int> NSL;
    std::vector <int> NSLAux;
    
    for (int i=1; i<=numLS; i++)
    {
        NSL.push_back(i);
        NSLAux.push_back(i);
    }

    int numIter = 0;
    // while (!NSL.empty())
    while (!NSL.empty() && numIter < numLS*5) 
    // while (!NSL.empty() && numIter < n/5) 
    {
        if (stop_execution.load()) return;      

        // current objective function
        double foCurrent = s.ofv;
        numIter++;

        // randomly choose a neighborhood
        int pos = rand() % NSL.size();
        k = NSL[pos];

        switch (k)
        {
            case 1: 
                SwapLS(s);
                break;

            case 2: 
                InvertLS(s);
                break;

            case 3: 
                NelderMeadSearch(s); 
                break;
                
            case 4: 
                FareyLS(s); 
                break;

            case 5: 
                FibonacciLS(s);
                break;

            default:
                break;
        }

        // we better the current solution
        if (s.ofv < foCurrent){
            // refresh NSL
            NSL.clear();
            NSL = NSLAux;
        }
        else{
            // Remove N(k) from NSL
            NSL.erase(NSL.begin()+pos);
        }
    } //end while
}

/************************************************************************************
 Method: CretePoolSolutions
 Description: create a pool of solutions with different solutions
*************************************************************************************/
void CretePoolSolutions()
{
    pool.resize(sizePool);
    for (int i = 0; i < sizePool; i++){
        CreateInitialSolutions(pool[i]);
        pool[i].ofv = Decoder(pool[i]);
    }
    
    // apply local search in the pool solutions
    for (int i = 0; i < sizePool; i++){
        FareyLS(pool[i]);

        // update the best solution found
        if (pool[i].ofv < bestSolution.ofv) 
            updateBestSolution(pool[i], -1);
    }

    // sort pool in increase order of fitness
    sort(pool.begin(), pool.end(), sortByFitness);

    // verify if exists similar solutions in the pool
    for (int i = sizePool-1; i >0 ; i--){
        if (pool[i].ofv == pool[i-1].ofv){
            ShakeSolution(pool[i], 0.1, 0.3);
            pool[i].ofv = Decoder(pool[i]);
        }
    }
}

/************************************************************************************
 Method: UpdatePoolSolutions
 Description: update the pool with different solutions
*************************************************************************************/
void UpdatePoolSolutions(TSol s, int mh)
{
    #pragma omp critical
    {  
        int difSol = 0;

        // check if s is better than the worst pool solution
        if (s.ofv < pool[sizePool-1].ofv)
        {
            difSol = 1;
            
            // check if s is different from the solutions in the pool
            for (int i = 0; i < (int)pool.size(); i++){
                if (s.ofv == pool[i].ofv){
                    difSol = 0;
                }
            }
        }
        if (difSol == 1)
        {
            // insert s in the last position of the pool
            pool[sizePool-1] = s;

            // sort pool in increase order of fitness
            sort(pool.begin(), pool.end(), sortByFitness);
        }

        // update the best solution found
        if (s.ofv < bestSolution.ofv) updateBestSolution(s, mh);
    }
}

/************************************************************************************
 Method: UpdatePoolSolutions
 Description: read the values ​​from the row and store them in the array
*************************************************************************************/
void readValues(FILE *file, std::vector<std::vector<double>> &parameters, int row) 
{
    double aux = 0;
    char line[100];   // Buffer line
    if (fgets(line, sizeof(line), file) != NULL) {
        char *token = strtok(line, "{},= "); // separete line by delimiters
        while (token != NULL) {
            if (sscanf(token, "%lf", &aux) == 1) {
                parameters[row].push_back(aux);
            }
            token = strtok(NULL, "{},= "); // next value
        }
    }
}

/************************************************************************************
 Method: readParameters
 Description: read the parameter values of the MH
*************************************************************************************/
void readParameters(int method, int control, std::vector<std::vector<double>> &parameters, int numPar)
{
    #pragma omp critical
    {  
        char paramFile[256];
        if (control == 0){
            strncpy(paramFile,"ParametersOffline.txt",255);
        }
        else{
            strncpy(paramFile,"ParametersOnline.txt",255);
        }

        // declare and initialize the array of strings
        const char *algorithms[] = {
            "BRKGA",     // 0
            "SA",        // 1
            "GRASP",     // 2
            "ILS",       // 3
            "VNS",       // 4
            "PSO",       // 5
            "SGA",       // 6
            "LNS",       // 7
            "BRKGA-CS"   // 8
        };

        FILE *file = fopen(paramFile, "r");
        if (file == NULL) {
            printf("Error in open file %s.\n", paramFile);
            getchar();
        }

        char line[100]; // read lines

        // Reading the file line by line
        while (fgets(line, sizeof(line), file) != NULL) {
            if (strstr(line, algorithms[method])) {
                // Read the parameters
                for (int i = 0; i < numPar; i++) {
                    readValues(file, parameters, i);
                }
            }
        }
        fclose(file);
    }
}

#endif