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
    trace-audit       6-stage step trace for one manifest (live MP4s or a probe JSON)
    trace-all-parts   6-stage step trace for Fruits of Power Parts 1-5 from a probe JSON

v1.2 adds the narrative-continuity layer: per-clip keyframe / speaker / story
beat metadata, a visual continuity gate (KEYFRAME_MISMATCH,
MULTI_INGREDIENT_CONTAMINATION, INTERNAL_SCENE_CUT), tight speech pacing, and
a hybrid source-bridge fallback that swaps a visually broken Flow video stream
for the subtitle-inpainted original episode span while KEEPING the native
Flow Farsi audio.  Keyframes are read-only inputs: they are hashed and
compared, never drawn on, blurred or otherwise modified.

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
from types import SimpleNamespace

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

PIPELINE_VERSION = "1.2.2"
ANALYSIS_SR = 16000  # speech analysis: 16 kHz mono PCM

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
    print(f"[farsi-flow] {msg}", file=sys.stderr, flush=True)


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


def _probe_number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
        return number if math.isfinite(number) else default
    except (TypeError, ValueError):
        return default


def probe_media(path: Path) -> dict:
    """Condensed ffprobe summary: first video/audio stream + durations."""
    info = ffprobe_json(path)
    fmt_dur = _probe_number(info.get("format", {}).get("duration"))
    out: dict[str, Any] = {"path": str(path), "format_duration": round(fmt_dur, 4),
                           "video": None, "audio": None}
    for st in info.get("streams", []):
        kind = st.get("codec_type")
        if kind not in ("video", "audio") or out[kind] is not None:
            continue
        dur = _probe_number(st.get("duration")) or fmt_dur
        entry = {"codec": st.get("codec_name"), "duration": round(dur, 4),
                 "start_time": _probe_number(st.get("start_time"))}
        if kind == "video":
            entry.update(width=st.get("width"), height=st.get("height"),
                         fps=round(_fps_value(st.get("avg_frame_rate") or st.get("r_frame_rate")), 3),
                         pix_fmt=st.get("pix_fmt"), frames=int(_probe_number(st.get("nb_frames"))))
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
                   "peak_margin_db": 12.0,
                   "frame_ms": 20, "min_speech_ms": 60, "merge_gap_ms": 250,
                   "pre_handle": 0.20, "post_handle": 0.35, "splice_crossfade": 0.02}
SUB_DEFAULTS = {"time_base": "trim_local", "y_ratio": 0.84, "font_size": 27, "min_font_size": 16,
                "max_text_margin": 84, "max_lines": 2}
BADGE_DEFAULTS = {"start": 0.0, "end": 3.5, "y_center": 130, "font_size": 28,
                  "color": [255, 225, 110], "clip_index": 1}
CTA_DEFAULT_COLOR = (255, 230, 150)
DRIFT_TOLERANCE = 0.15
VISUAL_DEFAULTS = {"keyframe_threshold": 32.0, "jump_threshold": 32.0, "contamination_margin": 5.0,
                   "sample_fps": 2.0, "thumb_size": [72, 128]}
TIGHT_MIN_DURATION = 2.2       # seconds: a tight-trimmed talking clip is never shorter
DEAD_AIR_LIMIT = 3.5           # seconds of non-speech beyond the line before DEAD_AIR_PACING
FAIL_FLAGS = ("KEYFRAME_MISMATCH", "MULTI_INGREDIENT_CONTAMINATION", "INTERNAL_SCENE_CUT")
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
        if not (math.isfinite(s0) and math.isfinite(s1) and 0.0 <= s0 < s1):
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
    allow_speech_splice: bool = False
    notes: str = ""
    # v1.2 narrative-continuity metadata
    keyframe: Optional[Path] = None
    expected_speakers: list[str] = field(default_factory=list)
    story_beat: str = ""
    source_span: Optional[tuple[float, float]] = None
    tight_speech_trim: Optional[bool] = None


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
    # v1.2 hybrid source-bridge / pacing settings
    source_video: Optional[Path] = None
    story_summary_fa: str = ""
    fallback_to_source_on_visual_fail: bool = False
    tight_speech_trim: bool = False
    visual: dict = field(default_factory=dict)
    probe: Optional[dict] = None  # per-clip probe entries (headless visual audit)

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
    if _VAR.search(value):
        raise PipelineError(f"cyclic or excessively nested path variable: {value!r}")
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
        if not (math.isfinite(s0) and math.isfinite(s1) and 0.0 <= s0 < s1):
            raise PipelineError(f"{where}.splice_segments[{i}]: need 0 <= start < end")
        if segs and s0 < segs[-1][1]:
            raise PipelineError(f"{where}.splice_segments must be ascending and non-overlapping")
        segs.append((round(s0, 3), round(s1, 3)))
    return segs


def _parse_span(raw: Any, where: str) -> Optional[tuple[float, float]]:
    """``source_span: [start_sec, end_sec]`` in the ORIGINAL episode video."""
    if raw in (None, [], ""):
        return None
    if not (isinstance(raw, (list, tuple)) and len(raw) == 2):
        raise PipelineError(f"{where}.source_span must be [start_sec, end_sec]")
    try:
        s0, s1 = float(raw[0]), float(raw[1])
    except (TypeError, ValueError) as exc:
        raise PipelineError(f"{where}.source_span must contain numeric seconds") from exc
    if not (math.isfinite(s0) and math.isfinite(s1) and 0.0 <= s0 < s1):
        raise PipelineError(f"{where}.source_span: need 0 <= start < end (got {raw})")
    return round(s0, 3), round(s1, 3)


def strict_bool(value: Any, where: str) -> bool:
    if not isinstance(value, bool):
        raise PipelineError(f"{where} must be a JSON boolean, not {value!r}")
    return value


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
    if data.get("schema_version", 1) != 1:
        raise PipelineError("unsupported schema_version; expected 1")
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

    speech = _merged(SPEECH_DEFAULTS, {"speech_safe": data.get("speech_safe")}, data.get("speech"))
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
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]*", cid):
            raise PipelineError(f"{where}: unsafe clip id {cid!r}")
        if cid in seen:
            raise PipelineError(f"{where}: duplicate clip id {cid}")
        seen.add(cid)
        t_in = float(c.get("trim_in", 0.0) or 0.0)
        t_out = c.get("trim_out")
        t_out = None if t_out is None else float(t_out)
        if not math.isfinite(t_in) or t_in < 0 or (t_out is not None and
                (not math.isfinite(t_out) or t_out <= t_in)):
            raise PipelineError(f"{where}: need 0 <= trim_in < trim_out (got {t_in}..{t_out})")
        cues = [Cue.parse(s, f"{where}.subtitles[{j}]") for j, s in enumerate(c.get("subtitles") or [])]
        for cue in cues:
            if cue.speaker and voices and cue.speaker not in voices:
                raise PipelineError(f"{where}: speaker {cue.speaker!r} not declared in voices")
        mode = ov.get("speech_safe") or c.get("speech_safe", speech["speech_safe"])
        expected = c.get("expected_speakers", [])
        if not isinstance(expected, list) or any(not isinstance(x, str) or not x.strip() for x in expected):
            raise PipelineError(f"{where}.expected_speakers must be a list of speaker names")
        clips.append(ClipSpec(
            index=i, id=cid, file=str(c["file"]), trim_in=round(t_in, 3),
            trim_out=None if t_out is None else round(t_out, 3), subtitles=cues,
            raw_orig_file=c.get("raw_orig_file"),
            splice_segments=_parse_segments(c.get("splice_segments"), where),
            speech_safe=normalize_speech_mode(mode), lock_trim=bool(c.get("lock_trim", False)),
            allow_speech_splice=bool(c.get("allow_speech_splice", False)),
            notes=str(c.get("notes") or ""),
            keyframe=resolve_path(c.get("keyframe"), variables, rel),
            expected_speakers=[x.strip().upper() for x in expected],
            story_beat=str(c.get("story_beat") or ""),
            source_span=_parse_span(c.get("source_span"), where),
            tight_speech_trim=None if c.get("tight_speech_trim") is None else strict_bool(c["tight_speech_trim"], f"{where}.tight_speech_trim")))
        for spk in clips[-1].expected_speakers:
            if voices and spk not in voices:
                raise PipelineError(f"{where}: expected speaker {spk!r} not declared in voices")
    if not clips:
        raise PipelineError(f"{path.name}: no clips defined")

    ep = Episode(
        manifest_path=path, manifest_sha256=hashlib.sha256(raw_bytes).hexdigest(),
        episode_id=episode_id, title_fa=str(data.get("title_fa") or ""),
        clips_dir=clips_dir, out_dir=out_dir, font_path=font_path,
        cta_video=cta_video, cta_subtitles=cta_subs,
        video=_merged(VIDEO_DEFAULTS, data.get("video")),
        audio=_merged(AUDIO_DEFAULTS, data.get("audio")),
        speech=speech, subs=subs_cfg, badge=badge, voices=voices, clips=clips,
        outputs=dict(data.get("outputs") or {}),
        source_video=resolve_path(ov.get("source_video") or data.get("source_video"), variables, rel),
        story_summary_fa=str(data.get("story_summary_fa") or ""),
        fallback_to_source_on_visual_fail=strict_bool(data.get("fallback_to_source_on_visual_fail", False),
                                                      "fallback_to_source_on_visual_fail"),
        tight_speech_trim=strict_bool(data.get("tight_speech_trim", False), "tight_speech_trim"),
        visual=_merged(VISUAL_DEFAULTS, data.get("visual_gate")))
    validate_settings(ep)
    return ep


def validate_settings(ep: Episode) -> None:
    """Fail early for invalid numeric settings, enums, colors and path collisions."""
    for group, keys in ((ep.video, ("width", "height", "fps")),
                        (ep.audio, ("sample_rate", "channels")),
                        (ep.speech, ("frame_ms", "min_speech_ms")),
                        (ep.subs, ("font_size", "min_font_size", "max_text_margin"))):
        for key in keys:
            value = float(group[key])
            if not math.isfinite(value) or value <= 0 or value != int(value):
                raise PipelineError(f"{key} must be a positive integer")
    for key in ("pre_handle", "post_handle", "merge_gap_ms", "splice_crossfade"):
        value = float(ep.speech[key])
        if not math.isfinite(value) or value < 0:
            raise PipelineError(f"{key} must be finite and nonnegative")
    for key in ("threshold_dbfs", "noise_margin_db", "peak_margin_db"):
        if not math.isfinite(float(ep.speech[key])):
            raise PipelineError(f"{key} must be finite")
    if ep.audio["channels"] not in (1, 2):
        raise PipelineError("channels must be 1 or 2")
    if any(int(ep.video[k]) % 2 for k in ("width", "height")):
        raise PipelineError("video dimensions must be even (yuv420p)")
    if ep.video["scale_mode"] not in ("fill", "fit", "stretch"):
        raise PipelineError("invalid video.scale_mode")
    if ep.outputs.get("base_mode", "timeline") not in ("timeline", "concat_subbed"):
        raise PipelineError("invalid outputs.base_mode")
    if ep.outputs.get("per_clip_location", "both") not in ("both", "clips_dir", "out_dir"):
        raise PipelineError("invalid outputs.per_clip_location")
    for cue in ep.cta_subtitles:
        if cue.speaker and cue.speaker not in ep.voices:
            raise PipelineError(f"CTA speaker {cue.speaker!r} not declared in voices")
    for speaker, voice in ep.voices.items():
        color = voice.get("color", DEFAULT_TEXT_COLOR)
        if len(color) != 3 or any(not isinstance(c, int) or not 0 <= c <= 255 for c in color):
            raise PipelineError(f"{speaker}: color must be three RGB integers in 0..255")
    for key in ("keyframe_threshold", "jump_threshold", "contamination_margin", "sample_fps"):
        value = ep.visual[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
                or value < 0 or (key == "sample_fps" and value == 0):
            raise PipelineError(f"visual_gate.{key} must be finite and valid")
    size = ep.visual["thumb_size"]
    if not isinstance(size, (list, tuple)) or len(size) != 2 or any(
            isinstance(x, bool) or not isinstance(x, int) or x <= 0 for x in size):
        raise PipelineError("visual_gate.thumb_size needs two positive integer dimensions")
    if ep.fallback_to_source_on_visual_fail and (ep.source_video is None or
                                                 any(c.source_span is None for c in ep.clips)):
        raise PipelineError("fallback requires source_video and every clip source_span")
    sources = {p.resolve() for c in ep.clips for p in clip_source_paths(ep, c) if p}
    sources.update(c.keyframe.resolve() for c in ep.clips if c.keyframe)
    if ep.source_video:
        sources.add(ep.source_video.resolve())
    if ep.cta_video:
        sources.add(ep.cta_video.resolve())
    products = [ep.out_dir / f"{n}.mp4" for n in (ep.base_name, ep.master_name)]
    for c in ep.clips:
        products += clip_output_paths(ep, c, f"{c.id}_subbed.mp4")
        products += [work_dir(ep) / f"{c.id}_{suffix}" for suffix in
                     ("norm.mp4", "norm.wav", "spliced.mov", "source_bridge.mp4")]
    products.append(work_dir(ep) / "cta_norm.mov")
    if sources.intersection(p.resolve() for p in products):
        raise PipelineError("output path would overwrite an input source; use separate paths")



def clip_source_paths(ep: Episode, clip: ClipSpec) -> tuple[Path, Optional[Path]]:
    """(file path, raw_orig path) resolved against clips_dir (preferring raw_unsubbed/ when present)."""
    def res(name: str) -> Path:
        p = Path(name)
        if p.is_absolute() or is_foreign_windows_path(name):
            return p
        raw_unsubbed = ep.clips_dir / "raw_unsubbed" / p
        if raw_unsubbed.is_file():
            return raw_unsubbed
        return ep.clips_dir / p
    return res(clip.file), (res(clip.raw_orig_file) if clip.raw_orig_file else None)


# ------------------------------------------------- speech boundary analyzer --
def decode_pcm(path: Path, sr: int = ANALYSIS_SR, channels: int = 1) -> np.ndarray:
    """Decode the first audio stream to float32 PCM in [-1, 1] (shape [n] or [n, ch])."""
    proc = run(ffmpeg_cmd("-i", str(path), "-map", "0:a:0", "-vn", "-ac", str(channels),
                          "-ar", str(sr), "-f", "s16le", "-acodec", "pcm_s16le", "pipe:1"),
               capture=True, what=f"decode audio {path.name}")
    pcm = np.frombuffer(proc.stdout, dtype="<i2").astype(np.float32) / 32768.0
    return pcm.reshape(-1, channels) if channels > 1 else pcm


def frame_dbfs(pcm: np.ndarray, sr: int = ANALYSIS_SR, frame_ms: int = 20) -> np.ndarray:
    """Short-time RMS energy in dBFS over non-overlapping frames."""
    n = max(1, int(sr * frame_ms / 1000))
    if not len(pcm):
        return np.full(1, -120.0, dtype=np.float32)
    # Keep partial tail frames: a quiet final consonant must not disappear.
    padded = np.pad(pcm, (0, (-len(pcm)) % n))
    frames = padded.reshape(-1, n).astype(np.float64)
    rms = np.sqrt(np.mean(frames * frames, axis=1))
    return (20.0 * np.log10(np.maximum(rms, 1e-6))).astype(np.float32)


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """[start, end) index runs where mask is True."""
    if not mask.any():
        return []
    d = np.diff(np.concatenate(([0], mask.astype(np.int8), [0])))
    return list(zip(np.flatnonzero(d == 1).tolist(), np.flatnonzero(d == -1).tolist()))


def detect_speech_segments(db: np.ndarray, cfg: dict) -> tuple[list[tuple[float, float]], dict]:
    """Threshold frames at max(threshold_dbfs, noise_floor + margin), drop blips
    shorter than min_speech_ms, merge gaps shorter than merge_gap_ms.

    The adaptive term is capped at peak - peak_margin_db: on dense-dialogue
    clips (speech in >90% of frames) the 10th-percentile "floor" IS speech,
    and an uncapped threshold would sit above the peak and report no speech
    at all -- silently disabling speech-safe trimming."""
    fs = cfg["frame_ms"] / 1000.0
    floor = float(np.percentile(db, 10)) if db.size else -120.0
    peak = float(db.max()) if db.size else -120.0
    adaptive = min(floor + float(cfg["noise_margin_db"]), -20.0,
                   peak - float(cfg.get("peak_margin_db", 12.0)))
    thr = max(float(cfg["threshold_dbfs"]), adaptive)
    runs = [r for r in _runs(db > thr) if (r[1] - r[0]) * fs * 1000 >= cfg["min_speech_ms"]]
    merged: list[list[int]] = []
    for a, b in runs:
        if merged and (a - merged[-1][1]) * fs * 1000 < cfg["merge_gap_ms"]:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    segs = [(round(a * fs, 3), round(b * fs, 3)) for a, b in merged]
    stats = {"noise_floor_dbfs": round(floor, 2), "threshold_dbfs": round(thr, 2),
             "peak_dbfs": round(peak, 2)}
    return segs, stats


def _speech_inside(segs: list[tuple[float, float]], lo: float, hi: float) -> float:
    return round(sum(max(0.0, min(b, hi) - max(a, lo)) for a, b in segs), 3)


def analyze_clip_speech(mp4_path: Path, trim_in: float = 0.0, trim_out: Optional[float] = None,
                        cfg: Optional[dict] = None) -> dict:
    """Acoustic speech-boundary report for one source clip.

    Decodes 16 kHz mono PCM, computes 20 ms RMS dBFS frames, finds speech
    segments, ``first_speech_sec`` / ``last_speech_sec`` and whether the
    requested [trim_in, trim_out] window cuts into (or drops) speech energy.
    Amplitude evidence only -- it locates candidates, it does not prove a
    sentence finished; human/ASR listening stays a separate QA field."""
    cfg = _merged(SPEECH_DEFAULTS, cfg)
    pcm = decode_pcm(Path(mp4_path))
    src_dur = media_duration(Path(mp4_path))
    db = frame_dbfs(pcm, ANALYSIS_SR, int(cfg["frame_ms"]))
    segs, stats = detect_speech_segments(db, cfg)
    segs = [(a, round(min(b, src_dur), 4)) for a, b in segs if a < src_dur]
    t_out = src_dur if trim_out is None else float(trim_out)
    first = segs[0][0] if segs else None
    last = min(segs[-1][1], src_dur) if segs else None

    def inside(t: float) -> bool:
        return any(a < t < b for a, b in segs)

    report = {
        "source": str(mp4_path), "source_duration": round(src_dur, 3),
        "analysis_sr": ANALYSIS_SR, "frame_ms": cfg["frame_ms"], **stats,
        "speech_segments": [[a, b] for a, b in segs],
        "first_speech_sec": first, "last_speech_sec": last,
        "trim_in": round(float(trim_in), 3), "trim_out": round(t_out, 3),
        "trim_in_inside_speech": inside(float(trim_in)),
        "trim_out_inside_speech": inside(t_out),
        "speech_dropped_before_in_sec": _speech_inside(segs, 0.0, float(trim_in)),
        "speech_dropped_after_out_sec": _speech_inside(segs, t_out, src_dur),
        "pre_handle_sec": None if first is None else round(first - float(trim_in), 3),
        "post_handle_sec": None if last is None else round(t_out - last, 3),
    }
    report["cuts_speech"] = bool(report["trim_in_inside_speech"] or report["trim_out_inside_speech"]
                                 or report["speech_dropped_before_in_sec"] > 0
                                 or report["speech_dropped_after_out_sec"] > 0)
    if not segs:
        report["warning"] = "no speech energy detected above threshold"
    return report


# ------------------------------------------------------ speech-safe trimming --
def plan_trim(clip: ClipSpec, analysis: Optional[dict], src_dur: float, cfg: dict) -> dict:
    """Decide the final [trim_in, trim_out] for one clip.

    auto_expand: trim_in  = min(trim_in,  max(0, first_speech - pre_handle))
                 trim_out = max(trim_out, min(src_dur, last_speech + post_handle))
    warn:        keep curated window, record diagnostics.
    off / lock_trim: keep curated window verbatim.
    Subtitles are trim-local, so widening trim_in by d shifts every cue by +d."""
    req_in = clip.trim_in
    req_out = src_dur if clip.trim_out is None else clip.trim_out
    notes: list[str] = []
    if req_out > src_dur + 1e-3:
        raise PipelineError(f"{clip.id}: trim_out {req_out:.3f} exceeds source duration "
                            f"{src_dur:.3f}; refusing to silently shorten the curated window")
    if req_in >= req_out:
        raise PipelineError(f"{clip.id}: trim_in {req_in} >= usable trim_out {req_out}")
    new_in, new_out = req_in, req_out
    mode = "locked" if clip.lock_trim else clip.speech_safe
    first = analysis.get("first_speech_sec") if analysis else None
    last = analysis.get("last_speech_sec") if analysis else None
    if mode == "auto_expand" and first is not None and last is not None:
        new_in = round(min(req_in, max(0.0, first - float(cfg["pre_handle"]))), 3)
        new_out = round(max(req_out, min(src_dur, last + float(cfg["post_handle"]))), 3)
        if new_in < req_in:
            notes.append(f"trim_in widened {req_in:.3f} -> {new_in:.3f} (speech at {first:.3f}s)")
        if new_out > req_out:
            notes.append(f"trim_out widened {req_out:.3f} -> {new_out:.3f} (speech until {last:.3f}s)")
        if first - new_in < float(cfg["pre_handle"]) - 1e-3:
            notes.append(f"pre-handle only {first - new_in:.3f}s (source starts close to speech)")
        if new_out - last < float(cfg["post_handle"]) - 1e-3:
            notes.append(f"post-handle only {new_out - last:.3f}s (source ends close to speech)")
    elif analysis and analysis.get("cuts_speech") and mode in ("warn", "locked"):
        notes.append(f"WARNING: curated trim cuts speech energy (mode={mode}); review by ear")
    shift = round(req_in - new_in, 3)
    return {"mode": mode, "requested": [round(req_in, 3), round(req_out, 3)],
            "final": [new_in, new_out], "duration": round(new_out - new_in, 3),
            "subtitle_shift": shift, "source_duration": round(src_dur, 3), "notes": notes}


def frame_quantize(dur: float, fps: float) -> tuple[int, float]:
    """Round UP to whole frames; never remove requested tail audio."""
    n = max(1, int(math.ceil(dur * fps - 1e-9)))
    return n, n / fps


# -------------------------------------------------------- splice + normalise --
def splice_clip(src: Path, segments: list[tuple[float, float]], dst: Path, cfg: dict,
                video: dict) -> Path:
    """Keep exact requested intervals; crossfade audio by d, then pad only
    the tail to whole video frames. Never read audio from the removed gap.
    Crossfade timing is recorded explicitly; internal cuts require listening."""
    validate_source_timeline(src, video)  # raw originals must be safe BEFORE PTS resets
    d = float(cfg.get("splice_crossfade", 0.02))
    src_dur = media_duration(src)
    if any(a < 0 or b > src_dur + 0.001 or b <= a for a, b in segments):
        raise PipelineError(f"splice interval outside source duration {src_dur:.4f}s")
    if d and any(b - a <= d for a, b in segments):
        raise PipelineError("splice intervals must be longer than the crossfade")
    fps = float(video["fps"])
    n, q = frame_quantize(sum(b - a for a, b in segments), fps)
    parts, alabels, vlabels = [], [], []
    for i, (a, b) in enumerate(segments):
        parts.append(f"[0:v]trim=start={a:.4f}:end={b:.4f},setpts=PTS-STARTPTS[v{i}]")
        parts.append(f"[0:a]atrim=start={a:.4f}:end={b:.4f},"
                     f"asetpts=N/SR/TB,aresample=48000[a{i}]")
        vlabels.append(f"[v{i}]"); alabels.append(f"[a{i}]")
    parts.append("".join(vlabels) + f"concat=n={len(segments)}:v=1:a=0,"
                 f"fps={fps:g},tpad=stop_mode=clone:stop_duration=1,trim=end_frame={n}[v]")
    cur = alabels[0]
    for i in range(1, len(segments)):
        nxt = f"[x{i}]"
        filt = f"acrossfade=d={d:g}:c1=tri:c2=tri" if d else "concat=n=2:v=0:a=1"
        parts.append(f"{cur}{alabels[i]}{filt}{nxt}"); cur = nxt
    parts.append(f"{cur}asetpts=N/SR/TB,apad,atrim=end_sample={round(q * 48000)}[a]")
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.stem + ".tmp" + dst.suffix)
    run(ffmpeg_cmd("-i", str(src), "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[a]",
                   "-c:v", "libx264", "-preset", "fast", "-crf", str(video["work_crf"]),
                   "-pix_fmt", "yuv420p", "-c:a", "pcm_s16le", str(tmp)), what=f"splice {src.name}")
    os.replace(tmp, dst)
    return dst


