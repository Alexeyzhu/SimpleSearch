import os

import pymongo
import redis as redis
from flask import Flask, render_template, request

from web_app.forms import SearchForm
from web_app.search import *
from web_app.soundex import make_soundex_index, update_soundex_index
from web_app.wildcard import build_search_trie, update_search_trie

SECRET_KEY = os.urandom(32)

AUXILIARY_INDEX_SIZE = 25
SONGS_ROOT = './web_app/Songs/'

mongodb = pymongo.MongoClient('mongodb://root:example@localhost:27017')
redis_index = redis.Redis(host='localhost', port=6379, db=1)
redis_soundex = redis.Redis(host='localhost', port=6379, db=2)

lock = RedLock("index_lock")
lock_soundex = RedLock("soundex_index_lock")

load_songs_collection(mongodb, SONGS_ROOT)
print('Collection loaded')

create_main_index(mongodb)
print('Index has been built')

make_soundex_index(mongodb, redis_soundex, lock_soundex)
print('Soundex index has been built')

search_tree = TrieNode('*')
search_tree = build_search_trie(mongodb, search_tree)
print('Search tree has been created')

app = Flask(__name__)
app.config['SECRET_KEY'] = SECRET_KEY


@app.route('/', methods=['GET'])
@app.route('/search', methods=['GET'])
def index_page():
    form = SearchForm(request.args)
    query = request.args.get('q', None)
    table = None
    relevant = []
    result_query = ''

    if query is not None:
        table = True
        relevant, result_query = andvanced_search(mongodb, redis_index, lock, redis_soundex,
                                                  lock_soundex, search_tree, query)

    return render_template('home.html', form=form, query=query, result_query=result_query, table=table,
                           web_data=relevant)


@app.route('/song', methods=['GET', 'POST'])
def song_page():
    selected_song = request.args.get('type')
    s_s = parse(selected_song)
    return render_template('song.html', selected_song=s_s)


@app.route('/song/add', methods=['POST'])
def song_add():
    content = request.json
    search_db = mongodb['search']
    songs_collection = search_db['songs']

    if songs_collection.find({'url': content['url']}).count() == 0:
        song_id = songs_collection.insert_one(content).inserted_id
        song_words = preprocess(content['title']) + preprocess(content['artist']) + preprocess(content['text'])
        song_words = list(set(song_words))

        update_auxiliary_index(redis_index, song_words, song_id, lock)
        update_soundex_index(song_words, redis_soundex, lock_soundex)
        update_search_trie(song_words, search_tree)

        if redis_index.dbsize() > AUXILIARY_INDEX_SIZE:
            persist_auxiliary_index(redis_index, mongodb, lock)

        persist_song(content, SONGS_ROOT)

        return {'answer': False}
    else:
        print(f'Skipping {content["title"]} by {content["artist"]}')
    return {'answer': False}


@app.route('/song/remove', methods=['POST'])
def song_remove():
    content = request.json
    search_db = mongodb['search']
    songs_collection = search_db['songs']

    if songs_collection.find({'url': content['url']}).count() > 0:
        remove_song(redis_index, mongodb, content, lock)

        return {'answer': False}
    return {'answer': False}


def parse(song):
    song = song[1:-1]
    sp = song.split(", 'artist': ")
    title = sp[0].split("'title': ")[1][1:-1]
    artist = sp[1].split(", 'text': ")[0][1:-1]
    spp = sp[1].split(", 'text': ")[1]
    text = spp.split(", 'url': ")[0][1:-1]
    url = spp.split(", 'url': ")[1][1:-1]
    return {'title': title, 'artist': artist, 'text': text.replace('\\n', '\n'), 'url': url}


if __name__ == '__main__':
    app.run(host='0.0.0.0')
