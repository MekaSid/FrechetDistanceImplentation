# Discrete Fréchet Edit Distance

An implementation of the three **strong discrete Fréchet edit-distance** algorithms from Fox, Nayyeri, Perry, and Raichel, *Fréchet Edit Distance* (SoCG 2024), together with an interactive presentation website.

The ordered reference curve `pi` is fixed. Only `sigma` may be edited. The goal is the minimum number of permitted vertex edits that produces a curve `sigma_prime` satisfying

```text
ordinary_discrete_frechet(pi, sigma_prime) <= delta.
```

This is not continuous Fréchet distance, weak Fréchet distance, or string edit distance.

## Included algorithms

| Public function | Allowed edits to `sigma` | Implemented running time |
|---|---|---:|
| `deletions_only` | delete existing vertices | O(mn) |
| `insertions_only` | insert arbitrary 2D vertices | O(m² + mn) expected |
| `insertions_and_deletions` | both | O(m² + mn) expected |
| `ordinary_discrete_frechet` | none; verifier/baseline | O(mn) |

The insertion algorithms compute the paper's monotone `mu(i)` preprocessing with randomized incremental 2D minimum enclosing balls, then evaluate each DP column with a monotonic minimum queue. Inserted points are not restricted to existing vertices or midpoints.

The implementation follows Sections 5.1, 5.2, and 5.3 of the full paper, corresponding to Theorems 17, 20, and 21 (Theorems 9, 10, and 11 in the conference version).

## Install

Python 3.11 or newer is required.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## Python API

```python
from frechet_edit import (
    ordinary_discrete_frechet,
    deletions_only,
    insertions_only,
    insertions_and_deletions,
)

pi = [(0, 0), (1, 0), (2, 0)]
sigma = [(0, 0), (99, 0), (2, 0)]
delta = 0.0

print(ordinary_discrete_frechet(pi, sigma))
print(deletions_only(pi, sigma, delta).min_edits)           # inf
print(insertions_only(pi, sigma, delta).min_edits)           # inf
print(insertions_and_deletions(pi, sigma, delta).min_edits)  # 2
```

Every edit method returns an `EditResult` with:

- `min_edits`: an integer or `math.inf`;
- `feasible`: whether the restricted edit type has a solution;
- `method`: the method name;
- `mu`: insertion preprocessing values for insertion-based methods;
- `dp_table`: included only with `return_table=True`.

Deletion-only supports `return_witness=True` and independently verifies the edited curve with the ordinary discrete Fréchet implementation. Verified insertion/combined witness reconstruction is deliberately left for a later milestone; requesting it raises `NotImplementedError` instead of returning an unverified curve.

## Command line

Compare all methods on a built-in example:

```bash
python -m frechet_edit --example repair-both
```

Supply curves as semicolon-separated points:

```bash
python -m frechet_edit \
  --pi '0,0;1,0;2,0' \
  --sigma '0,0;99,0;2,0' \
  --delta 0
```

Add `--witness` to include the verified deletion-only edit sequence when that method is feasible.

## Interactive presentation website

The complete static site lives in `dist/`. Run it locally with:

```bash
python3 -m http.server 4173 --directory dist
```

Then open [http://localhost:4173](http://localhost:4173). The site includes:

- draggable curves and click-to-add vertices;
- teaching presets for deletion, insertion, combined repair, and the zero-edit case;
- a live threshold slider and all three edit counts;
- a state-by-state walkthrough that reveals cells in column-major order;
- live curve-pair, leash, and insertion-ball highlights;
- transition candidates with the winning recurrence value highlighted;
- a minimum-enclosing-ball explanation;
- a five-minute presentation talk track.

The browser demo mirrors the paper recurrences. Its minimum enclosing ball routine is a small-input exhaustive implementation for clarity; the Python library uses randomized incremental MEB and the optimized monotonic queue.

## Tests

```bash
pytest
```

The suite covers the six concrete examples from the project brief, boundary equality, repeated points, input validation, brute-force deletion subsequences, optimized-vs-reference insertion DPs, optimized-vs-reference `mu`, edit-count invariants, threshold monotonicity, and deletion-witness verification.

The slow reference implementations are available as:

```python
from frechet_edit.insertion import insertions_only_reference
from frechet_edit.combined import insertions_and_deletions_reference
```

They use an O(m) range minimum inside DP cells and exist only as correctness oracles. Do not use them for performance claims.

## Scope and limitations

- Curves must be nonempty and currently contain finite 2D Euclidean points.
- `delta` must be finite and nonnegative. The paper assumes positive `delta`; zero is supported for tests.
- Only `sigma` is editable. Insertions and deletions cost one each; substitutions are not allowed.
- The Python insertion preprocessing is O(m²) expected time in 2D. DP storage is O(mn).
- Verified edit witnesses for insertion-only and combined edits are not yet exposed. Optimal counts and DP tables are complete and tested.
- No benchmark claims are made yet. The next experimental phase should measure runtime and memory on smooth, random, outlier-corrupted, and undersampled curves.

## References

- Emily Fox, Amir Nayyeri, Jonathan James Perry, and Benjamin Raichel. “Fréchet Edit Distance.” *40th International Symposium on Computational Geometry (SoCG 2024)*. DOI: [10.4230/LIPIcs.SoCG.2024.58](https://doi.org/10.4230/LIPIcs.SoCG.2024.58)
- Full version: [arXiv:2403.12878](https://arxiv.org/abs/2403.12878)

