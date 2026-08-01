// Lesson 01 — threads exist (and you don't choose where they run).
//
// Concept: a kernel launch <<<blocks, threads>>> creates a grid of thread
// blocks; the hardware scheduler places each block on a Streaming
// Multiprocessor (SM). Each thread knows its coordinates (blockIdx,
// threadIdx) — and can even read which SM it landed on (%smid).
//
// What you'll see on the die (#live tab): exactly ONE SM tile lights — one
// block runs on one SM, never split across two. (The simulator's tile-aware
// mapping teaches the same rule.)
//
// Experiment: change GRID_BLOCKS to 8 and rerun a few times. Eight tiles
// light — and WHICH eight changes run to run. You don't choose SMs; the
// scheduler does. That variation is real, not a visualization effect.

#include <cstdio>
#include <cuda_runtime.h>

#include "twinprobe.cuh"

#define GRID_BLOCKS 1
#define BLOCK_THREADS 8

__global__ void hello_thread(TwinRecs* recs) {
  TWIN_PROLOGUE(recs);
  printf("hello from block %d thread %d on SM %u\n", blockIdx.x, threadIdx.x,
         __twin_smid());
  TWIN_EPILOGUE(recs);
}

int main() {
  dim3 grid(GRID_BLOCKS), block(BLOCK_THREADS);
  TwinProbe probe(grid, block);
  hello_thread<<<grid, block>>>(probe.recs());
  cudaDeviceSynchronize();
  probe.flush("hello_thread", hello_thread);
  return 0;
}