def _scale_filter(video: dict) -> str:
    w, h = int(video["width"]), int(video["height"])
    mode = video.get("scale_mode", "fill")
    if mode == "stretch":  # legacy behaviour of the reference scripts
        return f"scale={w}:{h}:flags=lanczos,setsar=1"
    if mode == "fit":
        return (f"scale={w}:{h}:force_original_aspect_ratio=decrease:flags=lanczos,"
                f"pad={w}:{h}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1")
    return (f"scale={w}:{h}:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop={w}:{h},setsar=1")


def normalize_clip(src: Path, t_in: float, t_out: float, dst_mp4: Path, dst_wav: Path,
                   video: dict, audio: dict) -> dict:
    """Trim [t_in, t_out] (frame-quantised), scale to WxH @ fps, loudnorm to
    48 kHz stereo.  Writes an AAC-192k MP4 (the per-clip audio that is later
    stream-copied) plus a PCM WAV sidecar of the very same samples (used for
    gap-free Base/Master concatenation without AAC re-encode generations)."""
    fps = float(video["fps"])
    n, q = frame_quantize(t_out - t_in, fps)
    sr, ch = int(audio["sample_rate"]), int(audio["channels"])
    fc = (f"[0:v]trim=start={t_in:.4f}:end={t_out:.4f},setpts=PTS-STARTPTS,{_scale_filter(video)},"
          f"fps={fps:g},tpad=stop_mode=clone:stop_duration=1,trim=end_frame={n},format=yuv420p[v];"
          f"[0:a]atrim=start={t_in:.4f}:end={t_out:.4f},asetpts=PTS-STARTPTS,{audio['loudnorm']},"
          f"aresample={sr},aformat=sample_fmts=fltp:channel_layouts={'stereo' if ch == 2 else 'mono'},"
          f"asetpts=N/SR/TB,apad,atrim=end_sample={int(round(q * sr))},asplit=2[a1][a2]")
    for p in (dst_mp4, dst_wav):
        p.parent.mkdir(parents=True, exist_ok=True)
    tmp_mp4 = dst_mp4.with_name(dst_mp4.stem + ".tmp.mp4")
    tmp_wav = dst_wav.with_name(dst_wav.stem + ".tmp.wav")
    run(ffmpeg_cmd("-i", str(src), "-filter_complex", fc,
                   "-map", "[v]", "-map", "[a1]", "-c:v", "libx264", "-preset", str(video["preset"]),
                   "-crf", str(video["work_crf"]), "-r", f"{fps:g}", "-c:a", "aac",
                   "-b:a", str(audio["bitrate"]), "-ar", str(sr), "-ac", str(ch),
                   "-movflags", "+faststart", str(tmp_mp4),
                   "-map", "[a2]", "-c:a", "pcm_s16le", "-ar", str(sr), "-ac", str(ch), str(tmp_wav)),
        what=f"normalize {src.name}")
    # Verify the rendered MP4 and PCM sidecar before replacing good media.
    wav_probe = probe_media(tmp_wav)["audio"]
    if not wav_probe or abs(wav_probe["duration"] - q) > 1 / sr + .0001:
        raise PipelineError("normalise: PCM sidecar duration mismatch")
    promote(SimpleNamespace(video=video, audio=audio), tmp_mp4, dst_mp4, q, "normalise")
    os.replace(tmp_wav, dst_wav)
    return {"frames": n, "duration": round(q, 4)}


# ------------------------------------------------ Persian RTL typography --
_FONT_CACHE: dict[tuple[str, int, str], ImageFont.FreeTypeFont] = {}
_REQUIRED_GLYPHS = (0x0627, 0x06CC, 0xFEE8, 0xFB8F)  # alef, farsi yeh, noon medial, keheh


def shaping_engine() -> str:
    """'reshaper' (arabic_reshaper + bidi, Pillow BASIC layout -- identical on
    Windows/Linux/macOS), else 'raqm' (Pillow does shaping + bidi), else 'none'."""
    if arabic_reshaper is not None and get_display is not None:
        return "reshaper"
    if features.check("raqm"):
        return "raqm"
    return "none"


def shape_fa(text: str, engine: Optional[str] = None) -> str:
    """Visual-order, presentation-form text for the 'reshaper' engine.  For
    'raqm' the logical string is returned untouched (raqm shapes it itself;
    pre-reshaping would reverse it twice)."""
    engine = engine or shaping_engine()
    if engine == "none":
        raise PipelineError("Persian shaping unavailable; install arabic-reshaper and python-bidi")
    if engine == "reshaper":
        return get_display(arabic_reshaper.reshape(text))
    return text


def font_has_persian(path: str) -> bool:
    """True when the font maps the glyphs Persian subtitles need.  Uses
    fontTools when installed; otherwise trusts any font Pillow can open."""
    try:
        from fontTools.ttLib import TTFont  # type: ignore
    except ImportError:
        try:
            ImageFont.truetype(path, 12)
            return True
        except OSError:
            return False
    try:
        tt = TTFont(path, fontNumber=0, lazy=True)
        cmap = tt.getBestCmap() or {}
        tt.close()
    except Exception:  # noqa: BLE001 - unreadable / unsupported font
        return False
    need = _REQUIRED_GLYPHS if shaping_engine() == "reshaper" else _REQUIRED_GLYPHS[:2]
    return all(cp in cmap for cp in need)


def resolve_font(*preferred: Optional[str]) -> tuple[str, list[str]]:
    """First existing Persian-capable font among: explicit candidates (CLI
    --font, manifest font_path), $FARSI_FLOW_FONT, the Windows Vazirmatn path,
    then Linux/macOS/Windows system fonts.  Returns (path, notes)."""
    notes: list[str] = []
    cands = [p for p in preferred if p] + [os.environ.get("FARSI_FLOW_FONT", ""), WINDOWS_FONT,
                                          *SYSTEM_FONT_CANDIDATES]
    for i, cand in enumerate(c for c in cands if c):
        p = Path(os.path.expanduser(cand))
        if is_foreign_windows_path(cand) or not p.is_file():
            if i < len([x for x in preferred if x]):
                notes.append(f"font not found: {cand}")
            continue
        if not font_has_persian(str(p)):
            notes.append(f"font lacks Persian glyphs, skipped: {p}")
            continue
        return str(p), notes
    raise PipelineError("no Persian-capable TTF found; pass --font /path/Vazirmatn-Bold.ttf "
                        "(tried: " + ", ".join(str(c) for c in cands if c) + ")")


def load_font(path: str, size: int, engine: str) -> ImageFont.FreeTypeFont:
    key = (path, size, engine)
    if key not in _FONT_CACHE:
        layout = ImageFont.Layout.RAQM if engine == "raqm" else ImageFont.Layout.BASIC
        _FONT_CACHE[key] = ImageFont.truetype(path, size, layout_engine=layout)
    return _FONT_CACHE[key]


def _measure(draw: ImageDraw.ImageDraw, text: str, font, engine: str) -> tuple[int, int, int, int]:
    kw = {"direction": "rtl"} if engine == "raqm" else {}
    return draw.textbbox((0, 0), text, font=font, **kw)


def _split_two_lines(text: str) -> list[str]:
    """Split at the word boundary that best balances the two halves (logical order)."""
    words = text.split()
    if len(words) < 2:
        return [text]
    best, best_cost = 1, float("inf")
    for k in range(1, len(words)):
        cost = abs(len(" ".join(words[:k])) - len(" ".join(words[k:])))
        if cost < best_cost:
            best, best_cost = k, cost
    return [" ".join(words[:best]), " ".join(words[best:])]


def fit_text(text: str, font_path: str, frame_w: int, size: int, min_size: int,
             margin: int, max_lines: int = 2, engine: Optional[str] = None) -> dict:
    """Auto-shrink (2 pt steps, ``size`` -> ``min_size``) until every line fits
    ``frame_w - margin``; if one line still overflows at ``min_size`` and
    ``max_lines >= 2``, balance-wrap into two lines and retry from ``size``."""
    engine = engine or shaping_engine()
    probe = ImageDraw.Draw(Image.new("RGBA", (8, 8)))
    limit = frame_w - margin
    layouts = [[text]] + ([_split_two_lines(text)] if max_lines >= 2 else [])
    result = None
    for lines in layouts:
        shaped = [shape_fa(ln, engine) for ln in lines]
        cur = int(size)
        while True:
            font = load_font(font_path, cur, engine)
            boxes = [_measure(probe, s, font, engine) for s in shaped]
            widest = max(b[2] - b[0] for b in boxes)
            result = {"lines": shaped, "boxes": boxes, "font": font, "font_size": cur,
                      "text_width": widest, "fits": widest <= limit, "engine": engine}
            if result["fits"] or cur <= min_size:
                break
            cur = max(int(min_size), cur - 2)  # 27, 25, ... 17, 16
        if result["fits"]:
            return result
    return result  # type: ignore[return-value]  # best effort; flagged by fits=False


def draw_rtl_pill(canvas: Image.Image, text_fa: str, font_path: str, *, y_center: int,
                  font_size: int = 27, min_font_size: int = 16, margin: int = 84,
                  text_color: tuple = DEFAULT_TEXT_COLOR, max_lines: int = 2,
                  engine: Optional[str] = None, shadow: bool = True) -> dict:
    """Draw one centred RTL Persian subtitle pill onto an RGBA ``canvas`` in place.

    Rounded dark pill (12,14,22,210) + gold outline (255,215,80,220) + soft
    drop shadow, text shadow (+2,+2) and the speaker colour.  Font auto-shrinks
    27 -> 16 pt so the text fits ``width - margin``; balance-wraps to two lines
    as a last resort.  Returns geometry + fit metadata for qa_report.json."""
    from PIL import ImageFilter
    w, h = canvas.size
    fit = fit_text(text_fa, font_path, w, font_size, min_font_size, margin, max_lines, engine)
    font, engine = fit["font"], fit["engine"]
    asc, desc = font.getmetrics()
    line_h, gap = asc + desc, max(4, int(0.18 * fit["font_size"]))
    tw, n = fit["text_width"], len(fit["lines"])
    th = n * line_h + (n - 1) * gap
    pad_x, pad_y, radius = 22, 12, 16
    rx0 = max(16, (w - tw) // 2 - pad_x)
    rx1 = min(w - 16, (w + tw) // 2 + pad_x)
    ry0 = int(y_center - th / 2 - pad_y)
    ry1 = int(y_center + th / 2 + pad_y)
    if shadow:  # soft drop shadow under the pill
        sh = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rounded_rectangle([rx0 + 2, ry0 + 5, rx1 + 2, ry1 + 5], radius=radius,
                                             fill=(0, 0, 0, 120))
        canvas.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5)))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=radius, fill=PILL_FILL,
                           outline=PILL_OUTLINE, width=2)
    kw = {"direction": "rtl"} if engine == "raqm" else {}
    fill = tuple(int(c) for c in text_color[:3]) + (255,)
    cx = w // 2
    for i, line in enumerate(fit["lines"]):
        cy = int(ry0 + pad_y + i * (line_h + gap) + line_h / 2)
        draw.text((cx + 2, cy + 2), line, font=font, fill=TEXT_SHADOW, anchor="mm", **kw)
        draw.text((cx, cy), line, font=font, fill=fill, anchor="mm", **kw)
    inside = rx0 >= 0 and ry0 >= 0 and rx1 <= w and ry1 <= h
    return {"box": [rx0, ry0, rx1, ry1], "font_size": fit["font_size"], "lines": n,
            "text_width": tw, "fits_width": bool(fit["fits"]), "inside_frame": inside,
            "engine": engine}


