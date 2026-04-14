#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <float.h>

#define MAXN 2100
#define INF 1e9

int adj[MAXN][MAXN];
int radj[MAXN][MAXN];
int n, e;
double timestamp[MAXN];
int hasTime;

int infected[MAXN];
int infectedCount;

double dist[MAXN][MAXN];

double probScore[MAXN];
double centrality[MAXN];

void reverseBFS_dist(int start, double *dist_out)
{
    int queue[MAXN];
    int front = 0, rear = 0;
    int visited[MAXN] = {0};

    for (int i = 1; i <= n; i++)
        dist_out[i] = -1;

    dist_out[start] = 0;
    visited[start] = 1;
    queue[rear++] = start;

    while (front < rear)
    {
        int node = queue[front++];
        for (int i = 1; i <= n; i++)
        {
            if (!radj[i][node])
                continue; /* no reverse edge i→node */
            if (visited[i])
                continue;

            if (hasTime && timestamp[i] > timestamp[node])
                continue;

            visited[i] = 1;
            dist_out[i] = dist_out[node] + 1;
            queue[rear++] = i;
        }
    }
}

void computeCentrality()
{
    int maxDeg = 0;
    for (int i = 1; i <= n; i++)
    {
        int deg = 0;
        for (int j = 1; j <= n; j++)
            deg += adj[j][i]; /* in-degree */
        centrality[i] = deg;
        if (deg > maxDeg)
            maxDeg = deg;
    }
    for (int i = 1; i <= n; i++)
        centrality[i] = 1.0 + (maxDeg > 0 ? centrality[i] / maxDeg : 0);
}

void computeProbScore()
{
    for (int c = 1; c <= n; c++)
    {
        double score = 0.0;
        int reachable = 0;
        for (int i = 0; i < infectedCount; i++)
        {
            double d = dist[i][c];
            if (d >= 0)
            {
                score += 1.0 / (d + 1.0);
                reachable = 1;
            }
        }
        probScore[c] = reachable ? score * centrality[c] : 0.0;
    }
}

int greedyMultiSource(int maxSources, int *sources)
{
    int covered[MAXN] = {0};
    int srcCount = 0;

    for (int s = 0; s < maxSources; s++)
    {
        int bestNode = -1;
        int bestNew = -1;

        for (int c = 1; c <= n; c++)
        {
            if (probScore[c] == 0.0)
                continue;

            int newCover = 0;
            for (int i = 0; i < infectedCount; i++)
            {
                if (!covered[i] && dist[i][c] >= 0)
                    newCover++;
            }
            if (newCover > bestNew ||
                (newCover == bestNew && probScore[c] > probScore[bestNode]))
            {
                bestNew = newCover;
                bestNode = c;
            }
        }

        if (bestNode == -1 || bestNew == 0)
            break;

        sources[srcCount++] = bestNode;
        for (int i = 0; i < infectedCount; i++)
            if (dist[i][bestNode] >= 0)
                covered[i] = 1;

        int allDone = 1;
        for (int i = 0; i < infectedCount; i++)
            if (!covered[i])
            {
                allDone = 0;
                break;
            }
        if (allDone)
            break;
    }
    return srcCount;
}

int main()
{
    char line[65536];

    if (!fgets(line, sizeof(line), stdin))
    {
        fprintf(stderr, "Error: could not read node/edge count.\n");
        return 1;
    }
    if (sscanf(line, "%d %d", &n, &e) != 2)
    {
        fprintf(stderr, "Error: expected '<nodes> <edges>' on first line.\n");
        return 1;
    }

    for (int i = 0; i < e; i++)
    {
        if (!fgets(line, sizeof(line), stdin))
            break;
        int u, v;
        if (sscanf(line, "%d %d", &u, &v) == 2)
        {
            adj[u][v] = 1;
            radj[v][u] = 1; /* build reverse graph simultaneously */
        }
    }

    if (!fgets(line, sizeof(line), stdin))
    {
        fprintf(stderr, "Error: could not read infected node count.\n");
        return 1;
    }
    sscanf(line, "%d", &infectedCount);

    if (!fgets(line, sizeof(line), stdin))
    {
        fprintf(stderr, "Error: could not read infected node list.\n");
        return 1;
    }
    {
        char *p = line;
        for (int i = 0; i < infectedCount; i++)
        {
            while (*p == ' ' || *p == '\t')
                p++;
            sscanf(p, "%d", &infected[i]);
            while (*p && *p != ' ' && *p != '\t' && *p != '\n' && *p != '\r')
                p++;
        }
    }

    hasTime = 0;
    if (fgets(line, sizeof(line), stdin) != NULL)
    {
        char *p = line;
        int count = 0;
        while (*p)
        {
            while (*p == ' ' || *p == '\t')
                p++;
            if (*p == '\n' || *p == '\r' || *p == '\0')
                break;
            char *next;
            double t = strtod(p, &next);
            if (next == p)
                break; /* not a number */
            count++;
            if (count <= MAXN)
                timestamp[count] = t;
            p = next;
        }
        if (count > 0)
        {
            hasTime = 1;
            printf("Timestamps loaded: %d values (time-constraint pruning ACTIVE)\n", count);
        }
    }

    for (int i = 0; i < infectedCount; i++)
        reverseBFS_dist(infected[i], dist[i]);

    computeCentrality();
    computeProbScore();

    printf("\n--- Distance-Based Probability Scores ---\n");
    printf("%-8s %-14s %-12s %-10s\n",
           "Node", "ProbScore", "Centrality", "Reachable");

    double maxScore = 0;
    for (int i = 1; i <= n; i++)
        if (probScore[i] > maxScore)
            maxScore = probScore[i];

    for (int i = 1; i <= n; i++)
    {
        if (probScore[i] == 0.0)
            continue;
        int reachable = 0;
        for (int k = 0; k < infectedCount; k++)
            if (dist[k][i] >= 0)
                reachable++;

        printf("%-8d %-14.4f %-12.4f %d / %d\n",
               i, probScore[i], centrality[i], reachable, infectedCount);
    }

    int bestNode = -1;
    double bestScore = -1;
    for (int i = 1; i <= n; i++)
        if (probScore[i] > bestScore)
        {
            bestScore = probScore[i];
            bestNode = i;
        }

    printf("\n--- Most Probable Single Source ---\n");
    if (bestNode != -1)
        printf("Node %d  (score = %.4f)\n", bestNode, bestScore);
    else
        printf("No reachable source found.\n");

    int sources[MAXN];
    int srcCount = greedyMultiSource(3, sources);

    printf("\n--- Multi-Source Detection (up to 3 sources) ---\n");
    if (srcCount == 0)
        printf("No sources found.\n");
    else
        for (int i = 0; i < srcCount; i++)
            printf("Source %d: Node %d  (score = %.4f)\n",
                   i + 1, sources[i], probScore[sources[i]]);

    printf("\n--- Node Centrality (In-Degree Hub Score, top 3) ---\n");
    for (int rank = 0; rank < 3 && rank < n; rank++)
    {
        int best = -1;
        double bestC = -1;
        for (int i = 1; i <= n; i++)
        {
            int already = 0;
            for (int r = 0; r < rank; r++)
                if (sources[r] == i)
                {
                    already = 1;
                    break;
                }
            if (!already && centrality[i] > bestC)
            {
                bestC = centrality[i];
                best = i;
            }
        }
        if (best != -1)
            printf("  Rank %d: Node %d  (centrality = %.4f)\n",
                   rank + 1, best, centrality[best]);
    }

    printf("\n[DONE]\n");
    return 0;
}