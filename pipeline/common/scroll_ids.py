"""One name for each scroll, winding and window, and one name for each face of the sheet (2026-10-21).

Canonical IDs. Folder names, page labels and board marks are made from these:
  scroll    PHerc0139
  winding   PHerc0139/z7680/w044          winding 44 of the fit band that starts at z 7680
  window    PHerc0139/z7680/w044/n64m128  the window of that winding's mesh whose first node row is 64 and first node column 128
                                          (the window size belongs to the survey that made it, e.g. 32 x 64 nodes)
  segment   PHerc0841/seg/ag2814          a segment known by its official name (controls)

parse() also reads the legacy forms we have used. Pass scroll= when the name doesn't say it:
  exp30k-z7680_w044 / exp30k-z7680_w044_66   a fit's winding mesh / its 66-layer render (fit family exp30k)
  z7680w044n64m128 / z7680w044n64m0dl        a 2.4 µm survey window / the deep-look crop made from it
  t2-z7680w044n64m128, line-z9680w044        human-view crops: <purpose>-<window or winding>
  0139-boxA:exp30k-z7680_w044                a scroll-ops board mark: <scroll short>-<board>:<render>
  c0841_w00 / c0841_w00_66                   a control segment and its render
Legacy names come back from Ref.legacy_render / Ref.legacy_window, so new code finds the existing folders.

Faces: 'reading' (the inked face we read) and 'back'. Each pipeline's own face token is translated here and only here.
Stdlib only, no I/O. Self-test: python3 scroll_ids.py   Tests: python3 -m unittest discover -s pipeline/common/tests"""
import re
from dataclasses import dataclass, replace

FACES = ('reading', 'back')

# Face tokens per pipeline, for a mesh whose +normal points away from the scroll centre (side_check; conventions.normal_sign).
# For a mesh whose normal points inward, pass normal_inward=True and the faces swap.
#   render66: the 66-layer renders read by the villa models / Reader V3 / Hecate: map file suffix '_reverse' or none
#             (conventions.map_name(reverse=True) = reading face).
#   track2:   the 2.4 µm survey crops: ink_fwd / ink_rev ('fwd' = the reading face; face_check of 37 windows, 2026-10-20).
FACE_TOKENS = {
    'render66': {'_reverse': 'reading', '': 'back'},
    'track2': {'fwd': 'reading', 'rev': 'back'},
}


def face(pipeline, token, normal_inward=False):
    """a pipeline's face token -> 'reading' or 'back'"""
    try:
        f = FACE_TOKENS[pipeline][token]
    except KeyError:
        raise ValueError(f'unknown face token {token!r} for pipeline {pipeline!r} (known: {FACE_TOKENS})') from None
    return FACES[1 - FACES.index(f)] if normal_inward else f


def face_token(pipeline, f, normal_inward=False):
    """'reading' / 'back' -> that pipeline's token"""
    if f not in FACES:
        raise ValueError(f'face must be one of {FACES}, not {f!r}')
    if normal_inward:
        f = FACES[1 - FACES.index(f)]
    return {v: k for k, v in FACE_TOKENS[pipeline].items()}[f]


def depth_label(d):
    """-1 -> 'd-1', 0 -> 'd+0'"""
    return f'd{int(d):+d}'


def parse_depth(s):
    m = re.fullmatch(r'd?([+-]?\d+)', s.strip())
    if not m:
        raise ValueError(f'not a depth: {s!r}')
    return int(m.group(1))


def scroll_name(s):
    """'139', '0139', 'PHerc0139', 'PHerc. 139', '0175A', 'Paris4' -> 'PHerc0139' / 'PHerc0175A' / 'PHercParis4'"""
    t = re.sub(r'^PHerc\.?\s*', '', s.strip())
    m = re.fullmatch(r'(\d{1,4})([A-Z]?)', t)
    if m:
        return f'PHerc{int(m.group(1)):04d}{m.group(2)}'
    m = re.fullmatch(r'Paris\s*(\d)', t)
    if m:
        return f'PHercParis{m.group(1)}'
    raise ValueError(f'not a scroll name: {s!r}')


@dataclass(frozen=True)
class Ref:
    scroll: str
    band: int = None        # z where the fit band starts
    winding: int = None
    n: int = None           # window: first node row
    m: int = None           # window: first node column
    seg: str = None         # official segment name (controls), instead of band / winding
    fit: str = 'exp30k'     # fit family of the winding meshes
    layers: int = None      # a render's layer count (66) when the name was a render
    tag: str = None         # purpose of a crop ('t2', 'line', 'clef', 'dl', a board name): not part of the identity

    @property
    def kind(self):
        return 'segment' if self.seg else 'window' if self.n is not None else 'winding' if self.winding is not None else 'scroll'

    @property
    def id(self):
        if self.seg:
            return f'{self.scroll}/seg/{self.seg}'
        s = self.scroll
        if self.winding is not None:
            s += f'/z{self.band}/w{self.winding:03d}'
        if self.n is not None:
            s += f'/n{self.n}m{self.m}'
        return s

    def __str__(self):
        return self.id

    @property
    def winding_ref(self):
        return replace(self, n=None, m=None, layers=None, tag=None)

    @property
    def legacy_render(self):
        """the folder / file prefix our runs use for this winding: exp30k-z7680_w044 (+ _66 for the render)"""
        if self.winding is None:
            raise ValueError(f'{self.id} is not a winding')
        return f'{self.fit}-z{self.band}_w{self.winding:03d}' + (f'_{self.layers}' if self.layers else '')

    @property
    def legacy_window(self):
        """the 2.4 µm survey's window name: z7680w044n64m128"""
        if self.n is None:
            raise ValueError(f'{self.id} is not a window')
        return f'z{self.band}w{self.winding:03d}n{self.n}m{self.m}'