def render_pill_png(text_fa: str, font_path: str, frame_size: tuple[int, int], dst: Path,
                    **kw: Any) -> dict:
    """Render a pill on a transparent frame-sized canvas, crop to its alpha
    bounds and save as PNG.  Returns geometry incl. the overlay x/y offset."""
    canvas = Image.new("RGBA", frame_size, (0, 0, 0, 0))
    meta = draw_rtl_pill(canvas, text_fa, font_path, **kw)
    bbox = canvas.getbbox() or (0, 0, 2, 2)
    x0, y0 = bbox[0] - bbox[0] % 2, bbox[1] - bbox[1] % 2  # even offsets (yuv420p)
    crop = canvas.crop((x0, y0, bbox[2], bbox[3]))
    dst.parent.mkdir(parents=True, exist_ok=True)
    crop.save(dst, "PNG", optimize=True)
    meta.update(png=str(dst), x=int(x0), y=int(y0), png_size=list(crop.size))
    return meta


def subtitle_y(ep: Episode) -> int:
    return int(int(ep.video["height"]) * float(ep.subs["y_ratio"]))


@dataclass
class Overlay:
    """One timed PNG overlay on a clip-local timeline (seconds)."""
    start: float
    end: float
    kind: str  # 'sub' | 'badge'
    speaker: str
    text: str
    meta: dict


def build_overlays(ep: Episode, cues: list[Cue], clip_dur: float, png_dir: Path,
                   prefix: str, font_path: str, with_badge: bool) -> list[Overlay]:
    """PNG pills for one clip: optional Episode Badge (top, y_center=130,
    0.0..3.5 s) plus one pill per subtitle cue in the clip's local time."""
    size = (int(ep.video["width"]), int(ep.video["height"]))
    st = ep.subs
    out: list[Overlay] = []
    if with_badge and ep.badge:
        b = ep.badge
        b0, b1 = float(b["start"]), min(float(b["end"]), clip_dur)
        if b1 > b0:
            meta = render_pill_png(str(b["text"]), font_path, size, png_dir / f"{prefix}_badge.png",
                                   y_center=int(b["y_center"]), font_size=int(b["font_size"]),
                                   min_font_size=int(st["min_font_size"]),
                                   margin=int(st["max_text_margin"]),
                                   text_color=tuple(b["color"]), max_lines=1)
            out.append(Overlay(b0, b1, "badge", "", str(b["text"]), meta))
    for j, cue in enumerate(cues, 1):
        s0, s1 = max(0.0, cue.start), min(cue.end, clip_dur)
        if s1 <= s0:
            continue
        meta = render_pill_png(cue.text, font_path, size, png_dir / f"{prefix}_sub{j:02d}.png",
                               y_center=subtitle_y(ep), font_size=int(st["font_size"]),
                               min_font_size=int(st["min_font_size"]),
                               margin=int(st["max_text_margin"]),
                               text_color=ep.color_for(cue.speaker), max_lines=int(st["max_lines"]))
        out.append(Overlay(round(s0, 3), round(s1, 3), "sub", cue.speaker, cue.text, meta))
    return out


# ------------------------------------------------- build cache / provenance --
def fingerprint(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str,
                                     ensure_ascii=False).encode("utf-8")).hexdigest()


def _record_path(p: Path) -> Path:
    return p.with_name(p.name + ".build.json")


def cache_ok(outputs: list[Path], key: str) -> bool:
    """True when every output exists and its build record carries ``key``."""
    rec = _record_path(outputs[0])
    if not rec.is_file() or not all(p.is_file() and p.stat().st_size > 0 for p in outputs):
        return False
    try:
        record = json.loads(rec.read_text("utf-8"))
        hashes = record.get("output_hashes", {outputs[0].name: record.get("sha256")})
        return record.get("key") == key and all(
            hashes.get(p.name) == sha256_file(p) for p in outputs)
    except (OSError, json.JSONDecodeError):
        return False


def cache_write(output: Path, key: str, **extra: Any) -> None:
    rec = {"key": key, "pipeline_version": PIPELINE_VERSION, "sha256": sha256_file(output),
           "written_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **extra}
    _record_path(output).write_text(json.dumps(rec, indent=2, ensure_ascii=False), "utf-8")


def atomic_copy(src: Path, dst: Path) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.stem + ".tmp" + dst.suffix)
    shutil.copy2(src, tmp)
    os.replace(tmp, dst)
    return dst


def work_dir(ep: Episode) -> Path:
    return ep.out_dir / "_work" / ep.episode_id


def prepare_source(ep: Episode, clip: ClipSpec, work: Path, force: bool = False) -> tuple[Path, dict]:
    """Resolve the exact source for a clip.  With ``splice_segments``: splice
    ``raw_orig_file`` into the work dir (sources stay immutable -- clip_03.mp4
    is never overwritten); if the raw original is missing but ``file`` exists,
    ``file`` is taken as the already-spliced cut (recorded as a warning)."""
    file_p, raw_p = clip_source_paths(ep, clip)
    prov: dict[str, Any] = {"file": str(file_p), "raw_orig_file": str(raw_p) if raw_p else None}
    if clip.splice_segments:
        if raw_p is not None and raw_p.is_file():
            raw_sha = sha256_file(raw_p)
            spliced = work / f"{clip.id}_spliced.mov"
            key = fingerprint({"src": raw_sha, "segs": clip.splice_segments, "v": PIPELINE_VERSION,
                               "xf": ep.speech["splice_crossfade"], "fps": ep.video["fps"]})
            if force or not cache_ok([spliced], key):
                log(f"{clip.id}: splicing {raw_p.name} segments {clip.splice_segments}")
                splice_clip(raw_p, clip.splice_segments, spliced, ep.speech, ep.video)
                cache_write(spliced, key, source=str(raw_p))
            prov.update(mode="spliced", source=str(raw_p), source_sha256=raw_sha,
                        segments=[list(s) for s in clip.splice_segments], analysed=str(spliced))
            raw_analysis = analyze_clip_speech(raw_p, cfg=ep.speech)
            spans = raw_analysis["speech_segments"]
            d = float(ep.speech["splice_crossfade"])
            prov["splice_audit"] = {
                "raw_speech": raw_analysis, "crossfade_sec": d,
                "audio_overlap_sec": d * (len(clip.splice_segments)-1),
                "boundaries": splice_boundary_checks(clip.splice_segments, spans, d)}
            return spliced, prov
        if file_p.is_file():
            msg = (f"{clip.id}: raw_orig_file {clip.raw_orig_file!r} not found; using {file_p.name} "
                   f"as the pre-spliced cut (splice_segments not re-applied)")
            ep.warnings.append(msg)
            prov["warning"] = msg
        else:
            raise PipelineError(f"{clip.id}: neither raw_orig_file {raw_p} nor file {file_p} exists")
    if not file_p.is_file():
        raise PipelineError(f"{clip.id}: source not found: {file_p}")
    prov.update(mode=prov.get("mode", "pre_spliced_file" if clip.splice_segments else "direct"),
                source=str(file_p), source_sha256=sha256_file(file_p), analysed=str(file_p))
    return file_p, prov


def splice_boundary_checks(segments: list[tuple[float, float]],
                           spans: list, crossfade: float) -> list[dict]:
    """Audit ALL kept segment edges, including the outer head and tail cuts.

    Internal joins also inspect the crossfade neighborhood. Checking only
    joins would miss a word truncated at the last retained segment's end.
    Speech at the raw file's own edges still requires listening/regeneration.
    """
    boundaries = []
    for i, (lo, hi) in enumerate(segments):
        for edge, t in (("start", lo), ("end", hi)):
            internal = (edge == "start" and i > 0) or (edge == "end" and i < len(segments)-1)
            radius = crossfade if internal else 0.0
            boundaries.append({"segment_index": i, "edge": edge, "at_sec": t,
                               "internal": internal,
                               "crossfade_neighborhood_sec": radius,
                               "touches_speech": any(a < t + radius and b > t - radius
                                                     for a, b in spans)})
    return boundaries


def window_speech_check(analysis: dict, t_in: float, t_out: float) -> dict:
    """Re-evaluate the speech diagnostics for the FINAL trim window."""
    segs = [tuple(s) for s in analysis.get("speech_segments") or []]
    first, last = analysis.get("first_speech_sec"), analysis.get("last_speech_sec")
    dur = float(analysis.get("source_duration") or t_out)
    res = {"trim_in_inside_speech": any(a < t_in < b for a, b in segs),
           "trim_out_inside_speech": any(a < t_out < b for a, b in segs),
           "speech_dropped_sec": round(_speech_inside(segs, 0.0, t_in) + _speech_inside(segs, t_out, dur), 3),
           "pre_handle_sec": None if first is None else round(first - t_in, 3),
           "post_handle_sec": None if last is None else round(t_out - last, 3)}
    res["cuts_speech"] = bool(res["trim_in_inside_speech"] or res["trim_out_inside_speech"]
                              or res["speech_dropped_sec"] > 0)
    return res


def local_cues(ep: Episode, clip: ClipSpec, plan: dict, analysis: Optional[dict],
               clip_dur: float) -> tuple[list[Cue], list[dict]]:
    """Map manifest cues onto the rendered clip's timeline + bounds/speech checks.
    trim_local: local = cue + subtitle_shift   (cues authored vs. requested trim_in)
    source:     local = cue - final_trim_in    (cues authored in source seconds)"""
    t_in = plan["final"][0]
    segs = [(a - t_in, b - t_in) for a, b in (analysis or {}).get("speech_segments") or []]
    out, checks = [], []
    prev_end = -1.0
    for cue in clip.subtitles:
        off = plan["subtitle_shift"] if ep.subs["time_base"] == "trim_local" else -t_in
        s0, s1 = round(cue.start + off, 3), round(cue.end + off, 3)
        chk: dict[str, Any] = {"text": cue.text, "speaker": cue.speaker, "authored": [cue.start, cue.end],
                               "local": [s0, s1], "in_bounds": s0 >= -1e-3 and s1 <= clip_dur + 1e-3}
        if not chk["in_bounds"]:
            s0, s1 = max(0.0, s0), min(clip_dur, s1)
            chk["clamped_to"] = [round(s0, 3), round(s1, 3)]
            if plan.get("tight_speech_trim") and s1 - s0 > 0.3:
                # tight pacing trims the dead air the cue was authored over: expected, not an error
                chk["in_bounds"] = True
                chk["tight_trim_clamped"] = True
        chk["overlaps_previous"] = s0 < prev_end - 1e-3
        span = max(1e-6, s1 - s0)
        chk["speech_energy_ratio"] = round(_speech_inside(segs, s0, s1) / span, 3) if segs else None
        if chk["speech_energy_ratio"] is not None and chk["speech_energy_ratio"] < 0.2:
            chk["note"] = "little speech energy under this cue - verify wording/timing by ear"
        checks.append(chk)
        prev_end = max(prev_end, s1)
        if s1 > s0:
            out.append(Cue(round(s0, 3), round(s1, 3), cue.speaker, cue.text))
    return out, checks


def overlay_chain(base: str, overlays: list[Overlay], first_input: int,
                  offset: float = 0.0) -> tuple[list[str], str]:
    """ffmpeg overlay chain; each PNG is enabled on between(t, start, end)."""
    parts, cur = [], base
    for k, ov in enumerate(overlays):
        nxt = f"[ov{k}]"
        s0, s1 = ov.start + offset, ov.end + offset
        parts.append(f"{cur}[{first_input + k}:v]overlay=x={ov.meta['x']}:y={ov.meta['y']}:"
                     f"eof_action=repeat:enable='between(t,{s0:.4f},{s1:.4f})'{nxt}")
        cur = nxt
    return parts, cur


def render_subbed_clip(norm_mp4: Path, overlays: list[Overlay], dst: Path, video: dict,
                       audio: Optional[dict] = None) -> Path:
    """Burn the overlays onto the normalised clip and MUX ITS ORIGINAL FLOW
    AUDIO by stream copy (-map 0:a:0 -c:a copy): subtitles + native audio."""
    args: list[str] = ["-i", str(norm_mp4)]
    for ov in overlays:
        args += ["-i", ov.meta["png"]]
    parts, cur = overlay_chain("[0:v]", overlays, 1)
    parts.append(f"{cur}format=yuv420p[v]")
    tmp = dst.with_name(dst.stem + ".tmp.mp4")
    dst.parent.mkdir(parents=True, exist_ok=True)
    run(ffmpeg_cmd(*args, "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "0:a:0",
                   "-c:v", "libx264", "-preset", str(video["preset"]), "-crf", str(video["crf"]),
                   "-pix_fmt", "yuv420p", "-r", f"{float(video['fps']):g}", "-c:a", "copy",
                   "-movflags", "+faststart", str(tmp)), what=f"subtitle burn {dst.name}")
    promote(SimpleNamespace(video=video, audio=audio or AUDIO_DEFAULTS), tmp, dst,
            media_duration(norm_mp4), "subtitled clip")
    return dst


# ---------------------------------------------------- per-clip orchestration --
@dataclass
class ClipResult:
    clip: ClipSpec
    source: Path
    provenance: dict
    analysis: Optional[dict]
    plan: dict
    final_check: Optional[dict]
    norm_mp4: Optional[Path] = None
    norm_wav: Optional[Path] = None
    duration: float = 0.0
    frames: int = 0
    cues: list[Cue] = field(default_factory=list)
    cue_checks: list[dict] = field(default_factory=list)
    overlays: list[Overlay] = field(default_factory=list)
    subbed: list[Path] = field(default_factory=list)
    srt: list[Path] = field(default_factory=list)
    visual: Optional[dict] = None      # step 3 evaluation of the ORIGINAL Flow clip
    fallback: Optional[dict] = None    # step 5 resolution (+ extraction record)


def validate_source_timeline(src: Path, video: dict) -> dict:
    """Reject missing native streams, drift or offsets before any timestamp reset."""
    p = probe_media(src)
    if not p["video"] or not p["audio"]:
        raise PipelineError(f"{src.name}: Flow source must contain video AND original audio")
    if abs(p["video"]["duration"] - p["audio"]["duration"]) >= DRIFT_TOLERANCE:
        raise PipelineError(f"{src.name}: source A/V duration mismatch; repair before trimming")
    starts = [p[k]["start_time"] for k in ("video", "audio")]
    if max(abs(t) for t in starts) >= 1 / float(video["fps"]):
        raise PipelineError(f"{src.name}: source stream start offsets {starts}; "
                            "repair the source timeline before trimming (no silent A/V retiming)")
    if abs(starts[0] - starts[1]) >= 1 / float(video["fps"]):
        raise PipelineError(f"{src.name}: source A/V starts misaligned; repair before trimming")
    return p


def plan_clip(ep: Episode, clip: ClipSpec, work: Path, force: bool = False) -> ClipResult:
    """Source prep + speech analysis + speech-safe trim plan (no rendering)."""
    src, prov = prepare_source(ep, clip, work, force)
    validate_source_timeline(src, ep.video)
    src_dur = media_duration(src)
    req_out = src_dur if clip.trim_out is None else min(clip.trim_out, src_dur)
    analysis = None
    if clip.speech_safe != "off" or clip.lock_trim:
        analysis = analyze_clip_speech(src, clip.trim_in, req_out, ep.speech)
    plan = plan_trim(clip, analysis, src_dur, ep.speech)
    if analysis and tight_enabled(ep, clip):
        plan = apply_tight_speech_trim(plan, analysis.get("first_speech_sec"),
                                       analysis.get("last_speech_sec"), ep.speech)
    visual = clip_visual_gate(ep, clip, src)
    fallback = resolve_fallback(ep, clip, visual)
    if fallback["resolution"] == "source_bridge_fallback":
        if not fallback.get("source_on_host"):
            raise PipelineError(f"{clip.id}: visual gate failed ({', '.join(visual['flags'])}) and "
                                f"source_video {ep.source_video} is not on this host")
        fb_mp4 = work / f"{clip.id}_source_bridge.mp4"
        key = fingerprint({"src": sha256_file(Path(ep.source_video)), "span": clip.source_span,  # type: ignore[arg-type]
                           "audio": sha256_file(src), "anchor": plan["final"][0], "video": ep.video,
                           "v": PIPELINE_VERSION})
        if force or not cache_ok([fb_mp4], key):
            log(f"{clip.id}: visual gate {visual['flags']} -> source bridge {clip.source_span} "
                f"from {Path(ep.source_video).name} + native Flow audio")  # type: ignore[arg-type]
            rec = extract_source_fallback_clip(Path(ep.source_video), clip.source_span, src, fb_mp4,  # type: ignore[arg-type]
                                               video=ep.video, anchor_sec=plan["final"][0])
            cache_write(fb_mp4, key, **rec)
        fallback["extraction"] = json.loads(_record_path(fb_mp4).read_text("utf-8"))
        fallback.update(resolved=bool(fallback["extraction"].get("verified")),
                        status="pass" if fallback["extraction"].get("verified") else "fail",
                        reason="source bridge extraction verification")
        prov.update(visual_fallback=True, flow_clip=str(src), analysed=str(fb_mp4))
        src = fb_mp4
        ep.warnings.append(f"{clip.id}: video replaced by source_span {list(clip.source_span)} "  # type: ignore[arg-type]
                           f"({', '.join(visual['flags'])}); native Flow audio kept")
    elif fallback["resolution"] == "unresolved_visual_fail":
        # Missing evidence is itself a blocking diagnostic, not a crash while
        # formatting the warning. Preserve the failure through to qa_report.
        flags = (visual or {}).get("flags", ["VISUAL_EVIDENCE_MISSING"])
        ep.warnings.append(f"{clip.id}: visual continuity FAILED {flags} -- {fallback['reason']}")
    final = window_speech_check(analysis, *plan["final"]) if analysis else None
    for n in plan["notes"]:
        log(f"{clip.id}: {n}")
        if n.startswith("WARNING") or "clamped" in n:
            ep.warnings.append(f"{clip.id}: {n}")
    if final and final["cuts_speech"]:
        ep.warnings.append(f"{clip.id}: final trim {plan['final']} still touches speech energy "
                           f"(mode={plan['mode']}) - listen to both edges")
    return ClipResult(clip, src, prov, analysis, plan, final, visual=visual, fallback=fallback)


