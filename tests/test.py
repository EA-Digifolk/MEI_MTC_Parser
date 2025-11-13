import sys
if not 'MEI_MTC_Parser' in sys.path:
  sys.path.append('.')

#import pandas as pd
from mei_mtc_parser import MeiParser

song = 'tests/MX-1951-00-VM-00001.mei'
mei_parser = MeiParser()
song_features = mei_parser.parse_mei(song, verbose=False)

print(song_features['v1'].keys())
print(song_features['v1']['ngram'])
print(song_features['v1']['bigram'])
print(song_features['v1']['textual_topics'])