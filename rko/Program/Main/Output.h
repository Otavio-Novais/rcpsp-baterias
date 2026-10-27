/************************************************************************************
									IO Functions
*************************************************************************************/

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <vector>
#include <math.h>

#include "Data.h"
 
void WriteSolutionScreen(char mh[], TSol s, int n, float timeBest, float timeTotal, char instance[])
{
	printf("\n\n\nMetaheuristic: %s \nInstance: %s \nsol: ", mh, instance);
	// for (int i=0; i<n; i++)
	// 	printf("%.3lf ", s.rk[i]);

	print = true;
	s.ofv = Decoder(s);
	print = false;

	printf("\nofv: %.5lf", s.ofv); 
	printf("\nTotal time: %.3f",timeTotal);
	printf("\nBest time: %.3f\n\n",timeBest);

	// print solution pool 
	printf("\nSolution Pool:\n");
	for (int i = (int)pool.size()-1; i >= 0; i--)
		printf("%.2lf\n", pool[i].ofv);
}

void WriteSolution(char mh[], TSol s, int n, float timeBest, float timeTotal, char instance[])
{
	char name[256]="../Results/Solutions_";
	strcat(name,mh);
	strcat(name,".txt");
	// FILE *arqSol;
    arqSol = fopen(name,"a");

	if (!arqSol)
	{
		printf("\n\nFile not found %s!!!",name);
		getchar();
		exit(1);
	}

    fprintf(arqSol,"\n\nInstance: %s", instance);
	fprintf(arqSol,"\nMethod: %s",mh);
	fprintf(arqSol,"\nSol: ");
	// for (int i=0; i<n; i++)
	// 	fprintf(arqSol,"%.3lf ", s.rk[i]);

	print = true;
	s.ofv = Decoder(s);
	print = false;

	fprintf(arqSol,"\nofv: %lf", s.ofv);
  	fprintf(arqSol,"\nBest time: %.3f",timeBest);
	fprintf(arqSol,"\nTotal time:%.3f \n",timeTotal);

	fclose(arqSol);
}

void WriteResults(char mh[], double ofv, double ofvAverage, std::vector <double> ofvs, float timeBest, float timeTotal, char instance[])
{
	char name[256]="../Results/Results_";
	strcat(name,mh);
	strcat(name,".csv");

	FILE *arq;
    arq = fopen(name,"a");

	if (!arq)
	{
		printf("\n\nFile not found %s!!!",name);
		getchar();
		exit(1);
	}

	fprintf(arq,"\n%s", instance);
	fprintf(arq,"\t%s", mh);
    fprintf(arq,"\t%d", (int)ofvs.size());
    for (unsigned int i=0; i<ofvs.size(); i++){
        fprintf(arq,"\t%lf", ofvs[i]);   
	}
	fprintf(arq,"\t%lf", ofv);
	fprintf(arq,"\t%lf", ofvAverage);
	fprintf(arq,"\t%.3f", timeBest);
	fprintf(arq,"\t%.3f", timeTotal);

	fclose(arq);
}