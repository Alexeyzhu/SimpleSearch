import json
import os
import pickle
import threading
import urllib.request
from os.path import isfile, join
from pathlib import Path
from time import sleep
from urllib.parse import quote

import requests
from song import Song

from crawler import Crawler


def send_song(song: Song, add=True):
    if add:
        url = "http://127.0.0.1:5000/song/add"
    else:
        url = "http://127.0.0.1:5000/song/remove"

    req = urllib.request.Request(url)
    req.add_header('Content-Type', 'application/json; charset=utf-8')
    jsondata = json.dumps(song.__dict__)
    jsondataasbytes = jsondata.encode('utf-8')
    req.add_header('Content-Length', str(len(jsondataasbytes)))

    timer = 1
    not_sent = True
    while (not_sent):
        try:
            response = urllib.request.urlopen(req, jsondataasbytes)
            not_sent = False
        except urllib.error.URLError as err:
            timer *= 2
            print(f'No connection could be made because the target machine actively refused it'
                  f' \nTry again in {timer}')
            sleep(timer)


def get_songs_forever():
    crawler = Crawler()

    root = './Urls/'
    initial_point = "https://www.lyrics.com/lyrics/love"
    domain = 'www.lyrics.com'
    songs_root = './Songs/'
    checkpoint_path = './urls.data'

    remove_thread = threading.Thread(target=check_on_remove, args=(songs_root,))
    remove_thread.start()

    for c in crawler.crawl_generator(initial_point, domain, checkpoint_path, root):
        if c.doc.song is not None:
            succ = persist_song(c.doc.song, songs_root)
            if succ:
                send_song(c.doc.song)

    os.remove(checkpoint_path)


def persist_song(content: Song, songs_root: str):
    if isinstance(songs_root, str):
        songs_root = Path(songs_root)

    songs_root.mkdir(parents=True, exist_ok=True)

    onlyfiles = [f for f in os.listdir(songs_root) if isfile(join(songs_root, f))]
    file_name = process(content.title) + process(content.artist) + process(content.url) + '.data'

    try:
        if file_name not in onlyfiles:
            with open(songs_root / Path(file_name), 'wb') as filehandle:
                pickle.dump([content.title, content.artist, content.text, content.url], filehandle)
                print(f'File {file_name} stored')
        return True
    except Exception as err:
        print(f"Cannot persist song due to {type(err).__name__}")
        return False


def process(s):
    return quote(s).replace('/', '=')


def check_on_remove(songs_root):
    while True:
        check_songs(songs_root)
        sleep(60 * 60 * 24)


def check_songs(songs_root):
    if isinstance(songs_root, str):
        songs_root = Path(songs_root)

    songs_root.mkdir(parents=True, exist_ok=True)

    onlyfiles = [f for f in os.listdir(songs_root) if isfile(join(songs_root, f))]
    print(f'Number of songs to load: {len(onlyfiles)}')
    for file_name in onlyfiles:
        with open(songs_root / Path(file_name), 'rb') as filehandle:
            song_pick = pickle.load(filehandle)
            if song_pick[0] and song_pick[1]:
                song = Song(song_pick[0], song_pick[1], song_pick[2], song_pick[3])
                r = requests.get(song.url)
                if r.status_code is not 200:
                    print(f'Deleting song {song.title} by {song.artist}')
                    send_song(song)


if __name__ == '__main__':
    while (True):
        get_songs_forever()
