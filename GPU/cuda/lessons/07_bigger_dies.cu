// Lesson 07 — the die is a parameter.
//
// Concept: nothing in a CUDA program names the GPU it runs on. This lesson
// asks the driver how many SMs the die has and sizes its grid from the
// answer — two blocks per SM, whatever the SM count is. On the RTX 4060
// Laptop that's 48 blocks over 24 tiles; on an H100 SXM the identical binary
// launches 264 blocks and lights 132 tiles; on a Blackwell Ultra B300, 320
// blocks over 160 tiles — and on Blackwell the two fused dies are invisible:
// %smid runs 0..159 with no seam, because NV-HBI presents one logical GPU.
//
// What you'll see on the die: every SM lights with ~2 blocks each. The die
// view resizes itself to your hardware — device_info sizes the grid of tiles
// (spec_12), so this lesson looks different on every machine, which is the
// lesson.
//
// Experiment: change BLOCKS_PER_SM to 1 and to 8. The placement picture
// stays uniform; the queue depth per SM is what moves. Then open the
// Simulator tab and switch the profile between RTX-4060-Laptop, H100-SXM,
// and B300-Blackwell-Ultra — the same matmul spreading across each fleet
// member is this lesson's software-side mirror.

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>

#include "twinprobe.cuh"

#define N (1 << 20)  // 1,048,576 elements
#define BLOCKS_PER_SM 2

__global__ void vector_add(const float* a, const float* b, float* c, int n,
                           TwinRecs* recs) {
  TWIN_PROLOGUE(recs);
  // Grid-stride loop: correct for ANY grid size, which is what lets the
  // launch geometry follow the hardware instead of the problem size.
  for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < n;
       i += gridDim.x * blockDim.x)
    c[i] = a[i] + b[i];
  TWIN_EPILOGUE(recs);
}

int main() {
  cudaDeviceProp prop;
  cudaGetDeviceProperties(&prop, 0);
  printf("%s: %d SMs -> launching %d blocks (%d per SM)\n", prop.name,
         prop.multiProcessorCount, prop.multiProcessorCount * BLOCKS_PER_SM,
         BLOCKS_PER_SM);

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

  dim3 block(256), grid(prop.multiProcessorCount * BLOCKS_PER_SM);
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
