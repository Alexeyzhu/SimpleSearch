from typing import Tuple, List

from pymongo import MongoClient


class TrieNode(object):

    def __init__(self, char: str):
        self.char = char
        self.children = []
        self.word_finished = False
        self.words = []


def add(root: TrieNode, word: str):
    """ Add word to prefix tree """
    node = root
    for char in word:
        found_in_child = False
        for child in node.children:
            if child.char == char:
                node = child
                if word not in node.words:
                    node.words.append(word)
                found_in_child = True
                break
        if not found_in_child:
            new_node = TrieNode(char)
            node.children.append(new_node)
            node = new_node
            if word not in node.words:
                node.words.append(word)
    node.word_finished = True


def find_prefix(root, prefix: str) -> Tuple[bool, List[str]]:
    """ Find prefix in prefix tree """
    node = root

    if not root.children:
        return node.word_finished, node.words
    for char in prefix:
        char_not_found = True
        for child in node.children:
            if child.char == char:
                char_not_found = False
                node = child
                break
        if char_not_found:
            return False, []

    return node.word_finished, node.words


def build_search_trie(mongodb: MongoClient, root: TrieNode) -> TrieNode:
    """ Build prefix tree using vocabulary """
    search_db = mongodb['search']
    vocabulary = search_db['index'].distinct('word')

    return update_search_trie(vocabulary, root)


def update_search_trie(vocabulary: List, root: TrieNode) -> TrieNode:
    for word in vocabulary:
        word = word + '$'
        for p in get_permutes(word):
            add(root, p)

    return root


def get_permutes(word):
    """ Get all rotations of the word """
    permutation = []
    for i in range(len(word)):
        permutation.append(word)
        word = word[1:] + word[0]
    return permutation


def remove_terminal(word):
    """ Rotate word so terminal symbol appear at the end """
    word = word.split('$')
    if len(word) < 2:
        return word[0]
    return word[1] + word[0]


def rotate_star(word):
    """ Rotate word so wildcard symbol appear at the end"""
    while word[-1] != '*':
        word = word[1:] + word[0]
    return word


def wildcard_handler(word: str, trie: TrieNode):
    """ Handles wildcard operations on a word """
    word = word + '$'
    prefix = rotate_star(word)[:-1]
    _, result = find_prefix(trie, prefix)

    for i in range(len(result)):
        result[i] = remove_terminal(result[i])

    return result
