"""Keep the box's flat script folder and the repo's status folders in step (run on the Mac, repo root).

On the GPU box every script lives flat in ~/scroll-prizes/bin/ (Nieuwlaar's scripts in bin/ink343/, the ink-first
package in bin/ink-first-src/), so jobs and the scripts that call each other ($S/bin/<name>) never depend on the repo's
folders. In the repo the same files are sorted by status: pipeline/, experiments/, dead-ends/, archive/, infra/box/.
File names are unique across those folders, so the name is the link.

Usage: python3 infra/box/sync_bin.py [check]          what differs, what is only on the box, only in the repo
       python3 infra/box/sync_bin.py pull [name ...]   copy the box version into its repo folder (all differing if no names)
       python3 infra/box/sync_bin.py push name ...     copy repo scripts to the box (names required: jobs may be using them)
Box address: $BOX, else the BOX= line of infra/aws/spot.env."""
import hashlib, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FOLDERS = ('pipeline', 'experiments', 'dead-ends', 'archive', 'infra/box')
MAC_ONLY = {'inkfirst_pilot.sh', 'inkfirst_sweep.sh', 'sync_bin.py'}   # launchers that run on the Mac


def box_host():
    if os.environ.get('BOX'):
        return os.environ['BOX']
    env = os.path.join(ROOT, 'infra/aws/spot.env')
    for line in open(env) if os.path.exists(env) else ():
        m = re.match(r'\s*BOX="?([^"\s]+)', line)
        if m:
            return m.group(1)
    sys.exit('set BOX=user@host')


def repo_files():
    """bin-relative name -> repo path, for every script that belongs on the box."""
    out = {}
    # private folders kept out of git (.git/info/exclude, lines ending in '/') are not synced to the box's shared bin
    ex = os.path.join(ROOT, '.git', 'info', 'exclude')
    private = {l.strip().strip('/') for l in open(ex) if l.strip().endswith('/') and not l.startswith('#')} if os.path.exists(ex) else set()
    for top in FOLDERS:
        for d, dirs, files in os.walk(os.path.join(ROOT, top)):
            rel = os.path.relpath(d, ROOT)
            dirs[:] = [x for x in dirs if x not in ('runs', '__pycache__', 'build', '.pytest_cache') and not x.endswith('.egg-info')
                       and os.path.join(rel, x) not in private]
            for f in files:
                if f in MAC_ONLY or f.startswith('.') or not (f.endswith(('.sh', '.py')) or f.startswith('LICENSE') or rel.endswith('ink343')):
                    continue
                p = os.path.join(rel, f)
                if '/tool/' in p + '/':
                    if '/tool/src/ink_first/' not in p:
                        continue
                    name = 'ink-first-src/ink_first/' + f
                elif rel.endswith('ink343'):
                    name = 'ink343/' + f
                else:
                    name = f
                if name in out:
                    sys.exit(f'name clash: {name}: {out[name]} and {p}')
                out[name] = p
    return out


def md5(p):
    return hashlib.md5(open(p, 'rb').read()).hexdigest()


def box_sums(host):
    cmd = ('cd ~/scroll-prizes/bin && find . \\( -name __pycache__ -o -name "*.egg-info" -o -name stroke-score-src \\) -prune '
           '-o -type f -print0 | xargs -0 md5sum')
    r = subprocess.run(['ssh', '-o', 'BatchMode=yes', host, cmd], capture_output=True, text=True, timeout=120)
    sums = {}
    for line in r.stdout.splitlines():
        h, p = line.split(None, 1)
        sums[p[2:] if p.startswith('./') else p] = h
    return sums


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'check'
    names = sys.argv[2:]
    host = box_host()
    repo = repo_files()
    box = box_sums(host)
    differ = sorted(n for n in repo if n in box and box[n] != md5(os.path.join(ROOT, repo[n])))
    if mode == 'check':
        print(f'{len(repo)} repo scripts, {len(box)} box files; differ: {len(differ)}')
        for n in differ:
            print('  differ   ', n, '->', repo[n])
        for n in sorted(set(box) - set(repo)):
            print('  box only ', n)
        for n in sorted(set(repo) - set(box)):
            print('  repo only', n, '(', repo[n], ')')
    elif mode == 'pull':
        for n in names or differ:
            if n not in repo:
                sys.exit(f'{n}: not in the repo; put it in a status folder first')
            subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', f'{host}:scroll-prizes/bin/{n}', os.path.join(ROOT, repo[n])], check=True)
            print('pulled', n, '->', repo[n])
    elif mode == 'push':
        if not names:
            sys.exit('push needs names (jobs on the box may be running the current copies)')
        for n in names:
            if n not in repo:
                sys.exit(f'{n}: not in the repo')
            subprocess.run(['scp', '-q', '-o', 'BatchMode=yes', os.path.join(ROOT, repo[n]), f'{host}:scroll-prizes/bin/{n}'], check=True)
            print('pushed', repo[n], '->', n)
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
