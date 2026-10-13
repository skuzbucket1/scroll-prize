#!/usr/bin/env python3
"""Mirror a public S3 prefix to local disk — v2: persistent keep-alive HTTPS connection per worker thread (small objects go
~5-10x faster than one TLS handshake per object), cached listing (<dest>/.mirror-listing.json; pass --relist to refresh),
size-verified resume, retries with backoff, progress + MIRROR-EXIT marker.
Usage: mirror_s3_v2.py <bucket-url> <prefix/> <dest-dir> [threads=32] [--levels 5,4,3,2,1,0] [--relist]"""
import sys, os, re, json, time, threading, http.client, urllib.parse, urllib.request, concurrent.futures as cf
args = [a for a in sys.argv[1:] if not a.startswith('--')]
bucket, prefix, dest = args[0].rstrip('/'), args[1], args[2]
threads = int(args[3]) if len(args) > 3 else 32
levels = sys.argv[sys.argv.index('--levels') + 1].split(',') if '--levels' in sys.argv else None
relist = '--relist' in sys.argv
host = urllib.parse.urlparse(bucket).netloc
os.makedirs(dest, exist_ok=True)
def http_get(url, timeout=120, tries=8):
    for a in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=timeout) as r: return r.read()
        except urllib.error.HTTPError as e:
            if e.code == 404 or a == tries - 1: raise
        except Exception:
            if a == tries - 1: raise
        time.sleep(min(60, 3 * (a + 1)))
def list_keys(pfx, delimiter=False):
    token = None
    while True:
        url = f"{bucket}/?list-type=2&prefix={urllib.parse.quote(pfx)}&max-keys=1000" + ("&delimiter=%2F" if delimiter else "") + (f"&continuation-token={urllib.parse.quote(token)}" if token else "")
        xml = http_get(url).decode()
        for block in re.findall(r"<Contents>(.*?)</Contents>", xml, re.S):
            k = re.search(r"<Key>([^<]+)</Key>", block); s = re.search(r"<Size>(\d+)</Size>", block)
            if k and s: yield k.group(1), int(s.group(1))
        m = re.search(r"<NextContinuationToken>([^<]+)</NextContinuationToken>", xml)
        if not m: break
        token = m.group(1)
cache = os.path.join(dest, ".mirror-listing.json"); t0 = time.time()
if os.path.exists(cache) and not relist:
    groups = [(n, [tuple(x) for x in g]) for n, g in json.load(open(cache))]; print(f"listing loaded from cache ({cache})", flush=True)
else:
    groups = []
    if levels:
        groups.append(("meta", [(k, s) for k, s in list_keys(prefix, delimiter=True) if '/' not in k[len(prefix):]]))
        for lv in levels: groups.append((f"level {lv}", list(list_keys(prefix + lv + '/'))))
    else:
        groups.append(("all", list(list_keys(prefix))))
    json.dump(groups, open(cache, "w")); print(f"listing saved to {cache}", flush=True)
total_n = sum(len(g) for _, g in groups); total_b = sum(s for _, g in groups for _, s in g)
print(f"{total_n:,} objects, {total_b/1e9:.1f} GB (listing {time.time()-t0:.0f}s)", flush=True)
for name, g in groups: print(f"  {name}: {len(g):,} objects, {sum(s for _, s in g)/1e9:.2f} GB", flush=True)
local = threading.local(); lock = threading.Lock(); st = {"n": 0, "b": 0, "skip": 0}; failed = []; t1 = time.time()
def conn(fresh=False):
    c = getattr(local, "conn", None)
    if c is None or fresh:
        if c is not None:
            try: c.close()
            except Exception: pass
        c = http.client.HTTPSConnection(host, timeout=120); local.conn = c
    return c
def get_keepalive(key, size):
    for a in range(8):
        try:
            c = conn(fresh=(a > 0)); c.request("GET", "/" + urllib.parse.quote(key), headers={"Connection": "keep-alive"})
            r = c.getresponse(); data = r.read()
            if r.status == 404: return None
            if r.status != 200: raise IOError(f"HTTP {r.status}")
            if len(data) != size: raise IOError(f"short read {len(data)} != {size}")
            return data
        except Exception as e:
            if a == 7: raise
            time.sleep(min(60, 2 * (a + 1)))
def fetch(item):
    k, s = item; path = os.path.join(dest, k[len(prefix):])
    if os.path.exists(path) and os.path.getsize(path) == s:
        with lock: st["n"] += 1; st["skip"] += 1
        return
    os.makedirs(os.path.dirname(path), exist_ok=True)
    try:
        data = get_keepalive(k, s)
        if data is None: raise IOError("404")
        tmp = path + f".part.{os.getpid()}"
        with open(tmp, "wb") as f: f.write(data)
        os.replace(tmp, path)
        with lock:
            st["n"] += 1; st["b"] += s
            if st["n"] % 2000 == 0:
                el = time.time() - t1; rate = st["b"] / el if el else 0; files_s = (st["n"] - st["skip"]) / el if el else 0
                rem_b = total_b - st["b"]; eta = rem_b / rate if rate else 0
                print(f"  {st['n']:,}/{total_n:,} files  {st['b']/1e9:.2f} GB  {rate/1e6:.1f} MB/s  {files_s:.0f} files/s  eta {eta/3600:.1f} h  (skipped {st['skip']})", flush=True)
    except Exception as e:
        with lock: failed.append((k, str(e)[:80]))
for name, g in groups:
    print(f"== {name}", flush=True)
    with cf.ThreadPoolExecutor(threads) as ex: list(ex.map(fetch, g))
el = time.time() - t1
print(f"done: {st['n']:,} files, {st['b']/1e9:.2f} GB downloaded ({st['skip']} already present) in {el/3600:.2f} h, {len(failed)} failed", flush=True)
if failed:
    with open(os.path.join(dest, ".mirror-failed.txt"), "w") as f: f.write("\n".join(f"{k}\t{e}" for k, e in failed))
print(f"MIRROR-EXIT: {0 if not failed else 1}")
