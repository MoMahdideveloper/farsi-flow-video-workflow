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


def test_build_outputs_and_original_audio(built):
    manifest, out, report, sources = built
    assert report["overall_status"] == report["overall_automatic"] == "pass"
    assert report["overall_status_scope"] == "automatic_checks_only"
    assert report["publication_status"] == "pending"
    assert set(report["gates"]["automatic"].values()) == {"pass"}
    assert set(report["gates"]["human_review"].values()) == {"pending"}
    for i, clip in enumerate(report["clips"], 1):
        for location in (out / "clips_subbed", Path(json.loads(manifest.read_text())["clips_dir"])):
            assert_av(location / f"clip_{i:02d}_subbed.mp4", clip["duration"])
        assert clip["mirror_sha256_match"] == [True]
        assert clip["plan"]["final"] == [0.3, 6.1]
        assert clip["plan"]["tail_padding_sec"] >= 0
        norm = out / "_work" / "Series1_Part1" / f"clip_{i:02d}_norm.mp4"
        sub = out / "clips_subbed" / f"clip_{i:02d}_subbed.mp4"
        # Stream-copy is stronger than merely finding an AAC track: samples match exactly.
        np.testing.assert_array_equal(fw.decode_pcm(norm), fw.decode_pcm(sub))
        samples = fw.decode_pcm(sub)[int(.6*16000):int(1.1*16000)]
        assert np.sqrt(np.mean(samples**2)) > .01, "audio must not be silent"
        peak = np.fft.rfftfreq(len(samples), 1/16000)[np.abs(np.fft.rfft(samples)).argmax()]
        assert peak == pytest.approx((310, 450, 630)[i-1], abs=5), "original source frequency changed"
        assert {"analysis_sr", "frame_ms", "speech_dropped_before_in_sec",
                "speech_dropped_after_out_sec", "trim_in_inside_speech", "pre_handle_sec"} <= clip["speech"].keys()
    for path, original in sources.items():
        assert fw.sha256_file(path) == original, "raw input was mutated"
    assert_av(out / "Base_Series1_Part1_Flow_Native_Farsi.mp4", report["base"]["duration"])
    assert_av(out / "Master_Series1_Part1_Flow_Native_Farsi.mp4", report["master"]["duration"])
    srt = out / "Master_Series1_Part1_Flow_Native_Farsi.srt"
    assert srt.read_bytes().startswith(b"\xef\xbb\xbf")
    assert srt.read_text("utf-8-sig").count(" --> ") == 7
    assert srt.read_text("utf-8-sig").count("قسمت بعدی را ببینید!") == 1
    with Image.open(out / "qa_Series1_Part1_contact.jpg") as image:
        image.load()
        assert image.format == "JPEG" and image.width >= 720 and image.height > 0
    assert (out / "Master_Series1_Part1_Flow_Native_Farsi_audit.mp3").stat().st_size > 1000


def test_build_is_idempotent(built):
    manifest, out, report, _ = built
    products = list(out.glob("*.mp4")) + list((out / "clips_subbed").glob("*.mp4"))
    before = {p: (fw.sha256_file(p), p.stat().st_mtime_ns) for p in products}
    cli(manifest)
    assert before == {p: (fw.sha256_file(p), p.stat().st_mtime_ns) for p in products}
    again = json.loads((out / "qa_report.json").read_text())
    assert again["overall_status"] == "pass"
    assert again["master"]["duration"] == pytest.approx(
        again["base"]["duration"] + again["master"]["cta_duration"], abs=.001)
    record = json.loads((out / "Master_Series1_Part1_Flow_Native_Farsi.mp4.build.json").read_text())
    assert record["cta_count"] == 1
    assert again["master"]["media"]["sha256"] == report["master"]["media"]["sha256"]


def test_subtitle_pixels_are_burned(built):
    _, out, _, _ = built
    def frame(path):
        p = command([fw.FFMPEG, "-v", "error", "-ss", "1.0", "-i", path,
                     "-frames:v", "1", "-pix_fmt", "rgb24", "-f", "rawvideo", "pipe:1"])
        return np.frombuffer(p.stdout, np.uint8).reshape(1280, 720, 3).astype(float)
    norm = frame(out / "_work" / "Series1_Part1" / "clip_01_norm.mp4")
    sub = frame(out / "clips_subbed" / "clip_01_subbed.mp4")
    delta = np.abs(norm-sub)
    assert delta[1030:1120, 200:520].mean() > 5, "subtitle band unchanged"
    assert delta[90:180, 200:520].mean() > 5, "episode badge absent"


