"""Empirical check of fit_spiral.ShellPolarMap on our outer_shell tifxyz: build the table exactly as the
fitter does (z range 8840..10160, 720 bins, config defaults) and query points at z 9525 at radii 10-30 mm
around the umbilicus. Prints confidence/valid statistics and target vs query radius."""
import sys, json, numpy as np, torch
sys.path.insert(0, ".")
from config import Config
from tifxyz import load_tifxyz
import fit_spiral
S = "/mnt/nvme/scroll-prizes/data/PHerc0191/spiral-dataset"
cfg = Config().as_dict()
patch = load_tifxyz(f"{S}/outer_shell")
cps = sorted(json.load(open(f"{S}/umbilicus.json"))["control_points"], key=lambda c: c["z"])
uz = np.array([c["z"] for c in cps]); ux = np.array([c["x"] for c in cps]); uy = np.array([c["y"] for c in cps])
def z_to_umb(z):
    z = np.asarray(z, dtype=np.float32)
    return np.stack([np.interp(z, uz, uy), np.interp(z, uz, ux)], axis=-1).astype(np.float32)
m = fit_spiral.ShellPolarMap(patch, z_to_umb, z_min=9000 - 160, z_max=10000 + 160, num_theta_bins=720, device="cpu", config=cfg)
lt = m.lookup_table
print("table shape", tuple(lt.shape), "radius min/med/max (mm)", [round(float(v) * 9.362 / 1000, 1) for v in (lt[0].min(), lt[0].median(), lt[0].max())])
print("confidence min/mean/max", float(lt[1].min()), float(lt[1].mean()), float(lt[1].max()), "shell_min_confidence", cfg["shell_min_confidence"])
# query points
z = torch.full((3600,), 9525.0); theta = torch.rand(3600) * 2 * np.pi
r_mm = torch.rand(3600) * 20 + 10; r = r_mm * 1000 / 9.362
c = torch.from_numpy(z_to_umb(z.numpy()))
pts = torch.stack([z, c[:, 0] + torch.sin(theta) * r, c[:, 1] + torch.cos(theta) * r], dim=-1)
target_r, scan_r, conf, valid = m.lookup(pts)
print("query: valid fraction", float(valid.float().mean()), "confidence min/mean", float(conf.min()), float(conf.mean()))
print("target radius mm: min/med/max", [round(float(v) * 9.362 / 1000, 1) for v in (target_r.min(), target_r.median(), target_r.max())])
print("scan radius check (should equal query r): max abs diff voxels", float((scan_r - r).abs().max()))
