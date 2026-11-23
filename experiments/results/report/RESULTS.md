# Experimental Results Brief

Generated from `raw.csv` with 6000 measured trials across 5 scenarios. Python `3.13.5`, NumPy `2.5.5`, commit `01b68eedc4037182e1187ef1ab281942765ecaff` (dirty working tree).

## Methodology

Each reported runtime uses `time.perf_counter_ns`. Repetitions operate on the same seeded input within a case. Warmups are excluded. Memory is measured in a separate invocation with `tracemalloc`, so it is not included in the timed interval. Reference implementations are limited by the configuration and checked against optimized results.

## Key findings

### Scaling against the theoretical work expression

| Algorithm | Median slope | Minimum | Maximum |
| --- | --- | --- | --- |
| compute_mu | 0.999 | 0.817 | 1.011 |
| deletions_only | 0.996 | 0.987 | 1.018 |
| insertions_and_deletions | 0.990 | 0.851 | 1.101 |
| insertions_only | 0.986 | 0.788 | 1.057 |
| ordinary_discrete_frechet | 1.001 | 0.985 | 1.010 |

A median slope near 1 supports proportional growth with the stated work expression; the range shows how much the estimate changes across scenarios and size regimes.

### Reference/optimized runtime ratio at the largest compared m

| Optimized component | Largest m | Median ratio | Compared cases |
| --- | --- | --- | --- |
| insertions_only | 128 | 1.04× | 30 |
| insertions_and_deletions | 128 | 1.01× | 30 |
| compute_mu | 64 | 55.78× | 30 |

A ratio above 1 favors the optimized implementation. Ratios near 1 are a useful negative result: asymptotic improvement need not produce a large practical win at the tested sizes and language/library constants.

### Mean feasibility across generated cases

| δ | Deletions | Insertions | Combined |
| --- | --- | --- | --- |
| 0.05 | 0.164 | 0.036 | 1.000 |
| 0.15 | 0.873 | 0.782 | 1.000 |
| 0.3 | 0.982 | 0.800 | 1.000 |

## Overall timing inventory

| Algorithm | Trials | Overall median (ms) |
| --- | --- | --- |
| compute_mu | 825 | 9.423 |
| compute_mu_reference | 525 | 116.4 |
| deletions_only | 825 | 5.794 |
| insertions_and_deletions | 825 | 21.2 |
| insertions_and_deletions_reference | 675 | 16.27 |
| insertions_only | 825 | 18.89 |
| insertions_only_reference | 675 | 15.31 |
| ordinary_discrete_frechet | 825 | 6.157 |

## Empirical scaling

A slope near 1 means elapsed time grows proportionally to the algorithm's stated theoretical work expression. Treat fits with few points or low R² as descriptive only.