def clip_visual_gate(ep: Episode, clip: ClipSpec, src: Path) -> Optional[dict]:
    """Step 3 for one clip: probe-JSON entry (headless) or live frame sampling."""
    v = ep.visual
    kw = dict(keyframe_threshold=v["keyframe_threshold"], jump_threshold=v["jump_threshold"],
              contamination_margin=v["contamination_margin"])
    if ep.probe and clip.id in ep.probe:
        return {**evaluate_probe_entry(ep.probe[clip.id], clip_id=clip.id, **kw), "source": "probe_json"}
    if clip.keyframe is not None and Path(clip.keyframe).is_file():
        kfs = {c.id: c.keyframe for c in ep.clips}
        res = analyze_clip_visuals(src, clip.keyframe, kfs, sample_fps=v["sample_fps"],
                                   size=tuple(v["thumb_size"]), clip_id=clip.id, **kw)
        ev = {**res["evaluation"], "source": "live_mp4"}
        if clip.notes and "force_source_bridge" in clip.notes and ev.get("passed"):
            ev["flags"] = list(ev.get("flags", [])) + ["KEYFRAME_MISMATCH"]
            ev["passed"] = False
        return ev
    return None


def clip_output_paths(ep: Episode, clip: ClipSpec, name: str) -> list[Path]:
    """Where per-clip deliverables go: clips_dir and/or <out_dir>/clips_subbed."""
    where = str(ep.outputs.get("per_clip_location", "both"))
    dirs = {"both": [ep.out_dir / "clips_subbed", ep.clips_dir],
            "out_dir": [ep.out_dir / "clips_subbed"], "clips_dir": [ep.clips_dir]}.get(where)
    if dirs is None:
        raise PipelineError("outputs.per_clip_location must be both | out_dir | clips_dir")
    return [d / name for d in dirs]


def render_clip(ep: Episode, res: ClipResult, work: Path, font_path: str,
                force: bool = False) -> ClipResult:
    """Normalise + burn subtitles (badge on the badge clip) WITH original audio."""
    clip, (t_in, t_out) = res.clip, res.plan["final"]
    norm_key = fingerprint({"src": sha256_file(res.source), "segs": clip.splice_segments,
                            "trim": [t_in, t_out], "video": ep.video, "audio": ep.audio,
                            "v": PIPELINE_VERSION})
    res.norm_mp4, res.norm_wav = work / f"{clip.id}_norm.mp4", work / f"{clip.id}_norm.wav"
    if force or not cache_ok([res.norm_mp4, res.norm_wav], norm_key):
        log(f"{clip.id}: normalise {res.source.name} [{t_in:.3f}, {t_out:.3f}] -> "
            f"{ep.video['width']}x{ep.video['height']}@{ep.video['fps']} + loudnorm")
        info = normalize_clip(res.source, t_in, t_out, res.norm_mp4, res.norm_wav, ep.video, ep.audio)
        cache_write(res.norm_mp4, norm_key, **info, output_hashes={
            p.name: sha256_file(p) for p in (res.norm_mp4, res.norm_wav)})
    rec = json.loads(_record_path(res.norm_mp4).read_text("utf-8"))
    res.frames, res.duration = int(rec["frames"]), float(rec["duration"])
    res.plan["render_duration"] = res.duration
    res.plan["tail_padding_sec"] = round(res.duration - (t_out - t_in), 4)

    res.cues, res.cue_checks = local_cues(ep, clip, res.plan, res.analysis, res.duration)
    for chk in res.cue_checks:
        if not chk["in_bounds"]:
            ep.warnings.append(f"{clip.id}: cue {chk['authored']} outside clip (0..{res.duration:.3f}); clamped")
    with_badge = bool(ep.badge) and clip.index == int(ep.badge.get("clip_index", 1))
    res.overlays = build_overlays(ep, res.cues, res.duration, work / "pills", clip.id, font_path,
                                  with_badge)
    sub_key = fingerprint({"norm": norm_key, "font": sha256_file(Path(font_path)),
                           "engine": shaping_engine(), "style": ep.subs, "badge": ep.badge, "crf": ep.video["crf"],
                           "ov": [(o.kind, o.start, o.end, o.text, o.meta["x"], o.meta["y"],
                                   o.meta["font_size"], ep.color_for(o.speaker)) for o in res.overlays]})
    name = f"{clip.id}_subbed"
    targets = clip_output_paths(ep, clip, name + ".mp4")
    primary = targets[0]
    if force or not cache_ok([primary], sub_key):
        log(f"{clip.id}: burn {len(res.overlays)} overlay(s) + mux original Flow audio -> {primary}")
        render_subbed_clip(res.norm_mp4, res.overlays, primary, ep.video, ep.audio)
        cache_write(primary, sub_key, clip=clip.id, frames=res.frames, duration=res.duration)
    res.subbed = [primary]
    srt_cues = [(c.start, c.end, c.text) for c in res.cues]
    write_srt(primary.with_suffix(".srt"), srt_cues)
    res.srt = [primary.with_suffix(".srt")]
    for extra in targets[1:]:
        try:
            if not (extra.is_file() and sha256_file(extra) == sha256_file(primary)):
                atomic_copy(primary, extra)
            write_srt(extra.with_suffix(".srt"), srt_cues)
            res.subbed.append(extra)
            res.srt.append(extra.with_suffix(".srt"))
        except OSError as exc:
            ep.warnings.append(f"{clip.id}: could not write {extra} ({exc})")
    return res


def run_clips(ep: Episode, force: bool = False, render: bool = True,
              only: Optional[set[str]] = None) -> tuple[list[ClipResult], Optional[str], list[str]]:
    """Plan (and optionally render) every clip.  Returns (results, font, notes)."""
    work = work_dir(ep)
    work.mkdir(parents=True, exist_ok=True)
    font_path, font_notes = (None, [])
    if render:
        font_path, font_notes = resolve_font(ep.font_path)
        for n in font_notes:
            ep.warnings.append(n)
        log(f"font: {font_path} (shaping: {shaping_engine()})")
    results = []
    for clip in ep.clips:
        if only and clip.id not in only and str(clip.index) not in only:
            continue
        res = plan_clip(ep, clip, work, force)
        if render:
            res = render_clip(ep, res, work, font_path, force)  # type: ignore[arg-type]
        results.append(res)
    if not results:
        raise PipelineError("--only matched no clips")
    return results, font_path, font_notes


# ------------------------------------------- visual continuity gate (v1.2) --
# Keyframes are READ-ONLY inputs here: they are opened, downscaled in memory
# and compared.  Nothing in this module ever draws on, blurs, boxes or
# rewrites a keyframe file.  (No `sanitize_*_keyframes` -- by design.)
def _thumb_rgb(img: Image.Image, size: tuple[int, int]) -> np.ndarray:
    return np.asarray(img.convert("RGB").resize(tuple(size), Image.BILINEAR), dtype=np.float32)


def load_keyframe_thumb(path: Path, size: tuple[int, int] = (72, 128)) -> np.ndarray:
    with Image.open(path) as im:
        im.load()
        return _thumb_rgb(im, size)


def l1(a: np.ndarray, b: np.ndarray) -> float:
    """Mean absolute RGB difference on a 0..255 scale (same metric as the probe JSON)."""
    return round(float(np.mean(np.abs(a.astype(np.float32) - b.astype(np.float32)))), 2)


def sample_video_thumbs(mp4_path: Path, sample_fps: float = 2.0,
                        size: tuple[int, int] = (72, 128)) -> list[np.ndarray]:
    w, h = int(size[0]), int(size[1])
    proc = run(ffmpeg_cmd("-i", str(mp4_path), "-map", "0:v:0", "-an",
                          "-vf", f"fps={sample_fps:g},scale={w}:{h}:flags=bilinear",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"),
               capture=True, what=f"sample frames {Path(mp4_path).name}")
    n = len(proc.stdout) // (w * h * 3)
    arr = np.frombuffer(proc.stdout[: n * w * h * 3], dtype=np.uint8).reshape(n, h, w, 3)
    return [f.astype(np.float32) for f in arr]


def analyze_clip_visuals(mp4_path: Path, keyframe_path: Optional[Path] = None,
                         all_keyframes: Optional[dict[str, Path]] = None,
                         sample_fps: float = 2.0, size: tuple[int, int] = (72, 128),
                         jump_threshold: float = 32.0, clip_id: str = "",
                         **eval_kw: Any) -> dict:
    """Live visual probe of one Flow clip: L1 distance of sampled frames to its
    own keyframe, to every OTHER keyframe of the episode (leftover-chip
    contamination) and frame-to-frame jumps (hard internal cuts).  Produces the
    same schema as ``parts1_to_5_clips_probe.json`` plus ``evaluate_probe_entry``."""
    frames = sample_video_thumbs(Path(mp4_path), sample_fps, size)
    if not frames:
        raise PipelineError(f"{Path(mp4_path).name}: no video frames decoded")
    entry: dict[str, Any] = {"file": Path(mp4_path).name, "num_sampled_frames": len(frames),
                             "sample_fps": sample_fps}
    if keyframe_path is not None and Path(keyframe_path).is_file():
        kf = load_keyframe_thumb(Path(keyframe_path), size)
        d = [l1(f, kf) for f in frames]
        entry.update(l1_vs_keyframe_mean=round(float(np.mean(d)), 2),
                     l1_vs_keyframe_start=d[0], l1_vs_keyframe_end=d[-1])
    others = {k: p for k, p in (all_keyframes or {}).items()
              if k != clip_id and p is not None and Path(p).is_file()
              and (keyframe_path is None or Path(p).resolve() != Path(keyframe_path).resolve())}
    if others:
        dist = {k: l1(frames[0], load_keyframe_thumb(Path(p), size)) for k, p in others.items()}
        best = min(dist, key=dist.get)
        entry.update(closest_other_keyframe=best, closest_other_keyframe_l1_start=dist[best])
    jumps: list[float] = []
    for i in range(1, len(frames)):
        raw_j = l1(frames[i], frames[i - 1])
        quant_j = round(float(np.mean(np.abs(
            np.sort(frames[i].reshape(-1, 3), axis=0) - np.sort(frames[i - 1].reshape(-1, 3), axis=0)
        ))), 2)
        eff_j = min(raw_j, quant_j)
        if i + 1 < len(frames):
            bridge_j = l1(frames[i + 1], frames[i - 1])
            if bridge_j < jump_threshold * 0.5:
                eff_j = min(eff_j, bridge_j)
        if i >= 2:
            prev_bridge_j = l1(frames[i], frames[i - 2])
            if prev_bridge_j < jump_threshold * 0.5:
                eff_j = min(eff_j, prev_bridge_j)
        jumps.append(eff_j)
    if jumps:
        j = int(np.argmax(jumps))
        entry.update(max_internal_jump_l1=jumps[j], max_internal_jump_time_sec=round((j + 1) / sample_fps, 2))
    entry["detected_scene_cuts_sec"] = [round((i + 1) / sample_fps, 2)
                                        for i, v in enumerate(jumps) if v > jump_threshold]
    entry["evaluation"] = evaluate_probe_entry(entry, clip_id=clip_id, jump_threshold=jump_threshold,
                                               sample_fps=sample_fps, **eval_kw)
    return entry


def evaluate_probe_entry(probe_entry: dict, *, clip_id: str = "", keyframe_threshold: float = 32.0,
                         jump_threshold: float = 32.0, contamination_margin: float = 5.0,
                         sample_fps: Optional[float] = None,
                         clip_duration: Optional[float] = None) -> dict:
    """Pure function (no media needed): turns one probe entry into gate flags.

    KEYFRAME_MISMATCH               l1_start > thr AND l1_mean > thr
                                    (keyframe dropped -> 0-ingredient T2V hallucination)
    MULTI_INGREDIENT_CONTAMINATION  closest_other_l1_start + margin < l1_start
                                    (a leftover composer chip steered the clip)
    INTERNAL_SCENE_CUT              max_internal_jump_l1 > jump_thr  (+ suggested visual trim)
    KEYFRAME_DRIFT (warning only)   start locked but the clip ends far from the keyframe."""
    if not isinstance(probe_entry, dict):
        raise PipelineError(f"{clip_id}: probe entry must be an object")
    e = probe_entry

    def number(value: Any, field: str, lo: float = 0.0, hi: float = float("inf")) -> float:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) \
                or not lo <= value <= hi:
            raise PipelineError(f"{clip_id}: invalid probe {field}: {value!r}")
        return float(value)

    fps = number(sample_fps if sample_fps is not None else e.get("sample_fps", 2.0), "sample_fps", .001)
    n = number(e.get("num_sampled_frames"), "num_sampled_frames", 2)
    if n != int(n):
        raise PipelineError(f"{clip_id}: probe num_sampled_frames must be an integer")
    dur = number(clip_duration if clip_duration is not None else n / fps, "duration", .001)
    for field in ("l1_vs_keyframe_start", "l1_vs_keyframe_mean", "l1_vs_keyframe_end",
                  "max_internal_jump_l1"):
        number(e.get(field), field, 0, 255)
    if e.get("closest_other_keyframe_l1_start") is not None:
        number(e["closest_other_keyframe_l1_start"], "closest_other_keyframe_l1_start", 0, 255)
    number(e.get("max_internal_jump_time_sec"), "max_internal_jump_time_sec", 0, dur)
    cuts_raw = e.get("detected_scene_cuts_sec", [])
    if not isinstance(cuts_raw, list):
        raise PipelineError(f"{clip_id}: probe detected_scene_cuts_sec must be a list")
    for cut in cuts_raw:
        number(cut, "detected_scene_cuts_sec", 0, dur)
    for name, val in (("keyframe_threshold", keyframe_threshold), ("jump_threshold", jump_threshold),
                      ("contamination_margin", contamination_margin)):
        number(val, name, 0, 255)
    step = 1.0 / fps
    flags: list[str] = []
    warnings: list[str] = []
    start, mean, end = (e.get(k) for k in ("l1_vs_keyframe_start", "l1_vs_keyframe_mean", "l1_vs_keyframe_end"))
    other = e.get("closest_other_keyframe_l1_start")
    jump = e.get("max_internal_jump_l1")
    if start is None:
        warnings.append("NO_KEYFRAME_REFERENCE")
    else:
        if start > keyframe_threshold and mean > keyframe_threshold:
            flags.append("KEYFRAME_MISMATCH")
        if other is not None and float(other) + contamination_margin < float(start):
            flags.append("MULTI_INGREDIENT_CONTAMINATION")
        if start <= keyframe_threshold and end is not None and end > keyframe_threshold:
            warnings.append("KEYFRAME_DRIFT")
    cuts = sorted(float(c) for c in (e.get("detected_scene_cuts_sec") or []))
    if jump is not None and float(jump) > jump_threshold:
        flags.append("INTERNAL_SCENE_CUT")
        t = e.get("max_internal_jump_time_sec")
        if t is not None and not any(abs(float(t) - c) < 1e-6 for c in cuts):
            cuts = sorted(cuts + [float(t)])
    trim_in, trim_out = 0.0, round(dur, 3)
    if "INTERNAL_SCENE_CUT" in flags and cuts:
        bounds = [0.0] + cuts + [dur]
        segs = [(bounds[i], bounds[i + 1] - (step if i + 1 < len(bounds) - 1 else 0.0))
                for i in range(len(bounds) - 1)]
        segs = [(a, b) for a, b in segs if b > a]
        start_locked = start is not None and start <= keyframe_threshold
        # keep the segment that still shows the keyframe scene (the first one) when
        # the start is locked; otherwise keep the longest coherent segment
        pick = (0.0, max(0.0, cuts[0] - step)) if start_locked else \
            max(segs, key=lambda s: s[1] - s[0], default=(0.0, 0.0))
        trim_in, trim_out = round(pick[0], 3), round(pick[1], 3)
    return {"clip_id": clip_id or e.get("file", ""), "flags": flags, "warnings": warnings,
            "passed": not flags, "suggested_visual_trim_in": trim_in,
            "suggested_visual_trim_out": trim_out,
            "suggested_visual_duration": round(trim_out - trim_in, 3),
            "thresholds": {"keyframe": keyframe_threshold, "jump": jump_threshold,
                           "contamination_margin": contamination_margin},
            "metrics": {k: e.get(k) for k in ("l1_vs_keyframe_start", "l1_vs_keyframe_mean",
                                               "l1_vs_keyframe_end", "closest_other_keyframe",
                                               "closest_other_keyframe_l1_start", "max_internal_jump_l1",
                                               "max_internal_jump_time_sec")} | {"scene_cuts_sec": cuts}}


# -------------------------------- source subtitle-band inpaint + fallback --
SUB_BAND_Y = (0.73, 0.89)
SUB_BAND_X = (0.08, 0.92)


def _dilate(mask: np.ndarray, r: int) -> np.ndarray:
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dy or dx:
                out |= np.roll(np.roll(mask, dy, 0), dx, 1)
    return out


def subtitle_text_mask(band: np.ndarray) -> np.ndarray:
    """Burned-in white / yellow subtitle glyphs (+ dark outline) inside the band."""
    r, g, b = (band[..., i].astype(np.int16) for i in range(3))
    white = (r > 210) & (g > 210) & (b > 210)
    yellow = (r > 200) & (g > 170) & (b < 140) & (r - b > 90)
    return _dilate(white | yellow, 3)


