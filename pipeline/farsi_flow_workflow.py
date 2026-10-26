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
    usable = (len(pcm) // n) * n
    if usable == 0:
        return np.full(1, -120.0, dtype=np.float32)
    frames = pcm[:usable].reshape(-1, n).astype(np.float64)
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
    shorter than min_speech_ms, merge gaps shorter than merge_gap_ms."""
    fs = cfg["frame_ms"] / 1000.0
    floor = float(np.percentile(db, 10)) if db.size else -120.0
    thr = max(float(cfg["threshold_dbfs"]), min(floor + float(cfg["noise_margin_db"]), -20.0))
    runs = [r for r in _runs(db > thr) if (r[1] - r[0]) * fs * 1000 >= cfg["min_speech_ms"]]
    merged: list[list[int]] = []
    for a, b in runs:
        if merged and (a - merged[-1][1]) * fs * 1000 < cfg["merge_gap_ms"]:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    segs = [(round(a * fs, 3), round(b * fs, 3)) for a, b in merged]
    stats = {"noise_floor_dbfs": round(floor, 2), "threshold_dbfs": round(thr, 2),
             "peak_dbfs": round(float(db.max()) if db.size else -120.0, 2)}
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
        notes.append(f"trim_out {req_out:.3f} > source duration {src_dur:.3f}; clamped")
        req_out = src_dur
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
    """Whole frames for a duration; returns (frames, quantised seconds)."""
    n = max(1, int(round(dur * fps)))
    return n, n / fps


# -------------------------------------------------------- splice + normalise --
def splice_clip(src: Path, segments: list[tuple[float, float]], dst: Path, cfg: dict,
                video: dict) -> Path:
    """Join source segments on one timeline.  Video: frame trims + concat.
    Audio: each join gets a centred `acrossfade=d` (segments are widened by d/2
    around the join), then padded/trimmed to the exact video length."""
    d = float(cfg.get("splice_crossfade", 0.02))
    src_dur = media_duration(src)
    segs = [(a, min(b, src_dur)) for a, b in segments if a < src_dur]
    if not segs:
        raise PipelineError(f"splice: no segment of {segments} inside {src.name} ({src_dur:.2f}s)")
    fps = float(video["fps"])
    parts, alabels, vlabels = [], [], []
    total = 0.0
    for i, (a, b) in enumerate(segs):
        n, q = frame_quantize(b - a, fps)
        total += q
        parts.append(f"[0:v]trim=start={a:.4f}:end={a + q:.4f},setpts=PTS-STARTPTS,fps={fps:g}[v{i}]")
        a0 = a - (d / 2 if i > 0 else 0.0)
        a1 = a + q + (d / 2 if i < len(segs) - 1 else 0.0)
        parts.append(f"[0:a]atrim=start={max(0.0, a0):.4f}:end={min(src_dur, a1):.4f},"
                     f"asetpts=PTS-STARTPTS,aresample=48000[a{i}]")
        vlabels.append(f"[v{i}]")
        alabels.append(f"[a{i}]")
    parts.append("".join(vlabels) + f"concat=n={len(segs)}:v=1:a=0[v]")
    cur = alabels[0]
    for i in range(1, len(segs)):
        nxt = f"[x{i}]"
        parts.append(f"{cur}{alabels[i]}acrossfade=d={d:g}:c1=tri:c2=tri{nxt}")
        cur = nxt
    parts.append(f"{cur}apad,atrim=end={total:.4f}[a]")
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
    fc = (f"[0:v]trim=start={t_in:.4f}:end={t_in + q:.4f},setpts=PTS-STARTPTS,{_scale_filter(video)},"
          f"fps={fps:g},tpad=stop_mode=clone:stop_duration=1,trim=end_frame={n},format=yuv420p[v];"
          f"[0:a]atrim=start={t_in:.4f}:end={t_in + q:.4f},asetpts=PTS-STARTPTS,{audio['loudnorm']},"
          f"aresample={sr},aformat=sample_fmts=fltp:channel_layouts={'stereo' if ch == 2 else 'mono'},"
          f"apad,atrim=end_sample={int(round(q * sr))},asplit=2[a1][a2]")
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
    os.replace(tmp_mp4, dst_mp4)
    os.replace(tmp_wav, dst_wav)
    return {"frames": n, "duration": round(q, 4)}
