import os
import re
import uuid
import shutil
import subprocess

# Ensure imageio_ffmpeg's bundled ffmpeg is on PATH
try:
    import imageio_ffmpeg
    _ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
    if _ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
    print(f"[INFO] ffmpeg available via imageio_ffmpeg: {imageio_ffmpeg.get_ffmpeg_exe()}")
except ImportError:
    print("[WARN] imageio_ffmpeg not installed; ffmpeg must be on PATH")


class VideoDownloader:
    def __init__(self, url):
        self.url = url
        self.video = None

    def sanitize_filename(self, name):
        base, ext = os.path.splitext(name)
        base = re.sub(r'[<>:"/\\|?*]', '', base)
        base = base.replace("...", "").replace("..", "").strip()
        base = str(uuid.uuid4())
        return base, ext

    def yt_download(self, path="downloads/"):
        os.makedirs(path, exist_ok=True)

        # Strategy 1: pytubefix with ANDROID client (progressive streams)
        try:
            import pytubefix as py
            yt = py.YouTube(self.url, client='ANDROID')
            print(f"[DOWNLOAD] pytubefix: Title = {yt.title}")

            # Try progressive stream first (audio+video combined)
            stream = yt.streams.get_highest_resolution()
            if stream:
                out_id = str(uuid.uuid4())
                file_path = stream.download(output_path=path, filename=f"{out_id}.mp4")
                print(f"[DOWNLOAD] Progressive stream saved: {file_path}")
                return out_id, ".mp4"

            # Fallback: download audio + video separately and mux with ffmpeg
            audio_stream = yt.streams.filter(only_audio=True).first()
            video_stream = yt.streams.filter(file_extension='mp4', only_video=True).first()

            if audio_stream and video_stream:
                out_id = str(uuid.uuid4())
                audio_path = audio_stream.download(output_path=path, filename=f"{out_id}_audio.mp4")
                video_path = video_stream.download(output_path=path, filename=f"{out_id}_video.mp4")

                merged_path = os.path.join(path, f"{out_id}.mp4")
                cmd = [
                    "ffmpeg", "-y",
                    "-i", video_path,
                    "-i", audio_path,
                    "-c:v", "copy", "-c:a", "aac",
                    "-shortest", merged_path
                ]
                subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                # Cleanup temp files
                try:
                    os.remove(audio_path)
                    os.remove(video_path)
                except OSError:
                    pass

                print(f"[DOWNLOAD] Muxed stream saved: {merged_path}")
                return out_id, ".mp4"

            # If only audio available (for transcript-only use)
            if audio_stream:
                out_id = str(uuid.uuid4())
                file_path = audio_stream.download(output_path=path, filename=f"{out_id}.mp4")
                print(f"[DOWNLOAD] Audio-only stream saved: {file_path}")
                return out_id, ".mp4"

            raise RuntimeError("No suitable streams found via pytubefix")

        except ImportError:
            print("[WARN] pytubefix not installed, trying yt_dlp...")
        except Exception as e:
            print(f"[WARN] pytubefix failed: {e}, trying yt_dlp...")

        # Strategy 2: yt_dlp fallback
        try:
            import yt_dlp
            out_id = str(uuid.uuid4())
            ydl_opts = {
                'outtmpl': os.path.join(path, f'{out_id}.%(ext)s'),
                'format': 'best',  # Don't restrict to mp4 - let yt_dlp pick best available
                'quiet': True,
                'no_warnings': True,
            }
            ydl = yt_dlp.YoutubeDL(ydl_opts)
            info = ydl.extract_info(self.url, download=True)
            ext = f".{info.get('ext', 'mp4')}"
            print(f"[DOWNLOAD] yt_dlp saved: {out_id}{ext}")
            return out_id, ext
        except ImportError:
            raise RuntimeError("Neither pytubefix nor yt_dlp is installed for video downloads.")
        except Exception as e:
            raise RuntimeError(f"yt_dlp also failed: {e}")


if __name__ == "__main__":
    tester = VideoDownloader("https://youtu.be/sample")
