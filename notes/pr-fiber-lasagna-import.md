# PR 3 — fiber_trace.geometry lasagna import fallback (finding #8)

Open: https://github.com/ScrollPrize/villa/compare/main...skuzbucket1:villa:fix/fiber-lasagna-import?expand=1
Tested commit: `6222bbb8b` on branch `fix/fiber-lasagna-import` (one commit on top of upstream `a329895ea`).

## Title (replace the pre-filled long one)
vesuvius: fiber_trace.geometry lasagna import fallback

## Body (paste, replacing everything GitHub pre-filled)

**In one sentence:** Run the 3D fibre inference (`vesuvius.neural_tracing.fiber_trace_3d.infer`) from a plain `uv sync --extra models` environment with `PYTHONPATH` pointing at `villa/lasagna`, the layout the other fiber_trace modules already support.

**One real example:** Starting with the PHerc0191 volume `20250821151635-9.362um-1.2m-113keV-masked.zarr` (level 0, crop z 8500–10500) and the `scrollprize/lasagna-fiber` checkpoint `s1a_128_2_single_8x8_20260728_094259_best_25_9k.pt`, I ran `fiber_trace_3d.infer` with `PYTHONPATH=<villa>/lasagna`, and it produced `fiber_nx/ny/presence.ome.zarr` pyramids for the band (20,172 tiles, 1.6 h on one RTX 3060).

**Before:** The same command exits at import time:
```
  File ".../vesuvius/src/vesuvius/neural_tracing/fiber_trace/geometry.py", line 6, in <module>
    from lasagna.omezarr_pyramid import _decode_normals as _lasagna_decode_normals
ModuleNotFoundError: No module named 'lasagna'
```
`fiber_trace_3d/infer.py`, `inference_adapter.py` and `fiber_trace/dataset.py` all guard their lasagna imports with the `PYTHONPATH=lasagna` fallback; `geometry.py` does not, so the documented layout fails.

**After this PR:** `geometry.py` uses the same `try: from lasagna.omezarr_pyramid … except ImportError: from omezarr_pyramid …` fallback, the import succeeds, and the inference runs.

**Proof:** Same interpreter (`villa/vesuvius/.venv`, `uv sync --extra models`), same `PYTHONPATH`, only the source tree differs:
```
# upstream main
$ PYTHONPATH=/path/villa/lasagna python -c "import vesuvius.neural_tracing.fiber_trace.geometry as g; print('import ok:', g.__file__)"
ModuleNotFoundError: No module named 'lasagna'

# this branch
$ PYTHONPATH=/path/villa-fix/vesuvius/src:/path/villa/lasagna python -c "import vesuvius.neural_tracing.fiber_trace.geometry as g; print('import ok:', g.__file__)"
import ok: /path/villa-fix/vesuvius/src/vesuvius/neural_tracing/fiber_trace/geometry.py
```
Full inference log from the run that then completed: `[predict3d] 20172/20172 tiles`, outputs `fiber_nx.ome.zarr` (792 MB), `fiber_ny.ome.zarr` (813 MB), `fiber_presence.ome.zarr` (937 MB), manifest `fiber.lasagna.json`.

**Why / where this is useful:** Anyone running fibre inference outside the monorepo's own environment (the `models` extra does not ship `lasagna`) currently hits a hard import error with no hint; with this they can follow the layout the rest of the package already documents and get direction fields for `vc_grow_seg_from_seed`.

- [ ] I personally verified that the example and proof above were produced by this PR on the stated data.

## Details

- Method: one-line change in `vesuvius/src/vesuvius/neural_tracing/fiber_trace/geometry.py`, mirroring the existing fallback in `fiber_trace_3d/infer.py` (lines 16–23) and `fiber_trace/dataset.py` (lines 289–292).
- Tested commit: `6222bbb8b` (branch on upstream `a329895ea`). Environment: Ubuntu 24.04, Python 3.14.8 via uv, `uv sync --extra models` in `villa/vesuvius`, CUDA 12.8, RTX 3060 12 GB.
- Command that failed before and ran after:
  `uv run --extra models python -m vesuvius.neural_tracing.fiber_trace_3d.infer --input <vol>/0 --output <out>/fiber.lasagna.json --checkpoint <ckpt> --devices all --no-download --crop 0 0 8500 8387 8387 2000 --tile-size 256 --overlap 48 --border 16 --inference-scaledown-power 2`
- Limitation: this only fixes the documented `PYTHONPATH=lasagna` layout. Making `lasagna` a path dependency of the `models` extra (like `volume-cartographer`) would remove the need for `PYTHONPATH` entirely; I left that decision to you.

## Re-run the proof yourself on the box (≈5 s)
```
ssh tbienapfl@100.74.214.106
PYV=/mnt/nvme/scroll-prizes/villa/vesuvius/.venv/bin/python
cd /tmp && PYTHONPATH=/mnt/nvme/scroll-prizes/villa/lasagna $PYV -c "import vesuvius.neural_tracing.fiber_trace.geometry as g; print('import ok:', g.__file__)"        # before: ModuleNotFoundError
cd /tmp && PYTHONPATH=/mnt/nvme/scroll-prizes/wt/fiber-lasagna-import/vesuvius/src:/mnt/nvme/scroll-prizes/villa/lasagna $PYV -c "import vesuvius.neural_tracing.fiber_trace.geometry as g; print('import ok:', g.__file__)"   # after: import ok
```
