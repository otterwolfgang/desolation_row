#!/usr/bin/env python3


# Import statements go here
from collections import Counter
from io import StringIO
from nltk.corpus import stopwords
import pandas as pd
from pathlib import Path
import re

from bokeh.layouts import column, layout, widgetbox
from bokeh.models import (
    ColumnDataSource, FactorRange, HoverTool, Label, LinearColorMapper,
    NumeralTickFormatter
)
from bokeh.models.widgets import Panel, Select, Tabs
from bokeh.palettes import magma, RdPu9
from bokeh.plotting import figure
from bokeh.transform import jitter

# #temp
# from collect_lyrics_data import proj_dir
# from bokeh.io import show
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
def tab_word_usage(df, plot_width, plot_height):

    # Functions for generation of data sources

    # Tokenize lyrics into single words and all individual words used
    def count_words(df):
        words_ctn = Counter()

        for song in df['Lyrics']:
            words_ctn.update(re.findall(r'\w+\'*\w*', song.lower()))

        return words_ctn

    # Tokenize lyrics into single words for songs
    def song_words(df):
        # Attach a y column with constant value for use in plot
        df['y'] = 1

        # Scale the pageviews for better display in plot
        df['PageviewsScaled'] = (df['Pageviews'] / df['Pageviews'].sum()) * 500 + 4

        # Group DataFrame by artists and calculate mean
        df_artists = df.groupby('Artist', as_index=False).mean()

        # Calculate overall mean for words used in songs
        avg = df['WordsUsed'].mean()

        return ColumnDataSource(df), ColumnDataSource(df_artists), avg

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
    def word_freq_years(df, lang='english', years):
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
    def top_freq_years(df, lang='english', years, ref_year, number):
        df_freq = word_freq_years(df, lang, years)

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


    # Functions for plotting the data

    # General style function for plots
    def style(plot):
        # Apply background color
        plot.background_fill_color = 'beige'
        plot.background_fill_alpha = 0.3

        return plot

    # Plot numerical data
    def plot_nums(src, title, plot_width, plot_height):
        # Create the ColumnDataSource
        source=ColumnDataSource(dict(x=[1], y=[1], text=[str(src)]))

        # Create the empty figure
        plot = figure(
            plot_width=int(plot_width),
            plot_height=int(plot_height),
            title=str(title),
            tools=''
        )

        # Add the text glyph
        plot.text(
            x='x', y='y', text='text', source=source,
            text_align='center', text_baseline='middle', text_color='salmon',
            text_font='futura', text_font_size='72pt'
        )

        plot.xaxis.visible = False
        plot.xgrid.visible = False
        plot.yaxis.visible = False
        plot.ygrid.visible = False
        plot.toolbar.logo = None
        # plot.toolbar_location = None

        return plot

    # Plot the number of songs per artist and the average
    def plot_words_per_song(src, plot_width, plot_height):
        # Create the empty figure
        plot = figure(
            plot_width=int(plot_width),
            plot_height=int(plot_height),
            y_range=(0.85, 1.2),
            title='Number of unique words used'
        )

        # Add the circle glyph for all songs
        songs = plot.circle(
            x='WordsUsed', y=jitter('y', width=0.25), source=src[0],
            size='PageviewsScaled', alpha=0.7, color='salmon',
            hover_color='firebrick'
        )

        # Add only for projects with multiple artists
        # # Add a circle glyph for artists and the average number of words used
        # artists = plot.circle(
        #     x='WordsUsed', y=jitter('y', width=0.05), source=src[1],
        #     size=40, alpha=0.7, color='orchid',
        #     hover_color='indigo'
        # )

        # Add a line glyph for the average number of individual words per song
        line = plot.line(
            x=[src[2], src[2]], y=[0, 2],
            line_width=5, color='firebrick', alpha=0.6
        )

        # Add a label for the average line
        label = Label(
            x=src[2] + 5, y=1.15,
            text='Average number of individual words per song',
            text_font='futura', text_font_size='10pt'
        )

        plot.add_layout(label)

        # Add a hover tool for the songs
        hover_songs = HoverTool(
            tooltips=[
                ('Song', '@SongTitle'),
                ('Artist', '@Artist'),
                ('Words used', '@WordsUsed'),
                ('Pageviews', '@Pageviews{0,0}')
            ],
            renderers=[songs]
        )

        # Add only for projects with multiple artists
        # # Add a hover tool for the artists
        # hover_artists = HoverTool(
        #     tooltips=[
        #         ('Artist', '@Artist'),
        #         ('Average per song', '@WordsUsed{0.0}')
        #     ],
        #     renderers=[artists]
        # )

        plot.add_tools(hover_songs)

        # Style the visual properties of the plot
        plot.yaxis.visible = False
        plot.ygrid.visible = False
        plot.xaxis.minor_tick_line_color = None

        return plot

    # Plot the frequency of the top used words for a year over all years
    def plot_top_freq_yrs(src, words, years, plot_width, plot_height):
        # Initialize a color mapper
        mapper = LinearColorMapper(
            palette=list(reversed(RdPu9)), # Palette with 9 colors
            # palette=list(reversed(magma(n))), # Palette with n colors
            low=src.data['Frequency'].min(), high=src.data['Frequency'].max()
        )

        # Create the empty figure
        plot = figure(
            title='Frequencies of the most used words in the selected time over the whole career ({} - {})'.format(years[0], years[-1]),
            x_range=years, y_range=list(reversed(words)),
            x_axis_location='above',
            plot_width=int(plot_width),
            plot_height=int(plot_height),
            tools='save, reset, help'
        )

        # Add a rect glyph
        plot.rect(
            x='Year', y='Word', width=0.99, height=0.99, source=src,
            fill_color={'field': 'Frequency', 'transform': mapper},
            line_color=None
        )

        # Add a hover tool
        hover = HoverTool(
            tooltips=[
                ('Year', '@Year'),
                ('Word', '@Word'),
                ('Frequency', '@Frequency{0.0}%')
            ]
        )

        plot.add_tools(hover)

        plot.grid.grid_line_color = None
        plot.axis.axis_line_color = None
        plot.axis.major_tick_line_color = None
        plot.axis.major_label_text_font_size = '8pt'
        plot.axis.major_label_standoff = 0
        plot.xaxis.major_label_orientation = 0.9
        plot.toolbar.logo = None

        return plot


    # Function to update the word frequency over years plot
    def update_freq(attr, old, new):
        new_src, new_words = top_freq_years(df, 'english', years, year_select.value, 10)

        src_freq.data.update(new_src.data)
        freq_table.y_range.factors = (list(reversed(new_words)))


    # Create plot 1 for total number of unique words in all songs
    total_words = plot_nums(
        len(count_words(df)),
        'Number of unique words in all songs',
        plot_width, plot_height * 0.8
    )
    total_words = style(total_words)

    # Create plot 2 for number of unique words per song
    words_per_song = plot_words_per_song(
        song_words(df),
        plot_width * 2, plot_height
    )
    words_per_song = style(words_per_song)

    # Create plot 3 for frequency table for top words in selected time
    # Years to use for analysis
    years = all_years(df)

    # Add a Select widget for selecting the displayed year
    # Make a copy of years to be able to insert 'overall' without changing the
    # data source
    years_overall = years.copy()
    years_overall.insert(0, 'overall')

    # Create the select object and link the callback
    year_select = Select(title='Most frequent words in', value='overall', options=years_overall)
    year_select.on_change('value', update_freq)

    # Data source for the plot
    src_freq, words = top_freq_years(df, 'english', years, 'overall', 10)

    freq_table = plot_top_freq_yrs(
        src_freq, words, years,
        plot_width * 3, plot_height
    )
    freq_table = style(freq_table)

    l1 = layout([
        [
            column(total_words, widgetbox(year_select)),
            words_per_song
        ],
        [
            freq_table
        ]
    ])

    tab = Panel(child=l1, title='Word Usage')

    return tab
