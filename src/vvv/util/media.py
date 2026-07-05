from __future__ import annotations
from dataclasses import dataclass, field
import json
import subprocess
from pathlib import Path
import os
import re
import urllib.request
import urllib.parse
from vvv.interfaces.source import SourceHandler
from vvv.registry import SOURCE_HANDLERS
from vvv.context import Context
from vvv.interfaces.source import SourceInfo

# Path to external tools
# TODO: Use config file
YTDLP = "yt-dlp"
FFPROBE = "ffprobe"
FFMPEG = "ffmpeg"

def probe_duration(filepath):
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-print_format", "json",
         "-show_format", str(filepath)],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed on {filepath}: {result.stderr}")
    info = json.loads(result.stdout)
    if "format" not in info or "duration" not in info.get("format", {}):
        raise RuntimeError(
            f"No duration for {filepath}. "
            f"format keys: {list(info.get('format', {}).keys())}. "
            f"Is this an image or a bad download?"
        )
    return float(info["format"]["duration"])

def download_video_media(url, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    ytcmd = [
        YTDLP,
        "--restrict-filenames",
        "--no-overwrites",
        "-o", f"{output_dir}/%(id)s.%(ext)s",
        "--print", "after_move:filepath",
    ]

    # dirty workaround trials in case it fails with some things. I force firefox cookies which is dumb and nasty for now but good enough for what is a tool none of you actually will use, lol
    attempts = [
        ytcmd + [url],
        ytcmd + ["--remote-components", "ejs:github", url],
        ytcmd + ["--cookies-from-browser", "firefox", url],
        ytcmd + ["--remote-components", "ejs:github", "--cookies-from-browser", "firefox", url],
    ]

    # TODO: you would want to find a way for the user the specify
    # download parameters (quality etc...) potentially in the DSL
    # How would you do that?
    errors = []
    for cmd in attempts:
        print("  $ " + " ".join(cmd), flush=True)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[-1]
        errors.append(result.stderr)

    raise RuntimeError(f"yt-dlp failed on {url}: {result.stderr} after {len(attempts)} attempts" + "\n\n - attempt error - \n".join(errors))

def is_image(url):
    #another one line function that might not deserve to live
    return re.search(r"\.(jpg|jpeg|png|gif|webp)$", url)

def is_url(path: str) -> bool:
       return bool(re.match(r"https?://", path))

def download_image_media(url: str, output_dir: str) -> str:
       Path(output_dir).mkdir(parents=True, exist_ok=True)
       filename = Path(urllib.parse.urlparse(url).path).name or "image"
       out_path = Path(output_dir) / filename

       # nasty workaround, sometimes without user agent you get 403'd
       req = urllib.request.Request(
               url,
                headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) "
                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                               "Chrome/120.0 Safari/537.36"},
        )
       with urllib.request.urlopen(req) as resp, open(out_path, "wb") as f:
           f.write(resp.read())
       return str(out_path)

def has_audio_stream(filepath: str | Path) -> bool:
    result = subprocess.run(
        [FFPROBE, "-v", "quiet", "-select_streams", "a",
         "-show_entries", "stream=index", "-of", "csv=p=0", str(filepath)],
        capture_output=True, text=True,
    )
    return bool(result.stdout.strip())

def has_video_stream(filepath: str | Path) -> bool:
    result = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v",
         "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(filepath)],
        capture_output=True, text=True,
    )
    return "video" in result.stdout

def concat(parts: list[Path], output: Path) -> Path:
    listfile = output.with_suffix(".txt")
    with open(listfile, "w") as f:
        for part in parts:
            f.write(f"file '{Path(part).resolve()}'\n")
    result = subprocess.run(
        [FFMPEG, "-f", "concat", "-safe", "0", "-i", str(listfile), "-c", "copy", "-y", str(output)],
        capture_output=True, text=True
    )
    listfile.unlink(missing_ok=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr}")
    return output

def resolve_media(source: str, ctx: Context) -> SourceInfo:
    source = str(source).strip()

    for handler in SOURCE_HANDLERS:
        if handler.handles(source):
            return handler.resolve(source, ctx)
    p = Path(source)
    if not p.is_absolute():
        p = Path(ctx.meta.assets_dir) / p
    if not p.exists():
        raise FileNotFoundError(f"Media not found: {p}")
    return SourceInfo(path=p.resolve())

def _ts_tag(seconds: float | None, default: str) -> str:
    if seconds is None:
        return default
    ms = int(round(float(seconds) * 1000))
    return f"{ms}ms"

def trim(media, from_s, to_s, output_dir):
    from pathlib import Path
    media_path = Path(media)
    if from_s is None and to_s is None:
        return media_path

    start_tag = _ts_tag(from_s, "start")
    end_tag = _ts_tag(to_s, "end")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out = output_dir / f"{media_path.stem}_seg_{start_tag}_{end_tag}{media_path.suffix}"
    
    # Dumb ''''''''''''''''''caching'''''''''''''''
    if out.exists():
        print(f"[trim] skip exists: {out}")
        return out

    cmd = ["ffmpeg", "-y", "-i", str(media_path)]
    if from_s is not None:
        cmd += ["-ss", str(from_s)]
    if to_s is not None:
        cmd += ["-t", str(to_s - (from_s or 0))]
    cmd += [str(out)]
    subprocess.run(cmd, check=True)
    return out
