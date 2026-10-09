# Friction log — villa tooling on real scroll data

Evidence-backed problems hit while running the First Letters workflow on the GPU box (`llm`, Ubuntu 24.04.5, 4× NVIDIA).
Each entry: what was run, what happened, evidence, candidate fix. Candidates for PRs per CONTRIBUTING.md (real data, before/after evidence).

## 1. `build_from_src_debian.sh` installs binaries that cannot start: `libvolcomp.so` missing from the `vc_runtime` component

- **Date / commit:** 2026-10-08, villa `12f21236a` (2026-10-09).
- **Setup:** mirrored the script's cmake configure/build/install steps exactly (`-DVC_BUILD_APPS=ON -DVC_BUILD_FLATBOI=ON -DVC_BUILD_PYTHON=OFF`,
  `cmake --install build --component vc_runtime`), with `PREFIX=$HOME/.local` instead of `/usr/local`.
- **Symptom:** `vc_render_tifxyz --help` →
  `error while loading shared libraries: libvolcomp.so: cannot open shared object file`.
  `ldd` shows the same missing library for `VC3D`, `vc_grow_seg_from_seed`, `flatboi`.
- **Evidence:** `~/.local/lib` contains `libvc_core.so`, `libutils_volcomp_codec.so`, … but no `libvolcomp.so`;
  the library exists in the build tree at `build/from-source/libs/volcomp/libvolcomp.so`.
  The script's own post-install check only tests `-x "$prefix/bin/$program"`, so it reports success.
- **Workaround:** `ln -s build/from-source/libs/volcomp/libvolcomp.so ~/.local/lib/` (+ `LD_LIBRARY_PATH=~/.local/lib`).
- **Candidate fix:** add `libvolcomp` to the `vc_runtime` install component (or install it alongside the other core libs);
  make the script's final check actually execute each program (`"$prefix/bin/$program" --help`).
- **Confirmed 2026-10-08:** `libs/volcomp/CMakeLists.txt` only has `add_library(volcomp volcomp_lib.c)` — no `install()` rule, so no
  component can ship it; `build/from-source/install_manifest_vc_runtime.txt` (59 entries) contains no `libvolcomp.so`; installed binaries
  carry `RUNPATH $ORIGIN/../lib`, so the default `/usr/local` prefix fails the same way (`/usr/local/lib/libvolcomp.so` is never created).
  Only the three `COMPONENT vc_runtime` rules exist (+ one `LibiglDevelopment`).
- **For the PR (CONTRIBUTING.md):** needs an error screenshot (terminal showing the `libvolcomp.so` error after a fresh install) plus the
  fix working (`vc_render_tifxyz --help` after the patched install); real-data before/after = the render below once it runs.
- **Fix verified 2026-10-08 (branch `fix/install-volcomp` on the box, uncommitted):** one line in `volume-cartographer/CMakeLists.txt`:
  `set(_vc_install_dirs core utils libs/c3d)` → `set(_vc_install_dirs core utils libs/c3d libs/volcomp)`. After re-configure +
  `cmake --install build/from-source --component vc_runtime`: `~/.local/lib/libvolcomp.so` installed (734 KB), manifest lists it,
  0 binaries with unresolved libs, `vc_render_tifxyz --help` runs with no `LD_LIBRARY_PATH`.
- **Impact / history:** `libs/volcomp` was added by #1704 (`e0bbb8b40`, 2026-10-06); the install walker predates it (`a84bf2d1b`, 2026-07-07).
  `volume-cartographer/Dockerfile:28` installs with the same `--component vc_runtime` and the `ci-release-gcc` preset sets no
  `BUILD_SHARED_LIBS` override, so the *next* image build will ship the same broken binaries; the currently published `:edge`/`:main`
  image (GHCR, created 2026-05-13, revision `1e3f4c0`) predates #1704 and is unaffected. Every CLI tool + VC3D from the documented
  Linux source build fails to start since #1704.

## 2. (low) `uv sync` in `vesuvius/` rewrites tracked files

- `vesuvius/uv.lock` is rewritten by uv 0.12.23 (`revision = 3` → `5`, `vc-delta3d` entry gains `version = "0.1.0"`) — the committed
  lock was produced by an older uv, so a fresh checkout is dirty after the documented `uv sync`. Suggest `uv lock` refresh or docs note.
