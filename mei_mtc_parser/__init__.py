# -*- coding: utf-8 -*-
"""
Created on Mon Feb 13 14:07:00 2023

@author: Nádia Carvalho
"""

from collections import defaultdict
from xml.etree import ElementTree as ET

import numpy as np

from .mtc_extractor import MTCExtractor
from .utils import isDigit

NAME_SPACE = {'mei': 'http://www.music-encoding.org/ns/mei'}
ID_SPACE = '{http://www.w3.org/XML/1998/namespace}id'

MEILINKS = {

    'metadata': {

        'title_stmt': {
            'id': './/mei:titleStmt/mei:title[@type="main"]',
            'title': './/mei:titleStmt/mei:title[@type="main"]',
            'subtitle': './/mei:titleStmt/mei:title[@type="subtitle"]',
            'compiler': './/mei:titleStmt/mei:respStmt/mei:persName[@role="compiler"]',
            'informer': './/mei:titleStmt/mei:respStmt/mei:persName[@role="informer"]',
            'geographic': './/mei:titleStmt/mei:respStmt/mei:persName[@role="informer"]/mei:geogName',
            'encoder': './/mei:titleStmt/mei:respStmt/mei:persName[@role="encoder"]',
            'editor': './/mei:titleStmt/mei:respStmt/mei:persName[@role="editor"]',
        },

        'source_desc': {
            'id': './/mei:sourceDesc/mei:source',
            'title': './/mei:sourceDesc//mei:title',
            'subtitle': './/mei:sourceDesc//mei:title[@type="subordinate"]',
            'compiler': './/mei:sourceDesc//mei:persName[@role="compiler"]',
            'informer': './/mei:sourceDesc//mei:persName[@role="informer"]',
            'bibliography': './/mei:sourceDesc//mei:persName[@role="bibliography"]',
            'introduction': './/mei:sourceDesc//mei:persName[@role="introduction"]',
            'edition': './/mei:sourceDesc//mei:persName[@role="edition"]',
            'publisher': './/mei:sourceDesc//mei:publisher',
            'publication_place': './/mei:sourceDesc//mei:pubPlace',
            'date': './/mei:sourceDesc//mei:date',
            'pages': './/mei:sourceDesc//mei:extent[@type="pages"]',
        },
    },

    'work': {
        'title': './/mei:work//mei:title[@type="main"]',
        'author': './/mei:work//mei:author',
        'lyrics': './/mei:work//mei:lyrics//mei:incipText',
        'key': './/mei:work//mei:key',
        'meter': './/mei:work//mei:meter',
        'tempo': './/mei:work//mei:tempo',
        'sections': './/mei:work//mei:section//mei:measure',
        'language': './/mei:work//mei:language',
        'performance_notes': './/mei:work//mei:notesStmt//mei:annot',

        'genre': './/mei:work//mei:term[@type="genre"]',
        'region': './/mei:work//mei:term[@type="region"]',
        'district': './/mei:work//mei:term[@type="district"]',
        'city': './/mei:work//mei:term[@type="city"]',
        'country': './/mei:workList//mei:term[@type="country"]',

        'clean_lyrics': './/mei:workList//mei:term[@type="clean-lyrics"]',
        'ngram': './/mei:workList//mei:term[@type="ngram"]',
        'bigram': './/mei:workList//mei:term[@type="bigram"]',
        'textual_topics': './/mei:workList//mei:term[@type="textual-topics"]',
    },

    'music': {
        'ambitus': './/mei:scoreDef//mei:ambitus//mei:ambNote',
        'pitch_pattern': './/mei:supplied[@type="pitch pattern"]',
        'interval_pattern': './/mei:supplied[@type="interval pattern"]',
        'rhythm_pattern': './/mei:supplied[@type="rhythm pattern"]',
        'phrases': './/mei:supplied[@type="phrases"]//mei:phrase',
        #'cadences': './/mei:note[@type]',
    }
}


