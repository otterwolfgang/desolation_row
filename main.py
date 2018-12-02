#!/usr/bin/env python3


# Import statements go here
from scripts.collect_lyrics_data import lyr_path, proj_dir
from scripts.read_data import read_data
from io import StringIO
import pandas as pd
from pathlib import Path
import re

from bokeh.io import curdoc
from bokeh.models.widgets import Tabs

from scripts.tab_overview import tab_overview
from scripts.tab_word_usage import tab_word_usage
from scripts.tab_ngrams import tab_ngrams


# Define the path to look for the pickled object
df_path = proj_dir.joinpath('data', 'df.pkl')

# Check wether the pickled object exists
try:
    df = pd.read_pickle(df_path)
except FileNotFoundError:
    read_data(lyr_path, df_path)
    df = pd.read_pickle(df_path)

# Print statements for exploratory data analysis
# print(df.info())
# print(df.describe())
# print(df['ReleaseDate'].value_counts())
# print(df['Pageviews'].value_counts())
# print(df['LyricsState'].value_counts())
# print(df.head())

# Create each tab
tab1 = tab_overview(df, 300, 300, proj_dir)
tab2 = tab_word_usage(df, 300, 300)
tab3 = tab_ngrams(df, 300, 300)

# Run a Bokeh server
curdoc().add_root(Tabs(tabs=[tab1, tab2, tab3]))
