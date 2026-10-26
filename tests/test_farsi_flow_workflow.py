"""Real ffmpeg/ffprobe integration tests; no network or real Flow footage required.

Synthetic harmonic bursts test acoustic timing, not Persian intelligibility.
Run: pytest tests/test_farsi_flow_workflow.py -v
"""
from __future__ import annotations

import copy
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import numpy as np
from PIL import Image
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "pipeline" / "farsi_flow_workflow.py"
SPEC = importlib.util.spec_from_file_location("farsi_flow_workflow", SCRIPT)
fw = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = fw
SPEC.loader.exec_module(fw)


def command(args, expected=0, timeout=600):
    proc = subprocess.run([str(x) for x in args], capture_output=True, timeout=timeout,
                          env={**os.environ, "PYTHONUTF8": "1"})
    assert proc.returncode == expected, proc.stderr.decode("utf-8", "replace")[-10000:]
    return proc


def cli(manifest, subcommand="build", *extra, expected=0):
    return command([sys.executable, SCRIPT, subcommand, "--manifest", manifest, *extra], expected)


def save_manifest(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def synth(path, frequency, duration=6.4, spans=((0.8, 1.6), (3.6, 5.7))):
    """Moving 9:16 picture + modulated harmonic voice-like bursts and real silence."""
    active = "+".join(f"between(t,{a},{b})" for a, b in spans)
    voice = (f"(0.10*sin(2*PI*{frequency}*t)+0.03*sin(2*PI*{frequency*2}*t))"
             f"*(0.8+0.2*sin(2*PI*5*t))*({active})")
    command([fw.FFMPEG, "-hide_banner", "-loglevel", "error", "-y",
             "-f", "lavfi", "-i", f"testsrc2=s=720x1280:r=24:d={duration}",
             "-f", "lavfi", "-i", f"aevalsrc='{voice}':s=44100:d={duration}",
             "-map", "0:v:0", "-map", "1:a:0", "-c:v", "libx264", "-threads", "2",
             "-preset", "ultrafast", "-crf", "30", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-b:a", "160k", "-ac", "1", path])


@pytest.fixture(scope="module")
def media(tmp_path_factory):
    assert shutil.which(fw.FFMPEG) and shutil.which(fw.FFPROBE), "ffmpeg and ffprobe are required"
    assert fw.shaping_engine() != "none", "install arabic-reshaper/python-bidi or Pillow with raqm"
    root = tmp_path_factory.mktemp("flow fixture فارسی spaces")
    clips = root / "original clips"
    clips.mkdir()
    for i, freq in enumerate((310, 450, 630), 1):
        synth(clips / f"clip_{i:02d}.mp4", freq)
    cta = root / "cta native.mp4"
    synth(cta, 880, duration=1.6, spans=((0.3, 1.2),))
    font, _ = fw.resolve_font()
    data = {
        "schema_version": 1, "episode_id": "Series1_Part1", "title_fa": "آزمون فارسی",
        "clips_dir": str(clips), "out_dir": str(root / "final masters"), "font_path": font,
        "cta_video": str(cta), "cta_speaker": "ELLA",
        "cta_subtitles": [[0.3, 1.2, "ELLA", "قسمت بعدی را ببینید!"]],
        "video": {"width": 720, "height": 1280, "fps": 24, "preset": "ultrafast", "crf": 24},
        "speech": {"speech_safe": "warn"},
        "outputs": {"per_clip_location": "both", "cta_burn_subtitles": True, "cta_loudnorm": True},
        "badge": {"text": "آزمون فارسی", "end": 2.0},
        "voices": {"ELLA": {"color": [130, 255, 220], "source": "google_flow_native"}},
        "clips": [{"id": f"clip_{i:02d}", "file": f"clip_{i:02d}.mp4",
                   "trim_in": 0.3, "trim_out": 6.1,
                   "subtitles": [[0.55, 1.25, "ELLA", "سلام، حالت چطوره؟"],
                                 [3.35, 5.35, "ELLA", "امروز با هم آشپزی می‌کنیم."]]}
                  for i in range(1, 4)]}
    return root, data


@pytest.fixture(scope="module")
def built(media):
    root, data = media
    manifest = save_manifest(root / "episode.json", data)
    sources = {p: fw.sha256_file(p) for p in Path(data["clips_dir"]).glob("*.mp4")}
    sources[Path(data["cta_video"])] = fw.sha256_file(Path(data["cta_video"]))
    cli(manifest)
    out = Path(data["out_dir"])
    report = json.loads((out / "qa_report.json").read_text("utf-8"))
    return manifest, out, report, sources


def assert_av(path, expected=None):
    probe = fw.probe_media(path)
    v, a = probe["video"], probe["audio"]
    assert v and a, f"missing original audio or video: {path}"
    assert (v["codec"], v["width"], v["height"], v["fps"]) == ("h264", 720, 1280, 24)
    assert (a["codec"], a["sample_rate"], a["channels"]) == ("aac", 48000, 2)
    assert abs(v["duration"] - a["duration"]) < 0.15
    assert not fw.audio_pts_gaps(path)
    if expected is not None:
        assert v["duration"] == pytest.approx(expected, abs=1/24)
    command([fw.FFMPEG, "-v", "error", "-xerror", "-i", path, "-f", "null", "-"])
    return probe
