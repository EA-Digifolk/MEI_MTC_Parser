# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 17:02:10 2023

@author: Nádia Carvalho
"""

import music21 as m21

from ..utils import sign_thresh, signs


def pitch_degree(pitch):
    """
    Get the pitch degree of a note from tuple (degree, accident)
    """
    (degree, accident) = pitch

    if accident is None:
        return degree
    return f"{degree}{accident.modifier}"


def getOnePitchReversal(implicative, realized):
    """
    Expectancy of the realized note modelled with pitch reversal (Schellenberg, 1997)
    """
    if abs(implicative) == 6 or abs(implicative) > 11 or abs(realized) > 12:
        return None

    if abs(implicative) < 6:
        pitchrev_dir = 0
    elif 6 < abs(implicative) < 12:
        pitchrev_dir = 1 if realized * implicative <= 0 else -1
    else:
        return None

    pitchrev_ret = 1.5 if ((abs(realized) > 0) and (
        realized*implicative < 0) and (abs(implicative+realized) <= 2)) else 0
    return pitchrev_dir + pitchrev_ret


class PitchExtractor():

    def __init__(self, stream, musical_metadata=None):
        """
        Initialize PitchExtractor
        """
        self.music_stream = stream

        self.metadata = {}
        if musical_metadata:
            self.metadata = musical_metadata

        self.scale = self.get_scale()

    def get_all_features(self):
        """Get all features pitch related features from the stream"""

        tonic, mode = self.get_tonic_and_mode()

        features = {
            'scaledegree': self.get_m21_scale_degrees(),
            'scaledegreespecifier': self.get_m21_scale_degree_specifiers(),
            'tonic': tonic,
            'mode': mode,
            'pitch': self.get_m21_pitch_names(),
            'midipitch': self.get_midi_pitch(),
            'pitch40': self.get_base40_pitch(),
            'diatonicpitch': self.get_m21_diatonic_pitches(),
            'chromaticinterval': self.get_chromatic_intervals(),
            'diatonicinterval': self.get_diatonic_intervals(),
        }

        features['pitchproximity'] = self.get_pitch_proximity(
            features['chromaticinterval'])
        features['pitchreversal'] = self.get_pitch_reversal(
            features['chromaticinterval'])
        features['contour3'] = self.get_contour_level(
            features['chromaticinterval'], thresh=0)
        features['contour5'] = self.get_contour_level(
            features['chromaticinterval'], thresh=3)

        return features

    def get_scale(self):
        """
        Get the scale of the piece
        """
        key = self.metadata.get('key')
        mode = self.metadata.get('mode')

        try:
          key = key.replace(' Flat', '-').replace(' Sharp', '#')

          if mode in list(m21.key.modeSharpsAlter.keys()):
            return m21.key.Key(tonic=key, mode=mode)
          else:
            if mode.startswith('aeolian'):
              return m21.key.Key(tonic=key, mode='aeolian')
            if mode.startswith('phrygian'):
              return m21.key.Key(tonic=key, mode='phrygian')       

            print(f"Can't yet process {key} {mode}")       
            return m21.key.Key(tonic=key, mode='major')
        except:
          try:
            return self.music_stream.analyze('key')
          except:
            return m21.key.Key(tonic='c', mode='major')        

    def get_m21_scale_degrees(self):
        """
        Get the scale degree of a note
        """
        return [pitch_degree(self.scale.getScaleDegreeAndAccidentalFromPitch(pitch)) for pitch in self.music_stream.flatten().pitches]

    def get_m21_scale_degree_specifiers(self):
        """
        Get the scale degree specifier of a note
        Specifier of the scaledegree: Perfect, Major, Minor, Augmented, Diminished, … above the tonic
        """
        intervals = [m21.interval.Interval(
            noteStart=self.scale.tonic, noteEnd=pitch).specifier for pitch in self.music_stream.flatten().pitches]

        return [m21.interval.prefixSpecs[interval] for interval in intervals] # type: ignore

    def get_tonic_and_mode(self):
        """
        Get the tonic of the piece
        """
        return [self.scale.tonic.name for _ in self.music_stream.flatten().pitches], [self.scale.mode.capitalize() for _ in self.music_stream.flatten().pitches]

    def get_m21_pitch_names(self):
        """
        Get the pitch name and octave of a note
        """
        return [pitch.nameWithOctave for pitch in self.music_stream.flatten().pitches]

    def get_midi_pitch(self):
        """
        Get the MIDI pitch of a note
        """
        return [pitch.midi for pitch in self.music_stream.flatten().pitches]

    def get_base40_pitch(self):
        """
        Get the base40 pitch of a note
        """
        return [m21.musedata.base40.pitchToBase40(pitch.nameWithOctave) for pitch in self.music_stream.flatten().pitches]  # type: ignore

    def get_m21_diatonic_pitches(self):
        """
        Get the diatonic pitch of a note
        """
        return [pitch.diatonicNoteNum for pitch in self.music_stream.flatten().pitches]

    def get_m21_pitch_classes(self):
        """
        Get the pitch class of a note
        """
        return [pitch.pitchClass for pitch in self.music_stream.flatten().pitches]

    def get_chromatic_intervals(self):
        """
        Get the chromatic interval between two consecutive notes
        """
        pitches = self.music_stream.flatten().pitches
        return [None] + [pitch.midi - pitches[i-1].midi for i, pitch in enumerate(pitches) if i > 0]

    def get_diatonic_intervals(self):
        """
        Get the diatonic interval between two consecutive notes
        """
        pitches = self.music_stream.flatten().pitches
        return [None] + [pitch.diatonicNoteNum - pitches[i-1].diatonicNoteNum for i, pitch in enumerate(pitches) if i > 0]

    def get_pitch_proximity(self, chromatic_intervals):
        """
        Get the pitch proximity of a note
        """
        return [None, None] + [abs(c_i) if abs(c_i) < 12 else None for c_i in chromatic_intervals[2:]]

    def get_pitch_reversal(self, chromatic_intervals):
        """
        Get the pitch reversal of a note
        """
        return [None, None] + [getOnePitchReversal(chromatic_intervals[i+1], c_i) for i, c_i in enumerate(chromatic_intervals[2:])]

    def get_contour_level(self, chromatic_intervals, thresh=0):
        """
        Get the contour level of a note
        (level 3 <=> thresh=0)
        (level 5 <=> thresh>0)
        """
        if thresh == 0:
            return [None] + [signs[sign_thresh(c)] for c in chromatic_intervals[1:]]
        else:
            return [None] + [signs[sign_thresh(c, thresh)] for c in chromatic_intervals[1:]]
