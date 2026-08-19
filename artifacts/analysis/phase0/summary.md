# Benchmark Analysis Summary

- Primary metric: `wall_time_ns`
- Confidence level: 95%
- Bootstrap resamples: 10000
- Random seed: 42

**Suite geometric-mean speedup:** 0.775x

## Workload: cv_preprocess_inference_postprocess

- Baseline variant: `b0`
- Workload geometric-mean speedup: 1.023x

| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup | Speedup CI | Significant |
|---------|--------:|------------:|---------:|---------:|---:|--------:|------------|-------------|
| b0 | 30 | 26.343 | 31.815 | 33.251 | 0.07696911533622443 | 1.000x | [1.000x, 1.000x] | no |
| b1 | 30 | 25.743 | 27.194 | 27.348 | 0.035183661292609435 | 1.023x | [0.998x, 1.064x] | no |

## Workload: model_ensemble

- Baseline variant: `b0`
- Workload geometric-mean speedup: 0.950x

| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup | Speedup CI | Significant |
|---------|--------:|------------:|---------:|---------:|---:|--------:|------------|-------------|
| b0 | 30 | 8.255 | 8.736 | 8.837 | 0.038453534609707844 | 1.000x | [1.000x, 1.000x] | no |
| b1 | 30 | 8.686 | 9.716 | 9.924 | 0.06071949265203185 | 0.950x | [0.901x, 0.977x] | yes |

## Workload: parquet_feature_inference

- Baseline variant: `b0`
- Workload geometric-mean speedup: 0.478x

| Variant | Samples | Median (ms) | p95 (ms) | p99 (ms) | CV | Speedup | Speedup CI | Significant |
|---------|--------:|------------:|---------:|---------:|---:|--------:|------------|-------------|
| b0 | 30 | 25.065 | 27.108 | 27.725 | 0.040454335657899104 | 1.000x | [1.000x, 1.000x] | no |
| b1 | 30 | 52.391 | 65.816 | 68.771 | 0.09731551249743733 | 0.478x | [0.455x, 0.495x] | yes |
