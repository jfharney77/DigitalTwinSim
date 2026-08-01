// Lesson 00 — who am I talking to?
//
// Concept: before anything runs, ask the driver what the device actually is.
// This lesson proves the toolchain works and checks that the hardware agrees
// with the digital twin: the RTX-4060-Laptop profile (spec_07) hardcodes
// 24 SMs and 128 lanes each — the numbers printed here must match.
//
// What you'll see on the die: nothing yet. That's the point — no kernel runs.
//
// Experiment: open the Die anatomy tab (#anatomy, "RTX 4060 Laptop (AD107)")
// and compare every printed number against the stats table.

#include <cstdio>
#include <cuda_runtime.h>

int main() {
  int count = 0;
  cudaError_t err = cudaGetDeviceCount(&count);
  if (err != cudaSuccess || count == 0) {
    fprintf(stderr, "no CUDA device: %s\n", cudaGetErrorString(err));
    return 1;
  }

  cudaDeviceProp p;
  cudaGetDeviceProperties(&p, 0);

  printf("device            : %s\n", p.name);
  printf("compute capability: %d.%d\n", p.major, p.minor);
  printf("SMs               : %d   (twin expects 24)\n", p.multiProcessorCount);
  printf("warp size         : %d\n", p.warpSize);
  printf("max threads/block : %d\n", p.maxThreadsPerBlock);
  printf("max threads/SM    : %d   (the occupancy ceiling)\n",
         p.maxThreadsPerMultiProcessor);
  printf("max blocks/SM     : %d\n", p.maxBlocksPerMultiProcessor);
  printf("global memory     : %.0f MB\n", p.totalGlobalMem / 1048576.0);
  printf("L2 cache          : %.0f MB\n", p.l2CacheSize / 1048576.0);
  printf("memory bus        : %d-bit\n", p.memoryBusWidth);

  if (p.multiProcessorCount != 24) {
    printf("\nNOTE: not the RTX 4060 Laptop GPU the twin models — the live\n"
           "view still works, but SM counts above 23 will be rejected.\n");
  }
  return 0;
}