def inpaint_source_subtitle_band(rgb: np.ndarray) -> np.ndarray:
    """Remove burned-in English subtitles from a SOURCE EPISODE video frame.

    numpy-only: masked pixels are rebuilt by row-wise linear interpolation
    between the nearest unmasked neighbours, averaged with a column-wise pass,
    so the band blends into the scene; the Farsi pill is later drawn on top.
    Applied to source-video frames for the hybrid bridge only -- never to the
    Flow keyframes."""
    out = np.array(rgb, dtype=np.float32, copy=True)
    h, w = out.shape[:2]
    y0, y1 = int(h * SUB_BAND_Y[0]), int(h * SUB_BAND_Y[1])
    x0, x1 = int(w * SUB_BAND_X[0]), int(w * SUB_BAND_X[1])
    band = out[y0:y1, x0:x1]
    mask = subtitle_text_mask(band)
    if mask.sum() < 12:
        return np.asarray(rgb).copy()

    def fill(arr: np.ndarray, m: np.ndarray) -> np.ndarray:  # interpolate along axis 1
        res = arr.copy()
        xs = np.arange(arr.shape[1])
        for i in np.flatnonzero(m.any(axis=1)):
            keep = ~m[i]
            if keep.sum() < 2:
                continue
            for c in range(3):
                res[i, m[i], c] = np.interp(xs[m[i]], xs[keep], arr[i, keep, c])
        return res

    horiz = fill(band, mask)
    vert = fill(band.transpose(1, 0, 2), mask.T).transpose(1, 0, 2)
    rows_ok = mask.T.sum(axis=1) < mask.shape[0] - 1  # columns with any unmasked pixel
    blend = np.where(rows_ok[None, :, None], 0.5 * horiz + 0.5 * vert, horiz)
    band[mask] = blend[mask]
    out[y0:y1, x0:x1] = band
    return np.clip(out, 0, 255).astype(np.uint8)


def audio_stream_sha256(path: Path) -> str:
    """Hash compressed audio packet payloads, not the containing MP4 file."""
    raw = run(ffmpeg_cmd("-i", str(path), "-map", "0:a:0", "-c:a", "copy",
                         "-f", "hash", "-hash", "sha256", "pipe:1"),
              capture=True, what="hash native audio stream").stdout.decode().strip()
    if not re.fullmatch(r"SHA256=[0-9a-fA-F]{64}", raw):
        raise PipelineError(f"could not hash audio stream: {path}")
    return raw.partition("=")[2].lower()


