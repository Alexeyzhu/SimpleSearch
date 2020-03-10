class Song:
    def __init__(self, title, artist, text, url):
        self.title = title
        self.artist = artist
        self.text = text
        self.url = url

    # def save(self, root):
    #     if isinstance(root, str):
    #         root = Path(root)
    #
    #     onlyfiles = [f for f in listdir(root) if isfile(join(root, f))]
    #     file_name = ''.join(normalize(self.title)) + ''.join(normalize(self.artist)) + '.data'
    #     if file_name not in onlyfiles:
    #         with open(root / Path(file_name), 'wb') as filehandle:
    #             pickle.dump([self.title, self.artist, self.text, self.url], filehandle)
    #             print(f'File {file_name} stored')
    #
    #     return len(onlyfiles)
    #
    # @staticmethod
    # def load_all_songs(root):
    #     if isinstance(root, str):
    #         root = Path(root)
    #
    #     songs = []
    #     onlyfiles = [f for f in listdir(root) if isfile(join(root, f))]
    #     for file_name in onlyfiles:
    #         with open(root / Path(file_name), 'rb') as filehandle:
    #             song_pick = pickle.load(filehandle)
    #             if song_pick[0] and song_pick[1]:
    #                 songs.append(Song(song_pick[0], song_pick[1], song_pick[2], song_pick[3]))
    #     return songs
    #
    # @staticmethod
    # def number_of_songs(root):
    #     if isinstance(root, str):
    #         root = Path(root)
    #
    #     return len([f for f in listdir(root) if isfile(join(root, f))])
