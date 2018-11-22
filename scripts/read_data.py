#!/usr/bin/env python3


# Import statements go here
from collections import Counter
from io import StringIO
import pandas as pd
from pathlib import Path
import re


def read_data(lyr_path, save_path):
    # Define column names
    columns = [
        'FullTitle',
        'SongTitle',
        'Artist',
        'ReleaseDate',
        'Pageviews',
        'LyricsState',
        'Lyrics'
    ]

    # Initialize empty DataFrame
    df = pd.DataFrame(columns=columns)

    # Load lyrics data into DataFrame row by row
    for song in lyr_path.glob('*.txt'):
        with open(song, 'r') as file:
            # Delete all markers for Verse or Chorus
            input = re.sub(r'\s*\[\w*\s*\w*\]\s*', '', file.read())
            # Replace all newline characters with a single whitespace
            input = re.sub(r'\n+', ' ', input)
            # Replace all semicolons that are not in the head of the file with colons
            input = re.sub(r';(?! ##)', ',', input)
            # Delete all double pound signs that were used as special markers
            input = StringIO(re.sub('(?<=;) ## ', '', input))

            # Effective with new changes in collect lyrics
            # # Delete all markers for Verse or Chorus
            # input = re.sub(r' *\[\w*\] *', '', file.read())
            # # Replace all newline characters with a single whitespace
            # input = re.sub(r'\n+', ' ', input)
            # # Replace all semicolons not followed by double pound signs with colons
            # input = re.sub(r';(?!##)', ',', input)
            # # Delete all double pound signs that were used as special markers
            # input = StringIO(re.sub('(?<=;)## ', '', input))

        df = df.append(pd.read_csv(input, sep=';', header=None, names=columns))

    # Drop all rows without a value for ReleaseDate
    df = df[df['ReleaseDate'] != 'None']

    # Change all missing pageviews to 0 to only have numerical data
    df.replace('missing', 0, inplace=True)

    # Initialize empty list for storing the words used in songs
    words_used = []

    # Loop through songs in DataFrame and append the words used
    for song in df['Lyrics']:
        words_ctn = Counter(re.findall(r'\w+\'*\w*', song.lower()))
        words_used.append(len(words_ctn))

    df['WordsUsed'] = words_used

    # Convert types for the columns Pageviews and LyricsState
    df['ReleaseDate'] = pd.to_datetime(df['ReleaseDate'])
    df['Pageviews'] = pd.to_numeric(df['Pageviews'])
    df['LyricsState'] = df['LyricsState'].astype('category')
    df['WordsUsed'] = pd.to_numeric(df['WordsUsed'])

    # Store data as a pickled object
    df.to_pickle(save_path)
