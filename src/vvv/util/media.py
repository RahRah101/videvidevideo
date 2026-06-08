import json
import subprocess
from pathlib import Path
import os
import re
import urllib.request
import urllib.parse


# Path to external tools
# TODO: Use config file
YTDLP = "yt-dlp"
FFPROBE = "ffprobe"


def probe_duration(filepath):
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json",
         "-show_format", str(filepath)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {filepath}: {result.stderr}")
    info = json.loads(result.stdout)
    return float(info["format"]["duration"])
def download_video_media(url, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    # TODO: you would want to find a way for the user the specify
    # download parameters (quality etc...) potentially in the DSL
    # How would you do that?
    result = subprocess.run(
        [YTDLP, "--restrict-filenames", "--no-overwrites",
         "-o", f"{output_dir}/%(id)s.%(ext)s",
         "--print", "after_move:filepath",
         url],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp failed on {url}: {result.stderr}")
    #print final filepath
    return result.stdout.strip().split('\n')[-1]

def download_image_media(url, output_dir):
    #one line... seriously? Is this even needed as a function?
    #are you dumb?
    urllib.request.urlretrieve(url, output_dir)

def is_image(url):
    #another one line function that might not deserve to live
    return re.search(r"\.(jpg|jpeg|png|gif|webp)$", url)

def resolve_media(path, assets_dir, download_dir):
    """
    Resolve a media reference to a local filepath.
    - URLs -> download via urllib if bare image, otherwise download via yt-dlp
    - Relative paths -> prepend assets_dir
    - Absolute paths -> use as-is
    """
    path = str(path).strip()

    if is_url(path):
        if is_image(path):
            print(f"  [download] {path}")
            return download_image_media(path, download_dir)
        print(f"  [download] {path}")
        return download_video_media(path, download_dir)

    p = Path(path)
    if not p.is_absolute():
        p = Path(assets_dir) / p

    if not p.exists():
        raise FileNotFoundError(f"Media not found: {p}")

    return str(p.resolve())

def is_url(path: str) -> bool:
       return bool(re.match(r"https?://", path))

def download_image_media(url: str, output_dir: str) -> str:
       Path(output_dir).mkdir(parents=True, exist_ok=True)
       filename = Path(urllib.parse.urlparse(url).path).name or "image"
       out_path = Path(output_dir) / filename
       urllib.request.urlretrieve(url, str(out_path))
       return str(out_path)