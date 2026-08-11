# CobraToGPU

This directory implements the lowering of Cobra IR to GPU kernel representations such as CUDA or ROCm. It transforms tensor and parallel operations into grid-level launches, manages device memory placement, and prepares code for GPU runtime execution.
