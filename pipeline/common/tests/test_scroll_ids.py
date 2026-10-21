"""Tests for scroll_ids.py: every name form we use parses to one ID, and back.  python3 -m unittest discover -s pipeline/common/tests"""
import os, sys, unittest
from dataclasses import replace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import scroll_ids as I  # noqa: E402


class TestNames(unittest.TestCase):
    def test_scroll_names(self):
        for s in ('139', '0139', 'PHerc0139', 'PHerc. 139', 'PHerc139'):
            self.assertEqual(I.scroll_name(s), 'PHerc0139')
        self.assertEqual(I.scroll_name('0175A'), 'PHerc0175A')
        self.assertEqual(I.scroll_name('Paris4'), 'PHercParis4')
        with self.assertRaises(ValueError):
            I.scroll_name('boxA')

    def test_render_and_winding(self):
        r = I.parse('exp30k-z7680_w044_66', scroll='0139')
        self.assertEqual((r.id, r.kind, r.layers, r.fit), ('PHerc0139/z7680/w044', 'winding', 66, 'exp30k'))
        self.assertEqual(r.legacy_render, 'exp30k-z7680_w044_66')
        self.assertEqual(r.winding_ref.legacy_render, 'exp30k-z7680_w044')
        self.assertEqual(I.parse('exp30k-z12000_w062', scroll='0139').id, 'PHerc0139/z12000/w062')

    def test_window_forms(self):
        a = I.parse('z7680w044n64m128', scroll='0139')
        b = I.parse('t2-z7680w044n64m128', scroll='0139')
        c = I.parse('PHerc0139/z7680/w044/n64m128')
        self.assertEqual(a.id, 'PHerc0139/z7680/w044/n64m128')
        self.assertEqual(a.kind, 'window')
        self.assertEqual(b.tag, 't2')
        self.assertEqual(replace(b, tag=None), a)
        self.assertEqual(c, a)
        self.assertEqual(a.legacy_window, 'z7680w044n64m128')
        self.assertEqual(I.parse('z7680w029n64m0dl', scroll='0139').tag, 'dl')
        self.assertEqual(I.parse('line-z9680w044', scroll='0139').id, 'PHerc0139/z9680/w044')

    def test_board_mark_and_control(self):
        m = I.parse('0139-boxA:exp30k-z7680_w044')
        self.assertEqual((m.id, m.tag), ('PHerc0139/z7680/w044', 'boxA'))
        self.assertEqual(I.parse('c0841_w00_66').id, 'PHerc0841/seg/w00')
        self.assertEqual(I.parse('PHerc0841/seg/ag2814').kind, 'segment')

    def test_scroll_must_be_known_and_agree(self):
        with self.assertRaises(ValueError):
            I.parse('exp30k-z7680_w044')                       # no scroll in the name, none passed
        with self.assertRaises(ValueError):
            I.parse('0139-boxA:exp30k-z7680_w044', scroll='0841')
        with self.assertRaises(ValueError):
            I.parse('something-else')

    def test_round_trip(self):
        for s in ('PHerc0139', 'PHerc0139/z7680/w044', 'PHerc0139/z7680/w044/n0m64', 'PHerc0841/seg/ag2814'):
            self.assertEqual(I.parse(s).id, s)


class TestFacesAndDepths(unittest.TestCase):
    def test_faces(self):
        self.assertEqual(I.face('render66', '_reverse'), 'reading')
        self.assertEqual(I.face('render66', ''), 'back')
        self.assertEqual(I.face('track2', 'fwd'), 'reading')
        self.assertEqual(I.face('track2', 'rev'), 'back')
        self.assertEqual(I.face('render66', '_reverse', normal_inward=True), 'back')
        self.assertEqual(I.face_token('track2', 'reading'), 'fwd')
        self.assertEqual(I.face_token('render66', 'back', normal_inward=True), '_reverse')
        with self.assertRaises(ValueError):
            I.face('track2', '_reverse')
        with self.assertRaises(ValueError):
            I.face_token('track2', 'front')

    def test_depths(self):
        self.assertEqual([I.depth_label(d) for d in (-1, 0, 1)], ['d-1', 'd+0', 'd+1'])
        self.assertEqual([I.parse_depth(s) for s in ('d-1', 'd+0', '+1', '-15')], [-1, 0, 1, -15])


if __name__ == '__main__':
    unittest.main()