class MeiParser:
    """
    MEI PARSER, parse MEI files relative to CoPOEM database's structure
    """

    def parse_mei(self, path, verbose=True):
        """
        Parses a MEI file and returns a list of dictionaries with the following
        information:
        - metadata
        - features
        """
        tree = ET.parse(path)
        root = tree.getroot()

        metadata = self.get_metadata(root)
        work = self.get_work_info(root)
        music = self.get_music_info(root)

        music_metadata = music
        for key in ['key', 'mode', 'meter', 'tempo', 'genre', 'ngram', 'bigram', 'textual_topics']:
            music_metadata[key] = work[key]

        if verbose:
            print(f'Parsing {metadata["title_stmt"]["id"]}')

        self.mtc_extractor = MTCExtractor(path, root, music_metadata)
        features = self.mtc_extractor.process_stream()
        if features:
            if isinstance(features, dict):
                return self.get_whole_dict(metadata, music_metadata, features)

            voice_features = {}
            for i, feature_voice in enumerate(features):
                voice_features[f'v{i+1}'] = self.get_whole_dict(metadata, music_metadata, feature_voice)
            return voice_features

        return None

    def get_whole_dict(self, metadata, music_metadata, features):
        music_dict = defaultdict(list)

        for cat, value in metadata.items():
            for key in value:
                if cat == 'source_desc' and key in music_dict:
                    music_dict[f'source_{key}'] = value[key]
                elif cat == 'title_stmt' and key in music_dict:
                    music_dict[f'title_{key}'] = value[key]
                else:
                    music_dict[key] = value[key]
        music_dict.update(music_metadata)

        music_dict['has_lyrics?'] = self.mtc_extractor.has_lyrics() # type: ignore
        music_dict['has_freemeter?'] = not self.mtc_extractor.has_meter() # type: ignore

        music_dict.update({'features': features}) # type: ignore

        return music_dict

    def get_metadata(self, root):
        """
        Returns a dictionary with the following information:
        - title
        - composer
        - date
        - source
        - license
        """
        return {
            'title_stmt': self.get_dict(root, extraction_dict=MEILINKS['metadata']['title_stmt']),
            'source_desc': self.get_dict(root, extraction_dict=MEILINKS['metadata']['source_desc']),
        }

    def get_work_info(self, root):
        """
        Returns a dictionary with the following information:
        - title
        - author
        - lyrics
        - key + mode
        - meter
        - tempo
        - sections
        - language
        - complete_lyrics
        - genre
        - region
        - district
        - city
        - textual topics
        """
        return self.get_dict(root, extraction_dict=MEILINKS['work'])

    def get_music_info(self, root):
        """
        Returns a dictionary with the following information:
        - ambitus
        - pitch_pattern
        - interval_pattern
        - rhythm_pattern
        - phrases
        """
        return self.get_dict(root, extraction_dict=MEILINKS['music'])

    def get_dict(self, root, extraction_dict=MEILINKS['metadata']['title_stmt']):
        """
        Gets the elements of a dictionary
        """
        output_dict = {}
        for element in extraction_dict:
            if element == 'id':
                output_dict[element] = self.get_element(
                    root, extraction_dict[element], ID_SPACE)
            elif element == 'sections':
                output_dict[element] = self.get_multiple_elements(
                    root, extraction_dict[element], 'copyof')
            elif element == 'ambitus':
                self.extract_ambitus_note(
                    root, extraction_dict, output_dict, element, 'lowest')
                self.extract_ambitus_note(
                    root, extraction_dict, output_dict, element, 'highest')
            elif element == 'pitch_pattern':
                output_dict[element] = self.extract_patterns(root, extraction_dict, element)
            elif element == 'interval_pattern':
                output_dict[element] = self.extract_patterns(root, extraction_dict, element)
            elif element == 'rhythm_pattern':
                output_dict[element] = self.extract_patterns(root, extraction_dict, element)
            elif element == 'phrases':
                output_dict[element] = self.extract_phrases(
                    root, extraction_dict, element)
            else:
                output_dict[element] = self.get_element(
                    root, extraction_dict[element])

            if element == 'key':
                output_dict['mode'] = self.get_element(
                    root, extraction_dict[element], 'mode')
            if element == 'textual_topics' and isinstance(output_dict[element], str):
                output_dict[element] = output_dict[element].split('; ')
        return output_dict

    def extract_patterns(self, root, extraction_dict, element):
        """
        Extracts the
        """
        try:
            histogram_dict = self.get_histogram(root, extraction_dict[element])
            hist = [(int(key.replace('pc_','').replace('intm_','').replace('bin_','')), float(val)) for key, val in histogram_dict.items() if any(x in key for x in ['pc_', 'intm_', 'bin_'])]

            ret_dict = {key:val for key, val in histogram_dict.items() if not any(x in key for x in ['pc_', 'intm_', 'bin_'])}
            ret_dict['histogram'] = [x[1] for x in sorted(hist)]
            return ret_dict
        except:
            return None

    def extract_phrases(self, root, extraction_dict, element):
        """
        Extracts the phrases from the MEI file
        """
        phrases_info = self.get_multiple_elements(
            root, extraction_dict[element], 'n')

        if not phrases_info:
            return None

        phrases = []
        for phr in phrases_info:
            phrase_start = self.get_element(
                root, extraction_dict[element] + f'[@n="{phr}"]', 'startid')
            phrase_end = self.get_element(
                root, extraction_dict[element] + f'[@n="{phr}"]', 'endid')
            phrase_type = self.get_element(
                root, extraction_dict[element] + f'[@n="{phr}"]', 'type')
            phrases.append(
                f'({phr}, {phrase_start}, {phrase_end}, {phrase_type})')
        return '; '.join(phrases)

    def extract_ambitus_note(self, root, extraction_dict, output_dict, element, note='highest'):
        """
        Extracts the ambitus notes
        """
        output_dict[f'ambitus_{note}'] = self.get_element(
            root, extraction_dict[element] + f'[@type="{note}"]', 'pname')
        octave = self.get_element(
            root, extraction_dict[element] + f'[@type="{note}"]', 'oct')

        if isinstance(output_dict[f'ambitus_{note}'], str) and isinstance(octave, str):
            output_dict[f'ambitus_{note}'] += octave

    def get_element(self, root, xpath, retrieve='text'):
        """
        Returns the text of an element given its xpath.
        """
        element = root.find(xpath, NAME_SPACE)

        if element is not None:
            if retrieve == 'text':
                text = str(element.text)
                if isDigit(text):
                  if np.isnan(float(text)):
                    return 0
                  else:
                    return int(float(text))
                if text.isspace() or text == 'None':
                    return None
                return text
            else:
                return element.attrib[retrieve]
        else:
            return None

    def get_histogram(self, root, xpath):
        """
        Returns the text of an element given its xpath.
        """
        element = root.find(xpath + '//mei:histogram', NAME_SPACE)
        if element is not None:
            return element.attrib
        else:
            return None

    def get_multiple_elements(self, root, xpath, retrieve='text'):
        """
        Returns a list of elements given their xpath.
        """
        elements = root.findall(xpath, NAME_SPACE)

        if elements is not None:
            if retrieve == 'text':
                return [element.text for element in elements]
            else:
                return [element.attrib[retrieve] for element in elements]
        else:
            return None
