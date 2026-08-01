// twinprobe.cuh — Tier A capture for the Live CUDA view.
// spec_08 core; spec_12 device_info; spec_14 mid-kernel streaming;
// spec_15 twin_post_json helper; spec_16 declared sampling for huge grids.
//
// Header-only, no dependencies beyond the CUDA runtime, popen(3), and
// std::thread. A lesson uses exactly three things:
//
//   #include "twinprobe.cuh"
//
//   __global__ void my_kernel(..., TwinRecs* recs) {
//       TWIN_PROLOGUE(recs);                 // first statement in the kernel
//       ...
//       TWIN_EPILOGUE(recs);                 // last statement before return
//   }
//
//   TwinProbe probe(grid, block);            // host, before the launch
//   probe.startStreaming();                  // optional (spec_14): live wave
//   my_kernel<<<grid, block>>>(..., probe.recs());
//   probe.flush("my_kernel", my_kernel);     // after the launch; syncs, POSTs
//
// Records live in PINNED, MAPPED host memory: the device writes land in
// host-visible pages while the kernel runs, which is what makes streaming
// possible and removes the flush-time memcpy. Grids above TWIN_MAX_RECORDS
// blocks are sampled deterministically (first 1024 + every k-th) and the
// event says so on the wire ("sampled": true) — declared sampling, never a
// silent truncation.

#ifndef TWINPROBE_CUH
#define TWINPROBE_CUH

#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <thread>

#include <cuda_runtime.h>

#ifndef TWIN_MAX_RECORDS
#define TWIN_MAX_RECORDS 8192u  // env TWIN_MAX_RECORDS overrides at runtime
#endif
#define TWIN_SAMPLE_HEAD 1024u  // blocks always kept 1:1 (the startup wave)

struct TwinBlockRec {
  unsigned smid;
  long long start;
  long long end;
};

// Header + records, in one pinned allocation the device writes through.
struct TwinRecs {
  unsigned head;    // first `head` blocks recorded 1:1
  unsigned stride;  // beyond head, every stride-th block
  unsigned cap;     // record slots available
  unsigned pad_;
  TwinBlockRec rec[1];  // cap entries actually allocated
};

// The SM id this block is executing on (real placement, run-to-run varying).
__device__ __forceinline__ unsigned __twin_smid() {
  unsigned id;
  asm("mov.u32 %0, %%smid;" : "=r"(id));
  return id;
}

__device__ __forceinline__ unsigned __twin_linear_block() {
  return blockIdx.x + gridDim.x * (blockIdx.y + gridDim.y * blockIdx.z);
}

__device__ __forceinline__ bool __twin_thread0() {
  return threadIdx.x == 0 && threadIdx.y == 0 && threadIdx.z == 0;
}

// Which record slot this block writes; -1 = not selected (sampled out).
__device__ __forceinline__ int __twin_slot(const TwinRecs* r) {
  unsigned b = __twin_linear_block();
  if (b < r->head) return (int)b;
  if (r->stride <= 1) return b < r->cap ? (int)b : -1;
  unsigned rel = b - r->head;
  if (rel % r->stride != 0) return -1;
  unsigned s = r->head + rel / r->stride;
  return s < r->cap ? (int)s : -1;
}

#define TWIN_PROLOGUE(recs)                                                    \
  do {                                                                         \
    if (__twin_thread0()) {                                                    \
      int __s = __twin_slot(recs);                                             \
      if (__s >= 0) {                                                          \
        (recs)->rec[__s].smid = __twin_smid();                                 \
        (recs)->rec[__s].start = clock64();                                    \
        (recs)->rec[__s].end = 0;                                              \
      }                                                                        \
    }                                                                          \
  } while (0)

#define TWIN_EPILOGUE(recs)                                                    \
  do {                                                                         \
    if (__twin_thread0()) {                                                    \
      int __s = __twin_slot(recs);                                             \
      if (__s >= 0) (recs)->rec[__s].end = clock64();                          \
    }                                                                          \
  } while (0)

#define TWIN_CHECK(call)                                                       \
  do {                                                                         \
    cudaError_t __e = (call);                                                  \
    if (__e != cudaSuccess) {                                                  \
      fprintf(stderr, "twinprobe: %s failed: %s\n", #call,                     \
              cudaGetErrorString(__e));                                        \
    }                                                                          \
  } while (0)

