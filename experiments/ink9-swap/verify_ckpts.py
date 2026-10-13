"""Do the ink9-swap candidates load as villa would load them, and are they the network we already use? (2026-10-13)
For each checkpoint, on CPU: torch.load; pick the weights the way villa's select_inference_weights does; compare tensor
names, shapes and dtypes with the reference (ink_9um seed 42 step 75000, our current member); compare the training
config with the reference's; build villa's model from the checkpoint's own config (InkConfig.from_mapping + make_model,
as vesuvius.ink_detection.inference.infer does) and load the weights with strict=True (villa itself loads with
strict=False, so a name mismatch there would silently run random weights); check every tensor is finite; give the
relative L2 distance of the weights to the reference. Run with CUDA_VISIBLE_DEVICES= (no GPU).
Usage: verify_ckpts.py <out.json> <reference.pth> name=ckpt.pth [name=ckpt.pth ...]"""
import json, sys

import torch
from vesuvius.ink_detection.config import InkConfig
from vesuvius.ink_detection.models.checkpoint import select_inference_weights
from vesuvius.ink_detection.models.model import make_model

out, refp = sys.argv[1], sys.argv[2]
cands = dict(a.split('=', 1) for a in sys.argv[3:])
torch.set_num_threads(2)
ref = torch.load(refp, map_location='cpu', weights_only=False)
_, rsd = select_inference_weights(ref, source=refp)
rows, ok_all = [], True
for name, p in cands.items():
    pl = torch.load(p, map_location='cpu', weights_only=False)
    sel, sd = select_inference_weights(pl, source=p)
    same_names = list(sd) == list(rsd)
    bad = [n for n in rsd if n in sd and (sd[n].shape != rsd[n].shape or sd[n].dtype != rsd[n].dtype)]
    finite = all(bool(torch.isfinite(v).all()) for v in sd.values() if torch.is_tensor(v) and v.is_floating_point())
    c, rc = pl.get('config') or {}, ref.get('config') or {}
    cdiff = {k: [str(rc.get(k))[:60], str(c.get(k))[:60]] for k in sorted(set(c) | set(rc)) if c.get(k) != rc.get(k)}
    model = make_model(InkConfig.from_mapping(pl['config']))
    try:
        r = model.load_state_dict(dict(sd), strict=True); strict_ok, why = True, ''
    except RuntimeError as e:
        strict_ok, why = False, str(e)[:300]
    fl = [n for n in rsd if torch.is_tensor(rsd[n]) and rsd[n].is_floating_point() and n in sd]
    num = sum(float((sd[n].double() - rsd[n].double()).pow(2).sum()) for n in fl)
    den = sum(float(rsd[n].double().pow(2).sum()) for n in fl)
    row = dict(name=name, path=p, state=sel, step=pl.get('step'), tensors=len(sd),
               params=int(sum(v.numel() for v in model.state_dict().values())), names_match_reference=same_names,
               shape_or_dtype_mismatch=bad, all_finite=finite, strict_load=strict_ok, strict_error=why,
               mixed_precision=c.get('mixed_precision'), config_diff_vs_reference=cdiff,
               rel_l2_vs_reference=round((num / den) ** 0.5, 6))
    ok = same_names and not bad and finite and strict_ok
    ok_all &= ok; row['ok'] = ok; rows.append(row)
    print(f"{name:14s} ok={ok} step={row['step']} tensors={row['tensors']} strict={strict_ok} finite={finite} "
          f"relL2_vs_ref={row['rel_l2_vs_reference']} config_diff={list(cdiff)}", flush=True)
    del pl, sd, model
json.dump(dict(reference=refp, all_ok=ok_all, candidates=rows), open(out, 'w'), indent=1)
print('ALL-OK' if ok_all else 'SOME-FAILED', out)
