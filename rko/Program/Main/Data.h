#ifndef _DATA_H
#define _DATA_H

//------ DEFINITION OF TYPES OF RKO --------

/***********************************************************************************
 Struct: TSol
 Description: struct to represent a solution problem
************************************************************************************/
struct TSol
{
    std::vector <double> rk;                // random-key vector
    double ofv;                             // objetive function value
    int label;                              // defines a community solution with a number
    int similar;                            // indicates if a solution is similar to other (0 no, 1 yes)
    int flag;                               // indicates if a local search has already been performed on this solution (0 no, 1 yes)
    int promising;                          // indicates if a solution is promising to apply local search
};

/***********************************************************************************
 Struct: TQ
 Description: struct to represent a quality matrix of Q-Learning
************************************************************************************/
struct TQ
{
    int S;                                  // state (parameter)
    double pVar;                            // value of the state
    double q;                               // q value
    int k;                                  // number of calls
    int kImp;                               // number of improvements
};

/***********************************************************************************
 Struct: TState
 Description: struct to represent a state of the MDP
************************************************************************************/
struct TState
{
    int label;                              // id of the state
    std::vector<double> par;                // vector of parameters        
    double ci;                              // cost of state i
    int numN;                               // number of runs of state i
    std::vector<int> Ai;                    // vector of actions
    std::vector<double> Qa;                 // vector of value function Q(s,a)
    double sumQ;                            // sum of Q(s,-)
    double maxQ;                            // max of Q(s,-)
    int minA;                               // index of the min Q(s,-)
    int maxA;                               // index of the max Q(s,-)
};

#endif