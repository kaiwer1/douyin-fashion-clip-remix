#!/usr/bin/env python3
"""
零食类组合脚本 — 基于镜头类型生成EDL

镜头类型：
- taste_demo: 口感展示（核心）
- product_closeup: 产品特写
- unboxing: 开箱展示
- ingredient: 配料成分
- usage_scene: 场景使用
- sales_pitch: 促销口播

模板：
- v1: 经典带货型（口感→产品→促单）
- v2: 快节奏型（开箱→口感×2→促单）
- v3: 场景带入型（场景→口感→产品→促单）
- v4: 四段式（产品→口感→配料→促单）
"""

import argparse
import json
import os
import random
import sys

TMP_DIR = "/tmp/clips"


def log(msg):
    print("[组合] %s" % msg, file=sys.stderr)


def build_segment_pool(data):
    """构建片段池"""
    pool = {
        "taste_demo": [],
        "product_closeup": [],
        "unboxing": [],
        "ingredient": [],
        "usage_scene": [],
        "sales_pitch": []
    }
    
    for item in data:
        clip_name = os.path.splitext(item["filename"])[0]
        clip_path = os.path.join("/tmp/clips", item["filename"])
        
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


def pick_segments(pool, stype, min_dur, max_dur, used_clips, allow_dup_clips=False):
    """选择符合时长要求的片段"""
    available = [s for s in pool.get(stype, [])
                 if (allow_dup_clips or s["source_clip"] not in used_clips)]
    
    if not available:
        return [], 0
    
    # 按置信度排序，随机取top候选
    available.sort(key=lambda x: x["confidence"], reverse=True)
    top_n = available[:min(6, len(available))]
    random.shuffle(top_n[:3])
    
    best_combo = None
    best_total = 0
    
    # 尝试单个片段
    for s in top_n:
        dur = min(s["duration"], max_dur)
        if min_dur <= dur <= max_dur:
            combo = [s.copy()]
            combo[0]["duration"] = dur
            combo[0]["end"] = s["start"] + dur
            return combo, dur
    
    # 尝试两个片段组合
    for i, s1 in enumerate(top_n[:4]):
        for j, s2 in enumerate(top_n[:4]):
            if i >= j or s1["source_clip"] == s2["source_clip"]:
                continue
            dur = min(s1["duration"], 10) + min(s2["duration"], 10)
            if min_dur <= dur <= max_dur:
                combo = [s1.copy(), s2.copy()]
                combo[0]["duration"] = min(s1["duration"], 10)
                combo[0]["end"] = s1["start"] + combo[0]["duration"]
                combo[1]["duration"] = min(s2["duration"], 10)
                combo[1]["end"] = s2["start"] + combo[1]["duration"]
                return combo, dur
    
    # 宽松匹配
    for s in top_n:
        dur = min(s["duration"], max_dur)
        if dur >= 4:
            combo = [s.copy()]
            combo[0]["duration"] = dur
            combo[0]["end"] = s["start"] + dur
            return combo, dur
    
    return [], 0


def compose_variant(v_id, pool, template):
    """组合单个版本"""
    segments = []
    total_duration = 0
    used_clips = set()
    
    for slot in template:
        stype = slot["type"]
        min_dur = slot["min"]
        max_dur = slot["max"]
        allow_dup = slot.get("allow_dup", False)
        
        picked, dur = pick_segments(pool, stype, min_dur, max_dur, used_clips, allow_dup)
        
        if picked:
            segments.extend(picked)
            total_duration += dur
            for s in picked:
                if not allow_dup:
                    used_clips.add(s["source_clip"])
        else:
            log("  警告: %s 无可用片段" % stype)
    
    return {
        "id": v_id,
        "segments": segments,
        "total_duration": total_duration
    }


def main():
    parser = argparse.ArgumentParser(description="零食视频组合")
    parser.add_argument("segments_json", nargs="?", default="/tmp/clips/segments.json")
    parser.add_argument("--variants", "-v", type=int, default=4)
    parser.add_argument("--output", "-o", default="edls.json")
    parser.add_argument("--seed", "-s", type=int, default=None)
    args = parser.parse_args()
    
    if args.seed:
        random.seed(args.seed)
    
    if not os.path.exists(args.segments_json):
        log("错误: %s 不存在" % args.segments_json)
        sys.exit(1)
    
    with open(args.segments_json) as f:
        data = json.load(f)
    
    log("加载 %d 个视频的片段数据" % len(data))
    
    pool = build_segment_pool(data)
    
    # 统计
    for stype, segs in pool.items():
        if segs:
            log("  %s: %d segments" % (stype, len(segs)))
    
    # 定义模板
    templates = [
        # v1: 经典带货型
        [
            {"type": "taste_demo", "min": 10, "max": 20},
            {"type": "product_closeup", "min": 8, "max": 15},
            {"type": "sales_pitch", "min": 8, "max": 15},
        ],
        # v2: 快节奏型
        [
            {"type": "unboxing", "min": 5, "max": 10},
            {"type": "taste_demo", "min": 8, "max": 15, "allow_dup": True},
            {"type": "taste_demo", "min": 8, "max": 15, "allow_dup": True},
            {"type": "sales_pitch", "min": 5, "max": 10},
        ],
        # v3: 场景带入型
        [
            {"type": "usage_scene", "min": 10, "max": 20},
            {"type": "taste_demo", "min": 10, "max": 20},
            {"type": "product_closeup", "min": 5, "max": 10},
            {"type": "sales_pitch", "min": 10, "max": 15},
        ],
        # v4: 四段式
        [
            {"type": "product_closeup", "min": 5, "max": 10},
            {"type": "taste_demo", "min": 10, "max": 15},
            {"type": "ingredient", "min": 5, "max": 10},
            {"type": "sales_pitch", "min": 10, "max": 15},
        ],
    ]
    
    variants = []
    for i in range(args.variants):
        template = templates[i] if i < len(templates) else templates[0]
        v = compose_variant("v%d" % (i + 1), pool, template)
        
        # 如果时长不够40s，补充片段
        if v["total_duration"] < 40:
            log("  v%d 时长不足 (%ds)，尝试补充..." % (i + 1, v["total_duration"]))
            
            # 补充taste_demo或usage_scene
            for stype in ["taste_demo", "usage_scene", "product_closeup"]:
                need = 40 - v["total_duration"]
                picked, dur = pick_segments(pool, stype, 5, need, set(), allow_dup_clips=True)
                if picked:
                    v["segments"].extend(picked)
                    v["total_duration"] += dur
                    log("    补充 %s +%ds" % (stype, dur))
                    if v["total_duration"] >= 40:
                        break
        
        variants.append(v)
        log("v%d: %ds — %s" % (i + 1, v["total_duration"], 
            " → ".join([s["type"] for s in v["segments"]])))
    
    # 输出
    output = {
        "source_videos": len(data),
        "total_segments": sum(len(v["segments"]) for v in variants),
        "variants": variants
    }
    
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    
    log("输出到 %s" % args.output)


if __name__ == "__main__":
    main()