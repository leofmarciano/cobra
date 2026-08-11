# Benchmark Analysis Summary

- Primary metric: `wall_time_ns`
- Confidence level: 95%
- Bootstrap resamples: 10000
- Random seed: 42

**Suite geometric-mean speedup:** 0.959x

## Workload: cv_preprocess_inference_postprocess

- Baseline variant: `b0`
- Workload geometric-mean speedup: 1.041x

| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup | Speedup CI | Significant |
|---------|--------:|------------:|---------:|---------:|---:|--------:|------------|-------------|
| b0 | 30 | 237.770 | 268.058 | 299.551 | 0.0727324880547055 | 1.000x | [1.000x, 1.000x] | no |
| b1 | 30 | 228.427 | 272.914 | 282.508 | 0.07332394812910971 | 1.041x | [1.004x, 1.062x] | yes |

## Workload: model_ensemble

- Baseline variant: `b0`
- Workload geometric-mean speedup: 0.944x

| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup | Speedup CI | Significant |
|---------|--------:|------------:|---------:|---------:|---:|--------:|------------|-------------|
| b0 | 30 | 72.858 | 80.984 | 87.173 | 0.05270694356361977 | 1.000x | [1.000x, 1.000x] | no |
| b1 | 30 | 77.156 | 81.771 | 89.100 | 0.04408846439517186 | 0.944x | [0.928x, 0.961x] | yes |

## Workload: parquet_feature_inference

- Baseline variant: `b0`
- Workload geometric-mean speedup: 0.897x

| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup | Speedup CI | Significant |
|---------|--------:|------------:|---------:|---------:|---:|--------:|------------|-------------|
| b0 | 30 | 380.098 | 423.745 | 455.532 | 0.05402927676693616 | 1.000x | [1.000x, 1.000x] | no |
| b1 | 30 | 423.922 | 462.378 | 509.109 | 0.05760224366387811 | 0.897x | [0.868x, 0.924x] | yes |
