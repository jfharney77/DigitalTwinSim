// twininject — Tier C capture (spec_17): zero-code-change kernel timing for
// ANY CUDA program via CUPTI's injection hook.
//
//   CUDA_INJECTION64_PATH=$PWD/libtwininject.so  ./your-cuda-app
//   (or: ../twin-run ./your-cuda-app args...)
//
// What it captures: CUPTI activity records for concurrent kernels — demangled
// name, grid/block, start/end timestamps — posted to the backend as
// kernel_launch events with "source":"cupti" and NO block records (the
// activity API carries timing, not per-block SM placement; the die view shows
// a timeline chip and labels it timing-only, never fake placement).
//
// WSL2/Windows note: full profiling counters need NVIDIA Control Panel ->
// Developer -> "Allow access to GPU performance counters to all users".
// Activity tracing (what this library uses) works without it; if CUPTI still
// reports insufficient privileges, we print the fix once and go inert — the
// host app must never be harmed by the probe.
//
// Build (needs the CUDA toolkit incl. CUPTI):  make -C twininject

#include <cuda_runtime.h>
#include <cupti.h>

#include <cinttypes>
#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <cxxabi.h>

#define BUF_SIZE (2 * 1024 * 1024)
#define ALIGN_SIZE 8
#define ALIGN(buf, align) \
  ((uint8_t*)(((uintptr_t)(buf) + (align)-1) & ~((uintptr_t)(align)-1)))

static bool g_disabled = false;

static void post_json(const char* json) {
  const char* base = getenv("TWIN_URL");
  if (!base) base = "http://localhost:8000";
  char cmd[512];
  snprintf(cmd, sizeof(cmd),
           "curl -sf -o /dev/null -X POST -H 'Content-Type: application/json' "
           "--data-binary @- %s/api/live/ingest",
           base);
  FILE* pipe = popen(cmd, "w");
  if (pipe) {
    fwrite(json, 1, strlen(json), pipe);
    if (pclose(pipe) == 0) return;
  }
  fprintf(stderr, "twininject (offline): %s\n", json);
}

static void emit_device_info() {
  // Keep the backend's die sized to this machine (spec_12). CUPTI gives us
  // the device activity record, but the simplest reliable source is the
  // driver API already loaded in this process.
  int count = 0;
  if (cudaGetDeviceCount(&count) != cudaSuccess || count == 0) return;
  cudaDeviceProp p;
  if (cudaGetDeviceProperties(&p, 0) != cudaSuccess) return;
  char json[512];
  snprintf(json, sizeof(json),
           "{\"type\":\"device_info\",\"name\":\"%s\",\"smCount\":%d,"
           "\"maxThreadsPerSm\":%d,\"warpSize\":%d,\"vramMb\":%.0f}",
           p.name, p.multiProcessorCount, p.maxThreadsPerMultiProcessor,
           p.warpSize, p.totalGlobalMem / 1048576.0);
  post_json(json);
}

static void emit_kernel(const CUpti_ActivityKernel4* k) {
  const char* raw = k->name ? k->name : "kernel";
  int status = 0;
  char* demangled = abi::__cxa_demangle(raw, nullptr, nullptr, &status);
  const char* name = (status == 0 && demangled) ? demangled : raw;

  // Strip template/argument clutter for the chip label: keep up to '('.
  char short_name[128];
  snprintf(short_name, sizeof(short_name), "%s", name);
  if (char* paren = strchr(short_name, '(')) *paren = '\0';

  double elapsed_ms = (double)(k->end - k->start) / 1e6;  // ns -> ms
  char json[768];
  snprintf(json, sizeof(json),
           "{\"type\":\"kernel_launch\",\"kernel\":\"%s\","
           "\"grid\":[%d,%d,%d],\"block\":[%d,%d,%d],"
           "\"elapsedMs\":%.4f,\"source\":\"cupti\",\"blocks\":[]}",
           short_name, k->gridX, k->gridY, k->gridZ, k->blockX, k->blockY,
           k->blockZ, elapsed_ms);
  post_json(json);
  free(demangled);
}

static void CUPTIAPI buffer_requested(uint8_t** buffer, size_t* size,
                                      size_t* max_num_records) {
  uint8_t* raw = (uint8_t*)malloc(BUF_SIZE + ALIGN_SIZE);
  *buffer = ALIGN(raw, ALIGN_SIZE);
  *size = BUF_SIZE;
  *max_num_records = 0;
}

static void CUPTIAPI buffer_completed(CUcontext, uint32_t, uint8_t* buffer,
                                      size_t, size_t valid_size) {
  CUpti_Activity* record = nullptr;
  while (!g_disabled) {
    CUptiResult res = cuptiActivityGetNextRecord(buffer, valid_size, &record);
    if (res == CUPTI_ERROR_MAX_LIMIT_REACHED) break;
    if (res != CUPTI_SUCCESS) break;
    if (record->kind == CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL ||
        record->kind == CUPTI_ACTIVITY_KIND_KERNEL) {
      emit_kernel((const CUpti_ActivityKernel4*)record);
    }
  }
  free(buffer - ((uintptr_t)buffer % ALIGN_SIZE));
}

// The CUDA runtime calls this once when CUDA_INJECTION64_PATH names us.
extern "C" int InitializeInjection() {
  CUptiResult res = cuptiActivityRegisterCallbacks(buffer_requested,
                                                   buffer_completed);
  if (res != CUPTI_SUCCESS) {
    fprintf(stderr, "twininject: CUPTI unavailable (%d); running inert.\n",
            res);
    g_disabled = true;
    return 1;  // never harm the host app
  }
  res = cuptiActivityEnable(CUPTI_ACTIVITY_KIND_CONCURRENT_KERNEL);
  if (res == CUPTI_ERROR_INSUFFICIENT_PRIVILEGES) {
    fprintf(stderr,
            "twininject: GPU perf counters are restricted. Fix: NVIDIA "
            "Control Panel -> Developer -> Allow access to GPU performance "
            "counters to all users. Running inert.\n");
    g_disabled = true;
    return 1;
  }
  if (res != CUPTI_SUCCESS) {
    cuptiActivityEnable(CUPTI_ACTIVITY_KIND_KERNEL);  // serial fallback
  }
  emit_device_info();
  atexit([] { cuptiActivityFlushAll(1); });
  return 1;
}
