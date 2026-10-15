#include <algorithm>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <thread>
#include <vector>

#include "CycleTimer.h"
#include "assignments_ispc.h"

using namespace std;

typedef struct {
  // Control work assignments
  int start, end;

  // Shared by all functions
  double *data;
  double *clusterCentroids;
  int *clusterAssignments;
  double *currCost;
  int M, N, K;
} WorkerArgs;

namespace {

template <typename Work>
void forEachPointRange(int pointCount, int threadCount, const Work &work) {
  const auto run = [&](int t) {
    const int begin = static_cast<long long>(pointCount) * t / threadCount;
    const int end = static_cast<long long>(pointCount) * (t + 1) / threadCount;
    work(t, begin, end);
  };
  vector<thread> workers;
  workers.reserve(threadCount - 1);
  for (int t = 1; t < threadCount; t++)
    workers.emplace_back(run, t);
  run(0);
  for (thread &worker : workers)
    worker.join();
}

} // namespace


/**
 * Checks if the algorithm has converged.
 * 
 * @param prevCost Pointer to the K dimensional array containing cluster costs 
 *    from the previous iteration.
 * @param currCost Pointer to the K dimensional array containing cluster costs 
 *    from the current iteration.
 * @param epsilon Predefined hyperparameter which is used to determine when
 *    the algorithm has converged.
 * @param K The number of clusters.
 * 
 * NOTE: DO NOT MODIFY THIS FUNCTION!!!
 */
static bool stoppingConditionMet(double *prevCost, double *currCost,
                                 double epsilon, int K) {
  for (int k = 0; k < K; k++) {
    if (abs(prevCost[k] - currCost[k]) > epsilon)
      return false;
  }
  return true;
}

/**
 * Computes L2 distance between two points of dimension nDim.
 * 
 * @param x Pointer to the beginning of the array representing the first
 *     data point.
 * @param y Poitner to the beginning of the array representing the second
 *     data point.
 * @param nDim The dimensionality (number of elements) in each data point
 *     (must be the same for x and y).
 */
double dist(double *x, double *y, int nDim) {
  double accum = 0.0;
  for (int i = 0; i < nDim; i++) {
    accum += pow((x[i] - y[i]), 2);
  }
  return sqrt(accum);
}

/**
 * Assigns each data point to its "closest" cluster centroid.
 */
void computeAssignments(WorkerArgs *const args) {
  if (args->M <= 0)
    return;

  constexpr int kThreadCount = 4;
  const int threadCount = min(kThreadCount, args->M);
  const auto assignRange = [args](int begin, int end) {
    // Batch the range to avoid crossing the C++/ISPC boundary for each distance.
    ispc::assignments_ispc(args->data, args->clusterCentroids,
                          args->clusterAssignments, args->N, args->start,
                          args->end, begin, end);
  };

  // Disjoint point ranges avoid shared updates; centroids stay read-only until join.
  thread workers[kThreadCount];
  for (int t = 1; t < threadCount; t++) {
    const int begin = static_cast<long long>(args->M) * t / threadCount;
    const int end = static_cast<long long>(args->M) * (t + 1) / threadCount;
    workers[t] = thread(assignRange, begin, end);
  }
  assignRange(0, args->M / threadCount);
  for (int t = 1; t < threadCount; t++)
    workers[t].join();
}

/**
 * Given the cluster assignments, computes the new centroid locations for
 * each cluster.
 */
void computeCentroids(WorkerArgs *const args) {
  constexpr int kThreadCount = 4;
  const int threadCount = min(kThreadCount, max(args->M, 1));
  const size_t centroidSize = static_cast<size_t>(args->K) * args->N;
  vector<vector<double>> sums(threadCount, vector<double>(centroidSize, 0.0));
  vector<vector<int>> counts(threadCount, vector<int>(args->K, 0));

  // Private accumulators avoid contention when many points share a cluster.
  forEachPointRange(args->M, threadCount, [&](int t, int begin, int end) {
    for (int m = begin; m < end; m++) {
      const int k = args->clusterAssignments[m];
      const size_t centroidOffset = static_cast<size_t>(k) * args->N;
      const size_t pointOffset = static_cast<size_t>(m) * args->N;
      for (int n = 0; n < args->N; n++)
        sums[t][centroidOffset + n] += args->data[pointOffset + n];
      counts[t][k]++;
    }
  });

  // A fixed reduction order makes results independent of thread scheduling.
  for (int k = 0; k < args->K; k++) {
    int count = 0;
    for (int t = 0; t < threadCount; t++)
      count += counts[t][k];
    const size_t offset = static_cast<size_t>(k) * args->N;
    for (int n = 0; n < args->N; n++) {
      double sum = 0.0;
      for (int t = 0; t < threadCount; t++)
        sum += sums[t][offset + n];
      args->clusterCentroids[offset + n] = sum / max(count, 1);
    }
  }
}

