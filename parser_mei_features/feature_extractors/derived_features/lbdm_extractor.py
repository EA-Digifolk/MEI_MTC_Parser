# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 16:55:47 2023

@author: Nádia Carvalho
"""
from fractions import Fraction

from ...utils import get_one_degree_change


def get_boundary_strength(pitches, intervals):
    """Find the boundary strength of the pitches and intervals"""
    strength = [c*(r1+r2) for r1, r2, c in list(zip(pitches[1:-1], pitches[2:-1], intervals[1:]))]

    if len(strength) == 0: # Very short piece
        return [None, None, None]

    max_spitch = max(strength)
    if max_spitch > 0:
        strength = [s/max_spitch for s in strength]

    return [None] + strength + [None, None]

class LBDMExtractor:

    def __init__(self, stream, features) -> None:
        """
        Initialize LBDMExtractor
        (LBDM: Local Boundary Detection Method)
        """
        self.music_stream = stream
        self.base_features = features

    def get_all_features(self):
        """Get all lbdm features from the stream"""
        features = {}

        features['lbdm_rpitch'], features['lbdm_spitch'] = self.get_lbdm_rpitch()
        features['lbdm_rioi'], features['lbdm_sioi'] = self.get_lbdm_rioi()
        features['lbdm_rrest'], features['lbdm_srest'] = self.get_lbdm_rrest()
        features['lbdm_boundarystrength'] = self.get_lbdm_local_boundarystrength(features['lbdm_spitch'], features['lbdm_sioi'], features['lbdm_srest'])

        return features

    def get_lbdm_rpitch(self, threshold=12, const_add=1):
        """Get lbdm_rpitch and boundary strength features"""
        thr_int = [min(threshold, abs(i)) for i in self.base_features['chromaticinterval'][1:]] + [None]
        rpitch = [None] + [get_one_degree_change(x1, x2, const_add=const_add) for x1, x2 in zip(thr_int[:-1],thr_int[1:-1])] + [None]
        return rpitch, get_boundary_strength(rpitch, thr_int)

    def get_lbdm_rioi(self, threshold=4.0):
        """Get lbdm_ioi and boundary strength features"""
        thr_ioi = [min(threshold, i) for i in self.base_features['ioi'][:-1]] + [None]
        rioi = [None] + [get_one_degree_change(x1, x2) for x1, x2 in zip(thr_ioi[:-1], thr_ioi[1:-1])] + [None]
        return rioi, get_boundary_strength(rioi, thr_ioi)

    def get_lbdm_rrest(self, threshold=4.0):
        """Get lbdm_rest and boundary strength features"""
        thr_rest = [min(threshold, float(Fraction(r))) if r is not None else 0.0 for r in self.base_features['restduration_frac'][:-1]] + [None]
        rrest = [None] + [get_one_degree_change(x1, x2) for x1, x2 in zip(thr_rest[:-1], thr_rest[1:-1])] + [None]
        return rrest, get_boundary_strength(rrest, thr_rest)

    def get_lbdm_local_boundarystrength(self, spitch, sioi, srest):
        """Get Local Boundary Strength"""
        return [None] + [.25*s1 + .5*s2 + .25*s3 for s1, s2, s3 in zip(spitch[1:-2], sioi[1:-2], srest[1:-2])] + [None, None]

