# Imports go here
import configparser
from pathlib import Path
import pytest
import requests

from scripts import collect_lyrics_data as cld


# Import Client Access Token for Genius API from config file
config_file = Path('../projekt_atemlos/config/config.ini')
config = configparser.ConfigParser()
config.read(config_file)
genius_access_token = config['DEFAULT']['CLIENT_ACCESS_TOKEN']

# Genius API configuration
genius_api_url = 'https://api.genius.com'
genius_api_headers = {'Authorization': 'Bearer ' + genius_access_token}


def test_access_token_loaded():
    assert isinstance(genius_access_token, str)

def test_api_call_ok():
    url = genius_api_url + '/search'
    query = {'q': 'Sia'}
    response = requests.get(url, data=query, headers=genius_api_headers).json()
    assert response['meta']['status'] == 200

def test_find_artist_id():
    assert isinstance(cld.find_artist_id('Sia'), int)
    assert cld.find_artist_id('Sia') == 16775

def test_find_song_ids():
    assert isinstance(cld.find_song_ids(16775, 5), list)

def test_scrape_song_url():
    assert isinstance(cld.scrape_song_url('https://genius.com/Sia-chandelier-lyrics'), str)
    assert 'chandelier' in cld.scrape_song_url('https://genius.com/Sia-chandelier-lyrics')

def test_find_song_data():
    assert isinstance(cld.find_song_data(378195), tuple)
    assert cld.find_song_data(378195)[1] == 'Chandelier'
    assert 'chandelier' in cld.find_song_data(378195)[-1]
