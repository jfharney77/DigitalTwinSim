// Lesson 03 — occupancy is a budget.
//
// Concept: the same vector add, launched once per block size from 32 to 1024.
// An SM can hold at most maxThreadsPerMultiProcessor threads (1,536 on Ada)
// AND at most maxBlocksPerMultiProcessor blocks (24) at once — whichever
// budget runs out first caps "occupancy", the fraction of thread slots kept
// busy. 32-thread blocks hit the 24-block ceiling at 24x32 = 768 threads:
// half the slots sit empty.
//
// What you'll see: the kernel timeline (#live tab) grows one entry per
// launch, each chip showing elapsed ms and the occupancy figure. Click
// through them and watch occupancy fall at the extremes.
//
// Experiment: find the fastest block size on YOUR die. It's usually not
// 1024 — and the reason (register pressure, scheduling slack) is exactly
// what the occupancy number summarizes.

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>

#include "twinprobe.cuh"

#define N (1 << 22)  // 4M elements: enough work that timing differences show

__global__ void vector_add_sweep(const float* a, const float* b, float* c,
                                 int n, TwinRecs* recs) {
  TWIN_PROLOGUE(recs);
  int i = blockIdx.x * blockDim.x + threadIdx.x;
  if (i < n) c[i] = a[i] + b[i];
  TWIN_EPILOGUE(recs);
}

int main() {
  size_t bytes = N * sizeof(float);
  float *da, *db, *dc;
  cudaMalloc(&da, bytes);
  cudaMalloc(&db, bytes);
  cudaMalloc(&dc, bytes);
  cudaMemset(da, 0, bytes);
  cudaMemset(db, 0, bytes);

  int sizes[] = {32, 64, 128, 256, 512, 1024};
  char name[64];
  for (int s = 0; s < 6; s++) {
    int bt = sizes[s];
    dim3 block(bt), grid((N + bt - 1) / bt);
    TwinProbe probe(grid, block);
    vector_add_sweep<<<grid, block>>>(da, db, dc, N, probe.recs());
    cudaDeviceSynchronize();
    snprintf(name, sizeof(name), "vector_add_bs%d", bt);
    probe.flush(name, vector_add_sweep);
    printf("block size %4d -> %d blocks launched\n", bt, grid.x);
  }

  cudaFree(da);
  cudaFree(db);
  cudaFree(dc);
  return 0;
}
