// *******************************************************************
//      file with specific functions to solve the TSP
// *******************************************************************
#ifndef _PROBLEM_H
#define _PROBLEM_H

#include "../Main/Data.h"

// Global Variables
extern int n;                                       // size of the vector solution

//---------------------- DEFINITION OF TYPES OF PROBLEM SPECIFIC --------------------

// struct with node informations
struct TNode								
{
	int id;
	double x;
	double y;
}; 

//------ DEFINITION OF GLOBAL CONSTANTS AND VARIABLES OF SPECIFIC PROBLEM  ----------

static std::vector <std::vector <double> > dist;	// matrix with Euclidean distance
static std::vector <TNode> node;					// vector of TSP nodes


//----------------------- IMPLEMENTATION OF FUNCTIONS  -------------------------------


/************************************************************************************
 Method: ReadData
 Description: read input data of the problem
*************************************************************************************/
void ReadData(char nameTable[])
{ 
    char name[200] = "../Instances/";
    strcat(name,nameTable);

    FILE *arq;
    arq = fopen(name,"r");

    if (arq == NULL)
    {
        printf("\nERROR: File (%s) not found!\n",name);
        getchar();
        exit(1);
    }

    // => read data

    // read instance head
    char temp[100];
    fgets(temp, sizeof(temp), arq);
    fgets(temp, sizeof(temp), arq);
    fgets(temp, sizeof(temp), arq);
    fgets(temp, sizeof(temp), arq);
    fgets(temp, sizeof(temp), arq);
    fgets(temp, sizeof(temp), arq);

    // read node informations
    int nAux = 0;
    node.clear();
    TNode nodeTemp;

    while (!feof(arq))
    {
    	fscanf(arq, "%d %lf %lf", &nodeTemp.id, &nodeTemp.x, &nodeTemp.y);
    	node.push_back(nodeTemp);

    	nAux++;
    }
    fclose(arq);

    // calculate the euclidean distance
    dist.clear();
    dist.resize(nAux, std::vector<double>(nAux));

    for (int i=0; i<nAux; i++)
    {
    	for (int j=i; j<nAux; j++)
    	{
    		dist[i][j] = dist[j][i] = (floor (sqrt( (node[j].x - node[i].x) * (node[j].x - node[i].x) +
    										        (node[j].y - node[i].y) * (node[j].y - node[i].y) ) + 0.5 ) )/1.0;
    	}
    }
    
    n = nAux;
}

/************************************************************************************
 Method: Decoders
 Description: mapping the random-key solutions into problem solutions
*************************************************************************************/
double Decoder(TSol s)
{
    // create an initial list of candidates
    std::vector <int> sC(n);  
    for (int j = 0; j < n; j++){ sC[j] = j;}

    // sort the problem vector based on the values in the rk vector
    std::sort(sC.begin(), sC.end(), [&s](int i1, int i2) {
        return s.rk[i1] < s.rk[i2];
    });

    // problem solution
    std::vector <int> sol; 

    // partial route with three points
    sol.push_back(sC[0]);
    sol.push_back(sC[1]);
    sol.push_back(sC[2]);

    // construct a solution with cheapest insertion
    for (int i = 3; i<n; i++)
    {
        // find the cheapest position to insert the i-th point of sC
        int bestPosition = 0;
        float costBest = INFINITY;
        float costInsertion = 0;
        for (unsigned int j = 0; j<sol.size(); j++)
        {
            if (j == sol.size()-1)
            {
                // cost to insert between i-1 and 0
                costInsertion = dist[sol[j]][sC[i]] + dist[sC[i]][sol[0]] - dist[sol[j]][sol[0]];
                if (costInsertion < costBest)
                {
                    costBest = costInsertion;
                    bestPosition = j;
                }
            }
            else
            {
                // cost to insert between i and i+1
                costInsertion = dist[sol[j]][sC[i]] + dist[sC[i]][sol[j+1]] - dist[sol[j]][sol[j+1]];
                if (costInsertion < costBest)
                {
                    costBest = costInsertion;
                    bestPosition = j;
                }
            }
        }

        // insert the i-th point in the cheapest position
        sol.insert(sol.begin()+bestPosition+1,sC[i]);
    }

    //calculate objective function
    s.ofv = 0.0;
    for (int i=0; i<n; i++){
        s.ofv += dist[sol[i%n]][sol[(i+1)%n]];
    }

    // print the solution in the screen
    if (debug && print)
    {
        for (int i=0; i<n; i++)
		    printf("%d ", sol[i]);
    }

    // print the solution in a file
    if (!debug && print)
    {
        for (int i=0; i<n; i++)
		    fprintf(arqSol,"%d ", sol[i]);
    }

    // return the objective function value
    return s.ofv;
}

/************************************************************************************
 Method: FreeMemoryProblem
 Description: Free local memory allocate by Problem
*************************************************************************************/
void FreeMemoryProblem()
{
    //specific problem
    dist.clear();
    node.clear();
}


#endif