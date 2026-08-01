// Lesson 02 — the grid washes across the die.
//
// Concept: c[i] = a[i] + b[i] over a million elements. 256 threads per block
// means 4,096 blocks — far more blocks than the die has SMs (24). That's not
// a problem, it's the design: each SM chews through a queue of blocks, and
// having many waiting is how the GPU hides memory latency.
//
// What you'll see on the die: every SM lights, each running ~170 blocks
// (4096 / 24). The counts won't be perfectly even — the scheduler feeds
// whichever SM frees up first.
//
// Experiment: set N to 4096 (16 blocks). A third of the die stays dark —
// too little work to fill the machine. Under-filled grids, not slow cores,
// are the usual reason small workloads disappoint on GPUs.

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>

#include "twinprobe.cuh"

#define N (1 << 20)  // 1,048,576 elements
#define BLOCK_THREADS 256

__global__ void vector_add(const float* a, const float* b, float* c, int n,
                           TwinRecs* recs) {
  TWIN_PROLOGUE(recs);
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) c[i] = a[i] + b[i];
  TWIN_EPILOGUE(recs);
}

int main() {
  size_t bytes = N * sizeof(float);
  float *ha = (float*)malloc(bytes), *hb = (float*)malloc(bytes),
        *hc = (float*)malloc(bytes);
  for (int i = 0; i < N; i++) {
    ha[i] = (float)i;
    hb[i] = 2.0f * i;
  }

  float *da, *db, *dc;
  cudaMalloc(&da, bytes);
  cudaMalloc(&db, bytes);
  cudaMalloc(&dc, bytes);
  cudaMemcpy(da, ha, bytes, cudaMemcpyHostToDevice);
  cudaMemcpy(db, hb, bytes, cudaMemcpyHostToDevice);

  dim3 block(BLOCK_THREADS), grid((N + BLOCK_THREADS - 1) / BLOCK_THREADS);
  TwinProbe probe(grid, block);
  vector_add<<<grid, block>>>(da, db, dc, N, probe.recs());
  cudaDeviceSynchronize();
  probe.flush("vector_add", vector_add);

  cudaMemcpy(hc, dc, bytes, cudaMemcpyDeviceToHost);
  int bad = 0;
  for (int i = 0; i < N; i++)
    if (hc[i] != 3.0f * i) bad++;
  printf("%d blocks x %d threads: %s\n", grid.x, block.x,
         bad ? "WRONG RESULTS" : "verified c[i] == 3*i for all i");

  cudaFree(da);
  cudaFree(db);
  cudaFree(dc);
  free(ha);
  free(hb);
  free(hc);
  return bad != 0;
}
