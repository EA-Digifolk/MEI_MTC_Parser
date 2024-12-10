from mei_mtc_parser import MeiParser
import music21 as m21

mei_parser = MeiParser()
song_feats = mei_parser.parse_mei('ES-1913-B-JSV-001.mei')

print(song_feats['v1']['features']['lyrics'])

print(m21.text.assembleLyrics(mei_parser.mtc_extractor.music_stream))