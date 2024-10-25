# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 15:45:52 2023

@author: Nádia Carvalho
"""

from collections import defaultdict
import copy

import converter21 as c21
import music21 as m21
import verovio

from .feature_extractors import (GPRExtractor, IOIExtractor, LBDMExtractor,
                                 MetricExtractor, PhraseExtractor,
                                 PitchExtractor)
from .utils import has_meter

from contextlib import redirect_stderr

#c21.mei.base.environLocal['warnings'] = 0
c21.shared.m21utilities.DEBUG = False
c21.shared.m21utilities.BEAMDEBUG = False
c21.shared.m21utilities.TUPLETDEBUG = False

env = m21.environment.Environment()
env['warnings'] = 0

class MTCExtractor():
    """
    """

    def __init__(self, path, mei_tree, musical_metadata=None):
        """
        Parse MEI file and extract features
        """
        self.tk = verovio.toolkit()
        self.tk.setOptions({"xmlIdChecksum": False, "xmlIdSeed": 0})
        self.tk.loadFile(path)
        # self.tk.renderToSVGFile('data/temp.svg')

        # m21.environment.Environment('converter21.mei.base')['warnings'] = 0 # type: ignore
        with open('stderr.txt', 'w') as f:
            with redirect_stderr(f):
                converter = c21.MEIConverter()
                self.music_stream = converter.parseFile(path, verbose=False)

        self.metadata = {}
        if musical_metadata:
            self.metadata = musical_metadata
              
        expressions = list(self.music_stream.recurse().getElementsByClass('Expression'))
        for exp in expressions:
          if exp.content == '𝄋':
            exp.content = 'Segno'
          if exp.content == '𝄌':
            exp.content = 'Coda'
          
          rep_exp = exp.getRepeatExpression()
          
          if rep_exp is not None:
            hierch = [e for e in exp.containerHierarchy()]
            hierch[0].insert(exp.offset, rep_exp)

        try:
            self.music_stream = self.music_stream.expandRepeats()
        except:
            for repeat_bracket in self.music_stream.recurse().getElementsByClass('RepeatBracket'):
                spanner_measures = repeat_bracket.getSpannedElements()

                if len(spanner_measures) > 0:
                    number_to_get = spanner_measures[0].number
                    ending = mei_tree.find(f'.//mei:measure[@n="{number_to_get}"]...', namespaces={
                                           'mei': 'http://www.music-encoding.org/ns/mei'})
                    if ending is not None:
                        if '-' in ending.attrib['n']:
                          st, end = ending.attrib['n'].split('-')
                          ending_markings = list(range(int(st), int(end)+1, 1))
                        else:
                          ending_markings = [
                              int(i) for i in ending.attrib['n'].split(',')]
                      
                        if len(ending_markings) == 1:
                            repeat_bracket.number = ending_markings[0]
                        elif list(range(ending_markings[0], ending_markings[-1])) == ending_markings:
                            repeat_bracket.number = f'{ending_markings[0]}-{ending_markings[-1]}'
                        else:
                            repeat_bracket.number = ', '.join(
                                [str(i) for i in ending_markings])

                        if isinstance(spanner_measures[-1].rightBarline, m21.bar.Repeat) and len(ending_markings) > 1:
                            spanner_measures[-1].rightBarline.times = len(
                                ending_markings)

            try:
                self.music_stream = self.music_stream.expandRepeats()
            except Exception as e:
                print('Error expanding repeats in: ' + path)
                print(e)
                return None


    def process_stream(self):
        """
        Process Music21 stream to extract JSON data
        """
        chords = self.music_stream.recurse().getElementsByClass(m21.chord.Chord)  # type: ignore
        if len(chords) > 0:
            voices_to_create = max(len(chord.pitches) for chord in chords)
            for measure in self.music_stream.recurse().getElementsByClass(m21.stream.Measure): # type: ignore
                if len(measure.voices) != voices_to_create:
                    new_voice = copy.deepcopy(measure.voices[-1])
                    new_voice.id = len(measure.voices) + 1
                    measure.insert(0, new_voice) # type: ignore
                for voice in measure.voices:
                    for chord in voice.recurse().getElementsByClass(m21.chord.Chord): # type: ignore
                        if len(chord.pitches) > 1:
                            p = chord.pitches[int(voice.id)-1]
                            new_chord = m21.note.Note(p, duration=chord.duration) # type: ignore
                            new_chord.id = chord.notes[0].id
                            voice.replace(chord, new_chord) # type: ignore

        self.music_stream = self.music_stream.voicesToParts(separateById=True)
        return [self.process_inside_stream(part) for part in self.music_stream.parts]

    def process_inside_stream(self, part=None):
        """
        Process Music21 stream to extract JSON data
        """
        if part is None:
            part = self.music_stream

        try:
            measure = part.recurse().getElementsByClass(m21.stream.Measure)[0]  # type: ignore
            if measure.barDurationProportion() < 1:
                duration_to_shift = measure.barDuration.quarterLength * (1 - measure.barDurationProportion())
                part.shiftElements(duration_to_shift)
        except:
            print('Error getting measure 0')

        features = defaultdict(list)

        features.update({'id': [n.id for n in part.flatten().notes]})

        # Scale/Key Features
        features.update(PitchExtractor(part,
                        self.metadata).get_all_features())

        # Metric Features
        features.update(MetricExtractor(
            part).get_all_features())

        try:
          # Phrasic Features
          features.update(PhraseExtractor(part,
                          self.metadata, features).get_all_features())
        except:
          print('Error getting phrase information')

        # Derived Features
        features.update(IOIExtractor(part,
                        features).get_all_features())
        features.update(GPRExtractor(part,
                        features).get_all_features())
        features.update(LBDMExtractor(
            part, features).get_all_features())

        return features

    def has_meter(self):
        """
        Check if stream has meter
        """
        return has_meter(self.music_stream)

    def has_lyrics(self):
        """
        Check if stream has lyrics
        """
        text = m21.text.assembleLyrics(self.music_stream)
        return 'Vocal' if text is not None else 'Instrumental'
