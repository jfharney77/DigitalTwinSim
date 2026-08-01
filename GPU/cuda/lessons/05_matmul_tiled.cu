// Lesson 05 — the simulator's tiling (spec_03), for real.
//
// Concept: same C = A x B, but each block first copies a TILE x TILE patch
// of A and B into __shared__ memory — the per-SM scratchpad the simulator
// draws as the "shared mem" strip — and every thread in the block reuses
// those patches TILE times before the next load. Global-memory traffic
// drops by a factor of TILE.
//
// What you'll see: die lighting and occupancy nearly identical to lesson 04,
// elapsed ms several times smaller. The speedup lives in the memory system,
// not in the placement picture — which is why the twin pairs this lesson
// with the Simulator tab's bandwidth model (spec_04) and the roofline
// read-out, now running the 4060's real ratios (spec_07).
//
// Experiment: change TILE to 8 and 32 (rebuild) and watch elapsed ms move;
// then replay the same sweep in the Simulator tab's tiling control.

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>

#include "twinprobe.cuh"

#define N 512
#define TILE 16

__global__ void matmul_tiled(const float* a, const float* b, float* c, int n,
                             TwinRecs* recs) {
  TWIN_PROLOGUE(recs);
  __shared__ float sa[TILE][TILE];
  __shared__ float sb[TILE][TILE];

  int row = blockIdx.y * TILE + threadIdx.y;
  int col = blockIdx.x * TILE + threadIdx.x;
  float acc = 0.0f;

  for (int t = 0; t < n / TILE; t++) {
    sa[threadIdx.y][threadIdx.x] = a[row * n + t * TILE + threadIdx.x];
    sb[threadIdx.y][threadIdx.x] = b[(t * TILE + threadIdx.y) * n + col];
    __syncthreads();  // the whole tile must land before anyone reads it
    for (int k = 0; k < TILE; k++)
      acc += sa[threadIdx.y][k] * sb[k][threadIdx.x];
    __syncthreads();  // ...and be fully consumed before it's overwritten
  }
  c[row * n + col] = acc;
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
  matmul_tiled<<<grid, block>>>(da, db, dc, N, probe.recs());
  cudaDeviceSynchronize();
  probe.flush("matmul_tiled", matmul_tiled);

  float* hc = (float*)malloc(bytes);
  cudaMemcpy(hc, dc, bytes, cudaMemcpyDeviceToHost);
  float want = 0.0f;
  for (int k = 0; k < N; k++) want += h[3 * N + k] * h[k * N + 5];
  printf("C[3][5] = %.1f (cpu %.1f) %s — compare elapsed ms with lesson 04\n",
         hc[3 * N + 5], want, hc[3 * N + 5] == want ? "ok" : "MISMATCH");

  cudaFree(da);
  cudaFree(db);
  cudaFree(dc);
  free(h);
  free(hc);
  return 0;
}
