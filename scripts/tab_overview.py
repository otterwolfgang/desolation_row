#!/usr/bin/env python3


# Import statements go here
from collections import Counter
from io import StringIO
import pandas as pd
from pathlib import Path
import re

from bokeh.layouts import column, gridplot, layout, row
from bokeh.models import BasicTicker, ColorBar, ColumnDataSource, HoverTool, Label, LabelSet, LinearColorMapper, NumeralTickFormatter
from bokeh.models.widgets import Panel, Tabs
from bokeh.palettes import RdPu9
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


# Functions for generation of data sources

# Generate the numerical data for the number of artists, songs and average
# songs per artist in the data set
def num_data(df):
    num_artists = len(df['Artist'].value_counts())
    num_songs = df['FullTitle'].count()
    avg_per_artist = num_songs/num_artists

    return num_artists, num_songs, avg_per_artist

# Generate the ColumnDataSource for the number of songs per artist
def song_per_artist(df):
#    df_songs = df.groupby('Artist')[['FullTitle']].count()
    df_songs = df.groupby('Artist', as_index=False).count()
    df_songs['y'] = 1

    return ColumnDataSource(df_songs)

# Generate the ColumnDataSource for the songs with the most pageviews
def hit_songs(df, number):
    df_hits = df.sort_values(by='Pageviews').tail(int(number))

    return df_hits

# Generate the source relationship between ReleaseDate and number of unique
# words used
def words_date(df, proj_dir):
    # Sort DataFrame by ReleaseDate and reset index
    df = df.sort_values(by='ReleaseDate', ascending=False).reset_index(drop=True)

    # Load image data from csv, sort by y values and reset index
    csv_path = proj_dir.joinpath('data', 'image_data', 'bob_dylan_02.csv')
    coordinates = pd.read_csv(csv_path).sort_values(by='y').reset_index(drop=True)

    # Invert y-axis because image file is inverted
    coordinates['y'] = coordinates['y'] * (-1)

    # Join DataFrame with song data with image data
    df_date = df.join(coordinates)

    # # Initialize empty list for storing the words used in songs
    # words_used = []
    #
    # # Loop through songs in DataFrame and append the words used
    # for song in df_date['Lyrics']:
    #     words_ctn = Counter(re.findall(r'\w+\'*\w*', song.lower()))
    #     words_used.append(len(words_ctn))
    #
    # df_date['WordsUsed'] = words_used

    return df_date

# Functions for plotting the data

