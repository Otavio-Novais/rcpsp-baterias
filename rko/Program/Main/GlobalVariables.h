#ifndef _GLOBALVARIABLES_H
#define _GLOBALVARIABLES_H

// /************************************************************************************
// 								GLOBAL VARIABLES
// *************************************************************************************/

// RKO
int n;                                      // size of the random-key vector

// Input File
char instance[100];                         // name of instance
int debug = 1;                              // 0 - run mode      		    1 - debug mode
int MAXTIME = 1;                            // maximum runtime
int MAXRUNS =  1;                           // maximum number of runs of the method

// Run
double start_time, end_time, best_time;     // computational times
char nameTable[256];                        // name of the instance
char nameMH[256];                           // name of the metaheuristic
TSol bestSolution;                          // best solution found
int sizePool = 20;                          // number of solution in the pool
std::vector <TSol> pool;                    // pool of best solutions with diversity
std::vector<int> RKorder;                   // define a random order for the neighors
std::mt19937 rng;                           // pseudo-random number generator Mersenne Twister
std::atomic<bool> stop_execution(false);    // execution flag
bool print = false;                         // print flag
FILE *arqSol;                               // file to write the best solution found
int run = 0;                                // current run

#endif