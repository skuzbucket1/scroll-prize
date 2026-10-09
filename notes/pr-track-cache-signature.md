# PR 1 — track-cache signature tolerant of truncated mtimes (finding #6)

Open: https://github.com/ScrollPrize/villa/compare/main...skuzbucket1:villa:fix/track-cache-signature?expand=1
Tested commit: `9c41cb9f5` on branch `fix/track-cache-signature` (one commit on top of upstream `a329895ea`).

## Title
spiral-fitting: accept shipped track caches after download (mtime precision)

## Body

**In one sentence:** Use the track-crossing cache and packed track store that ship next to a tracks DBM after downloading them, instead of rebuilding the crossings from the 9.9 GB DBM on every fit.

**One real example:** Starting with the public PHerc0191 tracks `PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm` and its shipped `.crossings.npz` (2.4 GB), mirrored with a plain HTTP download, I loaded the crossing cache with this branch, and it produced `loaded track crossing cache …: 22757127 tracks, 72311734 directed records` instead of a rebuild.

**Before:** Every `fit_spiral.py` run on that data printed
```
WARNING: ignoring invalid track crossing cache .../PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm.crossings.npz: tracks DBM has changed since the cache was built
WARNING: ignoring packed track store: source DBM changed after the packed store was written
```
and rebuilt the crossings. The cache stores the DBM signature `['…th0.2.dbm', 9901391872, 1785295357776482751]`; the downloaded file stats as `['…th0.2.dbm', 9901391872, 1785295357000000000]`. Same name, same size, mtime truncated to whole seconds because HTTP `Last-Modified` has one-second resolution, so `_tracks_db_signature()`'s exact `(name, size, mtime_ns)` match can never succeed after a download.

**After this PR:** `_db_signatures_match()` compares name and size exactly and mtime at whole-second resolution; both the crossing-cache and packed-store checks use it. The stored format is unchanged.

**Proof:** Same data, same interpreter (`villa/spiral-fitting/.venv`), only the source tree differs:
```
# upstream main
>>> load_track_crossing_cache(DBM, expected_z_range=(4500, 17499))
WARNING: ignoring invalid track crossing cache ...: tracks DBM has changed since the cache was built
cache loaded: False

# this branch
loaded track crossing cache .../PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm.crossings.npz: 22757127 tracks, 72311734 directed records
cache loaded: True
```

**Why / where this is useful:** Anyone fitting a scroll from a mirrored dataset (wget, rclone, curl, S3 sync all truncate mtime) gets the shipped caches to work instead of silently paying for a rebuild on every run.

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

- Method: `spiral-fitting/tracks.py` gains `_db_signatures_match(stored, expected)`; the two equality checks (`load_track_crossing_cache`, packed-store loader) call it. Name and size must match exactly; mtime_ns must match exactly or after integer division by 1e9.
- Tested commit `9c41cb9f5`. Ubuntu 24.04, Python 3.14.8 via uv, `uv sync` in `villa/spiral-fitting`.
- Data: `s3://vesuvius-challenge-open-data/PHerc0191/…/tracks/PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm` (+ `.crossings.npz`), downloaded 2026-10-08.
- Limitation / not changed: the loader also rejects a cache built for a different z range even when the fit's range is a subset of it (this cache is z 4500–17499; my band fits are 9000–10000 and still rebuild for that reason). Worth a follow-up but a separate decision.

## Re-run the proof yourself on the box (≈30 s each)
```
ssh tbienapfl@100.74.214.106
PY=/mnt/nvme/scroll-prizes/villa/spiral-fitting/.venv/bin/python
DBM=/mnt/nvme/scroll-prizes/data/PHerc0191/spiral/20250821151635/tracks/PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm
cd /mnt/nvme/scroll-prizes/villa/spiral-fitting && $PY -c "from tracks import load_track_crossing_cache as f; print('cache loaded:', f('$DBM', expected_z_range=(4500,17499)) is not None)"   # before
cd /mnt/nvme/scroll-prizes/wt/track-cache-signature/spiral-fitting && $PY -c "from tracks import load_track_crossing_cache as f; print('cache loaded:', f('$DBM', expected_z_range=(4500,17499)) is not None)"   # after
```
