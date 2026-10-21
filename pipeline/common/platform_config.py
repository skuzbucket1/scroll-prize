"""Where things are, read from ONE config file instead of being written into each script (2026-10-21).
Meant to grow into the config of the whole pipeline: machines, storage, volumes, models and the pages that show the results.

The file is found at $SCROLL_PLATFORM, else ~/.config/scroll/platform.toml, else platform.toml at the repo root. It is TOML; JSON with
the same structure works too (for Pythons older than 3.11). Our real one is private, since it holds machines and addresses. The
public example is platform.example.toml next to this file.

Sections:
  [nodes.<node>]                  host (ssh name), address, hostnames (to know which node we're on), role, cost, rules
  [nodes.<node>.paths]            work, renders, maps, scratch, checkpoints, python, ... (absolute or ~)
  [nodes.<node>.gpus.<role>]      uuid, model, vram_gb, usable (false = never schedule: gpu() refuses it), note
  [volumes.<scroll>.<scan>]       id (e.g. 20250728140407-9.362um-1.2m-113keV-masked.zarr), url (default: bucket/<scroll>/volumes/<id>),
                                  voxel_um (checked against the id). Scan 'main' = the eligible scan we read.
  [checkpoints.<name>]            path (absolute, or relative to the node's paths.checkpoints), sha256, source, licence, credit, status
  [ui.<name>]                     url, node (or hosted), served_by, built_by, data, auth, menu, note
  bucket                          the open-data bucket's URL

Python:  cfg = platform_config.load(); cfg.gpu('box:gpu0'); cfg.path('renders'); cfg.volume_url('PHerc0139'); cfg.checkpoint('reader-v3')
Shell:   G=$(python3 platform_config.py get gpu box:gpu0); R=$(python3 platform_config.py get path box:renders)
Check:   python3 platform_config.py check [file]   (validates it; exits 1 and lists every problem)
Stdlib only.
Usage: platform_config.py check [file] | get gpu|path|volume_url|checkpoint <ref> | export-json [file]"""
import json, os, re, socket, sys

UUID = re.compile(r'GPU-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}')
VOLUME_ID = re.compile(r'\d{14}-(\d+\.\d+)um-[\w.-]+\.zarr')
SHA256 = re.compile(r'[0-9a-f]{64}')
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))


class ConfigError(ValueError):
    pass


def find(path=None):
    for p in (path, os.environ.get('SCROLL_PLATFORM'), os.path.expanduser('~/.config/scroll/platform.toml'),
              os.path.join(REPO, 'platform.toml')):
        if p and os.path.exists(os.path.expanduser(p)):
            return os.path.expanduser(p)
    raise ConfigError('no platform config: set SCROLL_PLATFORM, or put one at ~/.config/scroll/platform.toml or <repo>/platform.toml '
                      f'(example: {os.path.join(HERE, "platform.example.toml")})')


def read(path):
    if path.endswith('.json'):
        return json.load(open(path))
    try:
        import tomllib
    except ImportError:                                           # Python < 3.11
        try:
            import tomli as tomllib
        except ImportError:
            raise ConfigError(f'{path}: TOML needs Python >= 3.11 (or tomli); use a .json copy instead '
                              '(python3.11+ platform_config.py export-json)') from None
    with open(path, 'rb') as f:
        return tomllib.load(f)


