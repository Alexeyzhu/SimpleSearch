import string
from collections import defaultdict

import nltk
import unidecode
from nltk import pos_tag
from nltk.corpus import stopwords
from nltk.corpus import wordnet as wn
from nltk.stem.wordnet import WordNetLemmatizer

nltk.download('punkt', quiet=True)
nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('averaged_perceptron_tagger', quiet=True)


# normilize text
def normalize(text):
    unaccented_string = unidecode.unidecode(text)
    removed_punctuation = " ".join(
        [word.lower() for word in unaccented_string.translate(str.maketrans('', '', string.punctuation)).split() if
         word.isalpha()])
    return removed_punctuation


# tokenize text using nltk lib
def tokenize(text):
    return nltk.word_tokenize(text)


def remove_stop_word(tokens):
    return [word for word in tokens if word not in stopwords.words('english')]


def lemmatization(tokens):
    tag_map = defaultdict(lambda: wn.NOUN)
    tag_map['J'] = wn.ADJ
    tag_map['V'] = wn.VERB
    tag_map['R'] = wn.ADV

    lemmatizer = WordNetLemmatizer()
    return [lemmatizer.lemmatize(token, tag_map[tag[0]]) for token, tag in pos_tag(tokens)]


def preprocess(text):
    text = normalize(text)
    tokens = tokenize(text)
    lemmed = lemmatization(tokens)
    clean = remove_stop_word(lemmed)
    return clean
