#@title Phrase Extractor
# -*- coding: utf-8 -*-
"""
Created on Mon Feb 22 16:20:06 2023

@author: Nádia Carvalho
"""

from collections import defaultdict
from fractions import Fraction

import numpy as np


def get_start_beat(first_note):
    """Get the beat of the first note in the measure"""
    start_beat = Fraction(first_note.beat)
    if start_beat != Fraction(1):  # upbeat
        start_beat = Fraction(-1 * first_note.getContextByClass(
            'TimeSignature').beatCount) + start_beat
    start_beat -= Fraction(1)  # shift origin to first "first beat" in measure
    return start_beat


def get_beat_fraction(note):
    """Get the beat fraction of a note"""
    return Fraction(note.duration.quarterLength) / Fraction(note.beatDuration.quarterLength)


class PhraseExtractor():

    def __init__(self, stream, musical_metadata=None, features=None):
        """
        Initialize PhraseExtractor
        """
        self.music_stream = stream

        self.metadata = {}
        if musical_metadata:
            self.metadata = musical_metadata
        if features:
            self.features = features

    def get_all_features(self):
        """Get all features phrase related features from the stream"""
        phrases, phrase_ix = self.get_phrases()

        features = {
            'phrasepos': self.get_phrase_position(phrases),
            'phrase_ix': phrase_ix,
            'phrase_end': self.get_phrase_end(),
        }

        features['beatinsong'], features['beatinphrase'], features['beatfractioninphrase'] = self.get_beat_in_song_and_phrase(
            phrases)

        features['beatinphrase_end'] = self.get_beat_in_phrase_end(
            features['beatinphrase'], phrase_ix)

        return features

    def get_phrases(self):
        """Get phrase position for each note"""
        if 'phrases' not in self.metadata:
            phrase_pos = [1] + [0] * (len(self.music_stream.recurse().notes) - 2) + [-1]
            return phrase_pos, [0] * len(self.music_stream.recurse().notes)

        self.metadata_phrases = [tuple(phrase[1:-1].split(', '))
                                 for phrase in self.metadata['phrases'].split('; ') ]

        phrase_starts = [phrase[1] for phrase in self.metadata_phrases]
        phrase_ends = [phrase[2] for phrase in self.metadata_phrases]

        phrase_pos = np.zeros(
            len(self.music_stream.recurse().notes), dtype=int)
        phrase_ix = []

        last_phrase = -1
        for i, note in enumerate(self.music_stream.recurse().notes):

            if f"#{note.id}" in phrase_starts:
                phrase_pos[i] = 1
                last_phrase += 1
            elif f"#{note.id}" in phrase_ends:
                phrase_pos[i] = -1
                if phrase_pos[i-1] == -1:
                    phrase_pos[i-1] = 0

            phrase_ix.append(last_phrase)
        return list(phrase_pos), phrase_ix

    def get_phrase_position(self, phrases):
        """Get phrase position for each note"""

        total_duration = self.music_stream.duration.quarterLength

        if all(x == 0 for x in phrases):
            return [note.quarterLength/total_duration for note in self.music_stream.recurse().notes]

        start_indexes = [i for i, x in enumerate(phrases) if x == 1]
        end_indexes = [i for i, x in enumerate(phrases) if x == -1]

        if len(start_indexes) != len(end_indexes):
            raise ValueError(
                "Number of start indexes must be equal to number of end indexes")

        all_notes = self.music_stream.flatten().notes

        phrase_pos = np.zeros(len(phrases), dtype='float')

        def get_ph_position(all_notes, st, end):
          phrase_duration = all_notes[end].offset - all_notes[st].offset
          if phrase_duration == 0:
            return [0] * (end - st + 1)
          return [(note.offset - all_notes[st].offset) / phrase_duration
                                            for note in all_notes[st:end+1]]

        for st, end in zip(start_indexes, end_indexes):
            phrase_pos[st:end+1] = get_ph_position(all_notes, st, end)

        return phrase_pos.tolist()

    def get_phrase_end(self):
        """Get phrase position for each note"""
        if 'phrases' not in self.metadata:
            return [False] * (len(self.music_stream.recurse().notes) -1) + [True]

        phrase_ends = [phrase[2] for phrase in self.metadata_phrases]
        return [True if f"#{note.id}" in phrase_ends else False for note in self.music_stream.recurse().notes]

    def get_beat_in_song_and_phrase(self, phrases):
        """Get beat in phrase for each note"""
        notes = self.music_stream.recurse().notesAndRests
        start_phrases = [i for i, x in enumerate(phrases) if x == 1 and i != 0]

        start_beat = get_start_beat(notes[0])

        beatinsong, beatinphrase, beatfraction = [], [], []
        if notes[0].isNote or notes[0].isChord:
            beatinsong = [start_beat]
            beatinphrase = [start_beat]
            beatfraction = [get_beat_fraction(notes[0])]

        cumulative_beat_song = start_beat
        cumulative_beat_phrase = start_beat

        note_ix = 0
        for note, next_note in zip(notes, notes[1:]):
            cumulative_beat_song += get_beat_fraction(note)
            if note.isNote or note.isChord:
                if note_ix in start_phrases:
                    cumulative_beat_phrase = get_start_beat(note)
                    beatinphrase[-1] = cumulative_beat_phrase
                note_ix += 1
            cumulative_beat_phrase += get_beat_fraction(note)

            if next_note.isNote or next_note.isChord:
                beatinsong.append(cumulative_beat_song)
                beatinphrase.append(cumulative_beat_phrase)
                beatfraction.append(get_beat_fraction(next_note))

        return [str(f) for f in beatinsong], [str(f) for f in beatinphrase], [str(f) for f in beatfraction]

    def get_beat_in_phrase_end(self, beatinphrase, phrase_ix, epsilon=1e-4):
        """Get beat in phrase end for each note"""
        origin = defaultdict(lambda: 0.0)
        for ix, btp_ix in enumerate(beatinphrase):
            if abs(float(self.music_stream.recurse().notes[ix].beat) - 1.0) < epsilon:
                origin[phrase_ix[ix]] = Fraction(btp_ix)  # type: ignore

        beatinphrase_end = [Fraction(btp_ix) - Fraction(origin[phrase_ix[ix]])
                            for ix, btp_ix in enumerate(beatinphrase)]
        return [str(f) for f in beatinphrase_end]
