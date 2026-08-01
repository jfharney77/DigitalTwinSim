# twininject (spec_17) — CUPTI injection library. Needs the CUDA toolkit;
# CUPTI ships under $(CUDA_HOME)/extras/CUPTI.
CUDA_HOME ?= /usr/local/cuda
CUPTI := $(CUDA_HOME)/extras/CUPTI

libtwininject.so: twininject.cc
	g++ -shared -fPIC -O2 -std=c++17 \
	  -I$(CUDA_HOME)/include -I$(CUPTI)/include \
	  -L$(CUPTI)/lib64 -L$(CUDA_HOME)/lib64 \
	  -o $@ $< -lcupti -lcudart

clean:
	rm -f libtwininject.so

.PHONY: clean
