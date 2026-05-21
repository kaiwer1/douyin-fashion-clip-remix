#!/usr/bin/env python3
"""CLI entry: compose video variants from classified segments.

Usage:
  python compose.py segments.json [--variants 4] [--output edls.json]
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
from clip_remix import composer

if __name__ == "__main__":
    composer.main()
