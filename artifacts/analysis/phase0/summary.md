# Benchmark Analysis Summary

- Primary metric: `wall_time_ns`
- Confidence level: 95%
- Bootstrap resamples: 10000
- Random seed: 42

**Suite geometric-mean speedup:** 0.945x

## Workload: cv_preprocess_inference_postprocess

- Baseline variant: `b0`
- Workload geometric-mean speedup: 0.985x

| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup | Speedup CI | Significant |
|---------|--------:|------------:|---------:|---------:|---:|--------:|------------|-------------|
| b0 | 30 | 234.842 | 267.084 | 271.083 | 0.051909838406481223 | 1.000x | [1.000x, 1.000x] | no |
| b1 | 30 | 238.323 | 304.130 | 311.052 | 0.10201188536122303 | 0.985x | [0.971x, 1.021x] | no |

## Workload: model_ensemble

- Baseline variant: `b0`
- Workload geometric-mean speedup: 0.951x

| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup | Speedup CI | Significant |
|---------|--------:|------------:|---------:|---------:|---:|--------:|------------|-------------|
| b0 | 30 | 87.443 | 92.707 | 93.133 | 0.03307370899488142 | 1.000x | [1.000x, 1.000x] | no |
| b1 | 30 | 91.934 | 106.034 | 176.767 | 0.21598791738142448 | 0.951x | [0.938x, 0.971x] | yes |

## Workload: parquet_feature_inference

- Baseline variant: `b0`
- Workload geometric-mean speedup: 0.899x

| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup | Speedup CI | Significant |
|---------|--------:|------------:|---------:|---------:|---:|--------:|------------|-------------|
| b0 | 30 | 46.337 | 54.483 | 55.587 | 0.07736714852175183 | 1.000x | [1.000x, 1.000x] | no |
| b1 | 30 | 51.531 | 61.302 | 63.372 | 0.09067537115226026 | 0.899x | [0.835x, 0.950x] | yes |
