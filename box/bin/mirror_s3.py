#!/usr/bin/env python3
"""Mirror a public S3 prefix (e.g. an OME-Zarr volume) to local disk.
Lists keys with ListObjectsV2, downloads with a thread pool, retries with backoff, resumes by exact size.
Usage: mirror_s3.py <bucket-url> <prefix/> <dest-dir> [threads=32] [--levels 5,4,3,2,1,0]
With --levels, root metadata files under <prefix/> are fetched first, then each level in the given order."""
import sys, os, re, time, threading, urllib.request, urllib.parse, concurrent.futures as cf
args = [a for a in sys.argv[1:] if not a.startswith('--')]
bucket, prefix, dest = args[0].rstrip('/'), args[1], args[2]
threads = int(args[3]) if len(args) > 3 else 32
levels = sys.argv[sys.argv.index('--levels') + 1].split(',') if '--levels' in sys.argv else None
os.makedirs(dest, exist_ok=True)
def http(url, timeout=120, tries=8):
    for a in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404: raise
            if a == tries - 1: raise
        except Exception:
            if a == tries - 1: raise
        time.sleep(min(60, 3 * (a + 1)))
def list_keys(pfx):
    token = None
    while True:
        url = f"{bucket}/?list-type=2&prefix={urllib.parse.quote(pfx)}&max-keys=1000" + (f"&continuation-token={urllib.parse.quote(token)}" if token else "")
        xml = http(url).decode()
        for block in re.findall(r"<Contents>(.*?)</Contents>", xml, re.S):
            k = re.search(r"<Key>([^<]+)</Key>", block); s = re.search(r"<Size>(\d+)</Size>", block)
            if k and s: yield k.group(1), int(s.group(1))
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", xml)
        if not m: break
        token = m.group(1)
t0 = time.time(); groups = []
if levels:
    groups.append(("meta", [(k, s) for k, s in list_keys(prefix) if '/' not in k[len(prefix):]]))
    for lv in levels: groups.append((f"level {lv}", list(list_keys(prefix + lv + '/'))))
else:
    groups.append(("all", list(list_keys(prefix))))
total_n = sum(len(g) for _, g in groups); total_b = sum(s for _, g in groups for _, s in g)
print(f"listed {total_n:,} objects, {total_b/1e9:.1f} GB, in {time.time()-t0:.0f}s", flush=True)
for name, g in groups: print(f"  {name}: {len(g):,} objects, {sum(s for _, s in g)/1e9:.2f} GB", flush=True)
lock = threading.Lock(); st = {"n": 0, "b": 0, "skip": 0}; failed = []; t1 = time.time()
def fetch(item):
    k, s = item; path = os.path.join(dest, k[len(prefix):])
    if os.path.exists(path) and os.path.getsize(path) == s:
        with lock: st["n"] += 1; st["skip"] += 1
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        data = http(f"{bucket}/{urllib.parse.quote(k)}")
        if len(data) != s: raise IOError(f"short read {len(data)} != {s}")
        tmp = path + ".part"
        with open(tmp, "wb") as f: f.write(data)
        os.replace(tmp, path)
        with lock:
            st["n"] += 1; st["b"] += s
            if st["n"] % 2000 == 0:
                el = time.time() - t1; rate = st["b"] / el if el else 0
                rem = (total_b - st["b"]) / rate if rate else 0
                print(f"  {st['n']:,}/{total_n:,} files  {st['b']/1e9:.1f} GB  {rate/1e6:.1f} MB/s  eta {rem/3600:.1f} h  (skipped {st['skip']})", flush=True)
    except Exception as e:
        with lock: failed.append((k, str(e)[:80]))
for name, g in groups:
    print(f"== {name}", flush=True)
    with cf.ThreadPoolExecutor(threads) as ex: list(ex.map(fetch, g))
el = time.time() - t1
print(f"done: {st['n']:,} files, {st['b']/1e9:.1f} GB downloaded ({st['skip']} already present) in {el/3600:.2f} h, {len(failed)} failed", flush=True)
if failed:
    with open(os.path.join(dest, ".mirror-failed.txt"), "w") as f: f.write("\n".join(f"{k}\t{e}" for k, e in failed))
print(f"MIRROR-EXIT: {0 if not failed else 1}")
