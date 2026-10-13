# Local spacing from the winding model: didn't work

**Idea.** Give the spiral fitter a local measurement of sheet spacing from the public winding model, instead of one
global number. That should spread the windings correctly inside the scroll.

**What we tried** (2026-10-09 to 2026-10-10, PHerc0191 z 9000–10000):
- `hf_winding.sh` downloads the model. `winding_smoke.sh` is a 256-slab test.
- `winding_band.sh` builds the full cache: 7,102 slabs, 104 GB, about 3 hours on two GPUs. `export_wm.sh` turns it into
  fitter supervision.
- Two fits use it (`queue_after_winding.sh`, `queue_wm.sh`): exp-wm with the outer shell, exp-wm2 without its pull.

**What it showed.** The 104 GB cache reduces to 1 MB of supervision: 6,902 rays, about 130,000 crossings, because the
exporter keeps only each slab's centre ray. exp-wm scored 0.421, the same as every fit with the shell on. exp-wm2 scored
0.461, exactly the pilot baseline. The supervision was neutral.

**Why it failed.** Too sparse. That is about 6,900 rays for 1,000 slices, against roughly 140,000 in the documented PHerc.
Paris 4 run. A cache sized for rays rather than slabs might work, but the documented settings would have needed about
776 GB.

Site: https://skuzbucket1.github.io/scroll-prize/#run-exp-wm2
