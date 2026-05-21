"""
Utility functions for the clip-remix pipeline.
"""

import os
import sys


def get_env_or(key: str, default: str) -> str:
    """Get an environment variable, falling back to a default."""
    return os.environ.get(key, default)


def get_ffmpeg_path() -> str:
    """Get ffmpeg path from env FFMPEG_PATH or fallback to system ffmpeg."""
    return get_env_or("FFMPEG_PATH", "ffmpeg")


def get_ffprobe_path() -> str:
    """Get ffprobe path from env FFPROBE_PATH or fallback to system ffprobe."""
    return get_env_or("FFPROBE_PATH", "ffprobe")


def get_tmp_dir() -> str:
    """Get working directory from env CLIP_REMIX_TMP or fallback."""
    return get_env_or("CLIP_REMIX_TMP", "/tmp/clip-remix")


def get_doubao_api_key() -> str:
    """Get Doubao vision API key from environment variable."""
    api_key = os.environ.get("DOUBAO_API_KEY", "")
    if not api_key:
        print("[ERROR] DOUBAO_API_KEY environment variable not set.", file=sys.stderr)
        print("[ERROR] Get your API key from: https://console.volcengine.com/ark/", file=sys.stderr)
        sys.exit(1)
    return api_key


def get_doubao_base_url() -> str:
    """Get Doubao API base URL."""
    return get_env_or(
        "DOUBAO_BASE_URL",
        "https://ark.cn-beijing.volces.com/api/v3"
    )


def get_doubao_model() -> str:
    """Get Doubao vision model name."""
    return get_env_or(
        "DOUBAO_MODEL",
        "doubao-seed-1-6-vision-250815"
    )


def log(tag: str, msg: str):
    """Print a tagged log message to stderr."""
    print("[%s] %s" % (tag, msg), file=sys.stderr)