def test_speech_audit_auto_expands_and_retimes(media):
    root, data = media
    data = copy.deepcopy(data)
    data["clips"] = data["clips"][:1]
    data["clips"][0].update(trim_in=1.1, trim_out=5.2,
                           subtitles=[[.85, 1.55, "ELLA", "سلام!"], [3.65, 5.65, "ELLA", "خداحافظ!"]])
    data["subtitle_style"] = {"time_base": "source"}
    data["speech"]["speech_safe"] = "auto_expand"
    data["out_dir"] = str(root / "expanded")
    path = save_manifest(root / "tight.json", data)
    result = cli(path, "speech-audit", "--json")
    clips = json.loads(result.stdout)
    speech, plan = clips[0]["speech"], clips[0]["plan"]
    assert speech["first_speech_sec"] == pytest.approx(.8, abs=.06)
    assert speech["last_speech_sec"] == pytest.approx(5.7, abs=.06)
    assert speech["cuts_speech"]
    assert plan["final"][0] <= .62 and plan["final"][1] >= 6.0
    assert not clips[0]["final_window_speech"]["cuts_speech"]
    cli(path, "build", "--no-cta")
    report = json.loads((root / "expanded" / "qa_report.json").read_text())
    assert report["overall_status"] == "pass"
    assert report["clips"][0]["subtitles"][0]["local"][0] == pytest.approx(.85-plan["final"][0], abs=.001)
    assert_av(Path(report["clips"][0]["outputs"][0]))


def test_warn_retains_unsafe_window_and_fails_gate(media):
    root, original = media
    data = copy.deepcopy(original)
    data["clips"] = data["clips"][:1]
    data["clips"][0].update(trim_in=1.1, trim_out=5.2)
    data["out_dir"] = str(root / "warn")
    path = save_manifest(root / "warn.json", data)
    result = cli(path, "speech-audit", "--json", expected=1)
    clip = json.loads(result.stdout)[0]
    assert clip["plan"]["final"] == [1.1, 5.2]
    assert clip["final_window_speech"]["cuts_speech"]
    report = json.loads((root / "warn" / "qa_report_speech-audit.json").read_text())
    assert report["overall_status"] == "fail"
    assert report["gates"]["automatic"]["speech_safe_trim"] == "fail"


def test_exact_splice_raw_original_and_fallback(media):
    root, original = media
    data = copy.deepcopy(original)
    clips = Path(data["clips_dir"])
    raw = clips / "clip_03_raw_orig.mp4"
    synth(raw, 630, 8.9, ((.9, 1.8), (5.4, 5.9), (6.4, 7.8)))
    raw_hash = fw.sha256_file(raw)
    fallback_hash = fw.sha256_file(clips / "clip_03.mp4")
    data["clips"] = [{"id": "clip_03", "file": "clip_03.mp4", "raw_orig_file": raw.name,
                      "splice_segments": [[0.0, 5.22], [6.14, 8.60]], "trim_in": .5, "trim_out": 7.5,
                      "subtitles": [[.5, 1.2, "ELLA", "سلام!"], [4.7, 5.5, "ELLA", "ممنون!"]]}]
    data["out_dir"] = str(root / "splice output")
    path = save_manifest(root / "splice.json", data)
    cli(path, "build", "--no-cta")
    report = json.loads((Path(data["out_dir"]) / "qa_report.json").read_text())
    clip = report["clips"][0]
    assert report["overall_status"] == "pass"
    assert clip["provenance"]["mode"] == "spliced"
    assert clip["provenance"]["segments"] == [[0.0, 5.22], [6.14, 8.60]]
    assert clip["provenance"]["splice_audit"]["crossfade_sec"] == .02
    assert clip["plan"]["final"] == [.5, 7.5]
    assert fw.media_duration(Path(clip["provenance"]["analysed"])) == pytest.approx(185/24, abs=.002)
    pcm = fw.decode_pcm(Path(clip["provenance"]["analysed"]))
    assert np.max(np.abs(pcm[int(5.05*16000):int(5.30*16000)])) < .003, "removed-gap audio leaked"
    assert fw.sha256_file(raw) == raw_hash
    assert fw.sha256_file(clips / "clip_03.mp4") == fallback_hash
    assert_av(Path(clip["outputs"][0]), 7.0)
    raw.rename(raw.with_suffix(".saved"))
    try:
        cli(path, "build", "--no-cta")
        fallback = json.loads((Path(data["out_dir"]) / "qa_report.json").read_text())
        assert fallback["overall_status"] == "pass"
        assert fallback["clips"][0]["provenance"]["mode"] == "pre_spliced_file"
        assert fallback["clips"][0]["provenance"]["source_sha256"] == fallback_hash
        assert any("pre-spliced" in w for w in fallback["warnings"])
    finally:
        raw.with_suffix(".saved").rename(raw)


