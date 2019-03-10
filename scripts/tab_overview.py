#!/usr/bin/env python3


# Import statements go here
from collections import Counter
from datetime import timedelta
from io import StringIO
import pandas as pd
from pathlib import Path
import re

from bokeh.layouts import column, gridplot, layout, row, widgetbox
from bokeh.models import (
    BasicTicker, ColorBar, ColumnDataSource, FuncTickFormatter, HoverTool,
    Label, LabelSet, LinearColorMapper, NumeralTickFormatter
)
from bokeh.models.widgets import Panel, Select, Tabs
from bokeh.palettes import RdPu9
from bokeh.plotting import figure
from bokeh.transform import jitter

###
# #temp
# from collect_lyrics_data import proj_dir
#
# # Import df for temporary use
# # Define the path to look for the pickled object
# df_path = proj_dir.joinpath('data', 'df.pkl')
#
# # Check wether the pickled object exists
# df = pd.read_pickle(df_path)
###

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

# Generate the source for the relationship between ReleaseDate and number of
# unique words used
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

    return df_date

# Generate the source for the heatmap of the mean number of unique words used
# for the selected epoch
def words_epoch(df, offset):
    # Instantiate a resample object based on the selected offset
    resample = df.resample(offset, on='ReleaseDate')
    # Create a new DataFrame with the mean number of unique words used
    df_epoch = resample.mean()[['WordsUsed']]
    # Create a column with the number of songs used for each epoch
    df_epoch['NumSongs'] = resample.count()['SongTitle']
    # Drop the first row
    df_epoch.drop(df_epoch.index[0], inplace=True)
    # Rename the index
    df_epoch.index.name = 'right'
    # Create a column for the left end of the offset
    df_epoch['left'] = resample.count().index[:-1]
    # Move the left end of the offset by one day to have it start with the new year
    df_epoch['left'] = df_epoch['left'] + timedelta(days=1)
    # Create a new column giving the time delta between left and right end of the offset
    df_epoch['height'] = df_epoch.index - df_epoch['left']

    return ColumnDataSource(df_epoch)

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
        text_font='futura', text_font_size='64pt'
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
def plot_hit_songs(src, mapper, plot_width, plot_height):
    source = ColumnDataSource(src)

    # Get labels for the categorical x-axis
    songs = source.data['SongTitle']

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
        line_color='salmon', line_alpha=0.3,
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
    plot.yaxis.axis_line_color = None
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
def plot_words_date(src, mapper, plot_width, plot_height):
    source = ColumnDataSource(src)

    # Create the empty figure
    plot = figure(
        plot_width=plot_width * 2,
        plot_height=plot_height * 2,
        title='When did Bob Dylan talk the most? (or unique words per song over time)'
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

    plot.add_layout(color_bar, 'left')

    # Add a custom ticker
    high = src['y'].max()
    low = int(src['y'].min())

    plot.yaxis.ticker = [low, high]
    plot.yaxis.formatter = FuncTickFormatter(code="""
        var mapping = {"-911": "1961", "-20": "2018"};
        return mapping[tick];
    """)

    # Style the visual properties of the plot
    plot.grid.grid_line_color = None
    plot.axis.axis_line_color = None
    plot.xaxis.visible = False
    plot.toolbar_location = None
    plot.background_fill_color = 'beige'
    plot.background_fill_alpha = 0.3

    return plot

# Plot a heatmap giving the mean number of unique words per song for the
# specified epochs
def plot_words_epoch(src, mapper, plot_width, plot_height):
    # Create the empty figure
    plot = figure(
        plot_width=int(plot_width * 0.35),
        plot_height=int(plot_height * 1.82),
        x_range=(-1, 1),
        y_range=(src.data['left'].min(), src.data['right'].max()),
        title='Average',
        y_axis_type='datetime',
        tools=''
    )

    # Add a quad glyph
    plot.quad(
        left=-2, right=2, bottom='left', top='right', source=src,
        fill_color={'field': 'WordsUsed', 'transform': mapper},
        line_color='beige', line_alpha=0.3, line_width=0.5
    )

    # Add a hover tool
    hover = HoverTool(
        tooltips=[
            ('Timespan', '@left{%Y} - @right{%Y}'),
            ('Number of songs', '@NumSongs'),
            ('Mean unique words', '@WordsUsed{0.0}')
        ],
        formatters={'left': 'datetime', 'right': 'datetime'}
    )

    plot.add_tools(hover)

    # Style the visual properties of the plot
    plot.grid.grid_line_color = None
    plot.axis.axis_line_color = None
    plot.xaxis.visible = False
    plot.toolbar_location = None
    # plot.toolbar.logo = None
    plot.background_fill_color = 'beige'
    plot.background_fill_alpha = 0.3

    return plot


# Function to draw the whole tab
def tab_overview(df, plot_width, plot_height, proj_dir):
    # Function to update the epochs plot
    def update_epoch(attr, old, new):
        offset_dict = {'3 years': '3A', '5 years': '5A', '10 years': '10A'}
        new_src = words_epoch(df, offset_dict[epoch_select.value])

        src_epoch.data.update(new_src.data)

    # Add a Select widget for selecting the displayed epoch
    # Create the select object and link the callback
    epoch_select = Select(
        # title='Epoch',
        value='10 years', options=['3 years', '5 years', '10 years']
    )
    epoch_select.on_change('value', update_epoch)

    # Initialize a color mapper to use in all plots
    mapper = LinearColorMapper(
        palette=list(reversed(RdPu9)),
        low=df['WordsUsed'].min(), high=df['WordsUsed'].max()
    )

    # Create the source for the epochs plot
    src_epoch = words_epoch(df, '10A')

    # Create the whole tab
    # # Layout to use for more than one artist
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
    l2 = row([
        column([
            plot_nums(num_data(df)[1], 'Number of songs', plot_width, plot_height),
            plot_hit_songs(hit_songs(df, 10), mapper, plot_width, plot_height)
        ]),
        column([
            plot_words_date(words_date(df, proj_dir), mapper, plot_width, plot_height)
        ]),
        column([
            plot_words_epoch(src_epoch, mapper, plot_width, plot_height),
            widgetbox(epoch_select, width=120)
        ])
    ])
    # # Layout with one combined toolbar
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

# df_epoch = words_epoch(df, '10A')
# print(df[['ReleaseDate']].sort_values(by='ReleaseDate'))
# print(df_epoch.head(10))

#colormapper with absolute values for songs (min max on songs)
