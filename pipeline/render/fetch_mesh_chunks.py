"""Download only the level-0 chunks of a remote CT zarr (v2, dimension_separator '/') that a 66-layer render of a tifxyz mesh
reads: every chunk within `margin` voxels of a mesh point. Writes a local store with the same layout (.zattrs, .zgroup,
0/.zarray, chunks), so vc_render_tifxyz, which only opens local zarrs, can render the mesh from it.
Usage: fetch_mesh_chunks.py <CT zarr URL> <tifxyz dir> <out.zarr> [margin=48] [threads=24] [level=0]
(level L > 0: the chunks of pyramid level L instead, for a render with --group-idx L; the margin is in level-L voxels.)
2026-10-15 (audit B13): a cached file is trusted only if it is not empty and, for uncompressed chunks, has the exact chunk
size; otherwise it is fetched again (a full disk once left empty files behind)."""
import concurrent.futures as cf, json, os, sys, time, urllib.error, urllib.request
import numpy as np, tifffile, cv2


EXPECT = None                                                   # bytes per chunk when the store is uncompressed


def get(base, out, rel):
    dest = os.path.join(out, rel)
    if os.path.exists(dest):
        n = os.path.getsize(dest)
        if n > 0 and (EXPECT is None or rel.rsplit('/', 1)[-1].startswith('.') or n == EXPECT):
            return 0
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f'{base}/{rel}', timeout=90) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return -1                                    # never written: fill value
            if attempt == 3:
                raise
        except Exception:
            if attempt == 3:
                raise
        time.sleep(2 * (attempt + 1))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    part = f'{dest}.part{os.getpid()}'                           # per process: several fetches may share one store
    with open(part, 'wb') as f:
        f.write(data)
    os.replace(part, dest)
    return len(data)


base, mesh, out = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
margin = int(sys.argv[4]) if len(sys.argv) > 4 else 48; threads = int(sys.argv[5]) if len(sys.argv) > 5 else 24
lv = int(sys.argv[6]) if len(sys.argv) > 6 else 0
for m in ('.zattrs', '.zgroup', '0/.zarray', f'{lv}/.zarray'):
    get(base, out, m)
try:                                                           # the other levels' metadata too (no chunks), for readers that open them
    for d in json.load(open(os.path.join(out, '.zattrs')))['multiscales'][0]['datasets']:
        get(base, out, f"{d['path']}/.zarray")
except (KeyError, IndexError, FileNotFoundError):
    pass
za = json.load(open(os.path.join(out, str(lv), '.zarray'))); c = za['chunks']
if za.get('compressor') is None:
    EXPECT = int(np.prod(c)) * np.dtype(za['dtype']).itemsize
X, Y, Z = (tifffile.imread(os.path.join(mesh, f'{k}.tif')).astype(np.float32) for k in 'xyz')
f = 4                                                          # grid cells are ~20 voxels: sample every ~5 voxels
up = lambda A: cv2.resize(A, (A.shape[1] * f, A.shape[0] * f), interpolation=cv2.INTER_LINEAR)
ok = cv2.resize(((X > 0) & (Y > 0) & (Z > 0)).astype(np.uint8), (X.shape[1] * f, X.shape[0] * f), interpolation=cv2.INTER_NEAREST) > 0
P = np.stack([up(Z)[ok], up(Y)[ok], up(X)[ok]], 1) / 2 ** lv              # mesh points are level-0 voxels
keys = set()
for dz in (-margin, 0, margin):
    for dy in (-margin, 0, margin):
        for dx in (-margin, 0, margin):
            q = np.floor((P + np.array([dz, dy, dx])) / np.array(c)).astype(int)
            keys |= set(map(tuple, np.unique(q, axis=0)))
keys = [f'{lv}/{z}/{y}/{x}' for z, y, x in sorted(keys) if min(z, y, x) >= 0]
t0 = time.time()
with cf.ThreadPoolExecutor(threads) as ex:
    got = list(ex.map(lambda k: get(base, out, k), keys))
print(f'{len(keys)} chunks ({sum(g < 0 for g in got)} empty), {sum(g for g in got if g > 0) / 2 ** 30:.2f} GiB in {time.time() - t0:.0f}s -> {out}')
print('FETCHMESH-EXIT: 0')
