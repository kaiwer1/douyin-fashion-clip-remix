#!/usr/bin/env python3
"""
Pipeline runner - One-click full pipeline execution.

Processes raw clips through classifier -> composer -> renderer.
"""
import argparse
import json
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(BASE, "..", "src")
CLASSIFY = os.path.join(BASE, "classify.py")
COMPOSE = os.path.join(BASE, "compose.py")
RENDER = os.path.join(BASE, "render.py")


def run_step(script, args_list, desc, timeout=600):
    print("\n[Pipeline] ====== %s ======" % desc)
    cmd = ["python3", script] + args_list
    t0 = time.time()
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    elapsed = time.time() - t0
    print(result.stderr)
    if result.returncode != 0:
        print("[Pipeline] FAILED: %s (rc=%d, %.0fs)" % (desc, result.returncode, elapsed))
        print(result.stdout[-500:] if result.stdout else "")
        sys.exit(1)
    print("[Pipeline] Done: %s (%.0fs)" % (desc, elapsed))
    return result


def main():
    parser = argparse.ArgumentParser(description="Douyin fashion clip remix pipeline")
    parser.add_argument("--clips-dir", default="/tmp/clips",
                        help="Directory containing clip*.mp4 files")
    parser.add_argument("--variants", "-n", type=int, default=4,
                        help="Number of output variants (default: 4)")
    parser.add_argument("--skip-classify", action="store_true",
                        help="Skip classification (reuse existing segments.json)")
    parser.add_argument("--skip-compose", action="store_true",
                        help="Skip composition (reuse existing edls.json)")
    args = parser.parse_args()

    clips_dir = args.clips_dir
    segments_json = os.path.join(clips_dir, "segments.json")
    edls_json = os.path.join(clips_dir, "edls.json")
    output_dir = os.path.join(clips_dir, "output")

    # Check clips
    clips = sorted([
        os.path.join(clips_dir, f) for f in os.listdir(clips_dir)
        if f.startswith("clip") and f.endswith(".mp4")
    ])
    if not clips:
        print("[Pipeline] No clip*.mp4 found in %s" % clips_dir)
        sys.exit(1)
    print("[Pipeline] Found %d clips: %s" % (
        len(clips), ", ".join(os.path.basename(c) for c in clips)))

    # Step 1: Classify
    if not args.skip_classify:
        if os.path.exists(segments_json):
            os.remove(segments_json)
        run_step(CLASSIFY, clips + ["--interval", "5", "--output", segments_json],
                 "Frame classification (Doubao Vision API)")
    else:
        print("[Pipeline] Skipping classification")

    # Step 2: Compose
    if not args.skip_compose:
        run_step(COMPOSE, [segments_json, "--variants", str(args.variants),
                           "--output", edls_json, "--clips-dir", clips_dir],
                 "Three-act composition")
    else:
        print("[Pipeline] Skipping composition")

    # Step 3: Render
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    run_step(RENDER, [edls_json, "--output", output_dir], "Rendering")

    # Summary
    print("\n[Pipeline] %s" % ("=" * 50))
    print("[Pipeline] Complete!")
    for f in sorted(os.listdir(output_dir)):
        if f.endswith(".mp4"):
            path = os.path.join(output_dir, f)
            size_mb = os.path.getsize(path) / (1024 * 1024)
            print("[Pipeline]   %s (%.1fMB)" % (f, size_mb))
    print("[Pipeline] Output: %s" % output_dir)


if __name__ == "__main__":
    main()
