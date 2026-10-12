"""Download only the chunks of one pyramid level of a remote zarr v2 array that cover a bounding box (dimension_separator
'/'), into a local copy of the store with the same layout, so zarr opens it and reads the box. Stdlib only."""
from __future__ import annotations

import concurrent.futures as cf
import json
import os
import time
import urllib.error
import urllib.request


def _get(base: str, out: str, rel: str) -> int:
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
                return -1                                   # never written: fill value
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


def fetch_block(base: str, out: str, level: str, box, threads: int = 24, log=print) -> dict:
    """box = (z0, z1, y0, y1, x0, x1) at this level."""
    base = base.rstrip('/'); z0, z1, y0, y1, x0, x1 = map(int, box)
    for m in ('.zattrs', '.zgroup'):
        _get(base, out, m)
    _get(base, out, f'{level}/.zarray'); c = json.load(open(os.path.join(out, level, '.zarray')))['chunks']
    keys = [f'{level}/{z}/{y}/{x}' for z in range(z0 // c[0], (z1 - 1) // c[0] + 1) for y in range(y0 // c[1], (y1 - 1) // c[1] + 1)
            for x in range(x0 // c[2], (x1 - 1) // c[2] + 1)]
    t0 = time.time()
    with cf.ThreadPoolExecutor(threads) as ex:
        got = list(ex.map(lambda k: _get(base, out, k), keys))
    info = dict(chunks=len(keys), empty=sum(1 for g in got if g < 0), mib=round(sum(g for g in got if g > 0) / 2 ** 20), seconds=round(time.time() - t0))
    log(f'{base.split("/")[-1]} level {level}: {info["chunks"]} chunks ({info["empty"]} empty), {info["mib"]} MiB in {info["seconds"]}s -> {out}')
    return info
