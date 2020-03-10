import json
import pickle
from os import listdir
from os.path import isfile, join
from pathlib import Path
from typing import List
from urllib.parse import quote

from bson import json_util
from nltk.corpus import stopwords
from pymongo import MongoClient
from redis import Redis
from redlock.lock import RedLock

from web_app.preprocessing import normalize, preprocess, lemmatization
from web_app.soundex import soundex, get_closest_words
from web_app.wildcard import wildcard_handler, find_prefix, TrieNode


def load_songs_collection(mongodb: MongoClient, songs_root, n=500):
    search_db = mongodb['search']
    songs_collection = search_db['songs']

    if isinstance(songs_root, str):
        songs_root = Path(songs_root)
    songs_root.mkdir(parents=True, exist_ok=True)

    onlyfiles = [f for f in listdir(songs_root) if isfile(join(songs_root, f))]
    print(f'Number of songs to load: {len(onlyfiles)}')
    for file_name in onlyfiles:
        with open(songs_root / Path(file_name), 'rb') as filehandle:
            song_pick = pickle.load(filehandle)
            if song_pick[0] and song_pick[1]:
                songs_collection.insert_one(
                    {'title': song_pick[0], 'artist': song_pick[1], 'text': song_pick[2], 'url': song_pick[3]})


def create_main_index(mongodb: MongoClient):
    search_db = mongodb['search']
    index_collection = search_db['index']
    songs_collection = search_db['songs']

    collection = songs_collection.find({})

    for song in collection:
        song_words = preprocess(song['title']) + preprocess(song['artist']) + preprocess(song['text'])

        for word in song_words:
            if index_collection.find({'word': word}).count() > 0:
                word_songs = index_collection.find_one({'word': word})['songs']
                if song['_id'] not in word_songs:
                    word_songs.append(song['_id'])
                    index_collection.update({'word': word}, {'word': word, 'songs': word_songs})
            else:
                index_collection.insert_one({'word': word, 'songs': [song['_id']]})


def redis_list(l, dump: bool):
    if dump:
        return json.dumps(l, default=json_util.default)
    else:
        return json.loads(l, object_hook=json_util.object_hook)


def update_auxiliary_index(redis: Redis, song_words: List, song_id, lock: RedLock):
    lock.acquire()
    for word in song_words:
        if redis.exists(word):
            existent = redis_list(redis.get(word), False)
            existent.append(song_id)
            redis.set(word, redis_list(existent, True))
        else:
            redis.set(word, redis_list([song_id], True))
    lock.release()


def persist_auxiliary_index(redis: Redis, mongodb: MongoClient, lock: RedLock):
    search_db = mongodb['search']
    index_collection = search_db['index']

    lock.acquire()
    for word in redis.scan_iter():
        word = word.decode("utf-8")
        redis_song_ids = redis_list(redis.get(word), False)
        if index_collection.find({'word': word}).count() > 0:
            mongo_songs_ids = index_collection.find_one({'word': word})['songs']
            union_songs_ids = union(mongo_songs_ids, redis_song_ids)
            index_collection.update({'word': word}, {'word': word, 'songs': union_songs_ids})
        else:
            index_collection.insert_one({'word': word, 'songs': redis_song_ids})

        redis.delete(word)
    lock.release()


def process(s):
    return quote(s).replace('/', '=')


def persist_song(content: dict, songs_root):
    if isinstance(songs_root, str):
        songs_root = Path(songs_root)

    songs_root.mkdir(parents=True, exist_ok=True)
    onlyfiles = [f for f in listdir(songs_root) if isfile(join(songs_root, f))]
    file_name = ''.join(normalize(content['title'])) + ''.join(normalize(content['artist'])) + process(
        content['url']) + '.data'
    if file_name not in onlyfiles:
        with open(songs_root / Path(file_name), 'wb') as filehandle:
            pickle.dump([content['title'], content['artist'], content['text'], content['url']], filehandle)
            print(f'File {file_name} stored')


def remove_song(redis: Redis, mongodb: MongoClient, lock: RedLock, song):
    search_db = mongodb['search']
    songs_collection = search_db['songs']
    index_collection = search_db['index']

    song_id = songs_collection.find({'url': song['url']})['_id']

    song_words = preprocess(song['title']) + preprocess(song['artist']) + preprocess(song['text'])
    song_words = list(set(song_words))

    for word in song_words:
        lock.acquire()
        if redis.exists(word):
            existent = redis_list(redis.get(word), False)
            existent.pop(song_id)
            redis.set(word, redis_list(existent, True))
        lock.release()

        if index_collection.find({'word': word}).count() > 0:
            existent = index_collection.find_one({'word': word})['songs']
            existent.pop(song_id)
            index_collection.update({'word': word}, {'word': word, 'songs': existent})

    songs_collection.remove(song_id)


def intersection(lst1, lst2):
    lst3 = [value for value in lst1 if value in lst2]
    return lst3


def union(lst1, lst2):
    return list(set().union(lst1, lst2))


def andvanced_search(mongodb: MongoClient, redis: Redis, lock: RedLock, soundex_collection: Redis,
                     lock_soundex: RedLock, trie: TrieNode, query):
    search_db = mongodb['search']
    index_collection = search_db['index']
    songs_collection = search_db['songs']

    result_query = ''
    query_words = query.split()

    relevant_documents = []

    for query_word in query_words:

        or_relevant_docs = []
        or_list = []

        found, _ = find_prefix(trie, lemmatization([query_word])[0] + '$')
        print(found)

        # wildcard handler
        if '*' in query_word:
            or_list = wildcard_handler(query_word, trie)
            if not or_list:
                return or_list
        # mistake correction
        elif not found:
            if query_word not in stopwords.words('english'):
                soundex_misspelled = soundex(query_word)

                if not soundex_collection.exists(soundex_misspelled):
                    return [], 'query are not available. Try to paraphrase!'

                lock_soundex.acquire()
                soundex_misspelled_words = redis_list(soundex_collection.get(soundex_misspelled), False)
                lock_soundex.release()

                or_list = get_closest_words(query_word, soundex_misspelled_words)

                if not or_list:
                    return or_list, 'query are not available. Try to paraphrase!'
        # known word from vocabulary
        elif index_collection.find({'word': query_word}).count() > 0:
            if query_word not in or_list:
                or_list.append(query_word)
        elif redis.exists(query_word):
            if query_word not in or_list:
                or_list.append(query_word)
        else:
            print('Error: Problem of query processing')

        if or_list:
            result_query += '('

            # support OR operation on similar words
            for word in or_list:
                result_query += word + '|'

                lock.acquire()
                if index_collection.find({'word': word}).count() > 0:
                    or_relevant_docs = union(or_relevant_docs, index_collection.find_one(
                        {'word': word})['songs'])
                if redis.exists(word):
                    or_relevant_docs = union(or_relevant_docs, redis_list(redis.get(word), False))
                lock.release()

            result_query = result_query[:-1] + ')&'

            if not relevant_documents:
                relevant_documents = or_relevant_docs
            else:
                # support AND operation on query words
                and_list = intersection(or_relevant_docs, relevant_documents)

                if and_list:
                    relevant_documents = and_list
                else:
                    return and_list, result_query[:-1]

    result_query = result_query[:-1]
    print('Query:', result_query)
    result_docs = [songs_collection.find_one({'_id': id}) for id in relevant_documents]
    return result_docs, result_query
