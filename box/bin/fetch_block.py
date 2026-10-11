#!/usr/bin/env python3
"""Download the chunks of one pyramid level of a remote zarr v2 array that cover a bounding box (dimension_separator '/'),
into a local copy of the store (same layout, so zarr opens it and reads the box). Stdlib only.
Usage: fetch_block.py <zarr base url> <out store> <level> <z0> <z1> <y0> <y1> <x0> <x1> [threads=24]"""
import concurrent.futures as cf, json, os, sys, time, urllib.error, urllib.request

base, out, lv = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3]
z0, z1, y0, y1, x0, x1 = map(int, sys.argv[4:10]); threads = int(sys.argv[10]) if len(sys.argv) > 10 else 24


def fetch(rel):
    dest = os.path.join(out, rel)
    if os.path.exists(dest):
        return 0
    for attempt in range(4):
        try:
            with urllib.request.urlopen(f'{base}/{rel}', timeout=90) as r:
                data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return -1                      # chunk never written (empty: fill value)
            if attempt == 3:
                raise
        except Exception:
            if attempt == 3:
                raise
        time.sleep(2 * (attempt + 1))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest + '.part', 'wb') as f:
        f.write(data)
    os.replace(dest + '.part', dest)
    return len(data)


for m in ('.zattrs', '.zgroup'):
    fetch(m)
fetch(f'{lv}/.zarray'); a = json.load(open(os.path.join(out, lv, '.zarray'))); c = a['chunks']
keys = [f'{lv}/{z}/{y}/{x}' for z in range(z0 // c[0], (z1 - 1) // c[0] + 1) for y in range(y0 // c[1], (y1 - 1) // c[1] + 1)
        for x in range(x0 // c[2], (x1 - 1) // c[2] + 1)]
t0 = time.time()
with cf.ThreadPoolExecutor(threads) as ex:
    got = list(ex.map(fetch, keys))
print(f'{base.split("/")[-1]} level {lv}: {len(keys)} chunks ({sum(1 for g in got if g < 0)} empty), '
      f'{sum(g for g in got if g > 0) / 2**20:.0f} MiB in {time.time() - t0:.0f}s -> {out}')
