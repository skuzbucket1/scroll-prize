"""Tests for platform_config.py on the public example config.  python3 -m unittest discover -s pipeline/common/tests"""
import copy, os, sys, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import platform_config as P  # noqa: E402

EXAMPLE = os.path.join(HERE, 'platform.example.toml')


class TestExample(unittest.TestCase):
    def setUp(self):
        self.cfg = P.load(EXAMPLE, node='gpubox')

    def test_lookups(self):
        self.assertEqual(self.cfg.gpu('gpubox:gpu0'), 'GPU-00000000-0000-0000-0000-000000000001')
        self.assertEqual(self.cfg.gpu('gpu0'), self.cfg.gpu('gpubox:gpu0'))           # this node
        self.assertEqual(self.cfg.path('renders'), '/data/scroll/work/renders')
        self.assertEqual(self.cfg.gpus(), {'gpu0': 'GPU-00000000-0000-0000-0000-000000000001'})
        v = self.cfg.volume('PHerc0343')
        self.assertEqual(v['voxel_um'], 8.64)
        self.assertTrue(v['url'].endswith('/PHerc0343/volumes/20250521140437-8.640um-1.2m-116keV-masked.zarr'))
        self.assertEqual(self.cfg.volume('PHerc0841', 'rescan')['voxel_um'], 2.403)
        self.assertEqual(self.cfg.checkpoint('reader-v2')['path'], '/data/scroll/checkpoints/ckpt343/reader-v2-step040000.pth')

    def test_refusals(self):
        with self.assertRaises(P.ConfigError):
            self.cfg.gpu('gpubox:gpu1')                                              # usable = false
        with self.assertRaises(P.ConfigError):
            self.cfg.gpu('nobox:gpu0')
        with self.assertRaises(P.ConfigError):
            self.cfg.path('nothing')
        with self.assertRaises(P.ConfigError):
            self.cfg.volume('PHerc9999')

    def test_problems_found(self):
        d = copy.deepcopy(self.cfg.data)
        d['nodes']['gpubox']['gpus']['gpu1']['uuid'] = d['nodes']['gpubox']['gpus']['gpu0']['uuid']     # duplicate UUID
        d['nodes']['gpubox']['paths']['work'] = 'relative/path'
        d['volumes']['PHerc0343']['main']['voxel_um'] = 9.36                                             # disagrees with the id
        d['volumes']['PHerc0139'] = {'rescan': d['volumes']['PHerc0841']['rescan']}                     # no main scan
        d['ui']['results']['node'] = 'elsewhere'
        p = P.Platform(d).problems()
        self.assertEqual(len(p), 5, p)
        with self.assertRaises(P.ConfigError):
            P.Platform(d).check()


if __name__ == '__main__':
    unittest.main()
