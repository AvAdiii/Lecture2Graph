"""
module 1 - data ingestion & preprocessing
downloads a youtube video, extracts audio, and pulls keyframes
"""

import os
import subprocess
import argparse
import re
from pathlib import Path

# yt-dlp lives in the venv — check approach_1/venv first, then parent venv
_HERE = Path(__file__).resolve().parent
_BIN = _HERE / "venv" / "bin"
if not _BIN.exists():
    _BIN = _HERE.parent / "venv" / "bin"


def get_video_id(url: str) -> str:
    match = re.search(r'(?:v=|youtu\.be/|shorts/)([a-zA-Z0-9_-]{11})', url)
    if not match:
        raise ValueError(f"could not parse video id from url: {url}")
    return match.group(1)


def download_video(url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = out_dir / "video.mp4"

    if video_path.exists():
        print(f"[m1] video already exists, skipping download: {video_path}")
        return video_path

    print(f"[m1] downloading video: {url}")
    cmd = [
        str(_BIN / "yt-dlp"),
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format", "mp4",
        "-o", str(video_path),
        url,
    ]
    subprocess.run(cmd, check=True)
    print(f"[m1] video saved to: {video_path}")
    return video_path


def extract_audio(video_path: Path, out_dir: Path) -> Path:
    audio_path = out_dir / "audio.wav"

    if audio_path.exists():
        print(f"[m1] audio already exists, skipping: {audio_path}")
        return audio_path

    print(f"[m1] extracting audio from: {video_path}")
    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        str(audio_path),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"[m1] audio saved to: {audio_path}")
    return audio_path


def extract_keyframes(video_path: Path, out_dir: Path, fps: float = 1.0) -> Path:
    frames_dir = out_dir / "frames"

    if frames_dir.exists() and any(frames_dir.iterdir()):
        print(f"[m1] frames already exist, skipping: {frames_dir}")
        return frames_dir

    frames_dir.mkdir(parents=True, exist_ok=True)
    print(f"[m1] extracting frames at {fps}fps")

    cmd = [
        "ffmpeg", "-y",
        "-i", str(video_path),
        "-vf", f"fps={fps}",
        "-q:v", "2",
        str(frames_dir / "frame_%05d.jpg"),
    ]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    n = len(list(frames_dir.glob("*.jpg")))
    print(f"[m1] extracted {n} frames to: {frames_dir}")
    return frames_dir


def run(url: str, data_root: str = "data") -> dict:
    video_id = get_video_id(url)
    out_dir = Path(data_root) / video_id

    video_path = download_video(url, out_dir)
    audio_path = extract_audio(video_path, out_dir)
    frames_dir = extract_keyframes(video_path, out_dir, fps=1.0)

    return {
        "video_id": video_id,
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "frames_dir": str(frames_dir),
        "n_frames": len(list(frames_dir.glob("*.jpg"))),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("url", help="youtube video url")
    parser.add_argument("--data-root", default="data")
    args = parser.parse_args()
    print(run(args.url, args.data_root))
