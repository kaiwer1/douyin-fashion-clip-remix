#!/usr/bin/env python3
"""CLI entry: classify video clips into segments.

Usage:
  python classify.py /path/to/clip*.mp4 [--interval 5] [--output segments.json]
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from clip_remix import classifier

if __name__ == "__main__":
    classifier.main()