_CANON = re.compile(r'(?P<scroll>PHerc\w+)(?:/seg/(?P<seg>[\w.-]+)|(?:/z(?P<band>\d+)/w(?P<w>\d+)(?:/n(?P<n>\d+)m(?P<m>\d+))?)?)')
_RENDER = re.compile(r'(?P<fit>[a-z]+\d*k?)-z(?P<band>\d+)_w(?P<w>\d+)(?:_(?P<layers>\d+))?')
_WINDOW = re.compile(r'z(?P<band>\d+)w(?P<w>\d+)(?:n(?P<n>\d+)m(?P<m>\d+))?(?P<dl>dl)?')
_CONTROL = re.compile(r'c(?P<num>\d{3,4}[A-Z]?)_(?P<seg>[A-Za-z]+\d+)(?:_(?P<layers>\d+))?')


def _num(x):
    return int(x) if x is not None else None


def parse(name, scroll=None):
    """any of our names -> Ref; scroll= is used when the name doesn't say the scroll (and must agree when it does)"""
    s = name.strip()
    sc = scroll_name(scroll) if scroll else None
    m = _CANON.fullmatch(s)
    if m:
        r = Ref(scroll=scroll_name(m['scroll']), band=_num(m['band']), winding=_num(m['w']), n=_num(m['n']), m=_num(m['m']), seg=m['seg'])
        return _agree(r, sc, name)
    tag = None
    b = re.fullmatch(r'(?P<short>\d{3,4}[A-Z]?|Paris\d)-(?P<board>[\w]+):(?P<rest>.+)', s)
    if b:                                                       # board mark 0139-boxA:exp30k-z7680_w044
        sc = _agree_name(scroll_name(b['short']), sc, name); tag = b['board']; s = b['rest']
    else:
        t = re.fullmatch(r'(?P<tag>[a-z][a-z0-9]*)-(?P<rest>z\d+w\d+.*)', s)
        if t:                                                   # crop t2-z7680w044n64m128 / line-z9680w044
            tag = t['tag']; s = t['rest']
    m = _RENDER.fullmatch(s)
    if m:
        return Ref(scroll=_need(sc, name), band=int(m['band']), winding=int(m['w']), fit=m['fit'], layers=_num(m['layers']), tag=tag)
    m = _WINDOW.fullmatch(s)
    if m:
        return Ref(scroll=_need(sc, name), band=int(m['band']), winding=int(m['w']), n=_num(m['n']), m=_num(m['m']),
                   tag='dl' if m['dl'] else tag)
    m = _CONTROL.fullmatch(s)
    if m:
        return Ref(scroll=_agree_name(scroll_name(m['num']), sc, name), seg=m['seg'], layers=_num(m['layers']), tag=tag)
    raise ValueError(f'not one of our names: {name!r}')


def _need(sc, name):
    if not sc:
        raise ValueError(f'{name!r} does not say the scroll: pass scroll=')
    return sc


def _agree_name(found, given, name):
    if given and given != found:
        raise ValueError(f'{name!r} names {found}, but scroll={given} was passed')
    return found


def _agree(r, given, name):
    _agree_name(r.scroll, given, name)
    return r


def _selftest():
    r = parse('exp30k-z7680_w044_66', scroll='0139')
    assert r.id == 'PHerc0139/z7680/w044' and r.layers == 66 and r.legacy_render == 'exp30k-z7680_w044_66', r
    w = parse('t2-z7680w044n64m128', scroll='PHerc0139')
    assert w.id == 'PHerc0139/z7680/w044/n64m128' and w.tag == 't2' and w.legacy_window == 'z7680w044n64m128', w
    assert parse(w.id) == replace(w, tag=None) and parse(w.id).winding_ref.id == 'PHerc0139/z7680/w044'
    assert parse('0139-boxA:exp30k-z7680_w044').tag == 'boxA' and parse('c0841_w00_66').id == 'PHerc0841/seg/w00'
    assert face('render66', '_reverse') == 'reading' and face('track2', 'rev') == 'back' and face('track2', 'fwd', normal_inward=True) == 'back'
    assert face_token('render66', 'reading') == '_reverse' and depth_label(-1) == 'd-1' and depth_label(0) == 'd+0' and parse_depth('d+1') == 1
    print('scroll_ids self-test OK')


if __name__ == '__main__':
    _selftest()