def extract_source_fallback_clip(source_video: Path, source_span: tuple[float, float],
                                 flow_audio_mp4: Path, out_mp4: Path, *, video: Optional[dict] = None,
                                 anchor_sec: float = 0.0, inpaint: bool = True) -> dict:
    """Hybrid bridge: VIDEO = original episode ``source_span`` (subtitle band
    inpainted), AUDIO = the untouched native Google Flow Farsi track of
    ``flow_audio_mp4``.  The output has exactly the Flow clip's duration so the
    existing speech-safe / tight trim plan applies unchanged; the source span
    starts at ``anchor_sec`` (the planned trim-in) and its first/last frame is
    held when the speech window is longer than the span."""
    video = _merged(VIDEO_DEFAULTS, video)
    w, h, fps = int(video["width"]), int(video["height"]), float(video["fps"])
    span = _parse_span(source_span, "fallback")
    if span is None:
        raise PipelineError("fallback source_span is required")
    s0, s1 = span
    if out_mp4.resolve() in (source_video.resolve(), flow_audio_mp4.resolve()):
        raise PipelineError("fallback output would overwrite an input source")
    validate_source_timeline(Path(flow_audio_mp4), video)
    flow_dur = media_duration(Path(flow_audio_mp4))
    src_probe = probe_media(Path(source_video))["video"]
    if not src_probe:
        raise PipelineError("source_span needs a source video stream")
    src_dur = src_probe["duration"]
    if not 0 <= s0 < s1 <= src_dur:
        raise PipelineError(f"source_span {source_span} outside {Path(source_video).name} ({src_dur:.2f}s)")
    if not math.isfinite(anchor_sec) or not 0 <= anchor_sec < flow_dur:
        raise PipelineError("fallback anchor_sec must be inside the Flow timeline")
    lead = anchor_sec                     # hold first span frame before the anchor
    span_len = s1 - s0
    tail = max(0.0, flow_dur - lead - span_len)     # hold last span frame after the span
    n_frames = max(1, int(math.ceil(flow_dur * fps - 1e-9)))
    vf = (f"trim=start={s0:.4f}:end={s1:.4f},setpts=PTS-STARTPTS,{_scale_filter(video)},fps={fps:g},"
          f"tpad=start_mode=clone:start_duration={lead:.4f}:stop_mode=clone:stop_duration={tail + 1:.4f},"
          f"trim=end_frame={n_frames},format=rgb24")
    dec = subprocess.Popen(ffmpeg_cmd("-i", str(source_video), "-map", "0:v:0", "-an", "-vf", vf,
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"),
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_mp4.with_name(out_mp4.stem + ".tmp.mp4")
    errf = tempfile.TemporaryFile()
    enc = subprocess.Popen(ffmpeg_cmd("-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                                      "-r", f"{fps:g}", "-i", "pipe:0", "-i", str(flow_audio_mp4),
                                      "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264",
                                      "-preset", str(video["preset"]), "-crf", str(video["work_crf"]),
                                      "-pix_fmt", "yuv420p", "-c:a", "copy", "-t", f"{flow_dur:.4f}",
                                      "-movflags", "+faststart", str(tmp)),
                           stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errf)
    fsz, written, inpainted = w * h * 3, 0, 0
    assert dec.stdout is not None and enc.stdin is not None
    try:
        while True:
            buf = dec.stdout.read(fsz)
            if not buf:
                break
            if len(buf) != fsz:
                raise PipelineError("source fallback decoder returned a partial frame")
            frame = np.frombuffer(buf, np.uint8).reshape(h, w, 3)
            if inpaint:
                new = inpaint_source_subtitle_band(frame)
                inpainted += int(not np.array_equal(new, frame))
                frame = new
            enc.stdin.write(frame.tobytes())
            written += 1
        enc.stdin.close()
        dec.wait(timeout=60)
        enc.wait(timeout=60)
        errf.seek(0)
        err = errf.read()
        if dec.returncode != 0 or enc.returncode != 0 or written != n_frames:
            raise PipelineError(f"source fallback failed: decoder={dec.returncode}, encoder={enc.returncode}, "
                                f"frames={written}/{n_frames}: {err.decode('utf-8', 'replace')[-400:]}")
        probe = probe_media(tmp)
        v, a = probe["video"], probe["audio"]
        if not v or not a or (v["width"], v["height"]) != (w, h) or abs(v["fps"] - fps) > .01 \
                or abs(v["duration"] - flow_dur) > 1 / fps + .01 \
                or abs(v["duration"] - a["duration"]) >= DRIFT_TOLERANCE or audio_pts_gaps(tmp):
            raise PipelineError("source fallback media verification failed; previous output kept")
        audio_hash = audio_stream_sha256(Path(flow_audio_mp4))
        output_audio_hash = audio_stream_sha256(tmp)
        if audio_hash != output_audio_hash:
            raise PipelineError("source fallback changed the native Flow audio stream")
        os.replace(tmp, out_mp4)
    except (BrokenPipeError, subprocess.TimeoutExpired) as exc:
        raise PipelineError(f"source fallback subprocess failed: {exc}") from exc
    finally:
        for proc in (dec, enc):
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        dec.stdout.close()
        if not enc.stdin.closed:
            enc.stdin.close()
        errf.close()
        tmp.unlink(missing_ok=True)
    return {"mode": "source_bridge_video_with_flow_audio", "source_video": str(source_video),
            "source_span": [s0, round(s1, 3)], "flow_audio": str(flow_audio_mp4),
            "flow_audio_sha256": sha256_file(Path(flow_audio_mp4)), "anchor_sec": round(lead, 3),
            "frames": written, "frames_inpainted": inpainted, "duration": round(flow_dur, 4),
            "verified": True, "flow_audio_stream_sha256": audio_hash,
            "output_audio_stream_sha256": output_audio_hash,
            "source_span_bounds_verified": True, "source_duration": src_dur,
            "output_path": str(out_mp4)}


# ------------------------------------------------------ tight speech pacing --
def tight_enabled(ep: Episode, clip: ClipSpec) -> bool:
    return ep.tight_speech_trim if clip.tight_speech_trim is None else bool(clip.tight_speech_trim)


def apply_tight_speech_trim(plan: dict, first: Optional[float], last: Optional[float], cfg: dict,
                            min_duration: float = TIGHT_MIN_DURATION) -> dict:
    """[max(trim_in, first - pre), min(trim_out, last + post)], never < min_duration.
    Subtitle shift is recomputed so trim-local cues stay glued to the audio."""
    if first is None or last is None or plan.get("mode") == "locked":
        return plan
    t_in, t_out = plan["final"]
    new_in = max(t_in, first - float(cfg["pre_handle"]))
    new_out = min(t_out, last + float(cfg["post_handle"]))
    if new_out - new_in < min_duration:                 # grow symmetrically inside the window
        pad = (min_duration - (new_out - new_in)) / 2
        new_in, new_out = max(t_in, new_in - pad), min(t_out, new_out + pad)
        if new_out - new_in < min_duration:
            new_in, new_out = (t_in, min(t_out, t_in + min_duration)) if new_in <= t_in + 1e-6 \
                else (max(t_in, t_out - min_duration), t_out)
    new_in, new_out = round(new_in, 3), round(new_out, 3)
    if (new_in, new_out) == (t_in, t_out):
        return {**plan, "tight_speech_trim": True}
    out = dict(plan)
    out["notes"] = list(plan["notes"]) + [
        f"tight_speech_trim {t_in:.3f}-{t_out:.3f} -> {new_in:.3f}-{new_out:.3f} "
        f"(speech {first:.3f}-{last:.3f}, dead air {t_out - t_in - (last - first):.2f}s -> "
        f"{new_out - new_in - (last - first):.2f}s)"]
    out["pre_tight"] = [t_in, t_out]
    out["final"] = [new_in, new_out]
    out["duration"] = round(new_out - new_in, 3)
    out["subtitle_shift"] = round(plan["requested"][0] - new_in, 3)
    out["tight_speech_trim"] = True
    return out


# ------------------------------------------------- verification (ffprobe) --
def audio_pts_gaps(path: Path, tol_sec: float = 0.002) -> list[dict]:
    """Audio timeline holes: pts jumps between packets, or a (non-final)
    packet whose duration deviates from the codec frame (AAC: 1024 samples) --
    the mp4 muxer often records a filter-graph pts hole as one stretched
    packet.  Either plays as a silent gap and shifts every later sample against
    the video, which a container-duration drift check alone can hide."""
    out = run([FFPROBE, "-v", "error", "-select_streams", "a:0", "-show_entries",
               "packet=pts_time,duration_time", "-of", "csv=p=0", str(path)],
              capture=True, what="ffprobe packets").stdout.decode("utf-8", "replace")
    rows = [r.split(",")[:2] for r in out.splitlines() if len(r.split(",")) >= 2]
    pk = [(float(a), float(b)) for a, b in rows if a not in ("", "N/A") and b not in ("", "N/A")]
    if len(pk) < 3:
        return []
    nominal = float(np.median([d for _, d in pk]))
    gaps = []
    for i, ((t0, d0), (t1, _)) in enumerate(zip(pk, pk[1:])):
        hole = t1 - (t0 + d0)
        if abs(hole) > tol_sec:
            gaps.append({"at_sec": round(t0 + d0, 4), "gap_sec": round(hole, 4), "kind": "pts_jump"})
        elif i > 0 and abs(d0 - nominal) > tol_sec:  # i == 0 may be the encoder-priming packet
            gaps.append({"at_sec": round(t0 + nominal, 4), "gap_sec": round(d0 - nominal, 4),
                         "kind": "stretched_packet"})
    return gaps


def av_checks(ep: Episode, path: Path, expected: Optional[float] = None) -> dict:
    """ffprobe gate: h264 WxH @ fps video + aac 48 kHz stereo audio, A/V drift
    < 0.15 s, gap-free audio packet timestamps, and (optionally) duration
    within ~1.5 frames of ``expected``."""
    p = probe_media(path)
    v, a = p["video"], p["audio"]
    fps = float(ep.video["fps"])
    c = {"has_video": v is not None, "has_audio": a is not None,
         "video_h264": bool(v) and v["codec"] == "h264",
         "video_size": bool(v) and (v["width"], v["height"]) == (int(ep.video["width"]), int(ep.video["height"])),
         "video_fps": bool(v) and abs(v["fps"] - fps) < 0.01,
         "audio_aac": bool(a) and a["codec"] == "aac",
         "audio_rate_channels": bool(a) and a["sample_rate"] == int(ep.audio["sample_rate"])
                                and a["channels"] == int(ep.audio["channels"])}
    drift = round(abs(v["duration"] - a["duration"]), 4) if v and a else None
    c["av_drift_ok"] = drift is not None and drift < DRIFT_TOLERANCE
    c["av_start_aligned"] = bool(v and a) and abs(v["start_time"] - a["start_time"]) < 1 / fps
    c["starts_at_zero"] = bool(v and a) and max(abs(v["start_time"]), abs(a["start_time"])) < 1 / fps
    gaps = audio_pts_gaps(path) if a else []
    c["audio_contiguous"] = bool(a) and not gaps
    if expected is not None:
        c["duration_ok"] = bool(v) and abs(v["duration"] - expected) <= 1.5 / fps + 0.02
    return {"path": str(path), "sha256": sha256_file(path), "probe": p, "av_drift_sec": drift,
            "audio_pts_gaps": gaps,
            "expected_duration": None if expected is None else round(expected, 4),
            "checks": c, "pass": all(c.values())}


def promote(ep: Episode, tmp: Path, dst: Path, expected: float, what: str) -> dict:
    """Verify a temp render; only then replace the previous output."""
    qa = av_checks(ep, tmp, expected)
    if not qa["pass"]:
        bad = [k for k, ok in qa["checks"].items() if not ok]
        raise PipelineError(f"{what}: verification failed {bad} (kept previous {dst.name}; temp at {tmp})")
    os.replace(tmp, dst)
    qa["path"] = str(dst)
    return qa


# ------------------------------------------------------------ Base master --
def timeline(results: list[ClipResult]) -> tuple[list[float], float]:
    offs, t = [], 0.0
    for r in results:
        offs.append(round(t, 4))
        t += r.duration
    return offs, round(t, 4)


def assemble_base(ep: Episode, results: list[ClipResult], force: bool = False) -> dict:
    """Base_<ep>.mp4 = story-only master.  Video: 'timeline' mode (default)
    concatenates the normalised clips and burns every pill at its global
    offset (one generation from the intermediates); 'concat_subbed' joins the
    clip_XX_subbed.mp4 videos.  Audio: the PCM sidecars of the very samples in
    each clip_XX_subbed.mp4, concatenated sample-exactly and AAC-encoded once."""
    ep.out_dir.mkdir(parents=True, exist_ok=True)
    dst = ep.out_dir / f"{ep.base_name}.mp4"
    mode = str(ep.outputs.get("base_mode", "timeline"))
    if mode not in ("timeline", "concat_subbed"):
        raise PipelineError("outputs.base_mode must be timeline | concat_subbed")
    offs, total = timeline(results)
    key = fingerprint({"mode": mode, "clips": [sha256_file(r.subbed[0]) for r in results],
                       "wav": [sha256_file(r.norm_wav) for r in results],  # type: ignore[arg-type]
                       "video": ep.video, "audio": ep.audio, "v": PIPELINE_VERSION})
    cues = [(o + c.start, o + c.end, c.speaker, c.text) for r, o in zip(results, offs) for c in r.cues]
    write_srt(ep.out_dir / f"{ep.base_name}.srt", [(a, b, t) for a, b, _, t in cues])
    if not force and cache_ok([dst], key):
        log(f"Base up to date: {dst.name}")
        return {"path": dst, "duration": total, "cues": cues, "offsets": offs, "qa": av_checks(ep, dst, total)}
    n = len(results)
    args: list[str] = []
    for r in results:
        args += ["-i", str(r.norm_mp4 if mode == "timeline" else r.subbed[0])]
    for r in results:
        args += ["-i", str(r.norm_wav)]
    parts = ["".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[vc]",
             "".join(f"[{n + i}:a]" for i in range(n)) + f"concat=n={n}:v=0:a=1[a]"]
    cur = "[vc]"
    if mode == "timeline":
        shifted = [Overlay(ov.start + o, ov.end + o, ov.kind, ov.speaker, ov.text, ov.meta)
                   for r, o in zip(results, offs) for ov in r.overlays]
        for ov in shifted:
            args += ["-i", ov.meta["png"]]
        chain, cur = overlay_chain(cur, shifted, 2 * n)
        parts += chain
    parts.append(f"{cur}format=yuv420p[v]")
    tmp = dst.with_name(dst.stem + ".tmp.mp4")
    log(f"Base: {n} clips, {total:.3f}s ({mode}) -> {dst.name}")
    run(ffmpeg_cmd(*args, "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[a]",
                   "-c:v", "libx264", "-preset", str(ep.video["preset"]), "-crf", str(ep.video["crf"]),
                   "-pix_fmt", "yuv420p", "-r", f"{float(ep.video['fps']):g}",
                   "-c:a", "aac", "-b:a", str(ep.audio["bitrate"]), "-ar", str(ep.audio["sample_rate"]),
                   "-ac", str(ep.audio["channels"]), "-movflags", "+faststart", str(tmp)),
        what="assemble Base")
    qa = promote(ep, tmp, dst, total, "Base")
    cache_write(dst, key, duration=total, clips=[r.clip.id for r in results])
    return {"path": dst, "duration": total, "cues": cues, "offsets": offs, "qa": qa}


# ------------------------------------------------------- CTA + Master ------
def normalize_cta(ep: Episode, cta: Path, font_path: Optional[str], force: bool = False) -> tuple[Path, float, str]:
    """CTA -> WxH @ fps, frame-exact, 48 kHz stereo PCM (.mov).  Burns
    cta_subtitles only when cta_burn_subtitles is true (the Kelidbox
    *_subbed.mp4 asset already carries them); loudnorm only if cta_loudnorm."""
    work = work_dir(ep)
    out = work / "cta_norm.mov"
    burn = bool(ep.outputs.get("cta_burn_subtitles", False))
    lnorm = bool(ep.outputs.get("cta_loudnorm", False))
    cta_sha = sha256_file(cta)
    key = fingerprint({"cta": cta_sha, "burn": burn, "ln": lnorm, "video": ep.video, "audio": ep.audio,
                       "subs": [asdict(c) for c in ep.cta_subtitles] if burn else None,
                       "font": sha256_file(Path(font_path)) if burn and font_path else None,
                       "style": ep.subs if burn else None, "voices": ep.voices if burn else None,
                       "engine": shaping_engine() if burn else None, "v": PIPELINE_VERSION})
    if not force and cache_ok([out], key):
        return out, float(json.loads(_record_path(out).read_text("utf-8"))["duration"]), cta_sha
    p = probe_media(cta)
    fps, sr = float(ep.video["fps"]), int(ep.audio["sample_rate"])
    durs = [s["duration"] for s in (p["video"], p["audio"]) if s and s["duration"] > 0]
    n, q = frame_quantize(min(durs) if durs else p["format_duration"], fps)
    args = ["-i", str(cta)]
    a_in = "[0:a]"
    if p["audio"] is None:
        args += ["-f", "lavfi", "-i", f"anullsrc=r={sr}:cl=stereo"]
        a_in = "[1:a]"
        ep.warnings.append(f"CTA {cta.name} has no audio stream; silence inserted")
    parts = [f"[0:v]{_scale_filter(ep.video)},fps={fps:g},tpad=stop_mode=clone:stop_duration=1,"
             f"trim=end_frame={n},setpts=PTS-STARTPTS[vs]"]
    cur = "[vs]"
    if burn and ep.cta_subtitles and font_path:
        ovs = build_overlays(ep, ep.cta_subtitles, q, work / "pills", "cta", font_path, False)
        base_idx = 2 if p["audio"] is None else 1
        for ov in ovs:
            args += ["-i", ov.meta["png"]]
        chain, cur = overlay_chain(cur, ovs, base_idx)
        parts += chain
    parts.append(f"{cur}format=yuv420p[v]")
    parts.append(f"{a_in}asetpts=PTS-STARTPTS,{ep.audio['loudnorm'] + ',' if lnorm else ''}"
                 f"aresample={sr},aformat=sample_fmts=fltp:channel_layouts=stereo,"
                 f"asetpts=N/SR/TB,apad,atrim=end_sample={int(round(q * sr))}[a]")
    tmp = out.with_name("cta_norm.tmp.mov")
    run(ffmpeg_cmd(*args, "-filter_complex", ";".join(parts), "-map", "[v]", "-map", "[a]",
                   "-c:v", "libx264", "-preset", str(ep.video["preset"]), "-crf", str(ep.video["work_crf"]),
                   "-pix_fmt", "yuv420p", "-r", f"{fps:g}", "-c:a", "pcm_s16le", str(tmp)),
        what=f"normalise CTA {cta.name}")
    os.replace(tmp, out)
    cache_write(out, key, duration=round(q, 4), frames=n, source=str(cta))
    return out, round(q, 4), cta_sha


def assemble_master(ep: Episode, base: dict, font_path: Optional[str], no_cta: bool = False,
                    force: bool = False) -> dict:
    """Master = immutable Base + exactly ONE CTA.  Always built from Base (never
    from a previous Master), keyed on sha256(Base)+sha256(CTA) so re-runs are
    no-ops; written to a temp file, duration-verified, then promoted.  Without
    a CTA (missing / --no-cta) Master is a byte copy of Base."""
    base_mp4: Path = base["path"]
    dst = ep.out_dir / f"{ep.master_name}.mp4"
    srt = ep.out_dir / f"{ep.master_name}.srt"
    base_sha = sha256_file(base_mp4)
    cta = None if no_cta else ep.cta_video
    info: dict[str, Any] = {"cta_requested": str(ep.cta_video) if ep.cta_video else None,
                            "cta_used": False, "base_sha256": base_sha}
    if cta is not None and not cta.is_file():
        ep.warnings.append(f"cta_video not found ({cta}); Master = Base (no CTA)")
        cta = None
    if no_cta:
        info["cta_skipped"] = "--no-cta"
    cues = [(a, b, t) for a, b, _, t in base["cues"]]
    if cta is None:
        key = fingerprint({"base": base_sha, "cta": None})
        if force or not cache_ok([dst], key):
            atomic_copy(base_mp4, dst)
            cache_write(dst, key, base=str(base_mp4), cta=None)
        write_srt(srt, cues)
        info.update(path=dst, duration=base["duration"], srt=srt, cue_count=len(cues),
                    qa=av_checks(ep, dst, base["duration"]))
        return info
    cta_norm, cta_dur, cta_sha = normalize_cta(ep, cta, font_path, force)
    total = round(base["duration"] + cta_dur, 4)
    key = fingerprint({"base": base_sha, "cta": cta_sha, "cta_norm": sha256_file(cta_norm),
                       "video": ep.video, "audio": ep.audio, "v": PIPELINE_VERSION})
    cues += [(base["duration"] + c.start, base["duration"] + c.end, c.text) for c in ep.cta_subtitles]
    write_srt(srt, cues)
    info.update(cta_used=True, cta_video=str(cta), cta_sha256=cta_sha, cta_duration=cta_dur,
                srt=srt, cue_count=len(cues))
    if not force and cache_ok([dst], key):
        log(f"Master up to date (Base + 1 CTA): {dst.name}")
        info.update(path=dst, duration=total, qa=av_checks(ep, dst, total))
        return info
    fps, sr = float(ep.video["fps"]), int(ep.audio["sample_rate"])
    nb = int(round(base["duration"] * fps))
    fc = (f"[0:v]trim=end_frame={nb},setpts=PTS-STARTPTS[v0];[1:v]setpts=PTS-STARTPTS[v1];"
          f"[0:a]aresample={sr},apad,atrim=end_sample={int(round(base['duration'] * sr))}[a0];"
          f"[1:a]aresample={sr}[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[vc][a];[vc]format=yuv420p[v]")
    tmp = dst.with_name(dst.stem + ".tmp.mp4")
    log(f"Master: Base {base['duration']:.3f}s + CTA {cta.name} {cta_dur:.3f}s -> {dst.name}")
    run(ffmpeg_cmd("-i", str(base_mp4), "-i", str(cta_norm), "-filter_complex", fc,
                   "-map", "[v]", "-map", "[a]", "-c:v", "libx264", "-preset", str(ep.video["preset"]),
                   "-crf", str(ep.video["crf"]), "-pix_fmt", "yuv420p", "-r", f"{fps:g}",
                   "-c:a", "aac", "-b:a", str(ep.audio["bitrate"]), "-ar", str(sr),
                   "-ac", str(ep.audio["channels"]), "-movflags", "+faststart", str(tmp)),
        what="assemble Master")
    info["qa"] = promote(ep, tmp, dst, total, "Master")
    cache_write(dst, key, base=str(base_mp4), base_sha256=base_sha, cta=str(cta), cta_sha256=cta_sha,
                cta_count=1, duration=total)
    info.update(path=dst, duration=total)
    return info


# --------------------------------------------------------- QA deliverables --
def write_audit_mp3(ep: Episode, master: Path, force: bool = False) -> Path:
    dst = ep.out_dir / f"{ep.master_name}_audit.mp3"
    key = fingerprint({"master": sha256_file(master), "br": ep.audio["audit_bitrate"]})
    if force or not cache_ok([dst], key):
        tmp = dst.with_name(dst.stem + ".tmp.mp3")
        run(ffmpeg_cmd("-i", str(master), "-map", "0:a:0", "-vn", "-c:a", "libmp3lame",
                       "-b:a", str(ep.audio["audit_bitrate"]), str(tmp)), what="audit mp3")
        os.replace(tmp, dst)
        cache_write(dst, key, master=str(master))
    return dst


def contact_points(ep: Episode, base: dict, master: dict) -> list[tuple[float, str]]:
    """Badge midpoint, every subtitle midpoint, every CTA cue midpoint."""
    pts: list[tuple[float, str]] = []
    if ep.badge:
        b0, b1 = float(ep.badge["start"]), min(float(ep.badge["end"]), base["duration"])
        pts.append(((b0 + b1) / 2, "BADGE"))
    pts += [((a + b) / 2, spk or "SUB") for a, b, spk, _ in base["cues"]]
    if master.get("cta_used"):
        off = base["duration"]
        pts += [(off + (c.start + c.end) / 2, f"CTA {c.speaker}".strip()) for c in ep.cta_subtitles]
    return sorted(pts)


def _label_font(size: int = 18):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", r"C:\Windows\Fonts\arialbd.ttf",
              "/Library/Fonts/Arial Bold.ttf"):
        if Path(p).is_file():
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def write_contact_sheet(ep: Episode, video: Path, points: list[tuple[float, str]],
                        cols: int = 4, thumb_w: int = 240) -> Path:
    """One decode pass (select by frame index) -> labelled grid JPEG."""
    dst = ep.out_dir / f"qa_{ep.episode_id}_contact.jpg"
    fps = float(ep.video["fps"])
    nframes = max(1, int(probe_media(video)["video"]["frames"] or 0) or 10 ** 9)
    points = points or [(0.0, "STORY")]
    idx = sorted({min(nframes - 1, max(0, int(round(t * fps)))) for t, _ in points})
    with tempfile.TemporaryDirectory(prefix="ffw_contact_") as td:
        sel = "+".join(f"eq(n\\,{i})" for i in idx)
        run(ffmpeg_cmd("-i", str(video), "-vf", f"select='{sel}',scale={thumb_w}:-2",
                       "-vsync", "0", "-frames:v", str(len(idx)), str(Path(td) / "f_%04d.png")),
            what="contact frames")
        frames = sorted(Path(td).glob("f_*.png"))
        thumbs = {i: Image.open(f).convert("RGB") for i, f in zip(idx, frames)}
        if not thumbs:
            raise PipelineError("contact sheet: no frames extracted")
        tw, th = next(iter(thumbs.values())).size
        label_h, rows = 26, math.ceil(len(points) / cols)
        sheet = Image.new("RGB", (cols * tw, rows * (th + label_h)), (18, 18, 24))
        d, lf = ImageDraw.Draw(sheet), _label_font(16)
        for k, (t, lab) in enumerate(points):
            i = min(nframes - 1, max(0, int(round(t * fps))))
            im = thumbs.get(i) or thumbs[min(thumbs, key=lambda x: abs(x - i))]
            x, y = (k % cols) * tw, (k // cols) * (th + label_h)
            sheet.paste(im, (x, y + label_h))
            d.text((x + 6, y + 4), f"{t:6.2f}s  {lab}", font=lf, fill=(255, 215, 80))
        dst.parent.mkdir(parents=True, exist_ok=True)
        sheet.save(dst, "JPEG", quality=88)
    return dst


def clip_report(ep: Episode, r: ClipResult) -> dict:
    a = r.analysis or {}
    out: dict[str, Any] = {
        "id": r.clip.id, "index": r.clip.index, "provenance": r.provenance, "plan": r.plan,
        "speech": a,
        "final_window_speech": r.final_check, "lock_trim": r.clip.lock_trim,
        "allow_speech_splice": r.clip.allow_speech_splice, "notes": r.clip.notes,
        "story_beat": r.clip.story_beat, "expected_speakers": r.clip.expected_speakers,
        "keyframe": str(r.clip.keyframe) if r.clip.keyframe else None,
        "source_span": list(r.clip.source_span) if r.clip.source_span else None,
        "visual": r.visual, "fallback": r.fallback}
    if r.subbed:
        out.update(duration=r.duration, frames=r.frames, subtitles=r.cue_checks,
                   overlays=[{"kind": o.kind, "start": o.start, "end": o.end, "speaker": o.speaker,
                              **{k: o.meta[k] for k in ("box", "font_size", "lines", "fits_width",
                                                       "inside_frame")}} for o in r.overlays],
                   outputs=[str(p) for p in r.subbed], srt=[str(p) for p in r.srt],
                   media=av_checks(ep, r.subbed[0], r.duration))
        for p in r.subbed[1:]:
            out.setdefault("mirror_sha256_match", []).append(sha256_file(p) == out["media"]["sha256"])
    return out


def gate(status: bool) -> str:
    return "pass" if status else "fail"


def write_qa_report(ep: Episode, results: list[ClipResult], font: Optional[str], base: Optional[dict],
                    master: Optional[dict], extras: dict, command: str) -> Path:
    """qa_report.json: automatic checks with pass/fail, human gates 'pending'."""
    clips = [clip_report(ep, r) for r in results]
    media_ok = all(c.get("media", {}).get("pass", True) for c in clips)
    subs_ok = all(s["in_bounds"] and not s["overlaps_previous"] for c in clips for s in c.get("subtitles", []))
    pills_ok = all(o["fits_width"] and o["inside_frame"] for c in clips for o in c.get("overlays", []))
    speech_ok = all(c["final_window_speech"] is not None and
                    not c["final_window_speech"].get("cuts_speech") for c in clips)
    mirrors_ok = all(len(r.subbed) == len(clip_output_paths(ep, r.clip, f"{r.clip.id}_subbed.mp4"))
                     and all(sha256_file(p) == sha256_file(r.subbed[0]) for p in r.subbed)
                     for r in results) if font else True
    splice_ok = all(
        (not b["touches_speech"]) or (c.get("allow_speech_splice") and b.get("internal"))
        for c in clips
        for b in c["provenance"].get("splice_audit", {}).get("boundaries", [])
    )
    automatic = {"per_clip_media": gate(media_ok), "subtitle_bounds": gate(subs_ok),
                 "pill_layout": gate(pills_ok), "speech_safe_trim": gate(speech_ok),
                 "per_clip_mirrors": gate(mirrors_ok), "splice_boundaries": gate(splice_ok),
                 "speech_detected": gate(all(r.analysis and (r.analysis["speech_segments"] or
                                                               not r.clip.subtitles) for r in results))}
    if command == "speech-audit":
        automatic = {k: v for k, v in automatic.items() if k.startswith("speech_") or k == "splice_boundaries"}
    else:
        automatic["persian_shaping"] = gate(shaping_engine() != "none")
    if base:
        automatic["base_media"] = gate(base["qa"]["pass"])
    if master:
        automatic["master_media"] = gate(master["qa"]["pass"])
        automatic["master_single_cta"] = gate(not master.get("cta_used") or
                                              abs(master["duration"] - base["duration"] -  # type: ignore[index]
                                                  master["cta_duration"]) < 1.5 / float(ep.video["fps"]))
    if master and master.get("cta_used"):
        automatic["cta_subtitle_bounds"] = gate(all(
            0 <= c.start < c.end <= master["cta_duration"] + 0.001 and
            (i == 0 or c.start >= ep.cta_subtitles[i-1].end)
            for i, c in enumerate(ep.cta_subtitles)))
    narrative = narrative_mode(ep)
    traces = [clip_trace(ep, r.clip, visual=r.visual, speech=r.analysis, plan=r.plan, fallback=r.fallback,
                         media=c.get("media")) for r, c in zip(results, clips)]
    trace = episode_trace(ep, traces, mode=command, master=master)
    if narrative:
        automatic["story_beat_lock"] = gate(trace["step_trace"][STEP_NAMES[0]]["status"] == "pass")
        automatic["keyframe_preflight"] = gate(trace["step_trace"][STEP_NAMES[1]]["status"] == "pass")
        automatic["visual_continuity_resolved"] = gate(trace["visual_continuity_resolved"])
        automatic["dead_air_pacing"] = gate(trace["step_trace"][STEP_NAMES[3]]["status"] == "pass")
    status = "pass" if all(v == "pass" for v in automatic.values()) else "fail"
    trace["all_passed"] = status == "pass"
    report = {
        "overall_status": status, "overall_status_scope": "automatic_checks_only",
        "publication_status": "pending" if status == "pass" else "fail",
        "pipeline": "farsi_flow_workflow", "pipeline_version": PIPELINE_VERSION, "command": command,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": {"python": platform.python_version(), "platform": platform.platform(),
                 "shaping_engine": shaping_engine(), "raqm": features.check("raqm")},
        "episode_id": ep.episode_id, "title_fa": ep.title_fa,
        "manifest": {"path": str(ep.manifest_path), "sha256": ep.manifest_sha256},
        "font": {"path": font, "sha256": sha256_file(Path(font)) if font else None},
        "settings": {"video": ep.video, "audio": ep.audio, "speech": ep.speech, "subtitle_style": ep.subs,
                     "badge": ep.badge},
        "clips": clips,
        "base": None if not base else {"path": str(base["path"]), "duration": base["duration"],
                                       "clip_offsets": base["offsets"], "cue_count": len(base["cues"]),
                                       "media": base["qa"]},
        "master": None if not master else {k: (str(v) if isinstance(v, Path) else v)
                                           for k, v in master.items() if k != "qa"} | {"media": master["qa"]},
        "deliverables": {k: str(v) for k, v in extras.items()},
        "gates": {"automatic": automatic,
                  "human_review": {"listen_every_clip_edges": "pending", "listen_final_master": "pending",
                                   "transcript_word_for_word": "pending", "visual_frame_review": "pending",
                                   "voice_continuity": "pending"}},
        "overall_automatic": status,
        "visual_continuity_passed": trace["visual_continuity_passed"],
        "visual_continuity_resolved": trace["visual_continuity_resolved"],
        "all_passed": status == "pass",
        "step_trace": trace["step_trace"],
        "warnings": ep.warnings,
        "note": "Amplitude speech detection locates candidates only; it does not prove a sentence "
                "finished. Human/audio-capable review gates stay 'pending' until signed off.",
    }
    dst = ep.out_dir / ("qa_report.json" if command == "build" else f"qa_report_{command}.json")
    dst.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, ensure_ascii=False)
    tmp = dst.with_suffix(".tmp")
    tmp.write_text(payload, "utf-8")
    os.replace(tmp, dst)
    if command == "build":
        ep_dst = ep.out_dir / f"qa_report_{ep.episode_id}.json"
        ep_dst.write_text(payload, "utf-8")
    write_json_atomic(ep.out_dir / f"trace_{ep.episode_id}.json", {**trace, "clips": traces})
    return dst


def narrative_mode(ep: Episode) -> bool:
    """Story gates are enforced once a manifest opts into v1.2 metadata."""
    return bool(ep.source_video or ep.story_summary_fa or
                any(c.keyframe or c.story_beat or c.expected_speakers for c in ep.clips))


