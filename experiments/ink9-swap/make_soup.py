"""Checkpoint soup: the uniform weight average of several ink_9um checkpoints of one training run (2026-10-13).

The averaging is Erwin Nieuwlaar's recipe (HF Nieuwlaar/ink9um-dense-native, make_soup.py, MIT): every floating-point
tensor of the model state is summed in float64 in the order given, divided by the count and cast back to its own dtype.
For seed 42, steps 40k/50k/60k/75k, that gives his soup42_last4 tensor for tensor (--check compares).
Two differences from his script, neither of which changes a weight:
- the non-tensor payload (config, step) and any non-float tensors are taken from the LAST input, not the first;
- tensors that share storage in the last input (villa's networks hold each conv under two names, e.g. `.conv.weight`
  and `.all_modules.0.weight`) share storage in the soup too, so it saves at the released size (138 MB, not 273 MB).
The inputs must have the same keys, shapes and dtypes and the same training config apart from out_dir; anything else
stops the script. A sidecar <out>.json records the inputs (sha256), the method and the distance of the soup to each input.
Torch on CPU only (map_location cpu); run with CUDA_VISIBLE_DEVICES= so no GPU is touched.
Usage: make_soup.py <out.pth> <in1.pth> <in2.pth> [...] [--check ref.safetensors]"""
import hashlib, json, os, sys

import torch

args = sys.argv[1:]
check = None
if '--check' in args:
    i = args.index('--check'); check = args[i + 1]; del args[i:i + 2]
out, ins = args[0], args[1:]
if len(ins) < 2:
    sys.exit('need at least two input checkpoints')
KEYS = ('ema_model', 'state_dict', 'model_state_dict', 'model')   # villa's select_inference_weights order


def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


def state_of(payload, src):
    if isinstance(payload, dict):
        for k in KEYS:
            if isinstance(payload.get(k), dict) and payload[k]:
                return k, payload[k]
    sys.exit(f'{src}: no model state under {KEYS}')


payloads = [torch.load(p, map_location='cpu', weights_only=False) for p in ins]
key, last = state_of(payloads[-1], ins[-1])
sds = []
for p, pl in zip(ins, payloads):
    k, sd = state_of(pl, p)
    if k != key or list(sd) != list(last):
        sys.exit(f'{p}: state key or tensor names differ from {ins[-1]}')
    for n, v in sd.items():
        t = last[n]
        if torch.is_tensor(v) != torch.is_tensor(t) or (torch.is_tensor(v) and (v.shape != t.shape or v.dtype != t.dtype)):
            sys.exit(f'{p}: tensor {n} differs in type, shape or dtype')
    sds.append(sd)
cfg = [dict(pl.get('config') or {}) for pl in payloads]
for p, c in zip(ins, cfg):
    diff = sorted(k for k in set(c) | set(cfg[-1]) if k != 'out_dir' and c.get(k) != cfg[-1].get(k))
    if diff:
        sys.exit(f'{p}: training config differs from {ins[-1]} in {diff} (not one run; not souping)')

alias, soup = {}, {}
for n, t in last.items():
    if not (torch.is_tensor(t) and t.is_floating_point()):
        soup[n] = t                                   # non-float: from the last checkpoint
        continue
    a = (t.untyped_storage().data_ptr(), t.storage_offset(), tuple(t.shape), tuple(t.stride()))
    if a in alias:                                    # the same storage under a second name
        soup[n] = soup[alias[a]]
        continue
    acc = sds[0][n].detach().clone().double()
    for sd in sds[1:]:
        acc += sd[n].double()
    soup[n] = (acc / len(sds)).to(t.dtype).contiguous(); alias[a] = n
for sd in sds:                                        # the alias groups hold equal values in every input
    for n, t in last.items():
        a = (t.untyped_storage().data_ptr(), t.storage_offset(), tuple(t.shape), tuple(t.stride())) if torch.is_tensor(t) else None
        if a in alias and alias[a] != n and not torch.equal(sd[n], sd[alias[a]]):
            sys.exit(f'{n} and {alias[a]} share storage in the last input but differ in another')

payload = {k: v for k, v in payloads[-1].items()}
payload[key] = soup
tmp = out + '.part'
torch.save(payload, tmp); os.replace(tmp, out)

fl = [n for n, t in last.items() if torch.is_tensor(t) and t.is_floating_point()]
def dist(sd):                                         # relative L2 distance of the soup to one input, float tensors
    num = sum(float((soup[n].double() - sd[n].double()).pow(2).sum()) for n in fl)
    den = sum(float(sd[n].double().pow(2).sum()) for n in fl)
    return (num / den) ** 0.5
meta = dict(out=os.path.abspath(out), sha256=sha256(out), bytes=os.path.getsize(out), state_key=key, n=len(ins),
            method='uniform mean of float tensors (float64 sum in input order, cast back); config, step and non-float '
                   'tensors from the last input; storage aliases kept (make_soup.py, after Nieuwlaar)',
            tensors=len(last), float_tensors=len(fl), unique_storages=len(alias), step=payload.get('step'),
            inputs=[dict(path=os.path.abspath(p), sha256=sha256(p), step=pl.get('step'), rel_l2_soup_vs_input=round(dist(sd), 6))
                    for p, pl, sd in zip(ins, payloads, sds)])
if check:
    from safetensors.torch import load_file
    ref = load_file(check)
    same = sorted(set(ref) & set(soup)); miss = sorted(set(ref) ^ set(n for n in soup if torch.is_tensor(soup[n])))
    neq = [n for n in same if not torch.equal(ref[n], soup[n])]
    meta['check'] = dict(ref=os.path.abspath(check), ref_sha256=sha256(check), tensors_compared=len(same),
                         names_not_in_both=len(miss), not_bit_identical=len(neq), bit_identical=not neq and not miss)
json.dump(meta, open(out + '.json', 'w'), indent=1)
print(json.dumps({k: v for k, v in meta.items() if k != 'inputs'}))
for i in meta['inputs']:
    print(f"  {i['path']}  step {i['step']}  rel L2 soup-input {i['rel_l2_soup_vs_input']}")
