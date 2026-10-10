"""Stroke score: rank Herculaneum-scroll segments by stroke-like ink on the reading side versus the blind side."""
from .core import Params, run, score, ensemble, usable_area, valid_mask, read_map

__version__ = '0.1.0'
__all__ = ['Params', 'run', 'score', 'ensemble', 'usable_area', 'valid_mask', 'read_map']
