import pickle

from html_document import HtmlDocumentTextData


class Crawler:

    def crawl_generator(self, source, domain, checkpoints, root):
        urls = [source]
        old_urls = []

        try:
            with open(checkpoints, 'rb+') as filehandle:
                urls = pickle.load(filehandle)
                old_urls = pickle.load(filehandle)
                print('Checkpoint loaded')
        except Exception as e:
            print(f"{type(e).__name__}")

        i = 0
        for url in urls:
            if domain in url and '.php' not in url and 'artist-fans' not in url and url[-4:] not in (
                    '.pdf', '.mp3', '.avi', '.mp4', '.txt') and 'artists' not in url:
                print(f'Analyzing {url}')
                try:
                    doc = HtmlDocumentTextData(url, root)

                    for u in doc.doc.anchors:
                        if u[1] not in urls and u[1] not in old_urls:
                            urls.append(u[1])

                    yield doc
                except Exception as err:
                    print(f"Analyzing {url} led to {type(err).__name__}")
            else:
                print(f'Skipping not relevant resource: {url} ')

            if i % 100 == 0:
                with open(checkpoints, 'wb+') as filehandle:
                    pickle.dump(urls[i:], filehandle)
                    pickle.dump(old_urls, filehandle)
                    print(f'Made a checkpoint step {i}')

            i = i + 1
