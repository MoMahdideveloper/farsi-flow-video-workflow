#!/usr/bin/env python3
"""Farsi Google Flow Viral Series Workflow (config-driven CLI).

Industrialises the Google Flow (Veo) *native Farsi* localisation pipeline:

    raw Flow clips -> optional multi-segment splice -> speech-safe trim
      -> 720x1280 @ 24fps + loudnorm(-14 LUFS) 48 kHz stereo AAC 192k
      -> per-clip RTL Persian subtitles burned in WITH the original Flow audio
         (clip_XX_subbed.mp4 + clip_XX_subbed.srt)
      -> Base_<episode>_Flow_Native_Farsi.mp4      (immutable story-only master)
      -> Master_<episode>_Flow_Native_Farsi.mp4    (Base + exactly one Kelidbox CTA)
      -> .srt (UTF-8 BOM), _audit.mp3, qa_<episode>_contact.jpg, qa_report.json

Subcommands
    build             full episode: per-clip subbed clips, Base, Master, QA kit
    speech-audit      speech-boundary analysis + trim plan only (no rendering)
    sub-clips-only    per-clip subtitled+audio clips only (no Base / Master)
    clipboard-image   copy a verified 9:16 keyframe to the OS clipboard
    clipboard-prompt  copy a Google Flow scene prompt to the OS clipboard

Requirements: Python 3.10+, ffmpeg + ffprobe on PATH (or --ffmpeg/--ffprobe),
numpy, Pillow.  arabic-reshaper + python-bidi are used when present (needed
for correct Persian shaping on Pillow builds without libraqm, e.g. Windows).
No OpenCV: subtitles are rendered as RGBA pills with Pillow and composited by
ffmpeg's overlay filter, so video and audio stay on one explicit timeline.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Iterable, Optional

import numpy as np
from PIL import Image, ImageDraw, ImageFont, features

try:  # Persian shaping (preferred path on Windows Pillow without raqm)
    import arabic_reshaper  # type: ignore
except ImportError:  # pragma: no cover - minimal CI
    arabic_reshaper = None
try:
    from bidi.algorithm import get_display  # type: ignore
except ImportError:  # pragma: no cover
    try:
        from bidi import get_display  # type: ignore  # python-bidi >= 0.6
    except ImportError:
        get_display = None

PIPELINE_VERSION = "1.0.0"

# ----------------------------------------------------------------- defaults --
DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS = 720, 1280, 24
DEFAULT_LOUDNORM = "loudnorm=I=-14:TP=-1.5:LRA=11"
PILL_FILL = (12, 14, 22, 210)
PILL_OUTLINE = (255, 215, 80, 220)
TEXT_SHADOW = (0, 0, 0, 230)
DEFAULT_TEXT_COLOR = (255, 255, 255)
WINDOWS_FONT = (r"C:\Users\LifeCycle\.gemini\antigravity\scratch"
                r"\ugly-face-chef-farsi\03_farsi_audio_tts\Vazirmatn-Bold.ttf")
SYSTEM_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/vazirmatn/Vazirmatn-Bold.ttf",
    "/usr/local/share/fonts/Vazirmatn-Bold.ttf",
    os.path.expanduser("~/.fonts/Vazirmatn-Bold.ttf"),
    os.path.expanduser("~/.local/share/fonts/Vazirmatn-Bold.ttf"),
    "/usr/share/fonts/truetype/noto/NotoSansArabic-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoNaskhArabic-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/Library/Fonts/Vazirmatn-Bold.ttf",
    "/System/Library/Fonts/Supplemental/GeezaPro.ttc",
    r"C:\Windows\Fonts\Vazirmatn-Bold.ttf",
    r"C:\Windows\Fonts\tahomabd.ttf",
    r"C:\Windows\Fonts\arialbd.ttf",
]
FFMPEG = os.environ.get("FFMPEG_BIN", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE_BIN", "ffprobe")
VERBOSE = False


class PipelineError(RuntimeError):
    """Raised for manifest / media problems the operator must fix."""


# ------------------------------------------------------------------ helpers --
def log(msg: str) -> None:
    print(f"[farsi-flow] {msg}", flush=True)


def run(cmd: list[str], *, capture: bool = False, what: str = "") -> subprocess.CompletedProcess:
    """Run a subprocess; raise PipelineError with stderr tail on failure."""
    if VERBOSE:
        log("$ " + " ".join(cmd))
    proc = subprocess.run(cmd, stdout=subprocess.PIPE if capture else subprocess.DEVNULL,
                          stderr=subprocess.PIPE)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-12:]
        raise PipelineError(f"{what or cmd[0]} failed (exit {proc.returncode}):\n  " + "\n  ".join(tail))
    return proc


def ffmpeg_cmd(*args: str) -> list[str]:
    return [FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error", *args]


def ffprobe_json(path: Path) -> dict:
    proc = run([FFPROBE, "-v", "error", "-print_format", "json", "-show_format",
                "-show_streams", str(path)], capture=True, what=f"ffprobe {path.name}")
    return json.loads(proc.stdout.decode("utf-8", "replace") or "{}")


def _fps_value(rate: str | None) -> float:
    if not rate or rate in ("0/0", "0"):
        return 0.0
    num, _, den = rate.partition("/")
    return float(num) / float(den or 1) if float(den or 1) else 0.0


def probe_media(path: Path) -> dict:
    """Condensed ffprobe summary: first video/audio stream + durations."""
    info = ffprobe_json(path)
    fmt_dur = float(info.get("format", {}).get("duration", 0.0) or 0.0)
    out: dict[str, Any] = {"path": str(path), "format_duration": round(fmt_dur, 4),
                           "video": None, "audio": None}
    for st in info.get("streams", []):
        kind = st.get("codec_type")
        if kind not in ("video", "audio") or out[kind] is not None:
            continue
        dur = float(st.get("duration", 0.0) or 0.0) or fmt_dur
        entry = {"codec": st.get("codec_name"), "duration": round(dur, 4)}
        if kind == "video":
            entry.update(width=st.get("width"), height=st.get("height"),
                         fps=round(_fps_value(st.get("avg_frame_rate") or st.get("r_frame_rate")), 3),
                         pix_fmt=st.get("pix_fmt"), frames=int(st.get("nb_frames", 0) or 0))
        else:
            entry.update(sample_rate=int(st.get("sample_rate", 0) or 0),
                         channels=int(st.get("channels", 0) or 0))
        out[kind] = entry
    return out


def media_duration(path: Path) -> float:
    """Shortest of the video/audio stream durations (safe trim bound)."""
    p = probe_media(path)
    durs = [s["duration"] for s in (p["video"], p["audio"]) if s and s["duration"] > 0]
    return min(durs) if durs else p["format_duration"]


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def fmt_srt(sec: float) -> str:
    """SRT timestamp; rounds on total milliseconds (no ',1000' overflow)."""
    total_ms = max(0, int(round(sec * 1000)))
    h, rem = divmod(total_ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(path: Path, cues: Iterable[tuple[float, float, str]]) -> int:
    """Write UTF-8-with-BOM SRT; returns cue count."""
    blocks = [f"{i}\n{fmt_srt(s0)} --> {fmt_srt(s1)}\n{txt}\n"
              for i, (s0, s1, txt) in enumerate(cues, 1)]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text("\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8-sig")
    os.replace(tmp, path)
    return len(blocks)


# ----------------------------------------------------------------- manifest --
SPEECH_MODES = ("auto_expand", "warn", "off")
VIDEO_DEFAULTS = {"width": DEFAULT_WIDTH, "height": DEFAULT_HEIGHT, "fps": DEFAULT_FPS,
                  "crf": 18, "preset": "fast", "work_crf": 14, "scale_mode": "fill"}
AUDIO_DEFAULTS = {"loudnorm": DEFAULT_LOUDNORM, "sample_rate": 48000, "channels": 2,
                  "bitrate": "192k", "audit_bitrate": "128k"}
SPEECH_DEFAULTS = {"speech_safe": "auto_expand", "threshold_dbfs": -38.0, "noise_margin_db": 10.0,
                   "frame_ms": 20, "min_speech_ms": 60, "merge_gap_ms": 250,
                   "pre_handle": 0.20, "post_handle": 0.35, "splice_crossfade": 0.02}
SUB_DEFAULTS = {"time_base": "trim_local", "y_ratio": 0.84, "font_size": 27, "min_font_size": 16,
                "max_text_margin": 84, "max_lines": 2}
BADGE_DEFAULTS = {"start": 0.0, "end": 3.5, "y_center": 130, "font_size": 28,
                  "color": [255, 225, 110], "clip_index": 1}
CTA_DEFAULT_COLOR = (255, 230, 150)
DRIFT_TOLERANCE = 0.15
_WIN_ABS = re.compile(r"^[A-Za-z]:[\\/]")
_VAR = re.compile(r"\$\{(\w+)\}")


def normalize_speech_mode(value: Any) -> str:
    """true/None -> auto_expand, false -> off, plus 'warn' / aliases."""
    if value is True or value is None:
        return "auto_expand"
    if value is False:
        return "off"
    v = str(value).strip().lower().replace("-", "_")
    v = {"auto": "auto_expand", "expand": "auto_expand", "true": "auto_expand",
         "false": "off", "none": "off"}.get(v, v)
    if v not in SPEECH_MODES:
        raise PipelineError(f"speech_safe must be one of {SPEECH_MODES}, true or false (got {value!r})")
    return v


@dataclass
class Cue:
    start: float
    end: float
    speaker: str
    text: str

    @classmethod
    def parse(cls, raw: Any, where: str) -> "Cue":
        if isinstance(raw, dict):
            s0, s1, spk, txt = raw.get("start"), raw.get("end"), raw.get("speaker", ""), raw.get("text", "")
        elif isinstance(raw, (list, tuple)) and len(raw) in (3, 4):
            s0, s1, spk, txt = raw if len(raw) == 4 else (raw[0], raw[1], "", raw[2])
        else:
            raise PipelineError(f"{where}: cue must be {{start,end,speaker,text}} or [start,end,speaker,text]")
        try:
            s0, s1 = float(s0), float(s1)
        except (TypeError, ValueError) as exc:
            raise PipelineError(f"{where}: start/end must be numbers") from exc
        if not (0.0 <= s0 < s1):
            raise PipelineError(f"{where}: need 0 <= start < end (got {s0}..{s1})")
        if not str(txt).strip():
            raise PipelineError(f"{where}: empty subtitle text")
        return cls(round(s0, 3), round(s1, 3), str(spk or "").strip().upper(), str(txt).strip())


@dataclass
class ClipSpec:
    index: int
    id: str
    file: str
    trim_in: float
    trim_out: Optional[float]
    subtitles: list[Cue]
    raw_orig_file: Optional[str] = None
    splice_segments: Optional[list[tuple[float, float]]] = None
    speech_safe: str = "auto_expand"
    lock_trim: bool = False
    notes: str = ""


@dataclass
class Episode:
    manifest_path: Path
    manifest_sha256: str
    episode_id: str
    title_fa: str
    clips_dir: Path
    out_dir: Path
    font_path: Optional[str]
    cta_video: Optional[Path]
    cta_subtitles: list[Cue]
    video: dict
    audio: dict
    speech: dict
    subs: dict
    badge: Optional[dict]
    voices: dict
    clips: list[ClipSpec]
    outputs: dict = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)

    @property
    def base_name(self) -> str:
        return f"Base_{self.episode_id}_Flow_Native_Farsi"

    @property
    def master_name(self) -> str:
        return f"Master_{self.episode_id}_Flow_Native_Farsi"

    def color_for(self, speaker: str, default=DEFAULT_TEXT_COLOR) -> tuple[int, int, int]:
        col = (self.voices.get(speaker) or {}).get("color")
        return tuple(int(c) for c in col[:3]) if col else tuple(default)  # type: ignore[return-value]


def _expand(value: str, variables: dict[str, str]) -> str:
    def sub(m: re.Match) -> str:
        key = m.group(1)
        if key in variables:
            return variables[key]
        if key in os.environ:
            return os.environ[key]
        raise PipelineError(f"unknown path variable ${{{key}}} in {value!r}")
    for _ in range(6):  # allow nested ${a} -> ${b}
        new = _VAR.sub(sub, value)
        if new == value:
            break
        value = new
    return os.path.expanduser(value)


def is_foreign_windows_path(p: str | Path) -> bool:
    """A 'C:\\...' path while running on POSIX: can never exist here."""
    return os.name != "nt" and bool(_WIN_ABS.match(str(p)))


def resolve_path(value: Any, variables: dict[str, str], rel_to: Path) -> Optional[Path]:
    if value in (None, ""):
        return None
    s = _expand(str(value), variables)
    if is_foreign_windows_path(s):
        return Path(s)  # kept verbatim for messages; .exists() is False on POSIX
    if os.name != "nt":  # "${BASE}\\03_flow_clips" remapped via --var BASE=/data/x
        s = s.replace("\\", "/")
    p = Path(s)
    return p if p.is_absolute() else (rel_to / p).resolve()


def _merged(defaults: dict, *overrides: Optional[dict]) -> dict:
    out = dict(defaults)
    for o in overrides:
        if o:
            out.update({k: v for k, v in o.items() if v is not None})
    return out


def _parse_segments(raw: Any, where: str) -> Optional[list[tuple[float, float]]]:
    if raw in (None, [], ""):
        return None
    segs: list[tuple[float, float]] = []
    for i, seg in enumerate(raw):
        if not (isinstance(seg, (list, tuple)) and len(seg) == 2):
            raise PipelineError(f"{where}.splice_segments[{i}] must be [start, end]")
        s0, s1 = float(seg[0]), float(seg[1])
        if not (0.0 <= s0 < s1):
            raise PipelineError(f"{where}.splice_segments[{i}]: need 0 <= start < end")
        if segs and s0 < segs[-1][1]:
            raise PipelineError(f"{where}.splice_segments must be ascending and non-overlapping")
        segs.append((round(s0, 3), round(s1, 3)))
    return segs


def load_manifest(path: Path, overrides: Optional[dict] = None) -> Episode:
    """Parse + validate an episode manifest JSON.  ``overrides`` (from the CLI)
    may carry: vars, clips_dir, out_dir, font, cta_video, no_cta, speech_safe."""
    ov = overrides or {}
    path = Path(path).resolve()
    raw_bytes = path.read_bytes()
    try:
        data = json.loads(raw_bytes.decode("utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise PipelineError(f"{path.name}: invalid JSON ({exc})") from exc
    if not isinstance(data, dict):
        raise PipelineError(f"{path.name}: top level must be an object")
    episode_id = str(data.get("episode_id") or "").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_\-]*", episode_id):
        raise PipelineError(f"{path.name}: episode_id must be [A-Za-z0-9_-]+ (got {episode_id!r})")

    variables = {str(k): str(v) for k, v in (data.get("variables") or {}).items()}
    variables.update(ov.get("vars") or {})
    variables.setdefault("MANIFEST_DIR", str(path.parent))
    rel = path.parent

    clips_dir = resolve_path(ov.get("clips_dir") or data.get("clips_dir"), variables, rel)
    out_dir = resolve_path(ov.get("out_dir") or data.get("out_dir"), variables, rel)
    if clips_dir is None or out_dir is None:
        raise PipelineError(f"{path.name}: clips_dir and out_dir are required")
    font = ov.get("font") or data.get("font_path")
    font_path = str(resolve_path(font, variables, rel)) if font else None

    cta_video = None
    if not ov.get("no_cta"):
        cta_video = resolve_path(ov.get("cta_video") or data.get("cta_video"), variables, rel)
    cta_speaker = str(data.get("cta_speaker") or "").upper()
    cta_subs = []
    for i, c in enumerate(data.get("cta_subtitles") or []):
        cue = Cue.parse(c, f"cta_subtitles[{i}]")
        cue.speaker = cue.speaker or cta_speaker
        cta_subs.append(cue)

    speech = _merged(SPEECH_DEFAULTS, data.get("speech"))
    speech["speech_safe"] = normalize_speech_mode(ov.get("speech_safe") or speech.get("speech_safe"))
    subs_cfg = _merged(SUB_DEFAULTS, data.get("subtitle_style"))
    if subs_cfg["time_base"] not in ("trim_local", "source"):
        raise PipelineError("subtitle_style.time_base must be 'trim_local' or 'source'")
    badge = None
    if data.get("badge"):
        badge = _merged(BADGE_DEFAULTS, data["badge"])
        badge.setdefault("text", data.get("title_fa", ""))
        if not str(badge.get("text") or "").strip():
            badge = None

    voices = {str(k).upper(): v for k, v in (data.get("voices") or {}).items()}
    clips: list[ClipSpec] = []
    seen: set[str] = set()
    for i, c in enumerate(data.get("clips") or [], 1):
        where = f"clips[{i - 1}]"
        if not isinstance(c, dict) or not c.get("file"):
            raise PipelineError(f"{where}: needs at least a 'file'")
        cid = str(c.get("id") or f"clip_{i:02d}")
        if cid in seen:
            raise PipelineError(f"{where}: duplicate clip id {cid}")
        seen.add(cid)
        t_in = float(c.get("trim_in", 0.0) or 0.0)
        t_out = c.get("trim_out")
        t_out = None if t_out is None else float(t_out)
        if t_in < 0 or (t_out is not None and t_out <= t_in):
            raise PipelineError(f"{where}: need 0 <= trim_in < trim_out (got {t_in}..{t_out})")
        cues = [Cue.parse(s, f"{where}.subtitles[{j}]") for j, s in enumerate(c.get("subtitles") or [])]
        for cue in cues:
            if cue.speaker and voices and cue.speaker not in voices:
                raise PipelineError(f"{where}: speaker {cue.speaker!r} not declared in voices")
        mode = ov.get("speech_safe") or c.get("speech_safe", speech["speech_safe"])
        clips.append(ClipSpec(
            index=i, id=cid, file=str(c["file"]), trim_in=round(t_in, 3),
            trim_out=None if t_out is None else round(t_out, 3), subtitles=cues,
            raw_orig_file=c.get("raw_orig_file"),
            splice_segments=_parse_segments(c.get("splice_segments"), where),
            speech_safe=normalize_speech_mode(mode), lock_trim=bool(c.get("lock_trim", False)),
            notes=str(c.get("notes") or "")))
    if not clips:
        raise PipelineError(f"{path.name}: no clips defined")

    return Episode(
        manifest_path=path, manifest_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        episode_id=episode_id, title_fa=str(data.get("title_fa") or ""),
        clips_dir=clips_dir, out_dir=out_dir, font_path=font_path,
        cta_video=cta_video, cta_subtitles=cta_subs,
        video=_merged(VIDEO_DEFAULTS, data.get("video")),
        audio=_merged(AUDIO_DEFAULTS, data.get("audio")),
        speech=speech, subs=subs_cfg, badge=badge, voices=voices, clips=clips,
        outputs=dict(data.get("outputs") or {}))


def clip_source_paths(ep: Episode, clip: ClipSpec) -> tuple[Path, Optional[Path]]:
    """(file path, raw_orig path) resolved against clips_dir."""
    def res(name: str) -> Path:
        p = Path(name)
        return p if p.is_absolute() or is_foreign_windows_path(name) else ep.clips_dir / p
    return res(clip.file), (res(clip.raw_orig_file) if clip.raw_orig_file else None)
