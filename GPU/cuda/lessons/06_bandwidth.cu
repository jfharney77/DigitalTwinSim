// Lesson 06 — find the roof.
//
// Concept: a pure streaming kernel (grid-stride copy) does almost no math —
// one read, one write per element — so its speed IS the memory system's
// speed. The achieved GB/s plateaus near the 4060's ~256 GB/s ceiling no
// matter how much compute sits idle. That ceiling is the "roof" in the
// roofline model the Simulator tab's read-out uses (spec_04): workloads
// below the ridge intensity live here, on the memory roof.
//
// What you'll see: GPU util pinned high (start twin-sampler) while the
// printed GB/s stops improving; power climbs toward the TGP.
//
// Experiment: compute the arithmetic intensity where this die's ridge sits
// (peak FLOP/s / peak bytes/s) and check it against the Simulator tab's
// memory-bound / compute-bound verdict for small vs large N.

#include <cstdio>
#include <cstdlib>
#include <cuda_runtime.h>

#include "twinprobe.cuh"

#define N (1 << 26)  // 64M floats = 256 MB in, 256 MB out
#define BLOCK_THREADS 256
#define GRID_BLOCKS 1024  // grid-stride: a fixed grid walks the whole array

__global__ void stream_copy(const float* in, float* out, int n,
                            TwinRecs* recs) {
  TWIN_PROLOGUE(recs);
  for (int i = blockIdx.x * blockDim.x + threadIdx.x; i < n;
       i += gridDim.x * blockDim.x) {
    out[i] = in[i];
  }
  TWIN_EPILOGUE(recs);
}

int main() {
  size_t bytes = (size_t)N * sizeof(float);
  float *din, *dout;
  cudaMalloc(&din, bytes);
  cudaMalloc(&dout, bytes);
  cudaMemset(din, 1, bytes);

  dim3 block(BLOCK_THREADS), grid(GRID_BLOCKS);

  // Warm-up (scratch records, never flushed), then a timed run.
  TwinProbe warmup(grid, block);
  stream_copy<<<grid, block>>>(din, dout, N, warmup.recs());
  cudaDeviceSynchronize();

  TwinProbe probe(grid, block);
  probe.setKernelName("stream_copy");
  probe.startStreaming();  // spec_14: watch the wave mid-kernel on the die
  cudaEvent_t t0, t1;
  cudaEventCreate(&t0);
  cudaEventCreate(&t1);
  cudaEventRecord(t0);
  stream_copy<<<grid, block>>>(din, dout, N, probe.recs());
  cudaEventRecord(t1);
  cudaEventSynchronize(t1);
  float ms = 0.0f;
  cudaEventElapsedTime(&ms, t0, t1);
  probe.flush("stream_copy", stream_copy);

  double moved_gb = 2.0 * bytes / 1e9;  // read + write
  double gbps = moved_gb / (ms / 1000.0);
  printf("moved %.1f GB in %.2f ms -> %.0f GB/s (spec sheet: ~256 GB/s)\n",
         moved_gb, ms, gbps);

  // spec_15: this measurement calibrates the Simulator tab's roofline.
  char m[160];
  snprintf(m, sizeof(m),
           "{\"type\":\"measurement\",\"metric\":\"stream_gbps\","
           "\"value\":%.1f,\"kernel\":\"stream_copy\"}",
           gbps);
  twin_post_json(m);

  cudaFree(din);
  cudaFree(dout);
  return 0;
}
