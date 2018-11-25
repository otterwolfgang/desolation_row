#!/usr/bin/env python3


# Import statements go here
from collections import Counter
from io import StringIO
from nltk.corpus import stopwords
import pandas as pd
from pathlib import Path
import re


#temp
from collect_lyrics_data import proj_dir

from nltk.collocations import BigramCollocationFinder


# Import df for temporary use
# Define the path to look for the pickled object
df_path = proj_dir.joinpath('data', 'df.pkl')

# Check wether the pickled object exists
try:
    df = pd.read_pickle(df_path)
except FileNotFoundError:
    read_data(lyr_path, df_path)
    df = pd.read_pickle(df_path)


# Temporary space for creating bigram counters
# print(df.head())
stop_words = set(stopwords.words('english'))

words = []
words_clean = []

for song in df['Lyrics']:
    words.extend([w for w in re.findall(r'\w+\'*\w*', song.lower())])
for song in df['Lyrics']:
    words_clean.extend([w for w in re.findall(r'\w+\'*\w*', song.lower()) if w not in stop_words])

# print(words)
# print(words_clean)

# Find bigrams in the whole corpus of words and without stopwords
bigrams = BigramCollocationFinder.from_words(words)
bigrams_clean = BigramCollocationFinder.from_words(words_clean)

# print(bigrams.ngram_fd.items())

# List bigrams by frequency without regarding association measures
popular = list(bigrams_clean.ngram_fd.items())
popular.sort(key=lambda item: item[-1], reverse=True)
print(popular)

# List bigrams by frequency after applying a ranking measures


# List the most commonly associated words to the most popular words by raw frequency


# List the most commonly associated words to the most popular words by after applying a ranking filter


# Function to draw the whole tab
def tab_word_usage(df, plot_width, plot_height):
    pass
