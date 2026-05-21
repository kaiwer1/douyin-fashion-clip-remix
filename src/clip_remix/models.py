"""
Data models for clip-remix pipeline.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict


@dataclass
class VideoInfo:
    """Metadata for a source video clip."""
    filename: str
    path: str
    duration: float
    fps: float = 0
    width: int = 0
    height: int = 0


@dataclass
class FrameLabel:
    """Classification result for a single frame."""
    timestamp: float
    label: str      # product_shot | outfit_demo | sales_pitch | transition | other
    confidence: float
    source_file: str = ""


@dataclass
class Segment:
    """A continuous segment of classified frames."""
    type: str
    start: float
    end: float
    confidence: float
    source_file: str = ""
    source_clip: str = ""


@dataclass
class ClipResult:
    """Classification result for one video clip."""
    filename: str
    path: str
    video_info: Optional[Dict] = None
    segments: List[Segment] = field(default_factory=list)
    frame_labels: List[FrameLabel] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class ComposerSegment:
    """A segment selected by the composer for a variant."""
    type: str
    source_file: str
    source_clip: str
    start: float
    end: float
    duration: float
    confidence: float = 0.5


@dataclass
class Variant:
    """One composed video variant (EDL)."""
    id: str          # v1, v2, ...
    segments: List[ComposerSegment] = field(default_factory=list)
    total_duration: float = 0


@dataclass
class ComposeResult:
    """Result of composition phase."""
    variants: List[Variant] = field(default_factory=list)


def segment_to_dict(seg: Segment) -> dict:
    return {
        "type": seg.type,
        "start": seg.start,
        "end": seg.end,
        "confidence": seg.confidence,
        "source_file": seg.source_file,
        "source_clip": seg.source_clip,
    }


def dict_to_segment(d: dict) -> Segment:
    return Segment(
        type=d.get("type", ""),
        start=d.get("start", 0),
        end=d.get("end", 0),
        confidence=d.get("confidence", 0.5),
        source_file=d.get("source_file", ""),
        source_clip=d.get("source_clip", ""),
    )
