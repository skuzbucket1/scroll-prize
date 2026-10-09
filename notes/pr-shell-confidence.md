# PR 2 — shell confidence as proximity + warning (finding #7)

Open: https://github.com/ScrollPrize/villa/compare/main...skuzbucket1:villa:fix/shell-confidence?expand=1
Tested commit: `eec8eda20` on branch `fix/shell-confidence` (one commit on top of upstream `a329895ea`).

## Title
spiral-fitting: shell confidence as proximity; warn when the shell loss has no valid samples

## Body

**In one sentence:** Use an outer shell that is sampled every few slices (not every slice) and actually have the `shell_outer` loss constrain the fit, with a warning when it cannot.

**One real example:** Starting with PHerc0191 (z 9000–10000, 10k steps) and an outer shell derived from the masked CT every 8 slices (720/720 angular bins per row, 1.58 M points), I fitted with `input_use_outer_shell: true`, `loss_weight_shell_outer: 1.0`, `shell_outer_winding_idx: 105`, and with this branch the shell lookups are valid everywhere (confidence 0.61–1.0) so the loss engages; on `main` the same run logged `shell_outer = 0.0` for all 10k steps.

**Before:** The shell loads (`shell polar table: 1321 z bins x 720 theta bins, 119520/951120 occupied (12.6%)`, `using configured shell_outer_winding_idx = 105`) but every step line shows `shell_outer = 0.0`, no shell metrics are emitted, nothing warns, and the exported outer winding ends 7 mm inside the papyrus. Cause: `ShellPolarMap` sets confidence = `gaussian_filter(valid) / max`; with one occupied row in eight the max comes from the `mode='nearest'` replicated edge row, every interior bin lands at ~0.22, below `shell_min_confidence` 0.25, so every lookup is invalid and `_masked_mean` returns 0.

**After this PR:** Confidence is `exp(-d²/2)` with `d` the distance to the nearest shell sample in units of the smoothing sigmas: 1.0 on a sample, ~0 far from any sample, independent of the table's edges or sampling density. `get_shell_outer_loss` prints one warning at a metrics step when it has no valid samples instead of silently returning 0. Dense (every-slice) shells behave exactly as before (confidence 1.0).

**Proof:** Same shell, same umbilicus, same config defaults, `ShellPolarMap` built exactly as the fitter does (z 8840–10160, 720 bins) and queried at 3,600 points at z 9525, radii 10–30 mm:
```
# upstream main
confidence min/mean/max 0.2187 0.2261 1.0   shell_min_confidence 0.25
query: valid fraction 0.0

# this branch
confidence min/mean/max 0.6065 0.8526 1.0
query: valid fraction 1.0

# this branch, shell sampled every slice (sanity: unchanged behaviour)
query: valid fraction 1.0  confidence 1.0
```
Look at `valid fraction`: 0.0 means the shell loss was a no-op for the whole fit. The full 10k-step logs of the sparse-shell fit (`shell_outer = 0.0` throughout) and the dense-shell fit (`shell_outer = 176.9` at step 9800) are available on request.

**Why / where this is useful:** Anyone supplying an outer shell that is not sampled at every z (a boundary extracted at a coarser pyramid level, or any subsampled tifxyz) currently gets a fit where the shell does nothing and nothing says so. With this the shell works at any sampling density, and when it genuinely cannot (wrong z range, empty shell) the run says so once.

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

- Method: `spiral-fitting/fit_spiral.py` `ShellPolarMap.__init__`: replace the smoothed-occupancy-divided-by-max confidence with `scipy.ndimage.distance_transform_edt(~valid_ext, sampling=1/sigma)` → `exp(-0.5·d²)`, cropped from the wrapped table as the radius already is. `spiral-fitting/losses.py` `get_shell_outer_loss`: one-time `WARNING` when `valid.any()` is false at a metrics step.
- Tested commit `eec8eda20`. Ubuntu 24.04, Python 3.14.8 via uv, `uv sync` in `villa/spiral-fitting`, CPU for the lookup test, RTX 3060 Ti for the fits.
- Data: PHerc0191 `20250821151635` masked volume (level 2 for the shell boundary), `umbilicus.json` from `vc_gen_umbilicus` on the public normal grids; shell written as tifxyz (x/y/z.tif + meta.json with `scale`).
- Limitation: the confidence scale now depends on `shell_table_smooth_sigma_z/theta` (defaults 4.0 / 1.0): a shell sampled every N slices has minimum confidence `exp(-(N/2)²/(2·σz²))`, i.e. 0.61 for N = 8, 0.04 for N = 20, so very sparse shells still fall below `shell_min_confidence` by design.

## Re-run the proof yourself on the box (≈40 s each)
```
ssh tbienapfl@100.74.214.106
PY=/mnt/nvme/scroll-prizes/villa/spiral-fitting/.venv/bin/python
sed 's|f"{S}/outer_shell"|f"{S}/outer_shell_dz8"|' ~/scroll-prizes/bin/shell_lookup_test.py > /tmp/shell_lookup_dz8.py
cd /mnt/nvme/scroll-prizes/villa/spiral-fitting && CUDA_VISIBLE_DEVICES= $PY /tmp/shell_lookup_dz8.py | grep -E "confidence|valid fraction"     # before: valid fraction 0.0
cd /mnt/nvme/scroll-prizes/wt/shell-confidence/spiral-fitting && CUDA_VISIBLE_DEVICES= $PY /tmp/shell_lookup_dz8.py | grep -E "confidence|valid fraction"   # after: valid fraction 1.0
```
