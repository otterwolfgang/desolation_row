#!/usr/bin/env python3


# Import statements go here
from collections import Counter, defaultdict
from io import StringIO
from nltk.corpus import stopwords
import pandas as pd
from pathlib import Path
import re


#temp
from collect_lyrics_data import proj_dir, lyr_path
from read_data import read_data

from nltk import pos_tag
from nltk.collocations import BigramAssocMeasures, BigramCollocationFinder


# Import df for temporary use
# Define the path to look for the pickled object
df_path = proj_dir.joinpath('data', 'df.pkl')

# Check wether the pickled object exists
try:
    df = pd.read_pickle(df_path)
except FileNotFoundError:
    read_data(lyr_path, df_path)
    df = pd.read_pickle(df_path)


# Tokenize lyrics and return a list of tokens stripped of stopwords
def tokenize(df, lang='english'):
    # Import stop words from nltk corpus
    stop_words = set(stopwords.words(lang))

    words = []
    for song in df['Lyrics']:
        words.extend([w for w in re.findall(r'\w+\'*\w*', song.lower()) if w not in stop_words])

    return words

# Filter for bigrams to only show words with accepted POS tags
def filter_bigrams(bigram):
    # Use adjectives and nouns for the first position
    start_tag = ('JJ', 'JJR', 'JJS', 'NN', 'NNS', 'NNP', 'NNPS')
    # Use only nouns for the second position
    follow_tag = ('NN', 'NNS', 'NNP', 'NNPS')

    tags = pos_tag(bigram)

    if tags[0][1] in start_tag and tags[1][1] in follow_tag:
        return True
    else:
        return False

def score_bigrams(bigrams, method):
    # Apply association measures to rank bigrams based on the selected method
    measures = BigramAssocMeasures()

    if method == 'PMI':
        scored = bigrams.score_ngrams(measures.pmi)
    elif method == 't':
        scored = bigrams.score_ngrams(measures.student_t)
    else:
        # List bigrams by frequency without regarding association measures
        scored = bigrams.ngram_fd.items()

    return scored

# Create a DataFrame with the most frequent bigrams based on the selected method
def find_bigrams(words, filter=1, method='frequency', pos_filter=False):

    # Create the frequency dictionary of bigrams for the whole list of tokens
    bigrams = BigramCollocationFinder.from_words(words)

    # Apply a frequency filter to filter out bigrams with very low frequency
    # that would distort the applied association methods
    bigrams.apply_freq_filter(filter)

    # Apply the selected bigram association scoring
    scored = score_bigrams(bigrams, method)

    df = (pd.DataFrame(list(scored), columns=['bigram', method]).
        sort_values(by=method, ascending=False))

    # Filter out bigrams that do not have the accepted combination of POS tags
    if pos_filter:
        df = df[df['bigram'].map(lambda x: filter_bigrams(x))]

    return df

# List the most commonly associated words to every token
def word_links(words, filter=1, method='frequency'):

    # Create the frequency dictionary of bigrams for the whole list of tokens
    bigrams = BigramCollocationFinder.from_words(words)

    # Apply a frequency filter to filter out bigrams with very low frequency
    # that would distort the applied association methods
    bigrams.apply_freq_filter(filter)

    # Apply the selected bigram association scoring
    scored = score_bigrams(bigrams, method)

    # Group bigrams by first word in bigram
    word_list = defaultdict(list)
    for key, scores in scored:
        word_list[key[0]].append((key[1], scores))

    # Sort keyed bigrams by strongest association
    for key in word_list:
        word_list[key].sort(key=lambda x: -x[1])

    return word_list

# temp functions for testing
bigrams = find_bigrams(tokenize(df, 'english'), 10, 't', pos_filter=True)
print(bigrams.head())

word_list = word_links(tokenize(df), 5, method='PMI')
print('love', word_list['love'][:5])


# Function to draw the whole tab
def tab_word_usage(df, plot_width, plot_height):
    pass
