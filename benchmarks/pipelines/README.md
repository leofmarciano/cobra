# pipelines

End-to-end pipeline benchmarks that mirror real-world AI and data processing
workflows.  These workloads stress the full Cobra stack, including capture,
compilation, optimization, and heterogeneous execution.

## Workloads

### `parquet_feature_inference` (S02-T1)

A seeded synthetic Parquet dataset is read into pandas, filtered, feature-
engineered, converted to a torch tensor, and scored by a small MLP.  The final
projection is a JSON-serializable summary of per-row scores.

Pipeline stages:

1. **Generate** a mixed-dtype Parquet file (`id`, `category`, `flag`,
   `feature_a`, `feature_b`, `group`, `label`, `score`) with nulls and
   categoricals.  The file is written with `compression="none"`,
   `use_dictionary=False`, and `write_statistics=False` so the bytes are
   hash-stable across runs.
2. **read_parquet** into pandas.
3. **Filter** rows with `feature_a > -1.0`, `flag == True`, and non-null
   `score`.
4. **Feature engineering:**
   - `feature_c = feature_a * feature_b + group`
   - `score_filled = score.fillna(5.0)`
   - one-hot encode `category`
   - z-score normalize all numeric columns
5. **Tensor conversion** to `torch.float64`.
6. **MLP inference** with a seeded two-layer network.
7. **Projection** to summary statistics: `n_rows`, `mean_score`, `p95_score`,
   `p99_score`, `score_sum`.

#### Variants

- `b0` — ordinary eager Python: pandas + torch on CUDA when available.
- `b1` — deferred to S02-T4 (`torch.compile` + `cudf.pandas` where applicable).

#### Correctness oracle

The manifest uses `comparator: approx` (plan §33.4).

| Field | Type | Comparison |
|---|---|---|
| `n_rows` | `int` | exact |
| `mean_score`, `p95_score`, `p99_score`, `score_sum` | `float64` | `rtol=1.0e-5`, `atol=1.0e-8` |
| `float32` intermediate values (e.g. raw MLP outputs if exposed) | `float32` | `rtol=1.0e-4`, `atol=1.0e-6` |

The `approx` comparator applies exact equality to integers, strings, and
booleans and `math.isclose` with the per-dtype tolerances above for floats.
