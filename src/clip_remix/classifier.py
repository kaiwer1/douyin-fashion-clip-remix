"""
Classifier module - Frame analysis using Doubao vision API.

Extracts frames from video clips at configurable intervals,
sends them to Doubao vision API, and classifies each frame as:
  - product_shot: Close-up product detail shots
  - outfit_demo: Model wearing the outfit
  - sales_pitch: Host selling to camera
  - transition: Scene transitions
  - other: Uncategorized
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
from typing import List, Tuple

from . import models
from . import utils


def get_video_info(video_path: str) -> dict:
    """Extract metadata from a video file using ffprobe."""
    ffprobe = utils.get_ffprobe_path()
    cmd = [ffprobe, "-v", "quiet", "-print_format", "json",
           "-show_format", "-show_streams", video_path]
    out = subprocess.check_output(cmd, timeout=30).decode()
    info = json.loads(out)
    video_stream = None
    for s in info.get("streams", []):
        if s["codec_type"] == "video" and video_stream is None:
            video_stream = s
    duration = float(info.get("format", {}).get("duration", 0))
    fps = eval(video_stream.get("r_frame_rate", "0/1")) if video_stream else 0
    width = int(video_stream.get("width", 0)) if video_stream else 0
    height = int(video_stream.get("height", 0)) if video_stream else 0
    return {
        "duration": duration, "fps": fps,
        "width": width, "height": height,
        "filename": os.path.basename(video_path)
    }


def extract_frames_at_interval(video_path: str, interval: int = 5,
                                frames_dir: str = None) -> List[Tuple[float, str]]:
    """Extract frames every N seconds. Returns list of (timestamp_sec, frame_path)."""
    info = get_video_info(video_path)
    duration = info["duration"]
    basename = os.path.splitext(os.path.basename(video_path))[0]
    ffmpeg = utils.get_ffmpeg_path()

    if frames_dir is None:
        frames_dir = os.path.join(utils.get_tmp_dir(), "frames")
    clip_frames_dir = os.path.join(frames_dir, basename)
    os.makedirs(clip_frames_dir, exist_ok=True)

    timestamps = list(range(0, int(duration), interval))
    frames = []

    for ts in timestamps:
        frame_path = os.path.join(clip_frames_dir, f"frame_{ts:03d}s.jpg")
        if os.path.exists(frame_path):
            frames.append((ts, frame_path))
            continue

        cmd = [ffmpeg, "-ss", str(ts), "-i", video_path,
               "-vframes", "1", "-qscale:v", "2", "-y", frame_path]
        subprocess.run(cmd, capture_output=True, timeout=60)
        if os.path.exists(frame_path) and os.path.getsize(frame_path) > 1000:
            frames.append((ts, frame_path))

    utils.log("分类", "提取了 %d 帧 (每%ds) 来自 %s" % (len(frames), interval, basename))
    return frames


def encode_image(image_path: str, max_size_kb: int = 400) -> str:
    """Read and base64 encode an image, compressing if too large."""
    with open(image_path, "rb") as f:
        data = f.read()
    if len(data) > max_size_kb * 1024:
        resized_path = image_path.replace(".jpg", "_resized.jpg")
        ffmpeg = utils.get_ffmpeg_path()
        subprocess.run(
            [ffmpeg, "-y", "-i", image_path,
             "-vf", "scale='min(600,iw)':'min(600,ih)':force_original_aspect_ratio=decrease",
             "-qscale:v", "3", resized_path],
            capture_output=True, timeout=30
        )
        if os.path.exists(resized_path):
            with open(resized_path, "rb") as f:
                data = f.read()
    return base64.b64encode(data).decode()


def classify_frames_batch(frames_batch: List[Tuple[float, str]],
                           clip_name: str) -> List[dict]:
    """Send a batch of frames (up to 6) to doubao vision for classification."""
    api_key = utils.get_doubao_api_key()
    base_url = utils.get_doubao_base_url()
    model = utils.get_doubao_model()

    timestamps = [t for t, _ in frames_batch]
    content = [{
        "type": "text",
        "text": (
            "You are a fashion live-commerce video analysis assistant. "
            "Below are sequential frames extracted from one video clip.\n\n"
            "Classify each frame by type:\n"
            "- product_shot: Close-up product detail — fabric texture, collar/cuff detail, "
            "hand-held garment display (not worn by model)\n"
            "- outfit_demo: Model wearing the outfit — full-body or half-body outfit display\n"
            "- sales_pitch: Host talking to camera, making sales gestures, urging purchase\n"
            "- transition: Scene change, mid-shot transition\n"
            "- other: Anything else\n\n"
            "Clip name: %s\n"
            "Frame timestamps (seconds): %s\n\n"
            "Output JSON array only, no other text:\n"
            '[\n'
            '  {"timestamp": 0, "label": "product_shot", "confidence": 0.95},\n'
            '  {"timestamp": 5, "label": "outfit_demo", "confidence": 0.90}\n'
            ']\n\n'
            "Rules:\n"
            "- If a frame has multiple elements, choose the dominant one\n"
            "- confidence 0-1\n"
            "- Output ONLY valid JSON, no commentary\n"
            "- Look carefully at actual image content, do not guess"
        ) % (clip_name, timestamps)
    }]

    frame_count = 0
    for ts, fp in frames_batch:
        try:
            img_b64 = encode_image(fp)
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}
            })
            frame_count += 1
        except Exception as e:
            utils.log("分类", "跳过帧 %s: %s" % (fp, e))

    import urllib.request
    import urllib.error

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "max_tokens": 2048,
        "temperature": 0.1
    }

    req_data = json.dumps(payload).encode()
    headers = {
        "Authorization": "Bearer %s" % api_key,
        "Content-Type": "application/json"
    }

    try:
        req = urllib.request.Request(
            "%s/chat/completions" % base_url,
            data=req_data, headers=headers, method="POST"
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read())
            result = data["choices"][0]["message"]["content"]
            usage = data.get("usage", {})
            utils.log("分类", "Batch %ss~%ss: tokens入%s 出%s" % (
                frames_batch[0][0], frames_batch[-1][0],
                usage.get("prompt_tokens", "?"),
                usage.get("completion_tokens", "?")))

            json_match = re.search(r'\[\s*\{.*\}\]', result, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                for item in parsed:
                    if "timestamp" not in item or "label" not in item:
                        raise ValueError("Missing fields in: %s" % item)
                return parsed
            else:
                try:
                    return json.loads(result)
                except Exception:
                    utils.log("分类", "无法解析响应: %s..." % result[:200])
                    return [{"timestamp": t, "label": "transition", "confidence": 0.3}
                            for t in timestamps]

    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        if e.code == 429:
            if "RequestBurstTooFast" in error_body:
                utils.log("分类", "RequestBurstTooFast, 退避重试...")
                retry_delays = [5, 10, 20, 40]
                for attempt, delay in enumerate(retry_delays, 1):
                    time.sleep(delay)
                    try:
                        retry_req = urllib.request.Request(
                            "%s/chat/completions" % base_url,
                            data=req_data, headers=headers, method="POST"
                        )
                        with urllib.request.urlopen(retry_req, timeout=120) as retry_resp:
                            retry_data = json.loads(retry_resp.read())
                            retry_result = retry_data["choices"][0]["message"]["content"]
                            json_match = re.search(r'\[\s*\{.*\}\]', retry_result, re.DOTALL)
                            if json_match:
                                utils.log("分类", "重试%d成功 (%ds后)" % (attempt, delay))
                                return json.loads(json_match.group())
                    except urllib.error.HTTPError as retry_e:
                        if "RequestBurstTooFast" not in retry_e.read().decode():
                            break
                        utils.log("分类", "重试%d仍429" % attempt)
                    except Exception:
                        if attempt == len(retry_delays):
                            break
                        continue
            else:
                utils.log("分类", "SetLimitExceeded (Safe Experience Mode): %s" % error_body[:200])
        else:
            utils.log("分类", "视觉API错误 (HTTP %d): %s" % (e.code, error_body[:200]))
        return [{"timestamp": t, "label": "transition", "confidence": 0.25}
                for t in timestamps]
    except Exception as e:
        utils.log("分类", "请求异常: %s" % e)
        return [{"timestamp": t, "label": "transition", "confidence": 0.3}
                for t in timestamps]


def merge_segments(frame_labels: List[dict], interval: int = 5) -> List[dict]:
    """
    Merge consecutive frames with same label into continuous segments.
    Steps:
      1. Smooth isolated single-frame outliers
      2. Merge consecutive same-label frames
      3. Merge adjacent same-type segments
    """
    if not frame_labels:
        return []

    frame_labels.sort(key=lambda x: x["timestamp"])

    if len(frame_labels) > 1:
        interval = frame_labels[1]["timestamp"] - frame_labels[0]["timestamp"]

    # Step 1: Smooth isolated outliers
    smoothed = list(frame_labels)
    for i in range(1, len(smoothed) - 1):
        prev_lbl = smoothed[i-1]["label"]
        curr_lbl = smoothed[i]["label"]
        next_lbl = smoothed[i+1]["label"]
        if curr_lbl != prev_lbl and curr_lbl != next_lbl and prev_lbl == next_lbl:
            smoothed[i]["label"] = prev_lbl
            smoothed[i]["confidence"] = min(
                smoothed[i]["confidence"],
                smoothed[i-1]["confidence"],
                smoothed[i+1]["confidence"]
            )

    # Step 2: Merge consecutive same-label frames
    segments = []
    cur_type = smoothed[0]["label"]
    cur_start = smoothed[0]["timestamp"]
    cur_end = cur_start
    confs = [smoothed[0]["confidence"]]

    for item in smoothed[1:]:
        if item["label"] == cur_type:
            cur_end = item["timestamp"]
            confs.append(item["confidence"])
        else:
            seg_end = cur_end + interval
            if seg_end - cur_start >= 3:
                segments.append({
                    "type": cur_type,
                    "start": cur_start,
                    "end": seg_end,
                    "confidence": round(sum(confs) / len(confs), 3)
                })
            cur_type = item["label"]
            cur_start = item["timestamp"]
            cur_end = item["timestamp"]
            confs = [item["confidence"]]

    # Close last segment
    seg_end = cur_end + interval
    if seg_end - cur_start >= 3:
        segments.append({
            "type": cur_type,
            "start": cur_start,
            "end": seg_end,
            "confidence": round(sum(confs) / len(confs), 3)
        })

    # Step 3: Merge adjacent same-type segments
    merged = []
    for seg in segments:
        if merged and merged[-1]["type"] == seg["type"]:
            merged[-1]["end"] = max(merged[-1]["end"], seg["end"])
            merged[-1]["confidence"] = round(
                (merged[-1]["confidence"] + seg["confidence"]) / 2, 3
            )
        else:
            merged.append(seg)

    return merged


def classify_clip(video_path: str, output_path: str = None,
                   interval: int = 5) -> dict:
    """Classify a single video clip."""
    basename = os.path.basename(video_path)
    utils.log("分类", "分析: %s" % basename)

    frames_dir = os.path.join(utils.get_tmp_dir(), "frames")
    frames = extract_frames_at_interval(video_path, interval, frames_dir)
    if not frames:
        utils.log("分类", "未提取到帧，跳过")
        return {"filename": basename, "segments": [], "error": "no frames"}

    all_labels = []
    batch_size = 6
    clip_name = os.path.splitext(basename)[0]

    for i in range(0, len(frames), batch_size):
        batch = frames[i:i+batch_size]
        labels = classify_frames_batch(batch, clip_name)
        all_labels.extend(labels)
        if i + batch_size < len(frames):
            time.sleep(2.0)

    segments = merge_segments(all_labels)
    utils.log("分类", "得到 %d 个片段: %s" % (
        len(segments),
        ", ".join("%s(%ss-%ss)" % (s["type"], s["start"], s["end"]) for s in segments)
    ))

    result = {
        "filename": basename,
        "path": video_path,
        "video_info": get_video_info(video_path),
        "segments": segments,
        "frame_labels": all_labels
    }

    if output_path:
        existing = []
        if os.path.exists(output_path):
            with open(output_path) as f:
                existing = json.load(f)
            existing = existing if isinstance(existing, list) else []
        existing = [e for e in existing if e.get("filename") != result["filename"]]
        existing.append(result)
        with open(output_path, "w") as f:
            json.dump(existing, f, ensure_ascii=False, indent=2)
        utils.log("分类", "结果已保存到 %s" % output_path)

    return result


def main():
    parser = argparse.ArgumentParser(description="Classify video frames by type")
    parser.add_argument("videos", nargs="+", help="Video file paths")
    parser.add_argument("--interval", type=int, default=5,
                        help="Frame interval in seconds (default: 5)")
    parser.add_argument("--output", default=os.path.join(utils.get_tmp_dir(), "segments.json"),
                        help="Output JSON path (default: $CLIP_REMIX_TMP/segments.json)")
    args = parser.parse_args()

    os.makedirs(os.path.join(utils.get_tmp_dir(), "frames"), exist_ok=True)

    all_results = []
    for vpath in args.videos:
        if not os.path.exists(vpath):
            utils.log("分类", "文件不存在: %s" % vpath)
            continue
        result = classify_clip(vpath, output_path=args.output, interval=args.interval)
        all_results.append(result)

    print("\n" + "=" * 60, file=sys.stderr)
    utils.log("分类", "完成! %d 个视频" % len(all_results))
    for r in all_results:
        segs = r.get("segments", [])
        if segs:
            types = {}
            for s in segs:
                types[s["type"]] = types.get(s["type"], 0) + 1
            type_strs = ["%sx%s" % (k, v) for k, v in types.items()]
            utils.log("分类", "  %s: %s" % (r["filename"], ", ".join(type_strs)))
    utils.log("分类", "结果保存: %s" % args.output)


if __name__ == "__main__":
    main()
