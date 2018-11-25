#!/usr/bin/env python3


# Import statements go here
from collections import Counter, defaultdict
from io import StringIO
from nltk.corpus import stopwords
import pandas as pd
from pathlib import Path
import re


#temp
from collect_lyrics_data import proj_dir

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
# print(popular)

df_bigrams_cl = (pd.DataFrame(list(bigrams_clean.ngram_fd.items()), columns=['bigram', 'frequency']).
    sort_values(by='frequency', ascending=False))

print(df_bigrams_cl.head())

# List bigrams by frequency after applying a ranking measures
assoc_measures = BigramAssocMeasures()

# bigrams.apply_freq_filter(10)
# bigrams_clean.apply_freq_filter(10)

df_pmi = pd.DataFrame(
    list(bigrams.score_ngrams(assoc_measures.pmi)),
    columns=['bigram', 'PMI']
).sort_values(by='PMI', ascending=False)

df_pmi_cl = pd.DataFrame(
    list(bigrams_clean.score_ngrams(assoc_measures.pmi)),
    columns=['bigram', 'PMI']
).sort_values(by='PMI', ascending=False)

print(df_pmi.head(10))
print(df_pmi_cl.head(10))

df_t = pd.DataFrame(
    list(bigrams.score_ngrams(assoc_measures.student_t)),
    columns=['bigram', 't']
).sort_values(by='t', ascending=False)

df_t_cl = pd.DataFrame(
    list(bigrams_clean.score_ngrams(assoc_measures.student_t)),
    columns=['bigram', 't']
).sort_values(by='t', ascending=False)

print(df_t.head(10))
print(df_t_cl.head(10))



# List the most commonly associated words to the most popular words by raw frequency
def word_links(freq_dict):
    # Group bigrams by first word in bigram.
    word_list = defaultdict(list)
    for key, scores in freq_dict.ngram_fd.items():
        word_list[key[0]].append((key[1], scores))

    # Sort keyed bigrams by strongest association.
    for key in word_list:
        word_list[key].sort(key = lambda x: -x[1])

    return word_list

word_list = word_links(bigrams)
word_list_cl = word_links(bigrams_clean)

print('love', word_list['love'][:5])
print('love', word_list_cl['love'][:5])

# List the most commonly associated words to the most popular words by after applying a ranking filter


# Function to draw the whole tab
def tab_word_usage(df, plot_width, plot_height):
    pass