class Platform:
    def __init__(self, data, source='<dict>', node=None):
        self.data, self.source = data, source
        self.nodes = data.get('nodes', {}); self.volumes = data.get('volumes', {}); self.checkpoints = data.get('checkpoints', {})
        self.ui = data.get('ui', {}); self.bucket = data.get('bucket', 'https://vesuvius-challenge-open-data.s3.amazonaws.com')
        self._node = node

    # ---- which node are we on ----
    def this_node(self):
        if self._node:
            return self._node
        if os.environ.get('SCROLL_NODE'):
            return os.environ['SCROLL_NODE']
        h = socket.gethostname().split('.')[0]
        for name, n in self.nodes.items():
            if h in n.get('hostnames', []) or h == name:
                return name
        raise ConfigError(f'which node is this? hostname {h!r} is in no node\'s hostnames; set SCROLL_NODE')

    def _split(self, ref):
        node, _, key = ref.rpartition(':')
        node = node or self.this_node()
        if node not in self.nodes:
            raise ConfigError(f'unknown node {node!r} (nodes: {", ".join(self.nodes)})')
        return node, key

    # ---- lookups ----
    def node(self, name=None):
        return self.nodes[self._split(f'{name}:x')[0] if name else self.this_node()]

    def gpu(self, ref):
        """'box:gpu0' (or 'gpu0' on this node) -> UUID; refuses a GPU marked usable = false"""
        node, role = self._split(ref)
        g = self.nodes[node].get('gpus', {}).get(role)
        if g is None:
            raise ConfigError(f'node {node} has no GPU {role!r} (has: {", ".join(self.nodes[node].get("gpus", {}))})')
        if not g.get('usable', True):
            raise ConfigError(f'{node}:{role} is marked not usable: {g.get("note", "")}')
        return g['uuid']

    def gpus(self, node=None, usable=True):
        node = node or self.this_node()
        return {r: g['uuid'] for r, g in self.nodes[node].get('gpus', {}).items() if g.get('usable', True) or not usable}

    def path(self, ref):
        """'box:renders' (or 'renders' on this node) -> the absolute path, ~ expanded on this node only"""
        node, key = self._split(ref)
        p = self.nodes[node].get('paths', {}).get(key)
        if p is None:
            raise ConfigError(f'node {node} has no path {key!r} (has: {", ".join(self.nodes[node].get("paths", {}))})')
        return os.path.expanduser(p) if node == self._here() else p

    def _here(self):
        try:
            return self.this_node()
        except ConfigError:
            return None

    def volume(self, scroll, scan='main'):
        try:
            v = dict(self.volumes[scroll][scan])
        except KeyError:
            raise ConfigError(f'no volume {scroll}/{scan} (scrolls: {", ".join(self.volumes)})') from None
        v.setdefault('url', f'{self.bucket}/{scroll}/volumes/{v["id"]}')
        v.setdefault('voxel_um', float(VOLUME_ID.fullmatch(v['id']).group(1)))
        return v

    def volume_url(self, scroll, scan='main'):
        return self.volume(scroll, scan)['url']

    def checkpoint(self, name, node=None):
        """-> dict(path=absolute path on that node, sha256=..., ...)"""
        try:
            c = dict(self.checkpoints[name])
        except KeyError:
            raise ConfigError(f'no checkpoint {name!r} (have: {", ".join(self.checkpoints)})') from None
        if not c['path'].startswith(('/', '~')):
            c['path'] = os.path.join(self.path(f'{node or self.this_node()}:checkpoints'), c['path'])
        return c

    # ---- checks ----
    def problems(self):
        out, seen = [], {}
        if not self.nodes:
            out.append('no [nodes]')
        for name, n in self.nodes.items():
            for k, p in n.get('paths', {}).items():
                if not isinstance(p, str) or not p.startswith(('/', '~')):
                    out.append(f'nodes.{name}.paths.{k}: {p!r} is not absolute (/ or ~)')
            for role, g in n.get('gpus', {}).items():
                u = g.get('uuid', '')
                if not UUID.fullmatch(u):
                    out.append(f'nodes.{name}.gpus.{role}: uuid {u!r} is not a GPU UUID')
                elif u in seen:
                    out.append(f'nodes.{name}.gpus.{role}: uuid {u} is also {seen[u]}')
                else:
                    seen[u] = f'{name}:{role}'
                if 'usable' in g and not isinstance(g['usable'], bool):
                    out.append(f'nodes.{name}.gpus.{role}: usable must be true / false')
        for sc, scans in self.volumes.items():
            if 'main' not in scans:
                out.append(f'volumes.{sc}: no main scan (the eligible scan we read)')
            for scan, v in scans.items():
                m = VOLUME_ID.fullmatch(v.get('id', ''))
                if not m:
                    out.append(f'volumes.{sc}.{scan}: id {v.get("id")!r} is not a volume id')
                elif 'voxel_um' in v and abs(float(m.group(1)) - v['voxel_um']) > 1e-6:
                    out.append(f'volumes.{sc}.{scan}: voxel_um {v["voxel_um"]} but the id says {m.group(1)}')
        for name, c in self.checkpoints.items():
            if 'path' not in c:
                out.append(f'checkpoints.{name}: no path')
            if c.get('sha256') and not SHA256.fullmatch(c['sha256']):
                out.append(f'checkpoints.{name}: sha256 is not 64 hex characters')
        for name, u in self.ui.items():
            if 'url' not in u:
                out.append(f'ui.{name}: no url')
            if u.get('node') and u['node'] not in self.nodes:
                out.append(f'ui.{name}: node {u["node"]!r} is not in [nodes]')
        return out

    def check(self):
        p = self.problems()
        if p:
            raise ConfigError(f'{self.source}: ' + '; '.join(p))
        return self


def load(path=None, node=None, check=True):
    p = find(path)
    cfg = Platform(read(p), source=p, node=node)
    return cfg.check() if check else cfg


def _main(argv):
    if not argv or argv[0] not in ('check', 'get', 'export-json'):
        sys.exit(__doc__)
    if argv[0] == 'check':
        cfg = load(argv[1] if len(argv) > 1 else None, check=False); p = cfg.problems()
        print(f'{cfg.source}: {len(cfg.nodes)} nodes, {sum(len(n.get("gpus", {})) for n in cfg.nodes.values())} GPUs, '
              f'{sum(len(v) for v in cfg.volumes.values())} volumes, {len(cfg.checkpoints)} checkpoints, {len(cfg.ui)} UIs')
        for x in p:
            print('  PROBLEM', x)
        sys.exit(1 if p else 0)
    if argv[0] == 'export-json':
        cfg = load(argv[1] if len(argv) > 1 else None); out = os.path.splitext(cfg.source)[0] + '.json'
        json.dump(cfg.data, open(out, 'w'), indent=1); print('wrote', out); return
    kind, ref = argv[1], argv[2]
    cfg = load()
    val = {'gpu': cfg.gpu, 'path': cfg.path, 'volume_url': lambda r: cfg.volume_url(*r.split('/', 1)) if '/' in r else cfg.volume_url(r),
           'checkpoint': lambda r: cfg.checkpoint(r)['path']}.get(kind)
    if val is None:
        sys.exit(f'get what? gpu | path | volume_url | checkpoint, not {kind!r}')
    print(val(ref))


if __name__ == '__main__':
    try:
        _main(sys.argv[1:])
    except ConfigError as e:
        sys.exit(f'platform config: {e}')