/**
 * Computes the per-cluster cost. Used to check if the algorithm has converged.
 */
void computeCost(WorkerArgs *const args) {
  constexpr int kThreadCount = 4;
  const int threadCount = min(kThreadCount, max(args->M, 1));
  vector<vector<double>> costs(threadCount, vector<double>(args->K, 0.0));

  forEachPointRange(args->M, threadCount, [&](int t, int begin, int end) {
    for (int m = begin; m < end; m++) {
      const int k = args->clusterAssignments[m];
      costs[t][k] += dist(&args->data[static_cast<size_t>(m) * args->N],
                          &args->clusterCentroids[static_cast<size_t>(k) * args->N],
                          args->N);
    }
  });

  for (int k = args->start; k < args->end; k++) {
    double sum = 0.0;
    for (int t = 0; t < threadCount; t++)
      sum += costs[t][k];
    args->currCost[k] = sum;
  }
}

/**
 * Computes the K-Means algorithm, using std::thread to parallelize the work.
 *
 * @param data Pointer to an array of length M*N representing the M different N 
 *     dimensional data points clustered. The data is layed out in a "data point
 *     major" format, so that data[i*N] is the start of the i'th data point in 
 *     the array. The N values of the i'th datapoint are the N values in the 
 *     range data[i*N] to data[(i+1) * N].
 * @param clusterCentroids Pointer to an array of length K*N representing the K 
 *     different N dimensional cluster centroids. The data is laid out in
 *     the same way as explained above for data.
 * @param clusterAssignments Pointer to an array of length M representing the
 *     cluster assignments of each data point, where clusterAssignments[i] = j
 *     indicates that data point i is closest to cluster centroid j.
 * @param M The number of data points to cluster.
 * @param N The dimensionality of the data points.
 * @param K The number of cluster centroids.
 * @param epsilon The algorithm is said to have converged when
 *     |currCost[i] - prevCost[i]| < epsilon for all i where i = 0, 1, ..., K-1
 */
void kMeansThread(double *data, double *clusterCentroids, int *clusterAssignments,
               int M, int N, int K, double epsilon) {

  // Used to track convergence
  double *prevCost = new double[K];
  double *currCost = new double[K];

  // The WorkerArgs array is used to pass inputs to and return output from
  // functions.
  WorkerArgs args;
  args.data = data;
  args.clusterCentroids = clusterCentroids;
  args.clusterAssignments = clusterAssignments;
  args.currCost = currCost;
  args.M = M;
  args.N = N;
  args.K = K;

  // Initialize arrays to track cost
  for (int k = 0; k < K; k++) {
    prevCost[k] = 1e30;
    currCost[k] = 0.0;
  }

  /* Main K-Means Algorithm Loop */
  int iter = 0;
  double assignmentSeconds = 0.0;
  double centroidSeconds = 0.0;
  double costSeconds = 0.0;
  while (!stoppingConditionMet(prevCost, currCost, epsilon, K)) {
    // Update cost arrays (for checking convergence criteria)
    for (int k = 0; k < K; k++) {
      prevCost[k] = currCost[k];
    }

    // Setup args struct
    args.start = 0;
    args.end = K;

    double startTime = CycleTimer::currentSeconds();
    computeAssignments(&args);
    assignmentSeconds += CycleTimer::currentSeconds() - startTime;

    startTime = CycleTimer::currentSeconds();
    computeCentroids(&args);
    centroidSeconds += CycleTimer::currentSeconds() - startTime;

    startTime = CycleTimer::currentSeconds();
    computeCost(&args);
    costSeconds += CycleTimer::currentSeconds() - startTime;

    iter++;
  }

  // Print after convergence to keep console I/O out of the iteration timings.
  const double stageSeconds = assignmentSeconds + centroidSeconds + costSeconds;
  const double percentScale = stageSeconds > 0.0 ? 100.0 / stageSeconds : 0.0;
  const double averageScale = iter > 0 ? 1000.0 / iter : 0.0;
  printf("[Stage Timing]: %d iterations; percentages are of the three stages\n", iter);
  printf("[computeAssignments]: %.3f ms total, %.3f ms/iteration, %.2f%%\n",
         assignmentSeconds * 1000.0, assignmentSeconds * averageScale,
         assignmentSeconds * percentScale);
  printf("[computeCentroids]: %.3f ms total, %.3f ms/iteration, %.2f%%\n",
         centroidSeconds * 1000.0, centroidSeconds * averageScale,
         centroidSeconds * percentScale);
  printf("[computeCost]: %.3f ms total, %.3f ms/iteration, %.2f%%\n",
         costSeconds * 1000.0, costSeconds * averageScale,
         costSeconds * percentScale);

  delete[] currCost;
  delete[] prevCost;
}
