#!/usr/bin/env python3
"""Download selected pyramid levels of a remote zarr v2 group (dimension_separator '/') with a thread pool. Stdlib only."""
import sys, os, json, math, time, urllib.request, urllib.error, concurrent.futures as cf
base, out, levels = sys.argv[1].rstrip('/'), sys.argv[2], sys.argv[3].split(',')
threads = int(sys.argv[4]) if len(sys.argv) > 4 else 16
os.makedirs(out, exist_ok=True)
def fetch(rel):
    dest = os.path.join(out, rel)
    if os.path.exists(dest): return 'skip'
    for attempt in range(4):
        try:
            with urllib.request.urlopen(base + '/' + rel, timeout=90) as r: data = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404: return 'missing'
            if attempt == 3: raise
        except Exception:
            if attempt == 3: raise
        time.sleep(2 * (attempt + 1))
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    tmp = dest + '.part'
    with open(tmp, 'wb') as f: f.write(data)
    os.replace(tmp, dest); return len(data)
for m in ('.zattrs', '.zgroup'): fetch(m)
total, t0 = 0, time.time()
for lv in levels:
    fetch(f'{lv}/.zarray'); arr = json.load(open(os.path.join(out, lv, '.zarray')))
    grid = [math.ceil(s / c) for s, c in zip(arr['shape'], arr['chunks'])]
    keys = [f'{lv}/{z}/{y}/{x}' for z in range(grid[0]) for y in range(grid[1]) for x in range(grid[2])]
    print(f'level {lv}: shape {arr["shape"]} chunks {arr["chunks"]} grid {grid} -> {len(keys)} chunks', flush=True)
    done = missing = 0
    with cf.ThreadPoolExecutor(threads) as ex:
        for res in ex.map(fetch, keys):
            done += 1
            if res == 'missing': missing += 1
            elif isinstance(res, int): total += res
            if done % 1000 == 0: print(f'  {done}/{len(keys)} ({missing} missing) {total/1e9:.2f} GB @ {total/1e6/max(time.time()-t0,1):.1f} MB/s', flush=True)
    print(f'level {lv} done: {missing} missing of {len(keys)}', flush=True)
print(f'TOTAL {total/1e9:.2f} GB in {time.time()-t0:.0f}s'); print('DL-EXIT: 0')
