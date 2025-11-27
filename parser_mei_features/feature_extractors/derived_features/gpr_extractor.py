# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 16:55:47 2023

@author: Nádia Carvalho
"""

from fractions import Fraction

class GPRExtractor:

    def __init__(self, stream, features) -> None:
        """Initialize GPRExtractor"""
        self.music_stream = stream
        self.base_features = features

    def get_all_features(self):
        """Get all features phrase related features from the stream"""

        features = {
            'gpr2a_Frankland': self.get_gpr_2a(),
            'gpr2b_Frankland': self.get_gpr_2b(),
            'gpr3a_Frankland': self.get_gpr_3a(),
            'gpr3d_Frankland': self.get_gpr_3d(),
        }
        features['gpr_Frankland_sum'] = self.get_gpr_Frankland_sum(features) # type: ignore
        return features

    def get_gpr_2a(self):
        """Get gpr2a_Frankland"""
        return [min(1.0, float(Fraction(r) / 4.0)) if r is not None else None for r in self.base_features['restduration_frac']]

    def get_gpr_2b(self):
        """Get gpr2b_Frankland"""
        durations = [Fraction(f) for f in self.base_features['duration']]
        restduration_frac = self.base_features['restduration_frac']

        def get_one_Frankland_GPR2b(quad):
            n1, n2, n3, _ = quad
            return (1.0 - (float(n1+n3)/float(2.0*n2))) if (n2>n3) > 0 and (n2>n1) else None

        quads = zip(durations, durations[1:], durations[2:], durations[3:])

        frankland_one =  [None] + [get_one_Frankland_GPR2b(quad) for quad in quads] + [None, None]

        #check conditions (Frankland 2004, p.505): no rests in between, n2>n1 and n2>n3 (in getOneFranklandGPR2b())
        #rest_maks: positions with False result in None in res
        rest_present = [Fraction(r)>Fraction(0) if r is not None else False for r in restduration_frac]
        rest_mask = [False] + [not any(x for x in  t_r_p) for t_r_p in zip(rest_present, rest_present[1:], rest_present[2:])] + [False]

        #now set all values in res to None if False in mask
        return [res_ix if (ix < len(rest_mask) and rest_mask[ix]) else None for ix, res_ix in enumerate(frankland_one)]

    def get_gpr_3a(self):
        """Get gpr3a_Frankland, Frankland and Cohen 2004, p. 505"""

        def get_one_Frankland_GPR3a(quad):
            # The rule applies only if the transition from
            # n2 to n3 is greater than from n1 to n2 and from n3 to n4.
            # In addition, the transition from n2 to n3 must be nonzero
            n1, n2, n3, n4 = quad
            if n2 != n3 and abs(n2-n3) > abs(n1-n2) and abs(n2-n3) > abs(n3-n4):
                return 1.0 - (float(abs(n1-n2)+abs(n3-n4))/float(2.0 * abs(n2-n3)))
            return None

        midipitches = self.base_features['midipitch']
        return  [None] + [get_one_Frankland_GPR3a(quad) for quad in zip(midipitches, midipitches[1:], midipitches[2:], midipitches[3:])] + [None, None]

    def get_gpr_3d(self):
        """Get gpr3d_Frankland, Frankland and Cohen 2004, p. 505"""

        def get_one_Frankland_GPR3d(quad):
            # The rule applies only if the transition from
            # n2 to n3 is greater than from n1 to n2 and from n3 to n4.
            # In addition, the transition from n2 to n3 must be nonzero
            n1, n2, n3, n4 = quad
            if n1 != n2 or n3 != n4:
                return None
            if n3 > n1:
                return 1.0 - (float(n1)-float(n3))
            return 1.0 - (float(n3)-float(n1))

        ioi = self.base_features['ioi']
        return  [None] + [get_one_Frankland_GPR3d(quad) for quad in zip(ioi, ioi[1:], ioi[2:], ioi[3:])] + [None, None]

    def get_gpr_Frankland_sum(self, features):
        """Get gpr_Frankland_sum"""
        return [sum(filter(None, x)) for x in zip(features['gpr2a_Frankland'], features['gpr2b_Frankland'], features['gpr3a_Frankland'], features['gpr3d_Frankland'])]