// POST one JSON event to the backend (spec_15 exposes this for host-side
// events like measurements). Backend down or curl missing -> stderr, and the
// program keeps working as a plain CUDA program.
inline void twin_post_json(const char* json) {
  const char* env = getenv("TWIN_URL");
  char base[256];
  snprintf(base, sizeof(base), "%s", env ? env : "http://localhost:8000");
  size_t blen = strlen(base);  // trailing-slash tolerant (spec_21 #18)
  if (blen > 0 && base[blen - 1] == '/') base[blen - 1] = '\0';
  char cmd[512];
  snprintf(cmd, sizeof(cmd),
           "curl -sf -o /dev/null -X POST -H 'Content-Type: application/json' "
           "--data-binary @- %s/api/live/ingest",
           base);
  FILE* pipe = popen(cmd, "w");
  bool ok = false;
  if (pipe) {
    fwrite(json, 1, strlen(json), pipe);
    ok = pclose(pipe) == 0;
  }
  if (!ok && !getenv("TWIN_QUIET")) {
    // TWIN_QUIET=1 silences this — watch mode with the backend down would
    // otherwise spam a full JSON event per save (spec_21 #18).
    fprintf(stderr, "twinprobe (offline): %s\n", json);
  }
}

// Report the device once per process (spec_12) so the backend sizes the die
// from what this machine actually is.
inline void twin_emit_device_info() {
  static bool sent = false;
  if (sent) return;
  sent = true;
  cudaDeviceProp p;
  if (cudaGetDeviceProperties(&p, 0) != cudaSuccess) return;
  char json[512];
  snprintf(json, sizeof(json),
           "{\"type\":\"device_info\",\"name\":\"%s\",\"smCount\":%d,"
           "\"maxThreadsPerSm\":%d,\"warpSize\":%d,\"vramMb\":%.0f}",
           p.name, p.multiProcessorCount, p.maxThreadsPerMultiProcessor,
           p.warpSize, p.totalGlobalMem / 1048576.0);
  twin_post_json(json);
}

class TwinProbe {
 public:
  TwinProbe(dim3 grid, dim3 block) : grid_(grid), block_(block) {
    twin_emit_device_info();
    nblocks_ = (size_t)grid.x * grid.y * grid.z;

    unsigned cap = TWIN_MAX_RECORDS;
    if (const char* env = getenv("TWIN_MAX_RECORDS")) {
      unsigned v = (unsigned)strtoul(env, nullptr, 10);
      if (v >= 64) cap = v;
    }
    unsigned head = TWIN_SAMPLE_HEAD < cap ? TWIN_SAMPLE_HEAD : cap;
    if (nblocks_ <= cap) {
      head_ = (unsigned)nblocks_;
      stride_ = 1;
      cap_ = (unsigned)nblocks_;
    } else {
      head_ = head;
      stride_ = (unsigned)((nblocks_ - head + (cap - head) - 1) / (cap - head));
      cap_ = cap;
    }

    // Pinned + mapped: the device writes records straight into host memory —
    // flush needs no memcpy, and the streaming poller (spec_14) can watch
    // the buffer while the kernel runs.
    size_t bytes = sizeof(TwinRecs) + (size_t)(cap_ ? cap_ - 1 : 0) * sizeof(TwinBlockRec);
    TWIN_CHECK(cudaHostAlloc((void**)&host_, bytes, cudaHostAllocMapped));
    memset(host_, 0, bytes);
    host_->head = head_;
    host_->stride = stride_;
    host_->cap = cap_;
    TWIN_CHECK(cudaHostGetDevicePointer((void**)&dev_, host_, 0));

    TWIN_CHECK(cudaEventCreate(&ev_start_));
    TWIN_CHECK(cudaEventCreate(&ev_stop_));
    TWIN_CHECK(cudaEventRecord(ev_start_));
  }

  ~TwinProbe() {
    stopStreaming();
    cudaFreeHost(host_);
    cudaEventDestroy(ev_start_);
    cudaEventDestroy(ev_stop_);
  }

  TwinRecs* recs() { return dev_; }

  // spec_14: poll the pinned records while the kernel runs and POST
  // incremental per-SM counts. The reads may be torn mid-write; garbage smid
  // is ignored and end==0 means "still running" — the closing flush() event
  // is always the authoritative picture.
  void startStreaming(int interval_ms = 200) {
    if (streaming_.exchange(true)) return;
    poller_ = std::thread([this, interval_ms] {
      char* json = (char*)malloc(65536);
      if (!json) return;
      while (streaming_.load()) {
        std::this_thread::sleep_for(std::chrono::milliseconds(interval_ms));
        unsigned started[1024] = {0}, ended[1024] = {0};
        unsigned filled = recorded_count();
        for (unsigned i = 0; i < filled; i++) {
          volatile TwinBlockRec* r = &host_->rec[i];
          long long s = r->start;
          unsigned sm = r->smid;
          if (s == 0 || sm >= 1024) continue;  // unwritten or torn
          started[sm]++;
          if (r->end != 0) ended[sm]++;
        }
        size_t n = 0;
        n += snprintf(json + n, 65536 - n,
                      "{\"type\":\"kernel_progress\",\"kernel\":\"%s\","
                      "\"counts\":[",
                      name_);
        bool first = true;
        for (unsigned sm = 0; sm < 1024 && n + 64 < 65536; sm++) {
          if (!started[sm]) continue;
          n += snprintf(json + n, 65536 - n,
                        "%s{\"smid\":%u,\"started\":%u,\"ended\":%u}",
                        first ? "" : ",", sm, started[sm] * stride_est(sm),
                        ended[sm] * stride_est(sm));
          first = false;
        }
        n += snprintf(json + n, 65536 - n, "]}");
        if (!first) twin_post_json(json);
      }
      free(json);
    });
  }

