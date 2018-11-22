#!/usr/bin/env python3


# Import statements go here
from bs4 import BeautifulSoup
import configparser
import datetime
from pathlib import Path
import re
import requests
import time


# Define scraping parameters
# Number of song IDs returned per page
num_song_ids = 10
# Maximum number of pages queried per artist ID
max_pages = 1
# Delay between saving song data and the next song data request in seconds
t_delay = 2
# Path of project directory
proj_dir = Path(__file__).resolve().parents[1]
# Path for saving lyrics data
lyr_path = proj_dir.joinpath('data', 'lyrics')
# Path for saving log files
log_path = proj_dir.joinpath('data', 'logs')
# Path of config file
config_file = proj_dir.joinpath('config', 'config.ini')

# Import Client Access Token for Genius API from config file
config = configparser.ConfigParser()
config.read(config_file)
genius_access_token = config['DEFAULT']['CLIENT_ACCESS_TOKEN']

# Genius API configuration
genius_api_url = 'https://api.genius.com'
genius_api_headers = {'Authorization': 'Bearer ' + genius_access_token}


# Find Genius artist ID from given name
def find_artist_id(artist_name):
    url = genius_api_url + '/search'
    query = {'q': artist_name}
    response = requests.get(url, data=query, headers=genius_api_headers).json()
    artist_id = None

    for hit in response['response']['hits']:
        if artist_name in hit['result']['primary_artist']['name']:
            artist_id = hit['result']['primary_artist']['id']
            break

    return artist_id

# Find song IDs where artist ID is listed as primary artist
def find_song_ids(artist_id, num_song_ids, page):
    url = 'https://api.genius.com/artists/' + str(artist_id) + '/songs'
    # Payload defines sorting of songs and number listed
    payload = {'sort': 'popularity', 'per_page': num_song_ids, 'page': page}
    response = requests.get(url, headers=genius_api_headers,
                            params=payload).json()

    # Initiate an empty list to store all song IDs
    song_id_list = []
    for song in response['response']['songs']:
        # Check wether the queried artist ID is listed as primary artist
        if song['primary_artist']['id'] == artist_id:
            song_id_list.append(song['id'])

    # Return the number of the next page
    next_page = response['response']['next_page']

    return song_id_list, next_page

# Scrape song lyrics from web pages by given url
def scrape_song_url(url):
    page = requests.get(url)
    html = BeautifulSoup(page.text, 'html.parser')
    lyrics = html.find('div', class_='lyrics').get_text()

    return lyrics

# Query song IDs for data and lyrics
def find_song_data(song_id):
    url = 'https://api.genius.com/songs/' + str(song_id)
    response = requests.get(url, headers=genius_api_headers).json()

    full_title = response['response']['song']['full_title']
    title = response['response']['song']['title']
    ar_name = response['response']['song']['primary_artist']['name']

    try:
        rel_date = response['response']['song']['release_date']
    except KeyError:
        rel_date = 'missing'

    try:
        pageviews = response['response']['song']['stats']['pageviews']
    except KeyError:
        pageviews = 'missing'

    try:
        lyr_state = response['response']['song']['lyrics_state']
    except KeyError:
        lyr_state = 'missing'

    lyrics = scrape_song_url(response['response']['song']['url'])

    return full_title, title, ar_name, rel_date, pageviews, lyr_state, lyrics

# Find backslashes in a string and replace them with a space
def del_slash(input):
    output = re.sub(r'/+', ' ', input)

    return output

# Write log file with relevant data for scraping process
def write_log(log_path, t_start, t_end, num_artists, num_songs, not_found):
    log_name = (log_path.joinpath('log_{}.txt'.
                format(t_start.strftime('%Y_%m_%d_%H%M%S'))))
    with open(log_name, 'w') as file:
        print(
            'Start time: ' + t_start.strftime('%Y-%m-%d %H:%M:%S'),
            'End time: ' + t_end.strftime('%Y-%m-%d %H:%M:%S'),
            'Duration: ' + str(t_end - t_start),
            'Delay timer set to [seconds]: ' + str(t_delay),
            'Number of artists: ' + str(num_artists),
            'Number of songs: ' + str(num_songs),
            'Average no. of songs per artist: ' + str(num_songs/num_artists),
            'Time per song: ' + str((t_end - t_start)/num_songs),
            'Artists not found: ' + str(not_found),
            sep=';\n',
            file=file
        )


# Main function to scrape and store data
def main():

    # Initialize variables for logging
    t_start = datetime.datetime.now()
    num_artists = 0
    num_songs = 0
    not_found = []

    # Print start info to console
    print('{}: Starting scraping process...'.format(t_start.strftime('%Y-%m-%d %H:%M:%S')))

    # Parse Wikipedia page for artist names
    # url = 'https://de.wikipedia.org/wiki/Liste_deutschsprachiger_Schlagermusiker'
    # page = requests.get(url)
    # soup = BeautifulSoup(page.text, 'html.parser')
    # list_items = soup.find_all('li')
    # pattern = re.compile(r'\s(?!&)\W.*', re.U)
    # artist_list = [re.sub(pattern, '', a.get_text()) for a in list_items][0:488]

    # Input artist list directly
    artist_list = ['Sia']

    for artist in artist_list:
        # print('Scraping artist {} of {}'.format(num_artists+len(not_found)+1, len(artist_list)), end='\r')

        artist_id = find_artist_id(artist)
        if artist_id:
            page = 1
            while page is not None and page <= max_pages:
                song_id_list, page = find_song_ids(artist_id, num_song_ids, page)

                for song_id in song_id_list:
                    print('Scraping song ID {} on page {}...'.format(song_id, page - 1), end='\r')
                    full_title, title, ar_name, rel_date, pageviews, lyr_state, lyrics = find_song_data(song_id)

                    file_name = lyr_path.joinpath('{}_{}.txt'.format(del_slash(ar_name), del_slash(title)))
                    with open(file_name, 'w') as file:
                        print(
                            full_title,
                            title,
                            ar_name,
                            rel_date,
                            pageviews,
                            lyr_state,
                            lyrics,
                            sep=';##\n',
                            file=file
                        )
                    num_songs += 1
                    time.sleep(t_delay)

            num_artists += 1

        else:
            not_found.append(artist)

    # Log end time
    t_end = datetime.datetime.now()

    # Write log file
    write_log(log_path, t_start, t_end, num_artists, num_songs, not_found)

    # Print end info to console
    print('{}: Success! Scraping finished.'.format(t_end.strftime('%Y-%m-%d %H:%M:%S')))


if __name__ == '__main__':
    main()
