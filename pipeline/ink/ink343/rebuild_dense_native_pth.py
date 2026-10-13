#!/usr/bin/env python3
"""rebuild_dense_native_pth.py - rebuild a villa-loadable dense_native-016000 checkpoint from the public release.

The public model repository huggingface.co/Nieuwlaar/ink9um-dense-native ships the step-16000 weights as a bare
safetensors state_dict plus the training configuration. villa's flat ink inference needs a .pth payload that carries
the config, so I wrap the two (the three-line recipe from that repository's README):

  python rebuild_dense_native_pth.py dense_native_016000.safetensors train_dense_native.json dense_native-016000.rebuilt.pth

The rebuilt file is not byte-identical to the original training checkpoint (sha256 aacf6cb8...; that file also holds
optimizer state and a few trainer-added config keys). On the gate crop, the maps from the rebuilt file and from the
original checkpoint agree to r >= 0.99999 with a maximum difference of 1/255 on under 1 % of the pixels, the same level
as between repeated runs of the original checkpoint.
"""
import json
import sys

import torch
from safetensors.torch import load_file


def main():
    if len(sys.argv) != 4:
        raise SystemExit(__doc__)
    weights, config, out = sys.argv[1:]
    torch.save({'model': load_file(weights), 'config': json.load(open(config)), 'step': 16000}, out)
    print('written', out)


if __name__ == '__main__':
    main()