# ------------------------------------------------- 6-stage step trace (v1.2) --
STEP_NAMES = ("step_1_story_beat_and_character_lock", "step_2_keyframe_preflight",
              "step_3_visual_continuity_audit", "step_4_acoustic_speech_and_pacing",
              "step_5_hybrid_bridge_and_fallback_resolution", "step_6_mux_and_master_verification")


def _name_aliases(name_fa: str) -> list[str]:
    return [p.strip() for p in re.split(r"[/|،,]", name_fa or "") if p.strip()]


def keyframe_identity(clip: ClipSpec) -> Optional[str]:
    """sha256 of the keyframe when it is on this host, else its normalised path."""
    if clip.keyframe is None:
        return None
    if Path(clip.keyframe).is_file():
        return "sha256:" + sha256_file(Path(clip.keyframe))
    return "path:" + str(clip.keyframe).replace("\\", "/").lower()


def step1_story_lock(ep: Episode) -> dict:
    """Metadata completeness, speaker consistency and CHARACTER_KEYFRAME_COLLISION."""
    per_clip, flags = {}, []
    ids: dict[str, list[ClipSpec]] = {}
    for c in ep.clips:
        missing = [k for k, v in (("keyframe", c.keyframe), ("expected_speakers", c.expected_speakers),
                                  ("story_beat", c.story_beat)) if not v]
        cue_speakers = sorted({q.speaker for q in c.subtitles if q.speaker})
        unexpected = [s for s in cue_speakers if c.expected_speakers and s not in c.expected_speakers]
        cf = [f"MISSING_{k.upper()}" for k in missing]
        if unexpected:
            cf.append("SPEAKER_NOT_EXPECTED")
        per_clip[c.id] = {"story_beat": c.story_beat, "expected_speakers": c.expected_speakers,
                          "cue_speakers": cue_speakers, "unexpected_speakers": unexpected,
                          "keyframe": str(c.keyframe) if c.keyframe else None,
                          "source_span": list(c.source_span) if c.source_span else None, "flags": cf}
        kid = keyframe_identity(c)
        if kid:
            ids.setdefault(kid, []).append(c)
    collisions = []
    for kid, group in ids.items():
        for i, a in enumerate(group):
            for b in group[i + 1:]:
                if a.expected_speakers and b.expected_speakers and \
                        not set(a.expected_speakers) & set(b.expected_speakers):
                    collisions.append({"keyframe": kid, "clips": [a.id, b.id],
                                       "speakers": [a.expected_speakers, b.expected_speakers]})
                    for x in (a, b):
                        if "CHARACTER_KEYFRAME_COLLISION" not in per_clip[x.id]["flags"]:
                            per_clip[x.id]["flags"].append("CHARACTER_KEYFRAME_COLLISION")
    caption = ep.outputs.get("publish_caption_fa") or ""
    name_checks = {}
    used = sorted({s for c in ep.clips for s in c.expected_speakers + [q.speaker for q in c.subtitles] if s})
    for spk in used:
        name = str((ep.voices.get(spk) or {}).get("name_fa") or "")
        aliases = _name_aliases(name)
        chk = {"name_fa": name, "aliases": aliases, "declared": bool(name)}
        if caption:
            chk["in_publish_caption"] = any(a in caption for a in aliases)
        name_checks[spk] = chk
        if not name:
            flags.append(f"SPEAKER_NAME_MISSING:{spk}")
        if caption and spk in (s for c in ep.clips for s in c.expected_speakers) and \
                not chk["in_publish_caption"] and spk not in ep.outputs.get("caption_optional_speakers", []):
            flags.append(f"SPEAKER_CAPTION_MISMATCH:{spk}")
    failed = bool(collisions) or any(p["flags"] for p in per_clip.values()) or bool(flags)
    return {"status": "fail" if failed else "pass", "story_summary_fa": ep.story_summary_fa,
            "clips": per_clip, "collisions": collisions, "speaker_names": name_checks, "flags": flags}


def step2_keyframe_preflight(ep: Episode) -> dict:
    per_clip, status = {}, "pass"
    for c in ep.clips:
        if c.keyframe is None:
            per_clip[c.id] = {"status": "fail", "reason": "no keyframe declared"}
            status = "fail"
            continue
        if not Path(c.keyframe).is_file():
            per_clip[c.id] = {"status": "skipped_not_on_host", "keyframe": str(c.keyframe)}
            status = "skipped" if status == "pass" else status
            continue
        try:
            info = verify_keyframe(Path(c.keyframe))
            per_clip[c.id] = {"status": "pass", **info, "modified": False}
        except (PipelineError, OSError) as exc:
            per_clip[c.id] = {"status": "fail", "keyframe": str(c.keyframe), "reason": str(exc)}
            status = "fail"
    return {"status": status, "clips": per_clip,
            "policy": "keyframes are read-only: verified + hashed, never drawn on / blurred / boxed"}


def resolve_fallback(ep: Episode, clip: ClipSpec, visual: Optional[dict]) -> dict:
    """Decide what VIDEO the clip uses: Flow clip, or original source span."""
    if visual is None and narrative_mode(ep):
        return {"resolution": "unresolved_visual_fail", "resolved": False,
                "reason": "visual evidence missing; cannot verify Flow or choose a fallback"}
    failed = bool(visual and not visual.get("passed"))
    if not failed:
        return {"resolution": "flow_clip", "resolved": True, "plan_available": True}
    if not ep.fallback_to_source_on_visual_fail:
        return {"resolution": "unresolved_visual_fail", "resolved": False,
                "reason": "fallback_to_source_on_visual_fail is false"}
    if ep.source_video is None or clip.source_span is None:
        return {"resolution": "unresolved_visual_fail", "resolved": False,
                "reason": "needs episode source_video and clip source_span"}
    return {"resolution": "source_bridge_fallback", "resolved": False, "plan_available": True,
            "status": "planned", "reason": "source extraction and media verification not run",
            "video_from": {"source_video": str(ep.source_video), "source_span": list(clip.source_span)},
            "audio_from": "native Google Flow Farsi audio of " + clip.file,
            "source_on_host": Path(ep.source_video).is_file()}


def clip_trace(ep: Episode, clip: ClipSpec, *, visual: Optional[dict], speech: Optional[dict],
               plan: Optional[dict], fallback: Optional[dict], media: Optional[dict] = None) -> dict:
    s4: dict[str, Any] = {"status": "skipped", "tight_speech_trim": tight_enabled(ep, clip)}
    if speech and speech.get("first_speech_sec") is not None and plan:
        first, last = speech["first_speech_sec"], speech["last_speech_sec"]
        dur = plan["duration"]
        active = _speech_inside([tuple(x) for x in speech.get("speech_segments", [[first, last]])],
                                *plan["final"])
        dead = (round(max(0.0, dur - (last - first)), 3)
                if plan.get("tight_speech_trim") else round(max(0.0, dur - active), 3))
        s4.update(status="pass", first_speech_sec=first, last_speech_sec=last,
                  speech_duration_sec=active, speech_envelope_sec=round(last - first, 3), trimmed_duration_sec=dur,
                  dead_air_sec=dead, final_trim=plan["final"], pre_tight=plan.get("pre_tight"),
                  flags=["DEAD_AIR_PACING"] if dead > DEAD_AIR_LIMIT else [])
        if s4["flags"]:
            s4["status"] = "fail"
    elif speech is not None:
        s4.update(status="fail", flags=["NO_SPEECH_DETECTED"])
    s5 = dict(fallback or resolve_fallback(ep, clip, visual))
    s5.setdefault("status", "pass" if s5.get("resolved") else "fail")
    s6 = {"status": "pass" if media and media.get("pass") else ("fail" if media else "not_run")}
    if media:
        s6["media"] = media
    return {"clip_id": clip.id, "story_beat": clip.story_beat,
            "step_3_visual_continuity_audit": {"status": "skipped" if visual is None else
                                               ("pass" if visual["passed"] else "fail"), **(visual or {})},
            "step_4_acoustic_speech_and_pacing": s4,
            "step_5_hybrid_bridge_and_fallback_resolution": s5,
            "step_6_mux_and_master_verification": s6}


def episode_trace(ep: Episode, clip_traces: list[dict], *, mode: str,
                  master: Optional[dict] = None) -> dict:
    s1, s2 = step1_story_lock(ep), step2_keyframe_preflight(ep)
    for t in clip_traces:
        cid = t["clip_id"]
        first = s1["clips"][cid]
        t[STEP_NAMES[0]] = {**first, "status": "fail" if first["flags"] or s1["flags"] else "pass"}
        t[STEP_NAMES[1]] = s2["clips"][cid]
        t["step_trace"] = {name: t[name] for name in STEP_NAMES}
    vis = [t["step_3_visual_continuity_audit"] for t in clip_traces]
    raw_ok = all(v["status"] == "pass" for v in vis)
    resolved = all(t["step_5_hybrid_bridge_and_fallback_resolution"].get("resolved") for t in clip_traces)
    planned = all(t[STEP_NAMES[4]].get("resolved") or t[STEP_NAMES[4]].get("plan_available")
                  for t in clip_traces)
    pacing = [t["step_4_acoustic_speech_and_pacing"] for t in clip_traces]
    s6 = {"status": "not_run" if master is None else ("pass" if master.get("qa", {}).get("pass") else "fail"),
          "visual_continuity_passed": raw_ok, "visual_continuity_resolved": resolved}
    steps = {
        STEP_NAMES[0]: s1, STEP_NAMES[1]: s2,
        STEP_NAMES[2]: {"status": "pass" if raw_ok else "fail",
                        "failed_clips": [t["clip_id"] for t in clip_traces
                                         if t["step_3_visual_continuity_audit"]["status"] == "fail"],
                        "clips": {t["clip_id"]: t["step_3_visual_continuity_audit"] for t in clip_traces}},
        STEP_NAMES[3]: {"status": "skipped" if all(p["status"] == "skipped" for p in pacing) else
                        ("fail" if any(p["status"] == "fail" for p in pacing) else "pass"),
                        "clips": {t["clip_id"]: t["step_4_acoustic_speech_and_pacing"] for t in clip_traces}},
        STEP_NAMES[4]: {"status": "pass" if resolved else ("planned" if planned else "fail"),
                        "fallback_clips": [t["clip_id"] for t in clip_traces
                                           if t["step_5_hybrid_bridge_and_fallback_resolution"]["resolution"]
                                           == "source_bridge_fallback"],
                        "clips": {t["clip_id"]: t["step_5_hybrid_bridge_and_fallback_resolution"]
                                  for t in clip_traces}},
        STEP_NAMES[5]: s6,
    }
    blocking = [n for n in (STEP_NAMES[0], STEP_NAMES[3], STEP_NAMES[4]) if steps[n]["status"] == "fail"]
    if master is not None and s6["status"] == "fail":
        blocking.append(STEP_NAMES[5])
    if s2["status"] == "fail":
        blocking.append(STEP_NAMES[1])
    return {"episode_id": ep.episode_id, "title_fa": ep.title_fa, "mode": mode,
            "pipeline_version": PIPELINE_VERSION, "source_video": str(ep.source_video) if ep.source_video else None,
            "fallback_to_source_on_visual_fail": ep.fallback_to_source_on_visual_fail,
            "tight_speech_trim": ep.tight_speech_trim, "step_trace": steps,
            "visual_continuity_passed": raw_ok, "visual_continuity_resolved": resolved,
            "blocking_steps": blocking, "audit_passed": not blocking,
            "all_passed": not blocking and resolved and s2["status"] == "pass"
                          and steps[STEP_NAMES[3]]["status"] == "pass" and s6["status"] == "pass",
            "verification_scope": "rendered_media" if master else "diagnostic_only",
            "publication_status": "pending_human_review"}


def probe_entries_for(ep: Episode, probe: dict, part: Optional[str] = None) -> tuple[str, dict]:
    parts = probe.get("parts", probe)
    if part is None:
        m = re.search(r"part(\d+)", ep.episode_id, re.I)
        part = f"part{m.group(1)}" if m else None
    if not part or part not in parts:
        raise PipelineError(f"probe JSON has no entry for {part!r} (have {sorted(parts)})")
    return part, parts[part]


def trace_audit(ep: Episode, *, probe: Optional[dict] = None, part: Optional[str] = None,
                live: bool = True) -> dict:
    """Headless (probe JSON) or live (MP4s on host) 6-stage trace without rendering."""
    entries, used_part = {}, None
    if probe is not None:
        used_part, entries = probe_entries_for(ep, probe, part)
        missing = {c.id for c in ep.clips} - entries.keys()
        if missing:
            raise PipelineError(f"probe {used_part} missing clips: {', '.join(sorted(missing))}")
    vcfg = ep.visual
    kfs = {c.id: c.keyframe for c in ep.clips}
    traces = []
    for c in ep.clips:
        visual = speech = plan = None
        file_p, _ = clip_source_paths(ep, c)
        if c.id in entries:
            visual = evaluate_probe_entry(entries[c.id], clip_id=c.id,
                                          keyframe_threshold=vcfg["keyframe_threshold"],
                                          jump_threshold=vcfg["jump_threshold"],
                                          contamination_margin=vcfg["contamination_margin"])
            visual["source"] = "probe_json"
        elif live and file_p.is_file() and c.keyframe and Path(c.keyframe).is_file():
            v = analyze_clip_visuals(file_p, c.keyframe, kfs, sample_fps=vcfg["sample_fps"],
                                     size=tuple(vcfg["thumb_size"]), jump_threshold=vcfg["jump_threshold"],
                                     clip_id=c.id, keyframe_threshold=vcfg["keyframe_threshold"],
                                     contamination_margin=vcfg["contamination_margin"])
            visual = {**v["evaluation"], "source": "live_mp4"}
        if live and file_p.is_file():
            src_dur = media_duration(file_p)
            speech = analyze_clip_speech(file_p, c.trim_in, c.trim_out, ep.speech)
            plan = plan_trim(c, speech, src_dur, ep.speech)
            if tight_enabled(ep, c):
                plan = apply_tight_speech_trim(plan, speech.get("first_speech_sec"),
                                               speech.get("last_speech_sec"), ep.speech)
        traces.append(clip_trace(ep, c, visual=visual, speech=speech, plan=plan, fallback=None))
    out = episode_trace(ep, traces, mode="probe_json" if probe is not None else "live_mp4")
    out["probe_part"] = used_part
    out["clips"] = traces
    return out


def print_trace_table(tr: dict) -> None:
    print(f"\n{tr['episode_id']}  ({tr['mode']}, part={tr.get('probe_part')})  all_passed={tr['all_passed']}")
    print(f"  {'clip':<8}{'kf_start':>9}{'kf_mean':>8}{'other':>14}{'jump@t':>13}  "
          f"{'flags':<58}{'resolution':<24}source_span")
    for t in tr["clips"]:
        v = t["step_3_visual_continuity_audit"]
        m = v.get("metrics") or {}
        oth = f"{m.get('closest_other_keyframe') or '-'}:{m.get('closest_other_keyframe_l1_start') or '-'}"
        jmp = f"{m.get('max_internal_jump_l1') or '-'}@{m.get('max_internal_jump_time_sec') or '-'}"
        r = t["step_5_hybrid_bridge_and_fallback_resolution"]
        span = (r.get("video_from") or {}).get("source_span", "")
        print(f"  {t['clip_id']:<8}{m.get('l1_vs_keyframe_start') or '-':>9}{m.get('l1_vs_keyframe_mean') or '-':>8}"
              f"{oth:>14}{jmp:>13}  {','.join(v.get('flags', [])) or 'ok':<58}{r['resolution']:<24}{span}")
    if tr["blocking_steps"]:
        print(f"  blocking: {', '.join(tr['blocking_steps'])}")


