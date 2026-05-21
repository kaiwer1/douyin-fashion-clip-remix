#!/usr/bin/env python3
"""CLI entry: render videos from EDLs.

Usage:
  python render.py edls.json [--output ./output/]
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from clip_remix import renderer

if __name__ == "__main__":
    renderer.main()
