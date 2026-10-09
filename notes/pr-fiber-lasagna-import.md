# PR: vesuvius: fiber_trace.geometry falls back to a bare lasagna import like the rest of fiber_trace

Branch: `skuzbucket1/villa:fix/fiber-lasagna-import` → `ScrollPrize/villa:main`
Compare/open: https://github.com/ScrollPrize/villa/compare/main...skuzbucket1:villa:fix/fiber-lasagna-import?expand=1

## Title
vesuvius: fiber_trace.geometry falls back to a bare lasagna import like the rest of fiber_trace

## Body
Running fibre inference on PHerc0191 from a plain `uv sync --extra models` environment:

```
uv run --extra models python -m vesuvius.neural_tracing.fiber_trace_3d.infer --input <vol>/0 --output fiber.lasagna.json \
  --checkpoint s1a_128_2_single_8x8_20260728_094259_best_25_9k.pt --devices all --crop 0 0 8500 8387 8387 2000 \
  --tile-size 256 --overlap 48 --border 16 --inference-scaledown-power 2
```
died at import:
```
  File ".../vesuvius/src/vesuvius/neural_tracing/fiber_trace/geometry.py", line 6, in <module>
    from lasagna.omezarr_pyramid import _decode_normals as _lasagna_decode_normals
ModuleNotFoundError: No module named 'lasagna'
```

`fiber_trace_3d/infer.py`, `inference_adapter.py` and `fiber_trace/dataset.py` all guard their lasagna imports with the documented `PYTHONPATH=lasagna` fallback (`except ImportError: from live_omezarr_cache import ...`), but `geometry.py` imports `lasagna.omezarr_pyramid` unconditionally, so the documented layout does not work either. This adds the same fallback.

Before (upstream `main`, `PYTHONPATH=<villa>/lasagna`):
```
ModuleNotFoundError: No module named 'lasagna'
```
After (this branch, same command):
```
import ok: .../vesuvius/src/vesuvius/neural_tracing/fiber_trace/geometry.py
```
The full inference then ran to completion on the PHerc0191 band (20,172 tiles, 1.6 h on one RTX 3060) with `PYTHONPATH` set to the villa root.