- `segmentation/models/batchgeneratorsv2/batchgeneratorsv2.egg-info/SOURCES.txt` is tracked and gets regenerated (3 new lines) when the
  package builds — generated metadata should not be in git.
- Also: first `uv sync --extra models` attempt died on a 3-retry timeout fetching `nvidia-cufile` from pypi.nvidia.com over a ~12 MB/s link;
  succeeded on retry with `UV_HTTP_TIMEOUT=600`. Worth a line in the setup docs.

## 3. (docs) VC3D tutorial tells users to pull a container tag that does not exist; published image is 5 months stale

- scrollprize.org/tutorial_VC3D: `docker pull ghcr.io/scrollprize/villa/volume-cartographer:stable`.
- GHCR manifest query 2026-10-08: `:stable` → `MANIFEST_UNKNOWN`; `:latest` → `MANIFEST_UNKNOWN`; `:edge` and `:main` exist, both created
  2026-05-13T18:41Z from revision `1e3f4c021f4e` (`org.opencontainers.image.version: main`). Repo HEAD is `12f21236a` (2026-10-09).
- Candidate fix: either publish `:stable` or change the tutorial (source lives in `scrollprize.org/` in this monorepo) to a tag that exists,
  and note the image age. Related: issue #1588 (`:edge`/`:main` stale).

## 4. Flat ink inference on a remote https surface volume aborts the whole run on one transient disconnect

