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

from bokeh.io import output_file, show
from bokeh.models import ColumnDataSource, LinearColorMapper
from bokeh.palettes import magma, RdPu9
from bokeh.plotting import figure


# Import df for temporary use
# Define the path to look for the pickled object
df_path = proj_dir.joinpath('data', 'df.pkl')

# Check wether the pickled object exists
try:
    df = pd.read_pickle(df_path)
except FileNotFoundError:
    read_data(lyr_path, df_path)
    df = pd.read_pickle(df_path)


# Copied functions from tab_word_usage (temporary)
# Count word frequency in all songs excluding stopwords
def word_frequency(df, lang='english'):
    # Import stop words from nltk corpus
    stop_words = set(stopwords.words(lang))

    words_ctn = Counter()

    for song in df['Lyrics']:
        words_ctn.update([w for w in re.findall(r'\w+\'*\w*', song.lower()) if w not in stop_words])

    # Return the counter with all words and their numbers of occurence
    return words_ctn

# Find all years in dataset and put into a set
def all_years(df):
    years = set()
    for date in df['ReleaseDate']:
        years.update(re.findall(r'[0-9]{4}', str(date)))

    return sorted(list(years))

# Count word frequency for individual years
def word_freq_years(df, years, lang='english'):
    df = df.set_index(df['ReleaseDate']).sort_index()

    years_freq = []
    years_total = []
    for year in years:
        # Append the counter with all words and their numbers of occurence
        # for the specified year
        years_freq.append(word_frequency(df[year], lang))
        # Append the sum of all values in the counter giving the total
        # number of words minus stop words for that year
        years_total.append(sum(word_frequency(df[year], lang).values()))

    df_freq = pd.DataFrame(
        {'FreqCtn': years_freq, 'Total': years_total},
        index=years
    ).sort_index()

    return df_freq

# Find the top words and their frequency of occurence for a given time
def top_freq_years(df, years, ref_year, number, lang='english'):
    df_freq = word_freq_years(df, years, lang)

    # Find the most common words for the reference year or all years
    if ref_year == 'overall':
        top_words = word_frequency(df, lang).most_common(number)
    else:
        top_words = df_freq.loc[ref_year, 'FreqCtn'].most_common(number)

    words, count = zip(*top_words)

    freq_dict = {}

    for word in words:
        word_counts = []
        for year in df_freq.index.tolist():
            word_counts.append((df_freq.loc[year, 'FreqCtn'][word] / df_freq.loc[year, 'Total']) * 100)
        freq_dict.update({word: word_counts})

    df = pd.DataFrame(freq_dict, index=df_freq.index)
    df.columns.name = 'Word'
    df.index.name = 'Year'

    # Reshape to 1D array or frequency with a word and year for each row
    df = pd.DataFrame(df.stack(), columns=['Frequency']).reset_index()

    return ColumnDataSource(df), words


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

# Build a ColumnDataSource with the most frequent words and their links
def freq_links(word_list, words, num_links=10):
    terms = []
    y_pos = []
    links = []
    ranks = []

    for word in words:
        terms.extend([word for i in range(num_links)])
        y_pos.extend([i for i in range(num_links)])
        temp_links = [link[0] for link in word_list[word][:num_links]]
        temp_ranks = [link[1] for link in word_list[word][:num_links]]

        if len(temp_links) < num_links:
            temp_links.extend(['NaN'] * (num_links - len(temp_links)))
            temp_ranks.extend([0] * (num_links - len(temp_ranks)))

        links.extend(temp_links)
        ranks.extend(temp_ranks)

    df = pd.DataFrame({
        'Word': terms,
        'y': y_pos,
        'Link': links,
        'Rank': ranks
    })

    return ColumnDataSource(df)

# Find the frequency of occurence for a given word over all years
def freq_over_years(df, word, years, lang='english'):
    df_freq = word_freq_years(df, years, lang)

    word_counts = []
    for year in df_freq.index.tolist():
        word_counts.append((df_freq.loc[year, 'FreqCtn'][word] / df_freq.loc[year, 'Total']) * 100)

    df = pd.DataFrame({word: word_counts}, index=df_freq.index)
    df.index.name = 'Year'

    return df

# # temp functions for testing
# bigrams = find_bigrams(tokenize(df, 'english'), 10, 't', pos_filter=True)
# print(bigrams.head())
#
# word_list = word_links(tokenize(df), 5, method='PMI')
# print('love', word_list['love'][:5])

like = freq_over_years(df, 'like', all_years(df))
print(like.head(10))
god = freq_over_years(df, 'god', all_years(df))
print(god.tail(15))

num_links = 10
words = top_freq_years(df, all_years(df), 'overall', 10)[1]
src = freq_links(
    word_links(tokenize(df), 5, method='PMI'),
    words,
    num_links=num_links
)


# Functions for plotting the data

# General style function for plots
def style(plot):
    # Apply background color
    plot.background_fill_color = 'beige'
    plot.background_fill_alpha = 0.3

    return plot

# Try out bokeh's text glyph for displaying information
output_file('test.html')

x_range = words
y_range = [num_links - 0.5, -0.5]


# Initialize a color mapper
mapper = LinearColorMapper(
    palette=list(reversed(RdPu9)), # Palette with 9 colors
    # palette=list(reversed(magma(n))), # Palette with n colors
    low=src.data['Rank'].min(), high=src.data['Rank'].max()
)

p = figure(
    title='test', plot_width=900, plot_height=300,
    x_range=x_range, y_range=y_range,
    x_axis_location='above'
)

p.text(
    x='Word', y='y', text='Link', source=src,
    text_color={'field': 'Rank', 'transform': mapper},
    text_font='futura', text_font_size='9pt',
    text_align='center', text_baseline='middle'
)

p.grid.grid_line_color = None
p.xaxis.axis_line_color = None
p.xaxis.major_tick_line_color = None
p.xaxis.major_label_text_font_size = '9pt'
p.xaxis.major_label_text_font_style = 'bold'
p.yaxis.visible = False

p = style(p)
# show(p)

# Function to draw the whole tab
def tab_word_usage(df, plot_width, plot_height):
    pass
