"""
Composer module - Three-act template composition from classified segments.

Takes classified segments from the classifier, groups them by type,
and composes multiple variants using a three-act template:
  1. Product shot segment(s)   [10-20s]
  2. Outfit demo segment(s)    [10-20s]
  3. Sales pitch segment       [0-10s]
"""

import argparse
import json
import os
import random
import sys
from typing import List, Dict, Set, Optional


def log(msg: str):
    print("[compose] %s" % msg, file=sys.stderr)


def build_segment_pool(data: List[dict], clips_dir: str = None) -> Dict[str, list]:
    """Group segments by type, filtering minimum duration."""
    pool = {"product_shot": [], "outfit_demo": [], "sales_pitch": []}
    if clips_dir is None:
        clips_dir = "/tmp/clips"

    for item in data:
        clip_name = os.path.splitext(item["filename"])[0]
        clip_path = item.get("path", "")
        if not clip_path or not os.path.exists(clip_path):
            # Try resolving relative to clips_dir
            alt = os.path.join(clips_dir, item["filename"])
            if os.path.exists(alt):
                clip_path = alt
            else:
                clip_path = os.path.join(clips_dir, item["filename"])

        for seg in item.get("segments", []):
            stype = seg["type"]
            if stype not in pool:
                continue
            d = {
                "type": stype,
                "source_clip": clip_name,
                "source_file": clip_path,
                "start": seg["start"],
                "end": seg["end"],
                "duration": seg["end"] - seg["start"],
                "confidence": seg.get("confidence", 0.5),
            }
            if d["duration"] >= 4:
                pool[stype].append(d)
    return pool


def pick_segments(pool: dict, stype: str, min_dur: int, max_dur: int,
                   used_clips: Set[str],
                   allow_dup_clips: bool = False) -> tuple:
    """
    Pick 1-2 segments from pool[stype] to fit [min_dur, max_dur].
    Returns (picked_segments, total_duration).
    """
    available = [s for s in pool.get(stype, [])
                 if (allow_dup_clips or s["source_clip"] not in used_clips)]

    if not available:
        return [], 0

    available.sort(key=lambda x: x["confidence"], reverse=True)
    top_n = available[:min(6, len(available))]

    best_combo = None
    best_total = 0

    # Try single segment first
    for s in top_n:
        dur = min(s["duration"], max_dur)
        if min_dur <= dur <= max_dur:
            if best_combo is None or abs(dur - (min_dur + max_dur) / 2) < abs(
                    best_total - (min_dur + max_dur) / 2):
                best_combo = [s.copy()]
                best_combo[0]["duration"] = dur
                best_combo[0]["end"] = s["start"] + dur
                best_total = dur
                break

    # Try two segments
    if best_combo is None:
        for i, s1 in enumerate(top_n):
            for j, s2 in enumerate(top_n):
                if i >= j or s1["source_clip"] == s2["source_clip"]:
                    continue
                dur = min(s1["duration"], 15) + min(s2["duration"], 10)
                if min_dur <= dur <= max_dur:
                    combo = [s1.copy(), s2.copy()]
                    combo[0]["duration"] = min(s1["duration"], 15)
                    combo[0]["end"] = s1["start"] + combo[0]["duration"]
                    combo[1]["duration"] = min(s2["duration"], 10)
                    combo[1]["end"] = s2["start"] + combo[1]["duration"]
                    if best_combo is None or abs(dur - (min_dur + max_dur) / 2) < abs(
                            best_total - (min_dur + max_dur) / 2):
                        best_combo = combo
                        best_total = dur

    # Fallback: best single
    if best_combo is None and available:
        s = available[0]
        dur = min(s["duration"], max_dur)
        best_combo = [s.copy()]
        best_combo[0]["duration"] = dur
        best_combo[0]["end"] = s["start"] + dur
        best_total = dur

    if best_combo:
        for s in best_combo:
            used_clips.add(s["source_clip"])
        for s in best_combo:
            s["duration"] = s["end"] - s["start"]
        return best_combo, sum(s["duration"] for s in best_combo)

    return [], 0