# Plot numberical data
def plot_nums(src, title, plot_width, plot_height):
    # Create the ColumnDataSource
    source=ColumnDataSource(dict(x=[1], y=[1], text=[str(src)]))

    # Create the empty figure
    plot = figure(
        plot_width=plot_width,
        plot_height=int(plot_height * 0.7),
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
    plot.background_fill_color = 'beige'
    plot.background_fill_alpha = 0.3
    plot.toolbar.logo = None
    plot.toolbar_location = None

    return plot

# Plot the number of songs per artist and the average
def plot_song_per_artist(src, avg, plot_width, plot_height):
    # Create the empty figure
    plot = figure(
        plot_width=plot_width * 2,
        plot_height=plot_height,
        title='Number of songs per artist'
    )

    # Add a circle glyph for all artists
    circle = plot.circle(
        x=jitter('FullTitle', width=0.1), y=jitter('y', width=0.4), source=src,
        size=25, alpha=0.7, color='salmon',
        hover_color='firebrick'
    )

    # Add a line glyph for the average number of songs per artist
    line = plot.line(
        x=[avg, avg], y=[0, 2],
        line_width=5, color='firebrick', alpha=0.6
    )

    # Add a label for the average line
    label = Label(
        x=avg + 0.1, y=1.85,
        text='Average number of songs per artist',
        text_font='futura', text_font_size='10pt'
    )

    plot.add_layout(label)

    # Add a hover tool
    hover = HoverTool(
        tooltips=[
            ('Artist', '@Artist'),
            ('Number of songs', '@FullTitle')
        ],
        renderers=[circle]
    )
    plot.add_tools(hover)

    # Style the visual properties of the plot
    plot.yaxis.visible = False
    plot.ygrid.visible = False
    plot.xaxis.minor_tick_line_color = None
    plot.background_fill_color = 'beige'
    plot.background_fill_alpha = 0.3

    return plot

# Plot the songs with the most pageviews
def plot_hit_songs(src, plot_width, plot_height):
    source = ColumnDataSource(src)

    # Get labels for the categorical x-axis
    songs = source.data['SongTitle']

    # Initialize a color mapper
    mapper = LinearColorMapper(
        palette=list(reversed(RdPu9)),
        low=src['WordsUsed'].min(), high=src['WordsUsed'].max()
    )

    # Create the empty figure with a categorical x-axis
    plot = figure(
        # x_range=songs,
        y_range=songs,
        plot_width=plot_width,
        plot_height=int(plot_height * 1.3),
        title='Hit songs',
        tools='save, reset, help'
    )

    # # Add a vbar glyph for all songs
    # vbar = plot.vbar(
    #     x='SongTitle', top='Pageviews', source=source,
    #     width=0.9, color='salmon',
    #     hover_color='firebrick'
    # )

    # Add an hbar glyph for all songs
    vbar = plot.hbar(
        y='SongTitle', left=0, right='Pageviews', source=source,
        height=0.8, color={'field': 'WordsUsed', 'transform': mapper},
        hover_color='firebrick'
    )

    # Add a hover tool
    hover = HoverTool(
        tooltips=[
            ('Song', '@SongTitle'),
            # ('Artist', '@Artist'),
            ('Pageviews', '@Pageviews{0,0}'),
            ('Unique words', '@WordsUsed')
        ],
        renderers=[vbar]
    )
    plot.add_tools(hover)

    # Add a label for the average line
    label = LabelSet(
        x=0, y='SongTitle', text='SongTitle', source=source,
        x_offset=5, y_offset=-8,
        text_font='futura', text_font_size='8pt'
    )

    plot.add_layout(label)

    # Style the visual properties of the plot
    # plot.xgrid.visible = False
    # plot.xaxis.major_label_orientation = 0.6
    # plot.yaxis.axis_label = 'Views on Genius'
    # plot.yaxis[0].formatter = NumeralTickFormatter(format='0.0a')
    plot.ygrid.visible = False
    plot.yaxis.major_label_text_font_size = '0pt'
    # plot.yaxis.major_tick_line_color = None
    plot.xaxis.axis_label = 'Views on Genius'
    plot.xaxis[0].formatter = NumeralTickFormatter(format='0a')
    plot.background_fill_color = 'beige'
    plot.background_fill_alpha = 0.3
    plot.toolbar.logo = None

    return plot

# Plot the songs according to ReleaseDate in form of the image of Bob Dylan
# The newer the song, the higher on the y-axis; color gives number of unique words
def plot_words_date(src, plot_width, plot_height):
    source = ColumnDataSource(src)

    # Initialize a color mapper
    mapper = LinearColorMapper(
        palette=list(reversed(RdPu9)),
        low=src['WordsUsed'].min(), high=src['WordsUsed'].max()
    )

    # Create the empty figure
    plot = figure(
        plot_width=plot_width * 2,
        plot_height=plot_height * 2,
        title='Did Bob Dylan become more talkative?'
    )

    # Add a circle glyph for all songs
    plot.circle(
        x='x', y='y', source=source,
        size=6, alpha=0.9, color={'field': 'WordsUsed', 'transform': mapper},
        hover_color='firebrick'
    )

    # Add a hover tool
    hover = HoverTool(
        tooltips=[
            ('Song', '@SongTitle'),
            ('Release Date', '@ReleaseDate{%F}'),
            ('Unique words', '@WordsUsed')
        ],
        formatters={'ReleaseDate': 'datetime'}
    )

    plot.add_tools(hover)

    # Add a color bar
    color_bar = ColorBar(
        color_mapper=mapper, major_label_text_font_size="6pt",
        ticker=BasicTicker(desired_num_ticks=len(RdPu9)),
        #formatter=PrintfTickFormatter(format="%d%%"),
        label_standoff=6, border_line_color=None, location=(0, 0)
    )

    plot.add_layout(color_bar, 'right')

    # Style the visual properties of the plot
    plot.xaxis.visible = False
    plot.xgrid.visible = False
    plot.yaxis.visible = False
    plot.ygrid.visible = False
    plot.xaxis.minor_tick_line_color = None
    plot.background_fill_color = 'beige'
    plot.background_fill_alpha = 0.3

    return plot


# Function to update plots
def update():
    pass


# Function to draw the whole tab
def tab_overview(df, plot_width, plot_height, proj_dir):
    # l1 = layout([
    #     [
    #         plot_nums(num_data(df)[0], 'Number of artists', plot_width, plot_height),
    #         plot_song_per_artist(song_per_artist(df), num_data(df)[2], plot_width, plot_height)
    #     ],
    #     [
    #         plot_nums(num_data(df)[1], 'Number of songs', plot_width, plot_height),
    #         plot_hit_songs(hit_songs(df, 5), plot_width, plot_height)
    #     ]
    # ])
    l2 = row(
        column([
            plot_nums(num_data(df)[1], 'Number of songs', plot_width, plot_height),
            plot_hit_songs(hit_songs(df, 10), plot_width, plot_height)
        ]),
        column([
            plot_words_date(words_date(df, proj_dir), plot_width, plot_height)
        ])
    )
    # l3 = gridplot(
    #     [
    #         column([
    #             plot_nums(num_data(df)[1], 'Number of songs', plot_width, plot_height),
    #             plot_hit_songs(hit_songs(df, 10), plot_width, plot_height)
    #         ]),
    #         column([
    #             plot_words_date(words_date(df, proj_dir), plot_width, plot_height)
    #         ])
    #     ],
    #     ncols=2,
    #     toolbar_location='right'
    # )

    tab = Panel(child=l2, title='Overview')

    return tab

# Temporary show command for testing
# show(tab_overview(df, 300, 300))
# l1 = layout([
#     [
#         #plot_words_date(words_date(df), 300, 300)
#         plot_nums(num_data(df)[0], 'Number of artists', 300, 300)
#     ]
# ])
# show(l1)