def test_no_cta_missing_cta_and_restore_are_idempotent(built):
    manifest, out, original, _ = built
    base = out / "Base_Series1_Part1_Flow_Native_Farsi.mp4"
    master = out / "Master_Series1_Part1_Flow_Native_Farsi.mp4"
    cli(manifest, "build", "--no-cta")
    assert fw.sha256_file(master) == fw.sha256_file(base)
    assert (out / "Master_Series1_Part1_Flow_Native_Farsi.srt").read_text("utf-8-sig").count(" --> ") == 6
    cli(manifest, "build", "--cta-video", out / "missing.mp4")
    assert fw.sha256_file(master) == fw.sha256_file(base)
    cli(manifest)
    assert fw.sha256_file(master) == original["master"]["media"]["sha256"]
    assert (out / "Master_Series1_Part1_Flow_Native_Farsi.srt").read_text("utf-8-sig").count(" --> ") == 7


def test_cached_auxiliary_and_primary_hashes(tmp_path):
    primary, sidecar = tmp_path / "main.mp4", tmp_path / "samples.wav"
    primary.write_bytes(b"original"); sidecar.write_bytes(b"pcm")
    key = fw.fingerprint({"test": True})
    fw.cache_write(primary, key, output_hashes={p.name: fw.sha256_file(p) for p in (primary, sidecar)})
    assert fw.cache_ok([primary, sidecar], key)
    sidecar.write_bytes(b"bad")
    assert not fw.cache_ok([primary, sidecar], key)
    sidecar.write_bytes(b"pcm"); primary.write_bytes(b"tampered")
    assert not fw.cache_ok([primary], key)


def test_rendered_cache_corruption_is_rebuilt(built):
    manifest, out, report, _ = built
    sub = out / "clips_subbed" / "clip_02_subbed.mp4"
    sub.write_bytes(b"corrupted nonempty cache")
    cli(manifest)
    assert_av(sub)
    assert fw.sha256_file(sub) == report["clips"][1]["media"]["sha256"]


@pytest.mark.parametrize("file", ["series1_part1_whats_her_number.json", "ugly_chef_part2.json"])
def test_shipped_manifests_preserve_paths_text_and_windows(file, tmp_path):
    path = ROOT / "pipeline" / "manifests" / file
    data = json.loads(path.read_text())
    episode = fw.load_manifest(path)
    assert len(episode.clips) == 6
    assert episode.outputs["per_clip_location"] == "both"
    assert str(episode.clips_dir).startswith("C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch")
    mapped = fw.load_manifest(path, {"vars": {"BASE": str(tmp_path / "series"), "CHEF_BASE": str(tmp_path / "chef")}})
    assert mapped.clips_dir.is_absolute() and not fw.is_foreign_windows_path(mapped.clips_dir)
    assert [(c.trim_in, c.trim_out) for c in episode.clips] == [(c["trim_in"], c["trim_out"]) for c in data["clips"]]
    assert all(c.subtitles for c in episode.clips)
    if file.startswith("series1"):
        assert all(c.speech_safe == "warn" for c in episode.clips)
        assert [(c.trim_in, c.trim_out) for c in episode.clips] == [
            (0,9.4), (.5,8.9), (.5,7.5), (.6,9.4), (1.1,9.8), (.4,8.4)]
        assert episode.clips[2].splice_segments == [(0,5.22),(6.14,8.6)]
        assert mapped.clips_dir == tmp_path / "series" / "03_flow_clips" / "part1"