| Algorithm | Scenario | Regime | Sizes | Slope | R² |
| --- | --- | --- | --- | --- | --- |
| compute_mu | outliers | balanced | 5 | 1.002 | 1.000 |
| compute_mu | outliers | m-dominant | 3 | 1.001 | 1.000 |
| compute_mu | random_walk | balanced | 5 | 0.930 | 0.944 |
| compute_mu | random_walk | m-dominant | 3 | 0.817 | 0.984 |
| compute_mu | repeated | balanced | 5 | 0.984 | 1.000 |
| compute_mu | repeated | m-dominant | 3 | 1.011 | 1.000 |
| compute_mu | smooth | balanced | 5 | 0.993 | 1.000 |
| compute_mu | smooth | m-dominant | 3 | 0.999 | 1.000 |
| compute_mu | undersampled | balanced | 5 | 1.000 | 1.000 |
| compute_mu | undersampled | m-dominant | 3 | 1.008 | 1.000 |
| deletions_only | outliers | balanced | 5 | 0.995 | 1.000 |
| deletions_only | outliers | m-dominant | 3 | 1.010 | 1.000 |
| deletions_only | outliers | n-dominant | 3 | 1.011 | 1.000 |
| deletions_only | random_walk | balanced | 5 | 0.995 | 1.000 |
| deletions_only | random_walk | m-dominant | 3 | 0.988 | 1.000 |
| deletions_only | random_walk | n-dominant | 3 | 0.994 | 1.000 |
| deletions_only | repeated | balanced | 5 | 0.987 | 1.000 |
| deletions_only | repeated | m-dominant | 3 | 1.018 | 1.000 |
| deletions_only | repeated | n-dominant | 3 | 0.996 | 1.000 |
| deletions_only | smooth | balanced | 5 | 0.991 | 1.000 |
| deletions_only | smooth | m-dominant | 3 | 0.997 | 1.000 |
| deletions_only | smooth | n-dominant | 3 | 1.004 | 1.000 |
| deletions_only | undersampled | balanced | 5 | 0.996 | 1.000 |
| deletions_only | undersampled | m-dominant | 3 | 1.008 | 1.000 |
| deletions_only | undersampled | n-dominant | 3 | 0.991 | 1.000 |
| insertions_and_deletions | outliers | balanced | 5 | 0.997 | 1.000 |
| insertions_and_deletions | outliers | m-dominant | 3 | 1.041 | 1.000 |
| insertions_and_deletions | outliers | n-dominant | 3 | 0.854 | 1.000 |
| insertions_and_deletions | random_walk | balanced | 5 | 0.952 | 0.977 |
| insertions_and_deletions | random_walk | m-dominant | 3 | 0.870 | 0.982 |
| insertions_and_deletions | random_walk | n-dominant | 3 | 0.930 | 0.985 |
| insertions_and_deletions | repeated | balanced | 5 | 0.990 | 1.000 |
| insertions_and_deletions | repeated | m-dominant | 3 | 1.101 | 1.000 |
| insertions_and_deletions | repeated | n-dominant | 3 | 0.851 | 1.000 |
| insertions_and_deletions | smooth | balanced | 5 | 0.995 | 1.000 |
| insertions_and_deletions | smooth | m-dominant | 3 | 1.040 | 1.000 |
| insertions_and_deletions | smooth | n-dominant | 3 | 0.853 | 0.999 |
| insertions_and_deletions | undersampled | balanced | 5 | 1.004 | 1.000 |
| insertions_and_deletions | undersampled | m-dominant | 3 | 1.043 | 1.000 |
| insertions_and_deletions | undersampled | n-dominant | 3 | 0.853 | 0.999 |
| insertions_only | outliers | balanced | 5 | 0.999 | 1.000 |
| insertions_only | outliers | m-dominant | 3 | 1.057 | 1.000 |
| insertions_only | outliers | n-dominant | 3 | 0.788 | 0.999 |
| insertions_only | random_walk | balanced | 5 | 0.950 | 0.975 |
| insertions_only | random_walk | m-dominant | 3 | 0.879 | 0.980 |
| insertions_only | random_walk | n-dominant | 3 | 0.891 | 0.977 |
| insertions_only | repeated | balanced | 5 | 0.986 | 0.997 |
| insertions_only | repeated | m-dominant | 3 | 1.056 | 1.000 |
| insertions_only | repeated | n-dominant | 3 | 0.835 | 0.998 |
| insertions_only | smooth | balanced | 5 | 0.991 | 1.000 |
| insertions_only | smooth | m-dominant | 3 | 1.050 | 1.000 |
| insertions_only | smooth | n-dominant | 3 | 0.819 | 0.998 |
| insertions_only | undersampled | balanced | 5 | 0.990 | 1.000 |
| insertions_only | undersampled | m-dominant | 3 | 1.051 | 1.000 |
| insertions_only | undersampled | n-dominant | 3 | 0.803 | 0.999 |
| ordinary_discrete_frechet | outliers | balanced | 5 | 1.001 | 1.000 |
| ordinary_discrete_frechet | outliers | m-dominant | 3 | 1.006 | 1.000 |
| ordinary_discrete_frechet | outliers | n-dominant | 3 | 1.010 | 1.000 |
| ordinary_discrete_frechet | random_walk | balanced | 5 | 1.001 | 1.000 |
| ordinary_discrete_frechet | random_walk | m-dominant | 3 | 1.005 | 1.000 |
| ordinary_discrete_frechet | random_walk | n-dominant | 3 | 0.995 | 1.000 |
| ordinary_discrete_frechet | repeated | balanced | 5 | 0.985 | 1.000 |
| ordinary_discrete_frechet | repeated | m-dominant | 3 | 1.002 | 1.000 |
| ordinary_discrete_frechet | repeated | n-dominant | 3 | 1.003 | 1.000 |
| ordinary_discrete_frechet | smooth | balanced | 5 | 0.998 | 1.000 |
| ordinary_discrete_frechet | smooth | m-dominant | 3 | 0.997 | 1.000 |
| ordinary_discrete_frechet | smooth | n-dominant | 3 | 1.000 | 1.000 |
| ordinary_discrete_frechet | undersampled | balanced | 5 | 0.999 | 1.000 |
| ordinary_discrete_frechet | undersampled | m-dominant | 3 | 1.001 | 1.000 |
| ordinary_discrete_frechet | undersampled | n-dominant | 3 | 1.000 | 1.000 |

## Interpretation checklist

- Explain whether optimized and reference implementations return the same edit counts.
- Compare runtime trends with `m*n`, `m^2 + m*n`, and the reference work models.
- Discuss crossover points where preprocessing dominates or optimization pays off.
- Report feasibility and edit-count differences as edit-model behavior, not correctness errors.
- State that `tracemalloc` is a traced-allocation measure rather than total process RSS.
- Record unexpected or negative results; do not remove them solely because they weaken a hypothesis.

## Generated artifacts

- `summary.csv`: medians, quartiles, feasibility, edit counts, and memory by case.
- `scaling.csv`: log-log slopes against each optimized algorithm's theoretical work.
- `figures/`: report-ready PNG and PDF versions of all plots.
