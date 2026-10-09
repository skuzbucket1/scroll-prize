# PR: spiral-fitting: accept shipped track caches whose DBM mtime lost sub-second precision

Branch: `skuzbucket1/villa:fix/track-cache-signature` → `ScrollPrize/villa:main`
Compare/open: https://github.com/ScrollPrize/villa/compare/main...skuzbucket1:villa:fix/track-cache-signature?expand=1

## Title
spiral-fitting: accept shipped track caches whose DBM mtime lost sub-second precision

## Body
While fitting PHerc0191 (tracks `PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm`, mirrored from the public bucket with a plain HTTP download), every run printed

```
WARNING: ignoring invalid track crossing cache .../PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm.crossings.npz: tracks DBM has changed since the cache was built
WARNING: ignoring packed track store: source DBM changed after the packed store was written
```

and rebuilt the crossings from the 9.9 GB DBM. The 2.4 GB `.crossings.npz` that ships next to the DBM was downloaded for nothing.

Cause: `_tracks_db_signature()` fingerprints the DBM as `(name, size, st_mtime_ns)` and the loaders require an exact match. The cache stores `1785295357776482751`; the downloaded file has `1785295357000000000` — same name, same size, mtime truncated to whole seconds because HTTP `Last-Modified` has one-second resolution. Any wget/rclone/curl mirror hits this, so the shipped caches can never be used after download.

Fix: compare name and size exactly and mtime at whole-second resolution (`_db_signatures_match`), used by both the crossing-cache and packed-store checks. Stored format unchanged.

Before (upstream `main`, same data):
```
>>> load_track_crossing_cache(DBM, expected_z_range=(4500, 17499))
WARNING: ignoring invalid track crossing cache ...: tracks DBM has changed since the cache was built
cache loaded: False
```
After (this branch):
```
loaded track crossing cache .../PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm.crossings.npz: 22757127 tracks, 72311734 directed records
cache loaded: True
```

Not changed here: the loader also rejects a cache built for a different z range even when the fit's range is a subset; worth a follow-up but a separate decision.