- **Date / commit:** 2026-10-08, villa `12f21236a`; `vesuvius` env from `uv sync --extra models` (Python 3.14, torch 2.12.1, zarr 3, fsspec/aiohttp).
- **Command (the model card's documented usage, URL input):**
  `python -m vesuvius.ink_detection.inference.infer https://vesuvius-challenge-open-data.s3.amazonaws.com/PHerc0800/segments/20251028222030-auto_grown_20251028222030940/surface-volumes/8.64um-1.2m-116keV-volume-20250521135224.zarr checkpoints/ink_9um/hybrid_3d2d-seed42/step-075000.pth out.tif --resolution 0 --overlap 0.5 --blend-mode hann --batch-size 4 --direction both --no-compile`
- **Symptom:** 923 patches selected; after ~10 min of per-patch chunk reads over HTTPS (4 DataLoader workers, Wi-Fi link), one
  `aiohttp.client_exceptions.ServerDisconnectedError: Server disconnected` raised in `zarr/storage/_fsspec.py:289 → fsspec/implementations/http.py:248`
  inside DataLoader worker 0 → the run exits non-zero with no output. fsspec's `HTTPFileSystem` has no retry; `s3fs` does.
- **Candidate fix:** retry transient transport errors in `volume_io.open_volume_root` / the dataset's chunk reads (bounded retries with backoff), or
  default public-bucket https URLs to the already special-cased `s3://…` anonymous path and say so in the README. Related: #1846, #1666.
- **Workaround used:** mirror the six surface volumes locally with `bin/fetch_zarr.py` (retries) and infer on local copies.

## 5. `vc_render_tifxyz --remote-url` aborts the whole render on one chunk timeout (no retry), after a successful prefetch

- **Date / commit:** 2026-10-08, villa `12f21236a` built from source (with fix #1 applied), Ubuntu 24.04.5, Wi-Fi uplink ~12 MB/s shared with another download.
- **Command:** `vc_render_tifxyz -v <empty dir> --remote-url https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/volumes/20260411134726-2.400um-0.2m-78keV-masked.zarr -s <20231016151002 2.4um tifxyz> --scale 1 -g 2 --num-slices 28 --slice-step 1 --crop-x 4000 --crop-y 900 --crop-width 6500 --crop-height 2100 --voxel-size 2.4 --voxel-unit micrometer --cache-gb 12 --prefetch-remote --zarr-output render.zarr`
- **Symptom:** prefetch planned and fetched 614 chunks ("Prefetch: 614 chunk(s) across rows 0..16"); rendering reached tile-row 14/17 (82%) at 40–65 chunks/s,
  then `Error: HTTP 0 fetching 2/126/36/38: Operation timed out after 60000 milliseconds with 1689856 out of 2097152 bytes received` → exit 1 after 505 s,
  414 MB partial `render.zarr` left behind. The remote cache held 1,236 chunk files afterwards vs. the 614 the prefetch planned, i.e. rendering fetched
  about as many chunks again on demand (the slice stack along the normal reaches chunks the plan did not include); the failing chunk was one of those.
- **Candidate fix:** bounded retry with backoff on timeouts/transient HTTP errors in the remote chunk fetch (resume from the bytes already received if the
  server supports ranges), and make the prefetch plan cover the chunks the slice stack actually touches. Related: #1846, #1666.
- **Workaround:** re-run; chunks already fetched persist in `~/.VC3D/remote_cache`, so the second pass only needs the stragglers.
- **Re-run 2026-10-08 16:51Z:** identical command, no competing downloads → `rc=0` in 39 s; almost everything came from `~/.VC3D/remote_cache`. Confirms the
  abort was a single transient fetch, not the data — a bounded retry would have saved the first run.

## 6. spiral-fitting rejects the dataset's shipped track-crossing cache after download (mtime_ns signature)

**Observed (2026-10-09, PHerc0191, every fit run):** `WARNING: ignoring invalid track crossing cache .../PHerc0191_20250821151635_surface_m7_L0_th0.2.dbm.crossings.npz: tracks DBM has changed since the cache was built` and `WARNING: ignoring packed track store: source DBM changed after the packed store was written` — in `pilot-fit-full.log`, `fit-exp-30k-full.log`, `fit-exp-track2x-full.log`, `fit-exp-dr32-full.log`, `fit-exp-shell105-full.log` (2 lines each). The 2.4 GB `.crossings.npz` that ships next to the 9.9 GB DBM in the public dataset is therefore downloaded for nothing, and every run rebuilds the crossings (~2 min of track loading per run on NVMe; longer on slower disks).

**Cause:** `spiral-fitting/tracks.py::_tracks_db_signature()` fingerprints the DBM as `(name, st_size, st_mtime_ns)`. The DBM on disk has `mtime 2026-07-29 03:22:37.000000000` — nanoseconds zeroed by the HTTP `Last-Modified` header that wget/rclone apply — so the stored nanosecond mtime can never match after any download or copy without preserved timestamps, even though name and size match. The docstring says the signature is meant to cover "the portable set of files backing a logical DBM", but mtime_ns is not portable.

**Evidence (read from the shipped `.crossings.npz` metadata on 2026-10-09):** stored `db_signature` = `['…th0.2.dbm', 9901391872, 1785295357776482751]`; current `os.stat` = `['…th0.2.dbm', 9901391872, 1785295357000000000]` — identical name and size, mtime differs only below one second. Caveat: the cache also records `z_range [4500, 17499]` and the loader rejects a cache built for a different z range, so even with the signature fixed it only serves fits over exactly that range; a sub-range fit should be allowed to use a superset cache (or the mismatch should be stated explicitly).

**Fix idea (small PR):** compare `(name, size)` plus a cheap content fingerprint (e.g. sha256 of the first and last 1 MiB of each backing file) instead of `st_mtime_ns`; keep mtime only as a fast-path short-circuit. Before/after evidence: the warning disappears and the load prints the cache hit on the same downloaded dataset.

## 7. spiral-fitting: outer-shell loss silently zero when the shell is sampled every N slices (confidence normalisation)

**Observed (2026-10-09, PHerc0191 run `exp-shell105`):** `input_use_outer_shell: true`, `loss_weight_shell_outer: 1.0`, `shell_outer_winding_idx: 105`; the log shows the shell loading (`shell polar table: 1321 z bins x 720 theta bins, 119520/951120 occupied (12.6%)`, `using configured shell_outer_winding_idx = 105`) yet every step line reports `shell_outer = 0.0` from step 0 to 9800, no warning, and the exported w104 ends 7 mm inside the papyrus boundary (per-sector audit below). No shell metrics were ever emitted.

**Cause (`fit_spiral.py` `ShellPolarMap.__init__` / `lookup`):** the polar table's confidence is `gaussian_filter(valid, sigma=(4, 1), mode=('nearest','wrap'))` **divided by its global max**. Our shell tifxyz has one row every 8 slices (the file is otherwise complete: 720/720 bins per row). The interior of the smoothed comb is ~0.125 before normalisation, but `mode='nearest'` replicates the edge row along z, so a valid edge row produces a spike of ~0.5 at the table border; after dividing by that max every interior value is **0.22 < shell_min_confidence 0.25**, so `valid` is false for every lookup and `_masked_mean` returns 0. Reproduced outside the fitter with `bin/shell_lookup_test.py` (builds the same ShellPolarMap and queries 3,600 points at z 9525): `confidence min/mean/max 0.219 / 0.226 / 1.0`, `valid fraction 0.0`.

**Fix idea (small PR):** normalise confidence by the smoothed value of an all-valid table (i.e. 1.0, so confidence = local occupancy), or use `mode='reflect'`/`'constant'` along z and clamp; and print a WARNING when the shell loss has zero valid samples at a metrics step instead of logging `shell_outer = 0.0` silently. Workaround used here: regenerate the shell with one row per slice (`make_outer_shell.py --dz 1`).

## 8. vesuvius `fiber_trace_3d.infer` fails with `No module named 'lasagna'` in a plain `uv sync --extra models` env

**Observed (2026-10-09, `data/PHerc0191/fiber/band8500-10500/infer-attempt1.log`):** `python -m vesuvius.neural_tracing.fiber_trace_3d.infer …` exits 1 at import: `File ".../vesuvius/src/vesuvius/neural_tracing/fiber_trace/geometry.py", line 6, in <module> from lasagna.omezarr_pyramid import _decode_normals as _lasagna_decode_normals — ModuleNotFoundError: No module named 'lasagna'`.

**Cause:** `lasagna` lives in `villa/lasagna` and is not a dependency of any `vesuvius` extra. `fiber_trace_3d/infer.py` and `inference_adapter.py` guard their lasagna imports with a `PYTHONPATH=lasagna`-style fallback (`except ImportError: from live_omezarr_cache import …`), but `fiber_trace/geometry.py` imports `lasagna.omezarr_pyramid` unguarded, so neither a clean env nor the documented `PYTHONPATH=lasagna` layout works; only `PYTHONPATH=<villa root>` (so `lasagna.` resolves as a namespace package) does.

**Fix idea (small PR):** add the same fallback import to `geometry.py` (and any other unguarded `lasagna.` imports), or declare `lasagna` as a path dependency of the `models` extra like `volume-cartographer` is; document `PYTHONPATH=<villa root>` meanwhile. Workaround used here: `export PYTHONPATH=/mnt/nvme/scroll-prizes/villa` in `bin/fiber_band.sh`.

## 9. Resident-pool sidecars are reused after their source store is rebuilt (spiral-fitting, 0fb38c45 and current)

**Observed (2026-10-09, PHerc0191):** after rebuilding the surf-SDT store (first build had the wrong working-z range), the fitter loaded `surf_sdt: resident pool 1/1,456 bricks … from surf_sdt_band9000-10000.ome.zarr.respool_g1` — the sidecar packed at 15:24 from the *first* store, not the rebuilt one (15:48). The fit started training with effectively no SDT data and no warning. Deleting the sidecar fixed it.

**Cause:** the respool `meta.json` records the source channel paths and shapes but no fingerprint of the source store (mtime, attrs `created`, or a content hash), so a rebuilt store at the same path with the same shape passes the reuse check.

**Fix idea:** store the source store's `created` attribute / `.zattrs` hash in the sidecar `meta.json` and repack when it differs. Applies to the Lasagna normal/grad-mag pools too. Check whether current `main`'s `pack_resident_pools.py` has the same gap before filing.

## 10. Spiral-fit winding meshes declare a 20-voxel grid but are spaced 26–30 voxels → unflattened renders are compressed 25–33% and areas understated ~2×

**Observed (2026-10-09, PHerc0191 exp-30k w070, snapped):** `meta.json` `scale: [0.05, 0.05]` (one node per 20 voxels), but the median 3D distance between neighbouring nodes is 26.1 voxels along u and 29.9 along v. `vc_render_tifxyz --scale 1` therefore renders 0.77 × 0.67 pixels per voxel, i.e. the CT is shrunk by 23–33% in the rendered sheet, and `area_cm2` (5.62 cm²) is about half the true area. After Lasagna flattening the same winding has 19.6/19.7-voxel spacing and renders at 1.02 px/voxel (≈ 9.9 cm²).

**Why it matters:** the released 9 µm ink models are trained on 9 µm/px renders. The official First Letters workflow describes Lasagna flattening as "optional"; rendering a raw spiral winding feeds the models letters 25–33% too small in crushed regions. All of our pilot ink runs on raw windings were affected.

**Fix idea:** export spiral windings with the true node spacing in `scale` (or resample to 20 voxels on export), compute `area_cm2` from the 3D quads, and document flattening as required for ink inference.
