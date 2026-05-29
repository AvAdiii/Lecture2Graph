"""Download videos and extract media assets."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from lecture2graph.utils.youtube import get_video_id


def download_video(url: str, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    video_path = out_dir / "video.mp4"

    if video_path.exists():
        print(f"[ingest] using cached video: {video_path}")
        return video_path

    command = [
        sys.executable,
        "-m",
        "yt_dlp",
        "-f",
        "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--merge-output-format",
        "mp4",
        "-o",
        str(video_path),
        url,
    ]
    print(f"[ingest] downloading {url}")
    subprocess.run(command, check=True)
    return video_path


def extract_audio(video_path: Path, out_dir: Path) -> Path:
    audio_path = out_dir / "audio.wav"
    if audio_path.exists():
        print(f"[ingest] using cached audio: {audio_path}")
        return audio_path

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(audio_path),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return audio_path


def extract_frames(video_path: Path, out_dir: Path, fps: float = 1.0) -> Path:
    frames_dir = out_dir / "frames"
    if frames_dir.exists() and any(frames_dir.iterdir()):
        print(f"[ingest] using cached frames: {frames_dir}")
        return frames_dir

    frames_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vf",
            f"fps={fps}",
            "-q:v",
            "2",
            str(frames_dir / "frame_%05d.jpg"),
        ],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return frames_dir


def run(url: str, data_root: Path) -> dict:
    video_id = get_video_id(url)
    out_dir = data_root / video_id
    video_path = download_video(url, out_dir)
    audio_path = extract_audio(video_path, out_dir)
    frames_dir = extract_frames(video_path, out_dir)
    return {
        "video_id": video_id,
        "video_path": str(video_path),
        "audio_path": str(audio_path),
        "frames_dir": str(frames_dir),
        "data_dir": str(out_dir),
    }

