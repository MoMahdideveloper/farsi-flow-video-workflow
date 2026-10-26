#!/usr/bin/env python3
"""Synthetic Google Flow fixtures for smoke tests / CI (no real Flow assets).

For a given episode manifest, writes every source clip the manifest expects
into a chosen clips dir: ffmpeg ``testsrc2`` video (1080x1920 @ 24 fps by
default) + a 48 kHz stereo track where each subtitle cue is a voiced
"speech" burst (harmonic tone with a syllable-rate envelope) at the source
time it would occupy (``trim_in + cue`` -- mapped back through
``splice_segments`` for spliced clips).  A -62 dBFS noise floor sits under
everything.  Optional anomalies exercise the speech-safe analyzer:

  * ``--leak-in CLIP``   a word that starts 0.30 s *before* trim_in
  * ``--fps CLIP=30``    a source at a different frame rate
  * the spliced raw original gets a junk burst inside the removed gap

Also writes an optional CTA clip (bursts at cta_subtitles) and a 9:16 PNG
keyframe for ``clipboard-image``.  Usage:

  python pipeline/tools/synth_fixtures.py pipeline/manifests/ugly_chef_part2.json \
      --clips-dir /tmp/ffw/clips --cta /tmp/ffw/cta.mp4 --keyframe /tmp/ffw/KF_01.png \
      --leak-in clip_05 --fps clip_04=30
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

SR = 48000


def speech_burst(n: int, f0: float, seed: int) -> np.ndarray:
    """Voiced-ish burst: f0 + harmonics, 4-6 Hz syllable envelope, -12 dBFS peak."""
    t = np.arange(n) / SR
    rng = np.random.default_rng(seed)
    vib = 1 + 0.03 * np.sin(2 * np.pi * 5.5 * t)
    sig = sum((0.6 / k) * np.sin(2 * np.pi * f0 * k * np.cumsum(vib) / SR) for k in range(1, 6))
    syl = 0.55 + 0.45 * np.abs(np.sin(np.pi * rng.uniform(4.0, 6.0) * t))
    edge = np.minimum(1.0, np.minimum(t, t[::-1]) / 0.015)  # 15 ms attack / release
    out = sig * syl * edge
    return 0.25 * out / (np.max(np.abs(out)) + 1e-9)


def map_span(a: float, b: float, segs: list | None) -> list[tuple[float, float]]:
    """Map a span on the spliced timeline back onto raw-original time."""
    if not segs:
        return [(a, b)]
    out, base = [], 0.0
    for s0, s1 in segs:
        L = s1 - s0
        lo, hi = max(a, base), min(b, base + L)
        if hi > lo:
            out.append((s0 + lo - base, s0 + hi - base))
        base += L
    return out


def write_wav(path: Path, pcm: np.ndarray) -> None:
    st = np.stack([pcm, pcm * 0.97], axis=1)
    data = (np.clip(st, -1, 1) * 32767).astype("<i2").tobytes()
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data)


def render(dst: Path, dur: float, spans: list[tuple[float, float]], *, fps: int = 24,
           size: str = "1080x1920", seed: int = 0, label: str = "") -> None:
    n = int(round(dur * SR))
    rng = np.random.default_rng(seed)
    pcm = rng.normal(0, 10 ** (-62 / 20), n)  # noise floor
    for k, (a, b) in enumerate(spans):
        i0, i1 = max(0, int(a * SR)), min(n, int(b * SR))
        if i1 > i0:
            pcm[i0:i1] += speech_burst(i1 - i0, 140 + 35 * (k % 4), seed * 31 + k)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ffw_synth_") as td:
        wav = Path(td) / "a.wav"
        write_wav(wav, pcm)
        vf = (f"drawtext=text='{label} %{{pts\\:hms}}':fontsize=64:fontcolor=white:"
              f"box=1:boxcolor=black@0.6:x=(w-tw)/2:y=h*0.45") if label else "null"
        cmd = ["ffmpeg", "-y", "-loglevel", "error",
               "-f", "lavfi", "-i", f"testsrc2=size={size}:rate={fps}:duration={dur:.3f}",
               "-i", str(wav), "-vf", vf, "-map", "0:v", "-map", "1:a",
               "-c:v", "libx264", "-preset", "ultrafast", "-crf", "23", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-ar", str(SR), "-ac", "2", "-shortest", str(dst)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0 and "drawtext" in r.stderr:  # ffmpeg without libfreetype
            cmd[cmd.index("-vf") + 1] = "null"
            r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"ffmpeg failed for {dst}: {r.stderr[-600:]}")


def cue_times(raw) -> tuple[float, float]:
    if isinstance(raw, dict):
        return float(raw["start"]), float(raw["end"])
    return float(raw[0]), float(raw[1])


def keyframe(dst: Path, size=(1080, 1920)) -> None:
    from PIL import Image, ImageDraw
    w, h = size
    y = np.linspace(0, 1, h)[:, None]
    x = np.linspace(0, 1, w)[None, :]
    y, x = np.broadcast_arrays(y, x)
    rgb = np.stack([200 * y + 30 * x, 120 + 60 * x, 220 - 150 * y], axis=-1).clip(0, 255)
    im = Image.fromarray(rgb.astype(np.uint8), "RGB")
    d = ImageDraw.Draw(im)
    d.ellipse([w * 0.25, h * 0.30, w * 0.75, h * 0.62], fill=(250, 200, 70), outline=(60, 40, 20), width=8)
    d.ellipse([w * 0.47, h * 0.26, w * 0.56, h * 0.31], fill=(60, 170, 70))  # Agnes' single leaf
    dst.parent.mkdir(parents=True, exist_ok=True)
    im.save(dst)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("manifest", type=Path)
    ap.add_argument("--clips-dir", type=Path, required=True, help="where to write the source clips")
    ap.add_argument("--cta", type=Path, help="also write a synthetic CTA clip here")
    ap.add_argument("--keyframe", type=Path, help="also write a 9:16 PNG keyframe here")
    ap.add_argument("--size", default="1080x1920", help="source WxH (default 1080x1920)")
    ap.add_argument("--min-duration", type=float, default=10.0, help="Flow clip length floor (s)")
    ap.add_argument("--leak-in", action="append", default=[], metavar="CLIP",
                    help="add a word starting 0.30 s before trim_in (repeatable)")
    ap.add_argument("--fps", action="append", default=[], metavar="CLIP=FPS",
                    help="render this clip at another frame rate (repeatable)")
    a = ap.parse_args(argv)
    m = json.loads(a.manifest.read_text("utf-8-sig"))
    fps_over = {k: int(v) for k, _, v in (x.partition("=") for x in a.fps)}
    summary: dict = {"manifest": str(a.manifest), "clips": {}}
    for i, c in enumerate(m["clips"], 1):
        cid = c.get("id") or f"clip_{i:02d}"
        t_in = float(c.get("trim_in", 0.0) or 0.0)
        segs = c.get("splice_segments")
        timeline = [(t_in + s0 + 0.05, t_in + s1 - 0.05) for s0, s1 in map(cue_times, c.get("subtitles", []))]
        if cid in a.leak_in:
            timeline.insert(0, (max(0.0, t_in - 0.30), t_in + 0.12))
        last = max([b for _, b in timeline] + [float(c.get("trim_out") or 0.0)])
        if segs:  # raw original: speech mapped through the splice + junk inside each removed gap
            src_spans = [s for a0, b0 in timeline for s in map_span(a0, b0, segs)]
            src_spans += [(g0 + 0.15, g1 - 0.15) for (_, g0), (g1, _) in zip(segs, segs[1:]) if g1 - g0 > 0.4]
            dur = max(a.min_duration, segs[-1][1] + 0.6)
            dst = a.clips_dir / c["raw_orig_file"]
            spliced_len = sum(s1 - s0 for s0, s1 in segs)
            summary["clips"][cid] = {"raw_orig": str(dst), "spliced_duration": round(spliced_len, 3)}
        else:
            src_spans = timeline
            dur = max(a.min_duration, last + 0.6)
            dst = a.clips_dir / c["file"]
            summary["clips"][cid] = {}
        render(dst, dur, src_spans, fps=fps_over.get(cid, 24), size=a.size, seed=i, label=cid)
        summary["clips"][cid].update(path=str(dst), duration=round(dur, 3), fps=fps_over.get(cid, 24),
                                     speech_timeline=[[round(x, 3), round(y, 3)] for x, y in timeline],
                                     speech_source=[[round(x, 3), round(y, 3)] for x, y in src_spans],
                                     leak_in=cid in a.leak_in)
        print(f"{cid}: {dst.name} {dur:.2f}s, {len(src_spans)} speech bursts", file=sys.stderr)
    if a.cta:
        spans = [(s0 + 0.05, s1 - 0.05) for s0, s1 in map(cue_times, m.get("cta_subtitles") or [])]
        dur = max([b for _, b in spans] + [3.0]) + 0.45
        render(a.cta, dur, spans, size="720x1280", seed=99, label="CTA")
        summary["cta"] = {"path": str(a.cta), "duration": round(dur, 3)}
    if a.keyframe:
        keyframe(a.keyframe)
        summary["keyframe"] = str(a.keyframe)
    out = a.clips_dir / "fixtures.json"
    out.write_text(json.dumps(summary, indent=2), "utf-8")
    print(json.dumps({"fixtures": str(out), "clips": len(summary["clips"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