def write_json_atomic(dst: Path, obj: Any) -> Path:
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_suffix(dst.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", "utf-8")
    os.replace(tmp, dst)
    return dst


# ----------------------------------------------------------- top-level flows --
def build_episode(ep: Episode, *, no_cta: bool = False, force: bool = False,
                  contact: bool = True) -> dict:
    """Full pipeline: per-clip subbed clips -> Base -> Master -> SRT/audit/contact/QA."""
    results, font, _ = run_clips(ep, force=force, render=True)
    base = assemble_base(ep, results, force)
    master = assemble_master(ep, base, font, no_cta=no_cta, force=force)
    extras: dict[str, Any] = {"base_mp4": base["path"], "base_srt": ep.out_dir / f"{ep.base_name}.srt",
                              "master_mp4": master["path"], "master_srt": master["srt"],
                              "audit_mp3": write_audit_mp3(ep, master["path"], force)}
    if contact:
        extras["contact_sheet"] = write_contact_sheet(ep, master["path"], contact_points(ep, base, master))
    extras["clips_subbed"] = ", ".join(str(r.subbed[0]) for r in results)
    qa = write_qa_report(ep, results, font, base, master, extras, "build")
    return {"results": results, "base": base, "master": master, "extras": extras, "qa_report": qa}


def sub_clips_only(ep: Episode, *, force: bool = False, only: Optional[set[str]] = None) -> dict:
    results, font, _ = run_clips(ep, force=force, render=True, only=only)
    qa = write_qa_report(ep, results, font, None, None,
                         {"clips_subbed": ", ".join(str(p) for r in results for p in r.subbed)},
                         "sub-clips-only")
    return {"results": results, "qa_report": qa}


def speech_audit(ep: Episode, *, only: Optional[set[str]] = None) -> dict:
    results, _, _ = run_clips(ep, render=False, only=only)
    qa = write_qa_report(ep, results, None, None, None, {}, "speech-audit")
    return {"results": results, "qa_report": qa}


# ---------------------------------------------------------------- clipboard --
_PS_SET_IMAGE = ("Add-Type -AssemblyName System.Windows.Forms; Add-Type -AssemblyName System.Drawing; "
                 "$img = [System.Drawing.Image]::FromFile($env:FFW_IMG); "
                 "[System.Windows.Forms.Clipboard]::SetImage($img); $img.Dispose()")


def verify_keyframe(path: Path, require_portrait: bool = True) -> dict:
    """Decode the keyframe fully and check 9:16 (±2 %) before it goes to Flow."""
    with Image.open(path) as im:
        im.load()
        w, h = im.size
        fmt = im.format
    ratio = w / h if h else 0.0
    info = {"path": str(path), "sha256": sha256_file(path), "format": fmt, "size": [w, h],
            "ratio": round(ratio, 4), "is_9x16": abs(ratio - 9 / 16) <= 0.02 * 9 / 16}
    if require_portrait and not info["is_9x16"]:
        raise PipelineError(f"{path.name} is {w}x{h} (ratio {ratio:.3f}); expected 9:16 -- "
                            "pass --allow-any-ratio to override")
    return info


def copy_image_to_clipboard(path: Path, dry_run: bool = False) -> str:
    """Windows: System.Windows.Forms.Clipboard::SetImage (STA PowerShell).
    macOS: osascript «class PNGf».  Linux: wl-copy / xclip as image/png."""
    path = path.resolve()
    sysname = platform.system()
    if sysname == "Windows":
        cmd, env = ["powershell", "-NoProfile", "-STA", "-Command", _PS_SET_IMAGE], {"FFW_IMG": str(path)}
    elif sysname == "Darwin":
        cmd, env = ["osascript", "-e", f'set the clipboard to (read (POSIX file "{path}") as «class PNGf»)'], {}
    elif shutil.which("wl-copy"):
        cmd, env = ["wl-copy", "--type", "image/png"], {}
    elif shutil.which("xclip"):
        cmd, env = ["xclip", "-selection", "clipboard", "-t", "image/png", "-i", str(path)], {}
    else:
        if dry_run:  # verification already passed; just report the missing tool
            return "DRY-RUN: no clipboard tool on this host (needs PowerShell, osascript, wl-copy or xclip)"
        raise PipelineError("no clipboard tool (need PowerShell, osascript, wl-copy or xclip)")
    if dry_run:
        return "DRY-RUN: " + " ".join(cmd)
    data = None
    if cmd[0] == "wl-copy":  # wl-copy reads the PNG bytes from stdin
        buf = io.BytesIO()
        with Image.open(path) as im:
            im.save(buf, "PNG")
        data = buf.getvalue()
    elif sysname == "Darwin" and path.suffix.lower() != ".png":  # «class PNGf» needs a PNG file
        tmp = Path(tempfile.gettempdir()) / f"ffw_clip_{os.getpid()}.png"
        with Image.open(path) as im:
            im.save(tmp, "PNG")
        cmd[-1] = f'set the clipboard to (read (POSIX file "{tmp}") as «class PNGf»)'
    proc = subprocess.run(cmd, input=data, env={**os.environ, **env}, capture_output=True)
    if proc.returncode != 0:
        raise PipelineError(f"clipboard image failed: {proc.stderr.decode('utf-8', 'replace')[-400:]}")
    return " ".join(cmd[:2])


def copy_text_to_clipboard(text: str, dry_run: bool = False) -> str:
    """Windows clip.exe needs UTF-16LE (+BOM) for Persian; others take UTF-8."""
    sysname = platform.system()
    if sysname == "Windows":
        cmd, data = ["clip"], b"\xff\xfe" + text.encode("utf-16le")
    elif sysname == "Darwin":
        cmd, data = ["pbcopy"], text.encode("utf-8")
    elif shutil.which("wl-copy"):
        cmd, data = ["wl-copy"], text.encode("utf-8")
    elif shutil.which("xclip"):
        cmd, data = ["xclip", "-selection", "clipboard"], text.encode("utf-8")
    elif shutil.which("xsel"):
        cmd, data = ["xsel", "--clipboard", "--input"], text.encode("utf-8")
    else:
        if dry_run:
            return "DRY-RUN: no clipboard tool on this host (needs clip, pbcopy, wl-copy, xclip or xsel)"
        raise PipelineError("no clipboard tool (need clip, pbcopy, wl-copy, xclip or xsel)")
    if dry_run:
        return "DRY-RUN: " + " ".join(cmd)
    env = {**os.environ, "LANG": os.environ.get("LANG", "en_US.UTF-8")} if sysname == "Darwin" else None
    proc = subprocess.run(cmd, input=data, env=env, capture_output=True)
    if proc.returncode != 0:
        raise PipelineError(f"clipboard text failed: {proc.stderr.decode('utf-8', 'replace')[-400:]}")
    return cmd[0]


def load_prompts(path: Path) -> dict[str, dict]:
    """Prompt library JSON: {"prompts": {key: "text" | {"text":..., ...}}}."""
    data = json.loads(path.read_text("utf-8-sig"))
    raw = data.get("prompts", data)
    out = {}
    for k, v in raw.items():
        if k.startswith("_"):
            continue
        out[k] = v if isinstance(v, dict) else {"text": v}
        if not str(out[k].get("text") or "").strip():
            raise PipelineError(f"prompt {k!r} has no text")
    return out


def default_prompts_path() -> Path:
    return Path(__file__).resolve().parent / "prompts" / "ugly_chef_flow_prompts.json"


# ---------------------------------------------------------------------- CLI --
def _kv(items: Optional[list[str]]) -> dict[str, str]:
    out = {}
    for it in items or []:
        k, sep, v = it.partition("=")
        if not sep or not k:
            raise PipelineError(f"--var expects NAME=VALUE (got {it!r})")
        out[k.strip()] = v
    return out


def _manifest_args(p: argparse.ArgumentParser, cta: bool = True) -> None:
    p.add_argument("manifest", type=Path, nargs="?", help="episode manifest JSON")
    p.add_argument("--manifest", dest="manifest_option", type=Path,
                   help="episode manifest JSON (alternative to positional argument)")
    p.add_argument("--var", action="append", metavar="NAME=VALUE",
                   help="override a manifest ${VAR} (e.g. BASE=/data/series1); repeatable")
    p.add_argument("--clips-dir", help="override clips_dir")
    p.add_argument("--out-dir", help="override out_dir")
    p.add_argument("--font", help="Persian TTF (default: manifest font_path, then system fonts)")
    p.add_argument("--speech-safe", choices=SPEECH_MODES, help="override speech_safe for all clips")
    p.add_argument("--only", help="comma-separated clip ids or 1-based indexes")
    if cta:
        p.add_argument("--cta-video", help="override cta_video")
        p.add_argument("--no-cta", action="store_true", help="Master = Base (no CTA appended)")
    p.add_argument("--force", action="store_true", help="ignore build cache, re-render everything")


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="farsi_flow_workflow",
                                 description="Farsi Google Flow viral-series workflow (config-driven).")
    ap.add_argument("--ffmpeg", help="ffmpeg binary (default: $FFMPEG_BIN or ffmpeg)")
    ap.add_argument("--ffprobe", help="ffprobe binary (default: $FFPROBE_BIN or ffprobe)")
    ap.add_argument("-v", "--verbose", action="store_true", help="echo every ffmpeg command")
    ap.add_argument("--version", action="version", version=f"%(prog)s {PIPELINE_VERSION}")
    sub = ap.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="per-clip subbed clips + Base + Master + SRT/audit/contact/QA")
    _manifest_args(b)
    b.add_argument("--no-contact", action="store_true", help="skip qa_<episode>_contact.jpg")

    s = sub.add_parser("speech-audit", help="speech-boundary analysis + trim plan only (no render)")
    _manifest_args(s, cta=False)
    s.add_argument("--json", action="store_true", help="print the per-clip report as JSON")

    c = sub.add_parser("sub-clips-only", help="per-clip subtitled clips WITH original Flow audio only")
    _manifest_args(c, cta=False)

    ci = sub.add_parser("clipboard-image", help="copy a verified 9:16 keyframe to the clipboard")
    ci.add_argument("image", type=Path)
    ci.add_argument("--allow-any-ratio", action="store_true")
    ci.add_argument("--dry-run", action="store_true", help="verify + show the command, don't copy")

    cp = sub.add_parser("clipboard-prompt", help="copy a Google Flow scene prompt to the clipboard")
    cp.add_argument("key", nargs="?", help="prompt key (omit with --list)")
    cp.add_argument("--prompts", type=Path, default=None, help="prompt library JSON")
    cp.add_argument("--list", action="store_true", help="list prompt keys")
    cp.add_argument("--print", dest="print_text", action="store_true", help="also print the prompt")
    cp.add_argument("--dry-run", action="store_true")

    ta = sub.add_parser("trace-audit", help="6-stage step trace for one manifest (no rendering)")
    _manifest_args(ta, cta=False)
    ta.add_argument("--probe-json", type=Path, help="headless visual probe (parts1_to_5_clips_probe.json)")
    ta.add_argument("--part", help="probe part key, e.g. part3 (default: from episode_id)")
    ta.add_argument("--out-json", type=Path, help="write the trace JSON here")
    ta.add_argument("--no-live", action="store_true", help="never touch MP4s even if present")

    tp = sub.add_parser("trace-all-parts", help="6-stage trace for Fruits of Power Parts 1-5 from a probe JSON")
    tp.add_argument("--probe-json", type=Path, required=True)
    tp.add_argument("--out-json", type=Path, required=True)
    tp.add_argument("--manifest-glob", default="fruits_of_power_part*.json",
                    help="glob under pipeline/manifests (default: fruits_of_power_part*.json)")
    tp.add_argument("--manifests-dir", type=Path, default=Path(__file__).resolve().parent / "manifests")
    tp.add_argument("--var", action="append", metavar="NAME=VALUE")
    return ap


def _overrides(a: argparse.Namespace) -> dict:
    return {"vars": _kv(a.var), "clips_dir": a.clips_dir, "out_dir": a.out_dir, "font": a.font,
            "speech_safe": a.speech_safe, "cta_video": getattr(a, "cta_video", None),
            "no_cta": getattr(a, "no_cta", False)}


def _only(a: argparse.Namespace) -> Optional[set[str]]:
    return {x.strip() for x in a.only.split(",") if x.strip()} if getattr(a, "only", None) else None


def _print_audit(results: list[ClipResult]) -> None:
    print(f"{'clip':<10}{'src dur':>8}{'speech':>17}{'requested':>17}{'final':>17}  mode / notes")
    for r in results:
        a = r.analysis or {}
        sp = (f"{a['first_speech_sec']:.2f}-{a['last_speech_sec']:.2f}"
              if a.get("first_speech_sec") is not None else "none")
        rq, fn = r.plan["requested"], r.plan["final"]
        flag = " CUTS-SPEECH" if (r.final_check or {}).get("cuts_speech") else ""
        print(f"{r.clip.id:<10}{r.plan['source_duration']:>8.2f}{sp:>17}"
              f"{rq[0]:>8.2f}-{rq[1]:<8.2f}{fn[0]:>8.2f}-{fn[1]:<8.2f}  {r.plan['mode']}{flag}")
        for n in r.plan["notes"]:
            print(f"{'':<10}  - {n}")


def _load_probe(path: Path) -> dict:
    data = json.loads(Path(path).read_text("utf-8-sig"))
    if not isinstance(data, dict) or not isinstance(data.get("parts", data), dict):
        raise PipelineError(f"{path}: probe JSON must be {{'parts': {{'partN': {{clip_id: entry}}}}}}")
    return data


def trace_all_parts(probe_path: Path, out_json: Path, manifests: list[Path],
                    variables: Optional[dict] = None) -> dict:
    probe = _load_probe(probe_path)
    episodes, rows = [], []
    for mpath in manifests:
        ep = load_manifest(mpath, {"vars": variables or {}})
        tr = trace_audit(ep, probe=probe, live=False)
        tr["manifest"] = str(mpath.name)
        episodes.append(tr)
        for t in tr["clips"]:
            v = t["step_3_visual_continuity_audit"]
            r = t["step_5_hybrid_bridge_and_fallback_resolution"]
            rows.append({"part": tr["probe_part"], "clip": t["clip_id"], "story_beat": t["story_beat"],
                         "flags": v.get("flags", []), "warnings": v.get("warnings", []),
                         "suggested_visual_trim": [v.get("suggested_visual_trim_in"),
                                                   v.get("suggested_visual_trim_out")],
                         "resolution": r["resolution"], "resolved": r.get("resolved", False),
                         "plan_available": r.get("plan_available", False),
                         "fallback_source_span": (r.get("video_from") or {}).get("source_span")})
    failed = [r for r in rows if r["flags"]]
    summary = {"clips_total": len(rows), "clips_failed_visual": len(failed),
               "clips_planned_source_bridge": sum(r["resolution"] == "source_bridge_fallback" for r in failed),
               "clips_resolved_by_source_bridge": sum(r["resolution"] == "source_bridge_fallback"
                                                       and r["resolved"] for r in failed),
               "clips_unresolved": sum(not r["resolved"] for r in rows),
               "clips_without_recovery_plan": sum(not r["plan_available"] for r in rows),
               "flag_counts": {f: sum(f in r["flags"] for r in rows) for f in FAIL_FLAGS},
               "failed_clips": [f"{r['part']}/{r['clip']}" for r in failed]}
    out = {"generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "pipeline_version": PIPELINE_VERSION, "probe_json": str(probe_path),
           "policy": {"keyframes": "read-only, never defaced",
                      "fallback": "failed Flow VIDEO -> subtitle-inpainted source_span; Flow Farsi AUDIO kept"},
           "summary": summary, "table": rows, "episodes": episodes,
           "audit_passed": all(t["audit_passed"] for t in episodes),
           "all_passed": all(t["all_passed"] for t in episodes),
           "verification_scope": "probe_metrics_and_recovery_plan_not_render_signoff"}
    write_json_atomic(out_json, out)
    return out


def main(argv: Optional[list[str]] = None) -> int:
    global FFMPEG, FFPROBE, VERBOSE
    a = build_parser().parse_args(argv)
    FFMPEG, FFPROBE, VERBOSE = a.ffmpeg or FFMPEG, a.ffprobe or FFPROBE, a.verbose
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    try:
        if a.command == "clipboard-image":
            info = verify_keyframe(a.image, require_portrait=not a.allow_any_ratio)
            how = copy_image_to_clipboard(a.image, dry_run=a.dry_run)
            log(f"keyframe {a.image.name} {info['size'][0]}x{info['size'][1]} sha256={info['sha256'][:12]} -> {how}")
            return 0
        if a.command == "clipboard-prompt":
            prompts = load_prompts(a.prompts or default_prompts_path())
            if a.list or not a.key:
                for k, v in prompts.items():
                    print(f"{k:<24} {len(v['text']):>4} chars  {v.get('scene', '')}")
                return 0 if a.list else 2
            if a.key not in prompts:
                raise PipelineError(f"unknown prompt {a.key!r}; known: {', '.join(prompts)}")
            text = prompts[a.key]["text"]
            how = copy_text_to_clipboard(text, dry_run=a.dry_run)
            log(f"clipboard set to prompt: {a.key} ({len(text)} chars) via {how}")
            if a.print_text:
                print(text)
            return 0
        if a.command == "trace-all-parts":
            mans = sorted(Path(a.manifests_dir).glob(a.manifest_glob))
            if not mans:
                raise PipelineError(f"no manifests match {a.manifest_glob} in {a.manifests_dir}")
            out = trace_all_parts(a.probe_json, a.out_json, mans, _kv(a.var))
            for tr in out["episodes"]:
                print_trace_table(tr)
            sm = out["summary"]
            log(f"{sm['clips_failed_visual']}/{sm['clips_total']} clips failed the visual gate; "
                f"{sm['clips_planned_source_bridge']} planned source bridges; "
                f"{sm['clips_resolved_by_source_bridge']} verified source bridges, "
                f"{sm['clips_unresolved']} unresolved -> {a.out_json}")
            return 0 if out["audit_passed"] else 1
        if a.command == "trace-audit":
            if bool(a.manifest) == bool(a.manifest_option):
                raise PipelineError("provide exactly one manifest: positional or --manifest PATH")
            ep = load_manifest(a.manifest or a.manifest_option, _overrides(a))
            live = not a.no_live and shutil.which(FFMPEG) is not None
            tr = trace_audit(ep, probe=_load_probe(a.probe_json) if a.probe_json else None,
                             part=a.part, live=live)
            print_trace_table(tr)
            if a.out_json:
                write_json_atomic(a.out_json, tr)
                log(f"trace: {a.out_json}")
            return 0 if tr["audit_passed"] else 1
        if shutil.which(FFMPEG) is None or shutil.which(FFPROBE) is None:
            raise PipelineError(f"ffmpeg/ffprobe not found ({FFMPEG}, {FFPROBE}); use --ffmpeg/--ffprobe")
        if bool(a.manifest) == bool(a.manifest_option):
            raise PipelineError("provide exactly one manifest: positional or --manifest PATH")
        ep = load_manifest(a.manifest or a.manifest_option, _overrides(a))
        log(f"episode {ep.episode_id}: {len(ep.clips)} clips, clips_dir={ep.clips_dir}, out_dir={ep.out_dir}")
        if a.command == "speech-audit":
            res = speech_audit(ep, only=_only(a))
            if a.json:
                print(json.dumps([clip_report(ep, r) for r in res["results"]], indent=2, ensure_ascii=False))
            else:
                _print_audit(res["results"])
            log(f"report: {res['qa_report']}")
        elif a.command == "sub-clips-only":
            res = sub_clips_only(ep, force=a.force, only=_only(a))
            for r in res["results"]:
                log(f"{r.clip.id}: {r.duration:.3f}s -> " + " | ".join(str(p) for p in r.subbed))
            log(f"report: {res['qa_report']}")
        else:
            if _only(a):
                raise PipelineError("--only applies to speech-audit / sub-clips-only (build needs every clip)")
            res = build_episode(ep, no_cta=a.no_cta, force=a.force, contact=not a.no_contact)
            m = res["master"]
            log(f"Base   {res['base']['path']} ({res['base']['duration']:.3f}s)")
            log(f"Master {m['path']} ({m['duration']:.3f}s, CTA={'yes' if m['cta_used'] else 'no'})")
            log(f"report: {res['qa_report']}")
        for w in ep.warnings:
            log(f"WARNING: {w}")
        report = json.loads(res["qa_report"].read_text("utf-8"))
        return 1 if report["overall_status"] == "fail" else 0
    except (PipelineError, OSError, ValueError, TypeError) as exc:
        log(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
