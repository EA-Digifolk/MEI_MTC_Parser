# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 18:12:36 2023

@author: Nádia Carvalho
"""
import copy
import functools
import math
from fractions import Fraction

import numpy as np
from imapy_music import IMA

from ..utils import NoMeterError, has_meter, sign_thresh, signs


class MetricExtractor():

    def __init__(self, stream):
        """
        Initialize MetricExtractor
        """
        self.music_stream = stream

    def get_all_features(self):

        offsets = self.get_offsets()

        features = {
            'offsets': [str(off) for off in offsets],
            'duration': self.get_durations(),
            'duration_frac': self.get_duration_fraction(),
            'duration_fullname': self.get_duration_fullname(),
            'nextisrest': self.get_next_is_rest(),
            'restduration_frac': self.get_rest_duration_fraction(),
        }

        features['onsettick'] = self.get_onsetticks(offsets)
        features['durationcontour'] = self.get_contour(features['duration'])
        features['songpos'] = self.get_song_position(features['onsettick'])
        features['ima'] = self.get_IMA(features['onsettick'])
        features['ima_contour'] = self.get_IMA_contour(features['ima'])

        try:
            features['timesignature'] = self.get_time_signature()
            features['beat'] = self.get_beat_float()
            features['beat_str'], features['beat_fraction_str'] = self.get_beat_string_fraction()
            features['beatstrength'] = self.get_beat_strength()
            features['metriccontour'] = self.get_metric_contour(
                features['beatstrength'])
        except NoMeterError:
            features['timesignature'] = [None] * \
                len(self.music_stream.recurse().notes)
            features['beat'] = [None]*len(self.music_stream.recurse().notes)
            features['beat_str'] = [None] * \
                len(self.music_stream.recurse().notes)
            features['beat_fraction_str'] = [None] * \
                len(self.music_stream.recurse().notes)
            features['beatstrength'] = [None] * \
                len(self.music_stream.recurse().notes)
            features['metriccontour'] = [None] * \
                len(self.music_stream.recurse().notes)

        return features

    def get_time_signature(self):
        """
        Get the time signature of the stream
        """
        if not has_meter(self.music_stream):
            raise NoMeterError('No meter found in stream')
        return [n.getContextByClass('TimeSignature').ratioString for n in self.music_stream.recurse().notes]

    def get_durations(self):
        """
        Get the durations of all notes in the stream
        """
        return [str(note.duration.quarterLength) for note in self.music_stream.flatten().notes]

    def get_duration_fraction(self):
        """
        Get the duration fraction of all notes in the stream
        """
        return [str(Fraction(note.duration.quarterLength)) for note in self.music_stream.flatten().notes]

    def get_duration_fullname(self):
        """
        Get the duration fullname of all notes in the stream
        """
        return [note.duration.fullName for note in self.music_stream.flatten().notes]

    def get_offsets(self):
        """
        Get the offsets of all notes in the stream
        """
        return [note.offset for note in self.music_stream.flatten().notes]

    def get_rest_duration_fraction(self):
        """
        Get the duration fraction of all rests in the stream
        """

        notes_and_rests = list(self.music_stream.recurse().notesAndRests)

        cum_rest_duration = Fraction(0)
        rest_durations = []

        # this computes length of rests PRECEEDING the note
        for event in notes_and_rests:

            if event.isRest:
                cum_rest_duration += Fraction(event.duration.quarterLength)
            elif event.isNote or event.isChord:
                if cum_rest_duration == 0:
                    rest_durations.append(None)
                else:
                    rest_durations.append(str(cum_rest_duration))
                cum_rest_duration = Fraction(0)

        # shift list and add last
        if notes_and_rests[-1].isNote or notes_and_rests[-1].isChord:
            return rest_durations[1:] + [None]
        return rest_durations[1:] + [str(cum_rest_duration)]

    def get_position_in_song(self, onsets):
        """
        Get the position of all notes in the stream
        """
        onsets = np.array(onsets)
        return list(onsets / onsets[-1])

    def get_beat_float(self):
        """Get the beat of all notes in the stream"""
        return [float(note.beat) for note in self.music_stream.recurse().notes]

    def get_beat_strength(self):
        """Get the beat strength of all notes in the stream"""
        def get_note_accent(note):
            return note.getContextByClass('TimeSignature').getAccentWeight(note.offset, permitMeterModulus=True, forcePositionMatch=True)
        return [get_note_accent(note) for note in self.music_stream.flatten().notes]

    def get_beat_string_fraction(self):
        """Get the beat string and fraction of all notes in the stream"""

        def beat_str_to_tuple(beat_str):
            """Convert a beat string to a tuple"""
            split = beat_str.split(' ')
            return split[0], split[1] if len(split) > 1 else '0'

        tuple_beat_str = [beat_str_to_tuple(
            note.beatStr) for note in self.music_stream.recurse().notes]
        return [tps[0] for tps in tuple_beat_str], [tps[1] for tps in tuple_beat_str]

    def get_metric_contour(self, beat_strengths, thresh=0):
        """Get the metric contour of all notes in the stream"""
        return [None] + [signs[sign_thresh(d2-d1, thresh=thresh)] for d1, d2 in zip(beat_strengths, beat_strengths[1:])]

    def get_contour(self, values, thresh=0):
        """
        Get the contour of a list of values
        """
        return [None] + [signs[sign_thresh(Fraction(d2)-Fraction(d1), thresh=thresh)] for d1, d2 in zip(values, values[1:])]

    def get_next_is_rest(self):
        """
        Get the next note is rest
        """
        notes_and_rests = list(self.music_stream.recurse().notesAndRests)
        next_is_rest = [next_note.isRest for note, next_note in zip(
            notes_and_rests, notes_and_rests[1:]) if (note.isNote or note.isChord)]
        if notes_and_rests[-1].isNote or notes_and_rests[-1].isChord:
            next_is_rest.append(None)
        return next_is_rest

    def get_onsetticks(self, offsets):
        """
        Get the onset ticks of all notes in the stream
        """
        def gcd_reduction(fraction_offsets):
            """Get gcd reduction of fraction offsets"""
            num_dur = functools.reduce(
                math.gcd, [f.numerator for f in fraction_offsets])
            den_dur = functools.reduce(
                math.lcm, [f.denominator for f in fraction_offsets])
            return Fraction(num_dur, den_dur)

        gcd = gcd_reduction([Fraction(offset) for offset in offsets])
        return [int(offset//gcd) for offset in offsets]

    def get_song_position(self, onsetticks):
        """Get the song position of all notes in the stream"""
        return [float(onsettick)/onsetticks[-1] for onsettick in onsetticks]

    def get_IMA(self, onsetticks):
        """
        Get the IMA of all notes in the stream
        """
        ima_calculator = IMA(onsets=onsetticks)
        return ima_calculator.calculate_IMA_score()

    def get_IMA_contour(self, ima):
        """
        Get the IMA contour of all notes in the stream
        """
        return [None] + [signs[sign_thresh(d2-d1)] for d1, d2 in zip(ima, ima[1:])]
