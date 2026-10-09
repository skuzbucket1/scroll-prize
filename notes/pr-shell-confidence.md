# PR: spiral-fitting: make shell confidence a proximity measure; warn when the shell loss has no valid samples

Branch: `skuzbucket1/villa:fix/shell-confidence` → `ScrollPrize/villa:main`
Compare/open: https://github.com/ScrollPrize/villa/compare/main...skuzbucket1:villa:fix/shell-confidence?expand=1

## Title
spiral-fitting: make shell confidence a proximity measure; warn when the shell loss has no valid samples

## Body
I fitted PHerc0191 (z 9000–10000, 10k steps) with an outer shell derived from the masked CT, sampled every 8 slices (720/720 angular bins per row, 1.58 M valid points), `input_use_outer_shell: true`, `loss_weight_shell_outer: 1.0`, `shell_outer_winding_idx: 105`. The shell loaded fine:

```
shell polar table: 1321 z bins x 720 theta bins, 119520/951120 occupied (12.6%)
using configured shell_outer_winding_idx = 105
```

but every step line reported `shell_outer = 0.0` from step 0 to 9800, no shell metrics were ever emitted, and the exported outer winding ended 7 mm inside the papyrus. No warning anywhere.

Cause: `ShellPolarMap` builds its confidence as `gaussian_filter(valid) / max`. With one occupied row in eight, the maximum comes from the `mode='nearest'` replicated edge row, every interior bin lands at ~0.22, below `shell_min_confidence` 0.25, so every lookup is invalid and `_masked_mean` returns 0. Reproduced outside the fitter by building the same `ShellPolarMap` and querying 3,600 points at z 9525:

Before (upstream `main`):
```
confidence min/mean/max 0.2187 0.2261 1.0   shell_min_confidence 0.25
query: valid fraction 0.0
```

Fix: confidence is now `exp(-d²/2)` where `d` is the distance to the nearest shell sample in units of the smoothing sigmas (1.0 on a sample, ~0 far from any sample), so it no longer depends on the table's edges or sampling density. The shell loss also prints one warning at a metrics step when it has no valid samples instead of silently contributing 0.

After (this branch, same shell):
```
confidence min/mean/max 0.6065 0.8526 1.0
query: valid fraction 1.0
```
and with a shell sampled every slice: `valid fraction 1.0, confidence 1.0` (unchanged behaviour for dense shells).

Regenerating the shell with one row per slice was my workaround; with it the shell loss engages (`shell_outer = 176.9` at step 9800 on the same fit), which is how I noticed the sparse case had been a no-op.
