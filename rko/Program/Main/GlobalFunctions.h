#ifndef _GlobalFunctions_H
#define _GlobalFunctions_H

/************************************************************************************
 Method: RANDOMICO
 Description: Generate a double random number between min and max
*************************************************************************************/
static double randomico(double min, double max);

/************************************************************************************
 Method: IRANDOMICO
 Description: Generate a int random number between min and max
*************************************************************************************/
static int irandomico(int min, int max);

/************************************************************************************
 Method: sortByFitness
 Description: Sort TSol by objective function
*************************************************************************************/
static bool sortByFitness(const TSol &lhs, const TSol &rhs);

/************************************************************************************
 Method: updateBestSolution
 Description: Update the best solution found during the search process
*************************************************************************************/
void updateBestSolution(TSol s, int mh);

/************************************************************************************
 Method: CreateInitialSolutions
 Description: Create a initial random solution
*************************************************************************************/
static void CreateInitialSolutions(TSol &s);

/************************************************************************************
 Method: ShakeSolution
 Description: shake the current solution
*************************************************************************************/
static void ShakeSolution(TSol &s, float betaMin, float betaMax);

/************************************************************************************
 Method: CretePoolSolutions
 Description: create a pool of solutions with different solutions
*************************************************************************************/
static void CretePoolSolutions();

/************************************************************************************
 Method: UpdatePoolSolutions
 Description: update the pool with different solutions
*************************************************************************************/
static void UpdatePoolSolutions(TSol s, int mh);

/************************************************************************************
 Method: Blending
 Description: uniform crossover
*************************************************************************************/
TSol Blending(TSol &s1, TSol &s2, double factor);

/************************************************************************************
 Method: InvertLS
 Description: Invert local search
*************************************************************************************/
void InvertLS(TSol &s);

/************************************************************************************
 Method: SwapLS
 Description: swap local search
*************************************************************************************/
void SwapLS(TSol &s);

/************************************************************************************
 Method: Fribonacci LS
 Description: Fibonacci local search
*************************************************************************************/
void FibonacciLS(TSol &s);

/************************************************************************************
 Method: NelderMeadSearch
 Description: The Nelder–Mead method is a numerical method used to find the minimum 
 of an objective function in a multidimensional space. It is a direct search method 
 based on function comparison.
*************************************************************************************/
static void NelderMeadSearch(TSol &x1);

/************************************************************************************
 Method: Random Variable Neighborhood Descent
 Description: RVND
*************************************************************************************/
static void RVND(TSol &s);


#endif