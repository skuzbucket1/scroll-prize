"""Stroke score: rank Herculaneum-scroll segments by stroke-like ink on the reading side versus the blind side."""
from .core import Params, run, score, ensemble, usable_area, valid_mask, read_map, row_score, along_profile

__version__ = '0.2.1'
__all__ = ['Params', 'run', 'score', 'ensemble', 'usable_area', 'valid_mask', 'read_map', 'row_score', 'along_profile']
