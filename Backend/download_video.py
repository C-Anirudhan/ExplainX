import pytubefix as py
import os
import re
import uuid, shutil

class VideoDownloader:
    def __init__(self, url):
        self.url = url
        self.video = py.YouTube(url)
    def sanitize_filename(self,name):
        # Split filename into "base" and ".extension"
        base, ext = os.path.splitext(name)

        # Remove invalid Windows characters in the base name
        base = re.sub(r'[<>:"/\\|?*]', '', base)

        # Replace triple dots and double dots safely
        base = base.replace("...", "")
        base = base.replace("..", "")

        # Remove accidental spaces around
        base = base.strip()

        base = str(uuid.uuid4())

        # Reattach extension safely

        return base,ext
    
    def yt_download(self, path="downloads/"):

        stream = self.video.streams.get_highest_resolution()
        file_path = stream.download(output_path=path)

        original = os.path.basename(file_path)
        base,ext = self.sanitize_filename(original)

        clean = f"{base}{ext}"
        print(clean)
        # Rename only if needed
        if clean != original:
            new_path = os.path.join(path, clean)
            os.rename(file_path, new_path)
            file_path = new_path

        print(f"[DOWNLOAD] Saved as: {clean}")
        return base,ext




if __name__ == "__main__":
    tester = VideoDownloader("https://youtu.be/xLGUFFUS21w?si=Np5wciTq4FzY8REc")
    print(tester.yt_download())