def compose_variants(pool: dict, n_variants: int = 4,
                     dedup: bool = False) -> List[dict]:
    """Generate n_variants different compositions using three-act template."""
    variants = []
    used_across_variants = set()

    for vi in range(n_variants):
        rng = random.Random(42 + vi * 7)

        # Remove already-used segments
        for stype in pool:
            pool[stype] = [s for s in pool[stype]
                           if (s["source_clip"], s["start"]) not in used_across_variants]

        for stype in pool:
            rng.shuffle(pool[stype])

        used_clips = set()
        strategy = vi % 3

        if strategy == 0:
            prod_picks, prod_total = pick_segments(pool, "product_shot", 15, 25, used_clips)
            outfit_picks, outfit_total = pick_segments(pool, "outfit_demo", 15, 25, used_clips)
            sales_picks, sales_total = pick_segments(pool, "sales_pitch", 8, 15, used_clips)
        elif strategy == 1:
            outfit_picks, outfit_total = pick_segments(pool, "outfit_demo", 15, 25, used_clips)
            prod_picks, prod_total = pick_segments(pool, "product_shot", 15, 25, used_clips)
            sales_picks, sales_total = pick_segments(pool, "sales_pitch", 8, 15, used_clips)
        else:
            prod_picks, prod_total = pick_segments(pool, "product_shot", 15, 25, used_clips,
                                                    allow_dup_clips=True)
            sales_picks, sales_total = pick_segments(pool, "sales_pitch", 8, 15, used_clips)
            used_clips.clear()
            for s in prod_picks:
                used_clips.add(s["source_clip"])
            for s in sales_picks:
                used_clips.add(s["source_clip"])
            outfit_picks, outfit_total = pick_segments(pool, "outfit_demo", 15, 25, used_clips,
                                                        allow_dup_clips=True)

        total = prod_total + outfit_total + sales_total

        # Ensure minimum 40s
        if total < 40:
            if outfit_picks and outfit_total < 15:
                outfit_picks[0]["end"] = min(
                    outfit_picks[0]["end"] + (15 - outfit_total),
                    outfit_picks[0].get("end_trimmed", outfit_picks[0]["end"]) + 10
                )
                outfit_picks[0]["duration"] = outfit_picks[0]["end"] - outfit_picks[0]["start"]
                outfit_total = outfit_picks[0]["duration"]
            if total < 35 and sales_picks:
                sales_picks[0]["end"] = min(
                    sales_picks[0]["start"] + 12,
                    sales_picks[0].get("end_trimmed", sales_picks[0]["end"]) + 5
                )
                sales_picks[0]["duration"] = sales_picks[0]["end"] - sales_picks[0]["start"]
                sales_total = sales_picks[0]["duration"]

        total = prod_total + outfit_total + sales_total
        ordered_segments = prod_picks + outfit_picks + sales_picks

        variant = {
            "id": "v%d" % (vi + 1),
            "segments": [],
            "total_duration": total,
        }

        for seg in ordered_segments:
            if dedup:
                import random as _rd
                _rd.seed(42 + vi * 13 + len(variant["segments"]))
                offset = _rd.uniform(-1.0, 1.0)
                seg_start = max(0, seg["start"] + offset)
                seg_end = max(seg_start + 3, seg["end"] + offset)
                variant["segments"].append({
                    "type": seg["type"],
                    "source_file": seg["source_file"],
                    "source_clip": seg["source_clip"],
                    "start": round(seg_start, 1),
                    "end": round(seg_end, 1),
                    "duration": round(seg_end - seg_start, 1),
                })
            else:
                variant["segments"].append({
                    "type": seg["type"],
                    "source_file": seg["source_file"],
                    "source_clip": seg["source_clip"],
                    "start": seg["start"],
                    "end": seg["end"],
                    "duration": seg["end"] - seg["start"],
                })

        variant["total_duration"] = sum(s["duration"] for s in variant["segments"])

        seg_desc = " -> ".join(
            "%s[%s](%ss-%ss)" % (s["type"], s["source_clip"], s["start"], s["end"])
            for s in variant["segments"]
        )
        log("v%d: %.0fs - %s" % (vi + 1, variant["total_duration"], seg_desc))

        for seg in variant["segments"]:
            used_across_variants.add((seg["source_clip"], seg["start"]))

        variants.append(variant)

    return variants


def main():
    from . import utils as ut
    parser = argparse.ArgumentParser(description="Compose three-act video variants from classified segments")
    parser.add_argument("segments_json", nargs="?",
                        default=os.path.join(ut.get_tmp_dir(), "segments.json"))
    parser.add_argument("--variants", "-n", type=int, default=4, help="Number of variants (default: 4)")
    parser.add_argument("--output", default=os.path.join(ut.get_tmp_dir(), "edls.json"),
                        help="Output EDL path")
    parser.add_argument("--clips-dir", default="/tmp/clips",
                        help="Source clips directory")
    args = parser.parse_args()

    if not os.path.exists(args.segments_json):
        log("Error: %s not found" % args.segments_json)
        sys.exit(1)

    with open(args.segments_json) as f:
        data = json.load(f)
    log("Loaded %d clips' segment data" % len(data))

    pool = build_segment_pool(data, args.clips_dir)
    variants = compose_variants(pool, args.variants)

    result = {"variants": variants}
    with open(args.output, "w") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    log("Saved %d variants to %s" % (len(variants), args.output))


if __name__ == "__main__":
    # Import utils here for default paths in argparse
    from . import utils
    main()
