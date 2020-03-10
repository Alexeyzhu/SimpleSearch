import urllib.parse
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
from song import Song


class Document:
    def __init__(self, url, root):
        self.url = url
        self.root = root
        self.processed_url = Path(quote(self.url).replace('/', '='))

    def get(self):
        if not self.load():
            if not self.download():
                raise FileNotFoundError(self.url)
            else:
                self.persist()

    def download(self):
        r = requests.get(self.url)
        if r.status_code is 200:
            self.content = r.text
            return True
        return False

    def persist(self):
        root = Path(self.root)
        root.mkdir(parents=True, exist_ok=True)
        path = root / self.processed_url
        with path.open(mode='w', encoding='utf-8') as url_file:
            url_file.write(self.content)
            url_file.close()

    def load(self):
        root = Path(self.root)
        root.mkdir(parents=True, exist_ok=True)
        path = root / self.processed_url
        try:
            f = path.open(mode='r', encoding='utf-8')
            self.content = f.read()
            f.close()
            return True
        except IOError:
            return False


class HtmlDocument(Document):

    def parse(self):
        soup = BeautifulSoup(self.content, 'html.parser')
        self.anchors = self.anchors_from_html(soup)
        self.song = self.song_from_html(soup)

    def tag_visible(self, element):
        if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
            return False
        if isinstance(element, Comment):
            return False
        return True

    def song_from_html(self, soup):
        song_title, song_artist, song_text = None, None, None
        song_titles = soup.select('h1.lyric-title')
        visible_song_titles = filter(self.tag_visible, song_titles)
        for h1 in visible_song_titles:
            song_title = h1.text.strip()

        song_artists = soup.select('h3.lyric-artist')
        visible_song_artists = filter(self.tag_visible, song_artists)
        for h3 in visible_song_artists:
            a_href = h3.find('a')['href']
            if 'artist' in a_href:
                song_artist = h3.select('a')[0].text.strip()

        song_texts = soup.select('pre.lyric-body')
        visible_song_text = filter(self.tag_visible, song_texts)
        for pre in visible_song_text:
            song_text = pre.text

        if song_title is not None and song_artist is not None and song_text is not None:
            return Song(song_title, song_artist, song_text, self.url)

        return None

    def anchors_from_html(self, soup):
        links = soup.find_all('a')
        anchors = [(link.text, urllib.parse.urljoin(self.url, link.get('href'))) for link in links]
        return anchors


class HtmlDocumentTextData:

    def __init__(self, url, root):
        self.doc = HtmlDocument(url, root)
        self.doc.get()
        self.doc.parse()