@pytest.mark.parametrize("change", [
    {"schema_version": 99}, {"video": {"fps": 0}}, {"video": {"width": 721}},
    {"video": {"scale_mode": "unknown"}}, {"speech": {"pre_handle": -1}},
    {"outputs": {"base_mode": "unknown"}}, {"outputs": {"per_clip_location": "unknown"}},
    {"clips": [{"id": "../escape", "file": "clip.mp4"}]},
    {"clips": [{"file": "clip.mp4", "trim_in": float("nan")}]},
    {"clips": [{"file": "clip.mp4", "trim_out": float("inf")}]},
    {"voices": {"ELLA": {"color": [999, 2, 3]}}},
])
def test_invalid_manifest_rejected(media, tmp_path, change):
    _, data = media
    data = {**copy.deepcopy(data), **change}
    with pytest.raises(fw.PipelineError):
        fw.load_manifest(save_manifest(tmp_path / "bad.json", data))


def test_output_never_overwrites_source(media, tmp_path):
    _, data = media
    data = copy.deepcopy(data)
    data["clips"][0]["file"] = "clip_01_subbed.mp4"
    with pytest.raises(fw.PipelineError, match="overwrite"):
        fw.load_manifest(save_manifest(tmp_path / "collision.json", data))


def test_dense_speech_silence_and_partial_pcm_tail():
    cfg = fw.SPEECH_DEFAULTS
    segments, _ = fw.detect_speech_segments(np.full(300, -18.0), cfg)
    assert segments == [(0, 6.0)]
    assert fw.detect_speech_segments(np.full(300, -120.0), cfg)[0] == []
    db = fw.frame_dbfs(np.ones(321, dtype=np.float32) * .2)
    assert len(db) == 2 and db[-1] > -40, "partial tail lost"
    frames, seconds = fw.frame_quantize(9.4, 24)
    assert frames == 226 and seconds >= 9.4
    assert fw.fmt_srt(59.9996) == "00:01:00,000"


def test_trim_local_shift_and_lock():
    cue = fw.Cue(.2, .8, "ELLA", "سلام!")
    clip = fw.ClipSpec(1, "clip_01", "clip_01.mp4", 1, 2, [cue])
    analysis = {"first_speech_sec": .8, "last_speech_sec": 2.2, "cuts_speech": True}
    plan = fw.plan_trim(clip, analysis, 4, fw.SPEECH_DEFAULTS)
    assert plan["final"] == [.6, 2.55]
    assert plan["subtitle_shift"] == .4
    clip.lock_trim = True
    assert fw.plan_trim(clip, analysis, 4, fw.SPEECH_DEFAULTS)["final"] == [1, 2]


def test_windows_clipboard_encoding_without_mutation(monkeypatch):
    monkeypatch.setattr(fw.platform, "system", lambda: "Windows")
    calls = []
    def fake_run(cmd, **kwargs):
        calls.append((cmd, kwargs))
        return subprocess.CompletedProcess(cmd, 0, b"", b"")
    monkeypatch.setattr(fw.subprocess, "run", fake_run)
    fw.copy_text_to_clipboard("سلام!")
    assert calls[0][0] == ["clip"]
    assert calls[0][1]["input"] == b"\xff\xfe" + "سلام!".encode("utf-16le")
    assert "-STA" in fw.copy_image_to_clipboard(Path("C:/frames/keyframe.png"), dry_run=True)
    assert len(calls) == 1, "dry-run mutated clipboard"


def test_missing_shaper_does_not_silently_pass(monkeypatch):
    monkeypatch.setattr(fw, "arabic_reshaper", None)
    monkeypatch.setattr(fw, "get_display", None)
    monkeypatch.setattr(fw.features, "check", lambda _: False)
    with pytest.raises(fw.PipelineError, match="shaping unavailable"):
        fw.shape_fa("سلام!")


def test_unknown_only_filter_is_error(media, tmp_path):
    _, data = media
    path = save_manifest(tmp_path / "filter.json", data)
    proc = cli(path, "speech-audit", "--only", "does-not-exist", expected=1)
    assert b"matched no clips" in proc.stderr


def test_empty_contact_sheet_gets_story_frame(built, tmp_path):
    manifest, out, _, _ = built
    ep = fw.load_manifest(manifest, {"out_dir": str(tmp_path)})
    path = fw.write_contact_sheet(ep, out / "Base_Series1_Part1_Flow_Native_Farsi.mp4", [])
    with Image.open(path) as im:
        im.load()
        assert im.height > 0


def test_positional_manifest_remains_compatible(media, tmp_path):
    _, data = media
    path = save_manifest(tmp_path / "positional.json", data)
    proc = command([sys.executable, SCRIPT, "speech-audit", path, "--only", "1", "--json"])
    assert len(json.loads(proc.stdout)) == 1
