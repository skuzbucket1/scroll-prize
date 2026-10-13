# Re-inking published segments: didn't work

**Idea.** The community has already published surface volumes of some scrolls. Maybe our ink models would find letters
in them that others missed.

**What we tried** (2026-10-08). `dl_pherc0800.sh` downloads the six public PHerc0800 auto-grown segments (8.64 µm,
pre-rendered). `infer_pherc0800.sh` inks them with three checkpoints, both directions: 36 ink runs.

**What it showed.** No letters. The maps are mottled noise or blank.

**Why it failed.** Published segments have been looked at already. The chance of finding text lies in new geometry,
which is what the pipeline builds.

Site: https://skuzbucket1.github.io/scroll-prize/#run-pherc0800-public
