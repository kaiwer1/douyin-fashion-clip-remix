"""
Renderer module - FFmpeg-based video rendering from EDLs.

Takes composed EDLs (Edit Decision Lists), cuts segments from source
videos with loudness normalization, and concatenates them into final
output videos.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time


def log(msg: str):
    print("[render] %s" % msg, file=sys.stderr)


def run_cmd(cmd: list, timeout: int = 300) -> tuple:
    """Run a shell command and return (stdout, stderr, returncode)."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout, r.stderr, r.returncode
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT", -1


def cut_segment(source_file: str, start: float, end: float,
                 output_path: str) -> bool:
    """
    Cut a segment from source video with EBU R128 loudness normalization.
    Dual-pass: measure first, then apply with precise parameters.
    """
    from . import utils as ut
    ffmpeg = ut.get_ffmpeg_path()

    duration = end - start
    temp_log_base = os.path.splitext(output_path)[0]

    # First pass: measure loudness (audio only, faster)
    cmd_measure = [
        ffmpeg, "-ss", str(start), "-i", source_file,
        "-t", str(duration),
        "-vn",
        "-af", "loudnorm=I=-16:LRA=11:TP=-1.5:print_format=json",
        "-f", "null", "-",
    ]
    _, err, _ = run_cmd(cmd_measure, timeout=120)

    # Parse measured parameters from stderr
    loud_json = None
    lines = err.split("\n")
    for i, line in enumerate(lines):
        if "{" in line and '"input_i"' in line:
            json_text = line
            for j in range(i + 1, min(i + 20, len(lines))):
                json_text += "\n" + lines[j]
                if "}" in lines[j]:
                    break
            try:
                loud_json = json.loads(json_text)
            except Exception:
                pass
            break

    # Build audio filter
    if loud_json and "input_i" in loud_json:
        measured = {
            "input_i": loud_json.get("input_i", "-16"),
            "input_lra": loud_json.get("input_lra", "11"),
            "input_tp": loud_json.get("input_tp", "-1.5"),
            "input_thresh": loud_json.get("input_thresh", "-21"),
            "target_offset": loud_json.get("target_offset", "0"),
        }
        af_filter = (
            "loudnorm=I=-16:LRA=11:TP=-1.5:"
            "measured_I=%(input_i)s:measured_LRA=%(input_lra)s:"
            "measured_TP=%(input_tp)s:measured_thresh=%(input_thresh)s:"
            "offset=%(target_offset)s:print_format=summary"
        ) % measured
    else:
        af_filter = "loudnorm=I=-16:LRA=11:TP=-1.5"

    # Second pass: cut + normalize
    cmd = [
        ffmpeg, "-ss", str(start), "-i", source_file,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "22",
        "-af", af_filter,
        "-c:a", "aac", "-b:a", "128k",
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
               "pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black",
        "-pix_fmt", "yuv420p",
        "-y", output_path
    ]
    _, _, rc = run_cmd(cmd, timeout=120)
    return rc == 0 and os.path.exists(output_path) and os.path.getsize(output_path) > 10000


def render_variant(variant: dict, output_dir: str) -> str:
    """Render a single variant EDL into a video file."""
    vid = variant["id"]
    segments = variant["segments"]

    log("%s: rendering (%d segments, %.0fs total)" % (
        vid, len(segments), variant["total_duration"]))

    # Cut each segment
    intermediates = []
    for i, seg in enumerate(segments):
        source = seg["source_file"]
        if not os.path.exists(source):
            alt = os.path.join(output_dir, "..", os.path.basename(source))
            if os.path.exists(alt):
                source = alt
            else:
                log("  Source not found: %s" % source)
                return None

        out_seg = os.path.join(output_dir, "%s_seg%02d.mp4" % (vid, i))
        success = cut_segment(source, seg["start"], seg["end"], out_seg)
        if not success:
            log("  Cut failed: seg%d (%s %ss-%ss)" % (
                i, source, seg["start"], seg["end"]))
            return None
        log("  seg%d: %s %ss-%ss -> %.0fs OK" % (
            i, seg["source_clip"], seg["start"], seg["end"], seg["duration"]))
        intermediates.append(out_seg)

    if len(segments) == 1:
        output_path = os.path.join(output_dir, "%s.mp4" % vid)
        os.rename(intermediates[0], output_path)
        return output_path

    # Concatenate segments
    n = len(segments)
    stream_parts = []
    for i in range(n):
        stream_parts.append("[%d:v][%d:a]" % (i, i))
    filter_expr = "%s concat=n=%d:v=1:a=1[out]" % ("".join(stream_parts), n)

    from . import utils as ut
    ffmpeg = ut.get_ffmpeg_path()

    cmd = [ffmpeg]
    for seg_path in intermediates:
        cmd.extend(["-i", seg_path])
    cmd.extend([
        "-filter_complex", filter_expr,
        "-map", "[out]",
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "22",
        "-c:a", "aac",
        "-b:a", "128k",
        "-y", os.path.join(output_dir, "%s.mp4" % vid),
    ])

    output_path = os.path.join(output_dir, "%s.mp4" % vid)
    log("  Concatenating...")
    _, err, rc = run_cmd(cmd, timeout=600)
    if rc != 0 or not os.path.exists(output_path):
        log("  Concatenation failed: %s" % err[-200:])
        return None

    file_size = os.path.getsize(output_path) / (1024 * 1024)
    log("  Done: %s (%.0fs, %.1fMB)" % (output_path, variant["total_duration"], file_size))

    # Cleanup intermediates
    for seg_path in intermediates:
        if os.path.exists(seg_path):
            os.remove(seg_path)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Render video from EDLs")
    parser.add_argument("edl_json", nargs="?",
                        default=os.path.join(utils.get_tmp_dir(), "edls.json"))
    parser.add_argument("--output", "-o", default=os.path.join(utils.get_tmp_dir(), "output"),
                        help="Output directory")
    args = parser.parse_args()

    if not os.path.exists(args.edl_json):
        log("Error: %s not found" % args.edl_json)
        sys.exit(1)

    with open(args.edl_json) as f:
        data = json.load(f)

    variants = data.get("variants", [])
    if not variants:
        log("Error: no variants data")
        sys.exit(1)

    os.makedirs(args.output, exist_ok=True)

    results = []
    for vi, variant in enumerate(variants):
        result = render_variant(variant, args.output)
        if result:
            results.append(result)
        if vi < len(variants) - 1:
            time.sleep(1)

    if results:
        log("\n=== Done! %d/%d variants rendered ===" % (len(results), len(variants)))
        for r in results:
            size_mb = os.path.getsize(r) / (1024 * 1024)
            log("  %s (%.1fMB)" % (r, size_mb))
    else:
        log("\nAll variants failed")

    return results


if __name__ == "__main__":
    from . import utils
    main()
