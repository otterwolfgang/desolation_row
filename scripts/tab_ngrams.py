#!/usr/bin/env python3


# Import statements go here
from collections import Counter, defaultdict
from io import StringIO
from nltk.corpus import stopwords
import pandas as pd
from pathlib import Path
import re

from nltk import pos_tag
from nltk.collocations import BigramAssocMeasures, BigramCollocationFinder

from bokeh.layouts import layout, widgetbox
from bokeh.models import ColumnDataSource, LinearColorMapper, Legend, LegendItem
from bokeh.models.widgets import Panel, Tabs, TextInput
from bokeh.palettes import magma, RdPu9
from bokeh.plotting import figure

# #temp
# from collect_lyrics_data import proj_dir, lyr_path
# from read_data import read_data
# from bokeh.io import output_file, show
#
#
# # Import df for temporary use
# # Define the path to look for the pickled object
# df_path = proj_dir.joinpath('data', 'df.pkl')
#
# # Check wether the pickled object exists
# try:
#     df = pd.read_pickle(df_path)
# except FileNotFoundError:
#     read_data(lyr_path, df_path)
#     df = pd.read_pickle(df_path)


# Function to draw the whole tab
def tab_ngrams(df, plot_width, plot_height):

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


    # Functions for generation of data sources

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

        # Use nltk's pos_tag function to obtain tags for all words
        tags = pos_tag(bigram)

        if tags[0][1] in start_tag and tags[1][1] in follow_tag:
            return True
        else:
            return False

    # Score bigrams by selected association ranking measure
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
            # Put the word itself in the list
            terms.extend([word for i in range(num_links)])
            # Put increasing y values in the list for positioning in the plot
            y_pos.extend([i for i in range(num_links)])
            # Put the most closely linked terms in the list
            temp_links = [link[0] for link in word_list[word][:num_links]]
            # Put the ranks of the selected terms in the list
            temp_ranks = [link[1] for link in word_list[word][:num_links]]

            # Fill the list with 'NaN' and zeros up to the number of num_links
            if len(temp_links) < num_links:
                temp_links.extend(['NaN'] * (num_links - len(temp_links)))
                temp_ranks.extend([0] * (num_links - len(temp_ranks)))

            links.extend(temp_links)
            ranks.extend(temp_ranks)

        # Create the DataFrame out of the lists
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
        # Find the frequency of occurence for the given word in every year
        for year in df_freq.index.tolist():
            word_counts.append((df_freq.loc[year, 'FreqCtn'][word] / df_freq.loc[year, 'Total']) * 100)

        df = pd.DataFrame({'Word': word_counts}, index=df_freq.index)
        df.index.name = 'Year'

        return ColumnDataSource(df)


    # Functions for plotting the data

    # General style function for plots
    def style(plot):
        # Apply background color
        plot.background_fill_color = 'beige'
        plot.background_fill_alpha = 0.3

        return plot

    # Plot words and their most closely associated terms
    def plot_word_links(
        src, words, num_links=10,
        plot_width=900, plot_height=300
    ):
        x_range = words
        y_range = [num_links - 0.5, -0.5]

        # Initialize a color mapper
        mapper = LinearColorMapper(
            palette=list(reversed(RdPu9)), # Palette with 9 colors
            # palette=list(reversed(magma(n))), # Palette with n colors
            low=src.data['Rank'].min(), high=src.data['Rank'].max()
        )

        # Create the empty figure
        plot = figure(
            title='Top words and their most closely associated terms',
            plot_width=int(plot_width), plot_height=int(plot_height),
            x_range=x_range, y_range=y_range,
            x_axis_location='above'
        )

        plot.text(
            x='Word', y='y', text='Link', source=src,
            text_color={'field': 'Rank', 'transform': mapper},
            text_font='futura', text_font_size='9pt',
            text_align='center', text_baseline='middle'
        )

        plot.grid.grid_line_color = None
        plot.xaxis.axis_line_color = None
        plot.xaxis.major_tick_line_color = None
        plot.xaxis.major_label_text_font_size = '9pt'
        plot.xaxis.major_label_text_font_style = 'bold'
        plot.yaxis.visible = False

        return plot

    # Plot the frequency of occurence for certain words over the whole career
    def plot_word_trends(
        src01, src02, src03,
        plot_width=900, plot_height=300
    ):
        # Create the empty figure
        plot = figure(
            title='Word trends',
            plot_width=int(plot_width), plot_height=int(plot_height),
            x_range=[1960, 2020]
        )

        # Create the step glyph for the first word
        first = plot.step(
            x='Year', y='Word', source=src01, mode='after',
            color='salmon', alpha=0.7, line_width=2,
            # legend=w01_input.value
        )

        # Create the step glyph for the second word
        second = plot.step(
            x='Year', y='Word', source=src02, mode='after',
            alpha=0.7, line_width=2
        )

        # Create the step glyph for the third word
        third = plot.step(
            x='Year', y='Word', source=src03, mode='after',
            color='turquoise', alpha=0.7, line_width=2
        )

        return plot


    # # temp functions for testing
    # bigrams = find_bigrams(tokenize(df, 'english'), 10, 't', pos_filter=True)
    # print(bigrams.head())
    #
    # word_list = word_links(tokenize(df), 5, method='PMI')
    # print('love', word_list['love'][:5])





    # Create plot 1 for word trends
    # Default words for initial display
    w01 = 'god'
    w02 = 'lord'
    w03 = 'jesus'



    src01_trends = freq_over_years(df, w01, all_years(df))
    src02_trends = freq_over_years(df, w02, all_years(df))
    src03_trends = freq_over_years(df, w03, all_years(df))

    word_trends = plot_word_trends(
        src01_trends, src02_trends, src03_trends,
        plot_width * 3, plot_height
    )

    word_trends = style(word_trends)

    def add_legend(plot, label):
        li1 = LegendItem(label=label, renderers=[plot.renderers[5]])
        # li2 = LegendItem(label='blue', renderers=[p1.renderers[1]])
        # li3 = LegendItem(label='purple', renderers=[p1.renderers[2]])
        legend1 = Legend(items=[li1], location='top_right')
        plot.add_layout(legend1)

    add_legend(word_trends, 'god')

    # Function to update the word trends to specific words
    def update_trends(attr, old, new):
        src01_new = freq_over_years(df, w01_input.value, all_years(df))
        src02_new = freq_over_years(df, w02_input.value, all_years(df))
        src03_new = freq_over_years(df, w03_input.value, all_years(df))

        src01_trends.data.update(src01_new.data)
        src02_trends.data.update(src02_new.data)
        src03_trends.data.update(src03_new.data)

        add_legend(word_trends, w01_input.value)
        add_legend(word_trends, w02_input.value)
        add_legend(word_trends, w03_input.value)


    # Create three text input widget for displaying three words individually
    w01_input = TextInput(title='Word No. 1:', value=w01, placeholder='type here')
    w01_input.on_change('value', update_trends)
    w02_input = TextInput(title='Word No. 2:', value=w02, placeholder='type here')
    w02_input.on_change('value', update_trends)
    w03_input = TextInput(title='Word No. 3:', value=w03, placeholder='type here')
    w03_input.on_change('value', update_trends)

    # Create plot 2 for the most popular words and their closest links
    num_links = 10
    words = top_freq_years(df, all_years(df), 'overall', 10)[1]
    src_links = freq_links(
        word_links(tokenize(df), 5, method='PMI'),
        words,
        num_links=num_links
    )

    word_links = plot_word_links(
        src_links, words, num_links,
        plot_width * 3, plot_height
    )

    word_links = style(word_links)

    # Create a tab layout
    l1 = layout([
        [
            widgetbox(w01_input, w02_input, w03_input, width=200),
            word_trends
        ],
        [
            word_links
        ]
    ])

    tab = Panel(child=l1, title='Word Trends & Bigrams')

    return tab
