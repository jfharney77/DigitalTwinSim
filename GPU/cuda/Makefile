# CUDA curriculum (spec_09). Targets:
#   make            build every lesson into bin/
#   make run-01     build + run one lesson (any NN prefix works: run-00..run-06)
#   make lint       compile-check every lesson without linking (no GPU needed)
#   make clean
#
# ARCH defaults to Ada (sm_89, the RTX 4060 Laptop GPU). Override for other
# hardware: make ARCH=-arch=sm_86

NVCC ?= nvcc
ARCH ?= -arch=sm_89
FLAGS = -O2 -I.

LESSONS := $(wildcard lessons/*.cu)
BINS := $(patsubst lessons/%.cu,bin/%,$(LESSONS))

all: $(BINS)

bin:
	mkdir -p bin

bin/%: lessons/%.cu twinprobe.cuh | bin
	$(NVCC) $(ARCH) $(FLAGS) -o $@ $<

# `make run-01` runs whichever lesson starts with "01_".
run-%:
	@f=$$(ls lessons/$**.cu 2>/dev/null | head -1); \
	if [ -z "$$f" ]; then echo "no lesson matching '$*'"; exit 1; fi; \
	b=bin/$$(basename $$f .cu); \
	$(MAKE) --no-print-directory $$b && echo "--- $$b" && ./$$b

# `make watch-01` (spec_13): rebuild + rerun on every save of the lesson or
# twinprobe.cuh — the edit->run->see loop becomes save->see. Uses inotifywait
# when installed (apt install inotify-tools), else a 1s mtime poll. Compile
# errors print and the watcher keeps watching; Ctrl-C exits.
watch-%:
	@f=$$(ls lessons/$**.cu 2>/dev/null | head -1); \
	if [ -z "$$f" ]; then echo "no lesson matching '$*'"; exit 1; fi; \
	echo "watching $$f (+ twinprobe.cuh) — Ctrl-C to stop"; \
	echo "tip: name a session first so the timeline chips land in a kept recording"; \
	$(MAKE) --no-print-directory run-$* || true; \
	if command -v inotifywait >/dev/null 2>&1; then \
	  while inotifywait -qq -e close_write $$f twinprobe.cuh; do \
	    sleep 0.3; \
	    $(MAKE) --no-print-directory run-$* || true; \
	  done; \
	else \
	  last=$$(stat -c %Y $$f twinprobe.cuh | sort | tail -1); \
	  while sleep 1; do \
	    now=$$(stat -c %Y $$f twinprobe.cuh | sort | tail -1); \
	    if [ "$$now" != "$$last" ]; then \
	      last=$$now; sleep 0.3; \
	      $(MAKE) --no-print-directory run-$* || true; \
	    fi; \
	  done; \
	fi

# The whole curriculum in sequence — a demo reel for the Live tab (spec_19).
run-all: all
	@for b in $(sort $(BINS)); do echo "--- $$b"; ./$$b || true; done

lint:
	@for f in $(LESSONS); do \
	  echo "lint $$f"; \
	  $(NVCC) $(ARCH) $(FLAGS) -c -o /dev/null $$f || exit 1; \
	done

clean:
	rm -rf bin

.PHONY: all lint clean run-% watch-%
