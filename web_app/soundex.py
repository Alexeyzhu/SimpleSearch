import json
from typing import List

from bson import json_util
from pymongo import MongoClient
from redis import Redis
from redlock.lock import RedLock


def make_soundex_index(mongodb: MongoClient, redis: Redis, lock: RedLock):
    """ Build an index for collection of words:
    key - soundex code, value - coresponding word """
    search_db = mongodb['search']
    vocabulary = search_db['index'].distinct('word')

    return update_soundex_index(vocabulary, redis, lock)


def update_soundex_index(vocabulary: List, redis: Redis, lock: RedLock):
    for word in vocabulary:
        index = soundex(word)

        lock.acquire()
        if redis.exists(index):
            existent = redis_list(redis.get(index), False)
            existent.append(word)
            redis.set(index, redis_list(existent, True))
        else:
            redis.set(index, redis_list([word], True))
        lock.release()


def redis_list(l, dump: bool):
    if dump:
        return json.dumps(l, default=json_util.default)
    else:
        return json.loads(l, object_hook=json_util.object_hook)


def levenshtein_distance(s1, s2):
    if s1 == '':
        return len(s2)
    elif s2 == '':
        return len(s1)

    if s1[-1] == s2[-1]:
        cost = 0
    else:
        cost = 1

    dist = min([levenshtein_distance(s1[:-1], s2) + 1,
                levenshtein_distance(s1, s2[:-1]) + 1,
                levenshtein_distance(s1[:-1], s2[:-1]) + cost])

    return dist


def soundex(word):
    """ Soundex algorithm """
    word_list = [char.lower() for char in word if char.isalpha()]

    if len(word_list) == 1:
        return word_list[0] + '000'

    drop_list = ('a', 'e', 'i', 'o', 'u', 'y', 'h', 'w')

    first_letter = word_list[0]
    word_list = [c for c in word_list[1:] if c not in drop_list]

    replace_list = {'b': 1, 'f': 1, 'p': 1, 'v': 1,
                    'c': 2, 'g': 2, 'j': 2, 'k': 2, 'q': 2, 's': 2, 'x': 2, 'z': 2,
                    'd': 3, 't': 3, 'l': 4, 'm': 5, 'n': 5, 'r': 6}

    for i in range(len(word_list)):
        word_list[i] = str(replace_list[word_list[i]])

    word_list = list(dict.fromkeys(word_list))

    word_len = len(word_list)

    if word_len < 3:
        for i in range(3 - word_len):
            word_list.append('0')

    return first_letter + ''.join(word_list[:3])


def get_closest_words(initial, words):
    """ Get list of closest words based on levenshtein distance from initial word """
    result = []
    min_dist = 1000
    for word in words:
        d = levenshtein_distance(initial, word)
        if d < min_dist:
            result = [word]
            min_dist = d
        elif d == min_dist:
            result.append(word)

    return result