  void setKernelName(const char* name) {
    snprintf(name_, sizeof(name_), "%s", name);
  }

  void stopStreaming() {
    if (!streaming_.exchange(false)) return;
    if (poller_.joinable()) poller_.join();
  }

  template <typename Kernel>
  void flush(const char* name, Kernel kernel) {
    int max_blocks_per_sm = 0;
    int block_threads = (int)((size_t)block_.x * block_.y * block_.z);
    cudaOccupancyMaxActiveBlocksPerMultiprocessor(&max_blocks_per_sm, kernel,
                                                  block_threads, 0);
    cudaDeviceProp prop;
    cudaGetDeviceProperties(&prop, 0);
    double occupancy_pct =
        prop.maxThreadsPerMultiProcessor > 0
            ? 100.0 * max_blocks_per_sm * block_threads /
                  prop.maxThreadsPerMultiProcessor
            : -1.0;
    flush_impl(name, occupancy_pct);
  }

  void flush(const char* name) { flush_impl(name, -1.0); }

 private:
  unsigned recorded_count() const {
    if (nblocks_ <= cap_) return (unsigned)nblocks_;
    unsigned tail = (unsigned)((nblocks_ - head_ + stride_ - 1) / stride_);
    unsigned total = head_ + tail;
    return total < cap_ ? total : cap_;
  }

  // Progress counts are per-record; scale sampled tails so streamed numbers
  // land in the same units as the final event's estimates.
  unsigned stride_est(unsigned) const { return stride_ > 1 ? stride_ : 1; }

  void flush_impl(const char* name, double occupancy_pct) {
    setKernelName(name);
    stopStreaming();
    TWIN_CHECK(cudaEventRecord(ev_stop_));
    TWIN_CHECK(cudaEventSynchronize(ev_stop_));
    float elapsed_ms = 0.0f;
    TWIN_CHECK(cudaEventElapsedTime(&elapsed_ms, ev_start_, ev_stop_));

    unsigned count = recorded_count();
    // 80 bytes/record covers the worst case (2-digit smid + two full-width
    // 19-digit clock64 values + syntax = ~68); 64 could silently truncate.
    size_t cap = 512 + (size_t)count * 80;
    char* json = (char*)malloc(cap);
    if (!json) return;
    size_t n = 0;
    n += snprintf(json + n, cap - n,
                  "{\"type\":\"kernel_launch\",\"kernel\":\"%s\","
                  "\"grid\":[%u,%u,%u],\"block\":[%u,%u,%u],"
                  "\"elapsedMs\":%.4f,",
                  name, grid_.x, grid_.y, grid_.z, block_.x, block_.y,
                  block_.z, elapsed_ms);
    if (stride_ > 1) {
      n += snprintf(json + n, cap - n,
                    "\"sampled\":true,\"sampleStride\":%u,", stride_);
    }
    if (occupancy_pct >= 0.0) {
      n += snprintf(json + n, cap - n, "\"occupancyPct\":%.1f,",
                    occupancy_pct > 100.0 ? 100.0 : occupancy_pct);
    }
    n += snprintf(json + n, cap - n, "\"blocks\":[");
    bool first = true;
    for (unsigned i = 0; i < count && n + 80 < cap; i++) {
      const TwinBlockRec& r = host_->rec[i];
      if (r.start == 0) continue;  // slot never written (short sampled tail)
      n += snprintf(json + n, cap - n,
                    "%s{\"smid\":%u,\"start\":%lld,\"end\":%lld}",
                    first ? "" : ",", r.smid, r.start, r.end);
      first = false;
    }
    n += snprintf(json + n, cap - n, "]}");
    twin_post_json(json);
    free(json);
  }

  dim3 grid_, block_;
  size_t nblocks_ = 0;
  unsigned head_ = 0, stride_ = 1, cap_ = 0;
  TwinRecs* host_ = nullptr;
  TwinRecs* dev_ = nullptr;
  cudaEvent_t ev_start_{}, ev_stop_{};
  std::atomic<bool> streaming_{false};
  std::thread poller_;
  char name_[128] = "kernel";
};

#endif  // TWINPROBE_CUH
