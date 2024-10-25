# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 16:55:47 2023

@author: Nádia Carvalho
"""

from fractions import Fraction


class IOIExtractor:

    def __init__(self, stream, features) -> None:
        """Initialize IOIExtractor"""
        self.music_stream = stream
        self.base_features = features

    def get_all_features(self):
        """Get all lbdm features from the stream"""

        ioi_frac = self.get_ioi_frac()

        features = {
            'ioi_frac': ioi_frac,
            'ioi': self.get_ioi(ioi_frac),
            'ior_frac': self.get_ior_frac(ioi_frac)
        }
        features['ior'] = self.get_ior(features['ior_frac'])

        return features

    def get_ioi_frac(self):
        """Get the IOI fraction of the stream"""
        duration_frac = self.base_features['duration_frac']
        restduration_frac = self.base_features['restduration_frac']

        ioi_fracs = [str(Fraction(d)+Fraction(r)) if r is not None else str(Fraction(d))
                     for d, r, in zip(duration_frac[:-1], restduration_frac[:-1])]

        end = None
        if restduration_frac[-1] is not None:
            end = str(Fraction(duration_frac[-1]) +
                      Fraction(restduration_frac[-1]))

        return ioi_fracs + [end]

    def get_ioi(self, ioi_frac):
        """Get the IOI of the stream"""
        return [float(Fraction(i)) if i is not None else None for i in ioi_frac]

    def get_ior_frac(self, ioi_frac):
        """Get the IOR fraction of the stream"""
        return [None] + [str(Fraction(ioi2)/Fraction(ioi1)) if all(i not in [None, '0'] for i in [ioi1, ioi2]) else None for ioi1, ioi2 in zip(ioi_frac, ioi_frac[1:])]

    def get_ior(self, ior_frac):
        """Get the IOR of the stream"""
        return [float(Fraction(i)) if i is not None else None for i in ior_frac]
