// Lesson 04 — the simulator's matmul, for real (naive version).
//
// Concept: C = A x B, one thread per output cell — exactly the computation
// the Simulator tab animates (spec_01). Naive means every thread reads a
// full row of A and column of B straight from global memory: N reads of
// each operand per cell, nothing reused.
//
// What you'll see: the die lights like lesson 02 — placement looks the same.
// The difference from lesson 05 is invisible on the die and huge on the
// clock: same math, several times slower, because the cost lives in the
// memory system the die view doesn't draw. Note your elapsed ms, then run
// lesson 05.
//
// Experiment: run the Simulator tab with tiling OFF beside this — the
// repeated HBM loads it animates are the traffic you're paying for here.

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>

#include "twinprobe.cuh"

#define N 512
#define TILE 16  // block is TILE x TILE threads; same shape as lesson 05

__global__ void matmul_naive(const float* a, const float* b, float* c, int n,
                             TwinRecs* recs) {
  TWIN_PROLOGUE(recs);
  int row = blockIdx.y * blockDim.y + threadIdx.y;
  int col = blockIdx.x * blockDim.x + threadIdx.x;
  if (row < n && col < n) {
    float acc = 0.0f;
    for (int k = 0; k < n; k++) acc += a[row * n + k] * b[k * n + col];
    c[row * n + col] = acc;
  }
  TWIN_EPILOGUE(recs);
}

int main() {
  size_t bytes = (size_t)N * N * sizeof(float);
  float* h = (float*)malloc(bytes);
  for (int i = 0; i < N * N; i++) h[i] = (float)((i % 7) - 3);

  float *da, *db, *dc;
  cudaMalloc(&da, bytes);
  cudaMalloc(&db, bytes);
  cudaMalloc(&dc, bytes);
  cudaMemcpy(da, h, bytes, cudaMemcpyHostToDevice);
  cudaMemcpy(db, h, bytes, cudaMemcpyHostToDevice);

  dim3 block(TILE, TILE), grid(N / TILE, N / TILE);
  TwinProbe probe(grid, block);
  matmul_naive<<<grid, block>>>(da, db, dc, N, probe.recs());
  cudaDeviceSynchronize();
  probe.flush("matmul_naive", matmul_naive);

  // Spot-check one cell against the CPU.
  float* hc = (float*)malloc(bytes);
  cudaMemcpy(hc, dc, bytes, cudaMemcpyDeviceToHost);
  float want = 0.0f;
  for (int k = 0; k < N; k++) want += h[3 * N + k] * h[k * N + 5];
  printf("C[3][5] = %.1f (cpu %.1f) %s\n", hc[3 * N + 5], want,
         hc[3 * N + 5] == want ? "ok" : "MISMATCH");

  cudaFree(da);
  cudaFree(db);
  cudaFree(dc);
  free(h);
  free(hc);
  return 0;
}
