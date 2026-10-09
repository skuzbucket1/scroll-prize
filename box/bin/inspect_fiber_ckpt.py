import sys, torch, json
p=sys.argv[1]; ck=torch.load(p, map_location="cpu", weights_only=False)
print("INSPECT top-level keys:", list(ck.keys())[:20] if isinstance(ck,dict) else type(ck))
for k in ("config","cfg","args","train_config","inference","inference_config","meta"):
    if isinstance(ck,dict) and k in ck:
        v=ck[k]; s=json.dumps(v, default=str) if not isinstance(v,str) else v; print(f"INSPECT {k}: {s[:1500]}")
