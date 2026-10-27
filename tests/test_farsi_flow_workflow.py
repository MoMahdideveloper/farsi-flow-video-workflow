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
        for location in (out / "clips_subbed", Path(json.loads(manifest.read_text("utf-8"))["clips_dir"])):
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
    again = json.loads((out / "qa_report.json").read_text("utf-8"))
    assert again["overall_status"] == "pass"
    assert again["master"]["duration"] == pytest.approx(
        again["base"]["duration"] + again["master"]["cta_duration"], abs=.001)
    record = json.loads((out / "Master_Series1_Part1_Flow_Native_Farsi.mp4.build.json").read_text("utf-8"))
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
    report = json.loads((root / "expanded" / "qa_report.json").read_text("utf-8"))
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
    report = json.loads((root / "warn" / "qa_report_speech-audit.json").read_text("utf-8"))
    assert report["overall_status"] == "fail"
    assert report["gates"]["automatic"]["speech_safe_trim"] == "fail"


def test_exact_splice_raw_original_and_fallback(media):
    root, original = media
    data = copy.deepcopy(original)
    # A real pre-spliced fallback must cover the curated 7.50s out-point.
    # Keep it isolated so this regression cannot mutate the shared fixture.
    clips = root / "splice originals"
    clips.mkdir()
    data["clips_dir"] = str(clips)
    synth(clips / "clip_03.mp4", 630, 7.7, ((.9, 1.8), (5.46, 6.86)))
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
    report = json.loads((Path(data["out_dir"]) / "qa_report.json").read_text("utf-8"))
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
        fallback = json.loads((Path(data["out_dir"]) / "qa_report.json").read_text("utf-8"))
        assert fallback["overall_status"] == "pass"
        assert fallback["clips"][0]["provenance"]["mode"] == "pre_spliced_file"
        assert fallback["clips"][0]["plan"]["final"] == [.5, 7.5]
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
    data = json.loads(path.read_text("utf-8"))
    episode = fw.load_manifest(path)
    assert len(episode.clips) == 6
    assert episode.outputs["per_clip_location"] == "both"
    assert str(episode.clips_dir).startswith("C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch")
    mapped = fw.load_manifest(path, {"vars": {"BASE": str(tmp_path / "series"), "CHEF_BASE": str(tmp_path / "chef")}})
    assert mapped.clips_dir.is_absolute() and not fw.is_foreign_windows_path(mapped.clips_dir)
    assert [(c.trim_in, c.trim_out) for c in episode.clips] == [(c["trim_in"], c["trim_out"]) for c in data["clips"]]
    assert all(c.subtitles for c in episode.clips)
    if file.startswith("series1"):
        assert all(c.speech_safe in ("warn", "auto_expand") for c in episode.clips)
        assert episode.clips[2].allow_speech_splice is True
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


def test_all_six_series1_clips_with_shipped_windows(media):
    root, _ = media
    shipped = ROOT / "pipeline" / "manifests" / "series1_part1_whats_her_number.json"
    data = json.loads(shipped.read_text("utf-8"))
    clips = root / "six originals"
    clips.mkdir()
    for i, clip in enumerate(data["clips"], 1):
        centers = [clip["trim_in"] + (c[0]+c[1])/2 for c in clip["subtitles"]]
        # This fixture verifies fixed shipped windows. Keep synthetic bursts and
        # required handles INSIDE those windows; otherwise auto_expand correctly
        # widens clip_03 and the old fixed-duration assertion is self-contradictory.
        # Unsafe-window expansion is tested independently above, never disabled.
        centers = [min(max(c, clip["trim_in"] + .55), clip["trim_out"] - .70) for c in centers]
        spans = [(c-.20, c+.20) for c in centers]
        synth(clips / clip["file"], 280+i*40, clip["trim_out"]+.5, spans)
        if clip.get("raw_orig_file"):
            mapped = []
            for a, b in spans:
                offset = 0.0
                for lo, hi in clip["splice_segments"]:
                    x, y = max(a, offset), min(b, offset+hi-lo)
                    if x < y:
                        mapped.append((lo+x-offset, lo+y-offset))
                    offset += hi-lo
            synth(clips / clip["raw_orig_file"], 280+i*40, 9, mapped)
    cta = root / "six cta.mp4"
    synth(cta, 880, 8, ((.4, 3.2), (4.0, 7.6)))
    font, _ = fw.resolve_font()
    data.update(clips_dir=str(clips), out_dir=str(root / "six final"), font_path=font, cta_video=str(cta))
    data["video"]["preset"] = "ultrafast"
    data["outputs"]["cta_burn_subtitles"] = True
    path = save_manifest(root / "six.json", data)
    cli(path)
    out = Path(data["out_dir"])
    report = json.loads((out / "qa_report.json").read_text("utf-8"))
    assert report["overall_status"] == "pass"
    assert len(report["clips"]) == 6
    for original, result in zip(data["clips"], report["clips"]):
        assert result["plan"]["final"] == [original["trim_in"], original["trim_out"]]
        assert len(result["outputs"]) == 2
        assert_av(clips / f'{original["id"]}_subbed.mp4', result["duration"])
    assert report["base"]["duration"] == pytest.approx(50.375, abs=.001)
    assert report["master"]["duration"] == pytest.approx(58.375, abs=.001)
    assert report["master"]["cue_count"] == 17
    master = Path(report["master"]["path"])
    sha = fw.sha256_file(master)
    cli(path)
    assert fw.sha256_file(master) == sha


def test_reference_scripts_match_manifest_dialogue_and_trims():
    import ast
    import re
    import textwrap
    text = (ROOT / "docs" / "farsi-flow-workflow" / "00-context-and-requirements.md").read_text("utf-8")
    references = []
    for source in re.findall(r"```python\n(.*?)```", text, flags=re.S):
        for node in ast.parse(textwrap.dedent(source)).body:
            if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CLIPS" for t in node.targets):
                references.append(ast.literal_eval(node.value))
    assert len(references) == 2
    for filename, rows in zip(("series1_part1_whats_her_number.json", "ugly_chef_part2.json"), references):
        data = json.loads((ROOT / "pipeline" / "manifests" / filename).read_text("utf-8"))
        for actual, expected in zip(data["clips"], rows):
            assert (actual["file"], actual["trim_in"], actual["trim_out"]) == expected[:3]
            assert [tuple(s) for s in actual["subtitles"]] == expected[3]


def test_failed_promotion_keeps_previous_output(media, tmp_path):
    _, data = media
    ep = fw.load_manifest(save_manifest(tmp_path / "episode.json", data))
    previous, invalid = tmp_path / "previous.mp4", tmp_path / "render.tmp.mp4"
    previous.write_bytes(b"keep this previous output")
    invalid.write_bytes(b"invalid media")
    with pytest.raises(fw.PipelineError):
        fw.promote(ep, invalid, previous, 1.0, "test")
    assert previous.read_bytes() == b"keep this previous output"


def test_ffprobe_na_fields_are_tolerated(monkeypatch, tmp_path):
    monkeypatch.setattr(fw, "ffprobe_json", lambda _: {
        "format": {"duration": "1.5"}, "streams": [{"codec_type": "video", "codec_name": "h264",
            "duration": "N/A", "nb_frames": "N/A", "avg_frame_rate": "24/1", "start_time": "N/A"}]})
    probe = fw.probe_media(tmp_path / "video.mp4")
    assert probe["video"]["duration"] == 1.5 and probe["video"]["frames"] == 0


@pytest.mark.parametrize("edge,segments,span", [
    ("start", [(0.2, 5.22), (6.14, 8.6)], (0.1, 0.7)),
    ("end", [(0.0, 5.22), (6.14, 8.6)], (8.3, 8.8)),
])
def test_outer_splice_cuts_cannot_escape_audit(edge, segments, span):
    boundaries = fw.splice_boundary_checks(segments, [span], .02)
    assert len(boundaries) == 4
    flagged = [b for b in boundaries if b["touches_speech"]]
    assert len(flagged) == 1 and flagged[0]["edge"] == edge
    assert flagged[0]["crossfade_neighborhood_sec"] == 0


def test_internal_splice_crossfade_has_speech_guard():
    boundaries = fw.splice_boundary_checks([(0, 5.22), (6.14, 8.6)], [(5.19, 5.21)], .02)
    assert boundaries[1]["touches_speech"]
    assert boundaries[1]["crossfade_neighborhood_sec"] == .02


@pytest.mark.parametrize("mode", ["warn", "auto_expand", "off"])
def test_trim_beyond_source_is_not_silently_shortened(mode):
    clip = fw.ClipSpec(1, "clip_03", "clip_03.mp4", .5, 7.5, [], speech_safe=mode)
    with pytest.raises(fw.PipelineError, match="exceeds source duration"):
        fw.plan_trim(clip, None, 6.4, fw.SPEECH_DEFAULTS)
    assert (clip.trim_in, clip.trim_out) == (.5, 7.5)


@pytest.mark.parametrize("starts", [(0, .2), (10, 10), (-.03, .03)])
@pytest.mark.parametrize("stage", ["direct", "splice"])
def test_source_pts_offset_rejected_before_audio_retiming(tmp_path, monkeypatch, starts, stage):
    ep = fw.load_manifest(ROOT / "pipeline/manifests/series1_part1_whats_her_number.json")
    monkeypatch.setattr(fw, "prepare_source", lambda *args: (tmp_path / "source.mp4", {}))
    monkeypatch.setattr(fw, "probe_media", lambda _: {
        "video": {"duration": 10, "start_time": starts[0]},
        "audio": {"duration": 10, "start_time": starts[1]}})
    with pytest.raises(fw.PipelineError, match="source (stream start offsets|A/V starts misaligned)"):
        if stage == "direct":
            fw.plan_clip(ep, ep.clips[0], tmp_path)
        else:
            fw.splice_clip(tmp_path / "source.mp4", [(0, 1)], tmp_path / "out.mov", ep.speech, ep.video)


def test_outer_splice_tail_failure_reaches_cli_and_qa(media):
    root, original = media
    data = copy.deepcopy(original)
    clips = root / "unsafe splice originals"
    clips.mkdir()
    synth(clips / "clip_03_raw_orig.mp4", 630, 8.9, ((.9, 1.8), (8.3, 8.8)))
    data.update(clips_dir=str(clips), out_dir=str(root / "unsafe splice qa"))
    data["clips"] = [{"id": "clip_03", "file": "clip_03.mp4",
                      "raw_orig_file": "clip_03_raw_orig.mp4",
                      "splice_segments": [[0.0, 5.22], [6.14, 8.60]],
                      "trim_in": 0, "trim_out": None, "subtitles": []}]
    path = save_manifest(root / "unsafe-splice.json", data)
    cli(path, "speech-audit", "--json", expected=1)
    report = json.loads((Path(data["out_dir"]) / "qa_report_speech-audit.json").read_text("utf-8"))
    assert report["overall_status"] == "fail"
    assert report["gates"]["automatic"]["splice_boundaries"] == "fail"
    cuts = report["clips"][0]["provenance"]["splice_audit"]["boundaries"]
    assert any(c["at_sec"] == 8.6 and c["touches_speech"] for c in cuts)


def test_raw_unsubbed_preference_and_allow_speech_splice(tmp_path):
    raw_dir = tmp_path / "raw_unsubbed"
    raw_dir.mkdir(parents=True)
    raw_clip = raw_dir / "clip_01.mp4"
    raw_clip.write_bytes(b"clean")
    overwritten_clip = tmp_path / "clip_01.mp4"
    overwritten_clip.write_bytes(b"already-subbed")
    ep = fw.load_manifest(
        ROOT / "pipeline/manifests/series1_part1_whats_her_number.json",
        {"clips_dir": str(tmp_path), "out_dir": str(tmp_path / "out")},
    )
    src_file, _ = fw.clip_source_paths(ep, ep.clips[0])
    assert src_file == raw_clip
    boundaries = fw.splice_boundary_checks([(0.0, 5.22), (6.14, 8.6)], [(4.46, 7.46)], 0.02)
    assert [b["internal"] for b in boundaries] == [False, True, True, False]
    assert [b["touches_speech"] for b in boundaries] == [False, True, True, False]


# Stage 2: independent golden expectations, not values generated by the evaluator.
EVIDENCE = ROOT / 'docs/series2-meaning-and-pipeline-solution'
EXPECTED_FAILURES = {
    'part1': {'clip_01': set(fw.FAIL_FLAGS), 'clip_02': {'INTERNAL_SCENE_CUT'},
              'clip_03': {'KEYFRAME_MISMATCH'}, 'clip_06': {'KEYFRAME_MISMATCH'}},
    'part2': {'clip_04': {'KEYFRAME_MISMATCH'}, 'clip_05': set(fw.FAIL_FLAGS)},
    'part3': {'clip_04': {'KEYFRAME_MISMATCH'}},
    'part4': {'clip_04': {'KEYFRAME_MISMATCH', 'INTERNAL_SCENE_CUT'},
              'clip_06': set(fw.FAIL_FLAGS)},
    'part5': {f'clip_{i:02d}': {'KEYFRAME_MISMATCH'} for i in (1, 2, 3, 6)},
}


def good_probe(**updates):
    return {'num_sampled_frames': 20, 'l1_vs_keyframe_start': 10.0,
            'l1_vs_keyframe_mean': 12.0, 'l1_vs_keyframe_end': 14.0,
            'max_internal_jump_l1': 8.0, 'max_internal_jump_time_sec': .5,
            'detected_scene_cuts_sec': [], **updates}


@pytest.mark.parametrize('changes,flags', [
    ({}, set()),
    ({'l1_vs_keyframe_start': 32, 'l1_vs_keyframe_mean': 33}, set()),
    ({'l1_vs_keyframe_start': 33, 'l1_vs_keyframe_mean': 32}, set()),
    ({'l1_vs_keyframe_start': 32.01, 'l1_vs_keyframe_mean': 32.01}, {'KEYFRAME_MISMATCH'}),
    ({'closest_other_keyframe': 'other', 'closest_other_keyframe_l1_start': 5}, set()),
    ({'closest_other_keyframe': 'other', 'closest_other_keyframe_l1_start': 4.99},
     {'MULTI_INGREDIENT_CONTAMINATION'}),
    ({'max_internal_jump_l1': 32}, set()),
    ({'max_internal_jump_l1': 32.01}, {'INTERNAL_SCENE_CUT'}),
])
def test_stage2_probe_thresholds(changes, flags):
    result = fw.evaluate_probe_entry(good_probe(**changes), clip_id='clip_01')
    assert set(result['flags']) == flags
    assert result['passed'] == (not flags)
    assert 0 <= result['suggested_visual_trim_in'] <= result['suggested_visual_trim_out'] <= 10


@pytest.mark.parametrize('field,value', [
    ('l1_vs_keyframe_start', None), ('l1_vs_keyframe_mean', float('nan')),
    ('max_internal_jump_l1', float('inf')), ('num_sampled_frames', 0),
    ('sample_fps', -1), ('detected_scene_cuts_sec', [-.5]),
])
def test_stage2_invalid_probe_cannot_pass(field, value):
    with pytest.raises(fw.PipelineError, match='probe'):
        fw.evaluate_probe_entry(good_probe(**{field: value}))


@pytest.mark.parametrize('part', range(1, 6))
def test_stage2_all_manifests_and_exact_probe_flags(part, tmp_path):
    path = ROOT / f'pipeline/manifests/fruits_of_power_part{part}.json'
    ep = fw.load_manifest(path, {'vars': {'BASE': str(tmp_path), 'SRC': str(tmp_path)}})
    assert not ep.fallback_to_source_on_visual_fail and ep.tight_speech_trim
    assert ep.source_video and ep.story_summary_fa
    assert fw.step1_story_lock(ep)['status'] == 'pass'
    assert len(ep.clips) == 6
    probe = json.loads((EVIDENCE / 'parts1_to_5_clips_probe.json').read_text())['parts'][f'part{part}']
    for i, clip in enumerate(ep.clips, 1):
        assert clip.keyframe == tmp_path / f'part{part}/keyframes/KF_{i:02d}.jpg'
        assert clip.story_beat.strip() and clip.expected_speakers
        assert {c.speaker for c in clip.subtitles} <= set(clip.expected_speakers) <= ep.voices.keys()
        assert all(np.isfinite(clip.source_span)) and 0 <= clip.source_span[0] < clip.source_span[1]
        result = fw.evaluate_probe_entry(probe[clip.id])
        assert set(result['flags']) == EXPECTED_FAILURES[f'part{part}'].get(clip.id, set())
    if part == 5:
        assert 'دکتر گلابی' in ep.voices['PEACH']['name_fa']
        assert 'دکتر گلابی' in ep.outputs['publish_caption_fa']


def test_stage2_trace_all_parts_cli_complete_but_not_a_render_signoff(tmp_path):
    out = tmp_path / 'audit.json'
    command([sys.executable, SCRIPT, 'trace-all-parts', '--probe-json',
             EVIDENCE / 'parts1_to_5_clips_probe.json', '--out-json', out], expected=1)
    audit = json.loads(out.read_text(encoding='utf-8'))
    assert audit['summary']['clips_total'] == 30
    assert audit['summary']['clips_failed_visual'] == 13
    assert audit['summary']['flag_counts'] == dict(zip(fw.FAIL_FLAGS, (12, 3, 5)))
    assert audit['summary']['clips_planned_source_bridge'] == 0
    assert audit['summary']['clips_resolved_by_source_bridge'] == 0
    assert audit['audit_passed'] is False
    for ep in audit['episodes']:
        assert len(ep['clips']) == 6 and set(ep['step_trace']) == set(fw.STEP_NAMES)
        assert not ep['all_passed'] and not ep['audit_passed']
        assert ep['step_trace'][fw.STEP_NAMES[5]]['status'] == 'not_run'
        for clip in ep['clips']:
            assert set(clip['step_trace']) == set(fw.STEP_NAMES)
            assert clip['story_beat']
            step5 = clip['step_trace'][fw.STEP_NAMES[4]]
            if clip['step_trace'][fw.STEP_NAMES[2]]['flags']:
                assert step5['status'] == 'fail' and not step5['resolved']


def test_stage2_partial_probe_cli_must_fail(tmp_path):
    probe = json.loads((EVIDENCE / 'parts1_to_5_clips_probe.json').read_text())
    del probe['parts']['part5']['clip_06']
    path = save_manifest(tmp_path / 'partial.json', probe)
    proc = command([sys.executable, SCRIPT, 'trace-all-parts', '--probe-json', path,
                    '--out-json', tmp_path / 'out.json'], expected=1)
    assert b'clip_06' in proc.stderr and b'probe' in proc.stderr


@pytest.fixture(scope='module')
def stage2_media(tmp_path_factory):
    root = tmp_path_factory.mktemp('stage2 media')
    video = {**fw.VIDEO_DEFAULTS, 'width': 180, 'height': 320, 'preset': 'ultrafast'}
    voice = '(0.12*sin(2*PI*310*t))*(between(t,2,5))'
    flow = root / 'flow.mp4'
    command([fw.FFMPEG, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=magenta:s=180x320:r=24:d=10',
             '-f', 'lavfi', '-i', f"aevalsrc='{voice}':s=48000:d=10", '-c:v', 'libx264',
             '-threads', '2', '-preset', 'ultrafast', '-c:a', 'aac', '-ac', '2', flow])
    source = root / 'original.mp4'
    font, _ = fw.resolve_font()
    font_ff = str(font).replace('\\', '/').replace(':', r'\:')
    command([fw.FFMPEG, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'color=c=red:s=180x320:r=24:d=2',
             '-f', 'lavfi', '-i', 'color=c=blue:s=180x320:r=24:d=2',
             '-f', 'lavfi', '-i', 'color=c=green:s=180x320:r=24:d=2',
             '-f', 'lavfi', '-i', 'sine=frequency=880:sample_rate=48000:duration=6',
             '-filter_complex', f"[0:v][1:v][2:v]concat=n=3:v=1:a=0,drawtext=fontfile='{font_ff}':"
             "text='English':fontcolor=white:fontsize=24:x=(w-tw)/2:y=h*0.78[v]",
             '-map', '[v]', '-map', '3:a', '-c:v', 'libx264', '-threads', '2', '-preset', 'ultrafast',
             '-c:a', 'aac', '-ac', '2', source])
    kfs = {}
    for name, color in [('own', 'blue'), ('other', 'magenta'), ('start', 'red')]:
        kfs[name] = root / f'{name}.png'
        Image.new('RGB', (180, 320), color).save(kfs[name])
    return root, flow, source, kfs, video


def rgb_frame(path, sec, w=180, h=320):
    data = command([fw.FFMPEG, '-v', 'error', '-ss', str(sec), '-i', path, '-frames:v', '1',
                    '-f', 'rawvideo', '-pix_fmt', 'rgb24', 'pipe:1']).stdout
    return np.frombuffer(data, np.uint8).reshape(h, w, 3)


def audio_stream_hash(path):
    return command([fw.FFMPEG, '-v', 'error', '-i', path, '-map', '0:a:0', '-c:a', 'copy',
                    '-f', 'streamhash', '-hash', 'sha256', 'pipe:1']).stdout


def test_stage2_live_visual_detection_and_keyframe_immutability(stage2_media):
    _, flow, source, kfs, _ = stage2_media
    before = {p: fw.sha256_file(p) for p in kfs.values()}
    match = fw.analyze_clip_visuals(flow, kfs['other'], clip_id='other')
    assert match['evaluation']['passed']
    bad = fw.analyze_clip_visuals(flow, kfs['own'], kfs, clip_id='own')
    assert set(bad['evaluation']['flags']) == {'KEYFRAME_MISMATCH', 'MULTI_INGREDIENT_CONTAMINATION'}
    cut = fw.analyze_clip_visuals(source, kfs['start'], clip_id='start')
    assert 'INTERNAL_SCENE_CUT' in cut['evaluation']['flags']
    assert cut['detected_scene_cuts_sec'] == [2, 4]
    assert before == {p: fw.sha256_file(p) for p in kfs.values()}


def test_stage2_ten_second_clip_tight_trim_keeps_all_active_audio(stage2_media):
    _, flow, _, _, _ = stage2_media
    speech = fw.analyze_clip_speech(flow)
    clip = fw.ClipSpec(1, 'clip_01', str(flow), 0, 10, [])
    plan = fw.plan_trim(clip, speech, 10, fw.SPEECH_DEFAULTS)
    tight = fw.apply_tight_speech_trim(plan, speech['first_speech_sec'], speech['last_speech_sec'], fw.SPEECH_DEFAULTS)
    assert 3.5 <= tight['duration'] <= 3.65
    assert tight['final'][0] <= speech['first_speech_sec'] - .19
    assert tight['final'][1] >= speech['last_speech_sec'] + .34
    assert not fw.window_speech_check(speech, *tight['final'])['cuts_speech']
    assert plan['final'] == [0, 10], 'caller plan mutated'
    assert tight['subtitle_shift'] == -tight['final'][0]


def test_stage2_hybrid_real_video_source_span_inpaint_and_original_audio(stage2_media, tmp_path):
    _, flow, source, kfs, video = stage2_media
    originals = {p: fw.sha256_file(p) for p in [flow, source, *kfs.values()]}
    out = tmp_path / 'fallback.mp4'
    rec = fw.extract_source_fallback_clip(source, (2, 4), flow, out, video=video, anchor_sec=1.8)
    assert rec['verified'] and rec['frames'] == 240 and rec['frames_inpainted'] > 0
    assert rec['source_span'] == [2, 4]
    assert rec['flow_audio_stream_sha256'] == rec['output_audio_stream_sha256']
    assert audio_stream_hash(flow) == audio_stream_hash(out) != audio_stream_hash(source)
    np.testing.assert_array_equal(fw.decode_pcm(flow), fw.decode_pcm(out))
    original, replacement = rgb_frame(source, 2.5), rgb_frame(out, 2.3)
    assert np.abs(original[:220].astype(float) - replacement[:220]).mean() < 2
    assert np.abs(rgb_frame(flow, 2.3).astype(float) - replacement).mean() > 30
    assert (replacement[235:280].mean(axis=2) > 200).sum() < (original[235:280].mean(axis=2) > 200).sum()
    assert fw.media_duration(out) == pytest.approx(10, abs=1/24)
    assert originals == {p: fw.sha256_file(p) for p in originals}


@pytest.mark.parametrize('span', [(-1, 2), (3, 3), (4, 2), (5, 8), (6, 7)])
def test_stage2_fallback_refuses_invalid_source_spans(stage2_media, tmp_path, span):
    _, flow, source, _, video = stage2_media
    out = tmp_path / 'keep.mp4'
    out.write_bytes(b'previous-good-output')
    with pytest.raises(fw.PipelineError, match='source_span'):
        fw.extract_source_fallback_clip(source, span, flow, out, video=video)
    assert out.read_bytes() == b'previous-good-output'


def stage2_manifest(stage2_media, tmp_path):
    _, flow, source, kfs, video = stage2_media
    return {
        'schema_version': 1, 'episode_id': 'Stage2', 'clips_dir': str(flow.parent),
        'out_dir': str(tmp_path / 'out'), 'source_video': str(source),
        'story_summary_fa': 'آزمون', 'fallback_to_source_on_visual_fail': True,
        'tight_speech_trim': True, 'video': video,
        'voices': {'TEST': {'name_fa': 'آزمون'}},
        'clips': [{'id': 'clip_01', 'file': flow.name, 'trim_in': 0, 'trim_out': 10,
                   'keyframe': str(kfs['own']), 'expected_speakers': ['TEST'],
                   'story_beat': 'Synthetic source scene replaces corrupt Flow picture',
                   'source_span': [2, 4], 'subtitles': [[2, 5, 'TEST', 'سلام']]}],
    }


def test_stage2_hybrid_orchestration_build_and_cache(stage2_media, tmp_path):
    data = stage2_manifest(stage2_media, tmp_path)
    path = save_manifest(tmp_path / 'hybrid.json', data)
    cli(path, 'build', '--no-cta', '--no-contact')
    report = json.loads((Path(data['out_dir']) / 'qa_report.json').read_text())
    assert report['all_passed'] and report['visual_continuity_resolved']
    assert not report['visual_continuity_passed']
    assert report['publication_status'] == 'pending'
    clip = report['clips'][0]
    assert clip['fallback']['resolved'] and clip['fallback']['extraction']['verified']
    assert clip['provenance']['visual_fallback']
    assert not clip['final_window_speech']['cuts_speech']
    assert 3.5 <= clip['duration'] <= 3.7
    trace = json.loads((Path(data['out_dir']) / 'trace_Stage2.json').read_text())
    assert set(trace['clips'][0]['step_trace']) == set(fw.STEP_NAMES)
    bridge = Path(clip['provenance']['analysed'])
    before = (fw.sha256_file(bridge), bridge.stat().st_mtime_ns)
    cli(path, 'build', '--no-cta', '--no-contact')
    assert before == (fw.sha256_file(bridge), bridge.stat().st_mtime_ns)


@pytest.mark.parametrize('change', [
    {'fallback_to_source_on_visual_fail': 'false'}, {'tight_speech_trim': 'true'},
    {'visual_gate': {'sample_fps': 0}}, {'visual_gate': {'keyframe_threshold': float('nan')}},
    {'visual_gate': {'thumb_size': [0, 128]}}, {'source_video': None},
])
def test_stage2_invalid_narrative_schema_rejected(stage2_media, tmp_path, change):
    data = {**stage2_manifest(stage2_media, tmp_path), **change}
    with pytest.raises(fw.PipelineError):
        fw.load_manifest(save_manifest(tmp_path / 'bad.json', data))


@pytest.mark.parametrize('change', [
    {'expected_speakers': 'TEST'}, {'tight_speech_trim': 'false'},
    {'source_span': ['not-number', 4]}, {'source_span': [float('nan'), 4]},
    {'source_span': [4, 4]}, {'source_span': None},
])
def test_stage2_invalid_clip_schema_rejected(stage2_media, tmp_path, change):
    data = stage2_manifest(stage2_media, tmp_path)
    data['clips'][0].update(change)
    with pytest.raises(fw.PipelineError):
        fw.load_manifest(save_manifest(tmp_path / 'bad.json', data))


def test_stage2_missing_visual_or_disabled_fallback_blocks_build(stage2_media, tmp_path):
    data = stage2_manifest(stage2_media, tmp_path)
    data['clips'][0]['keyframe'] = str(tmp_path / 'missing.png')
    ep = fw.load_manifest(save_manifest(tmp_path / 'missing.json', data))
    tr = fw.trace_audit(ep)
    assert not tr['audit_passed'] and not tr['visual_continuity_resolved']
    data['clips'][0]['keyframe'] = str(stage2_media[3]['own'])
    data['fallback_to_source_on_visual_fail'] = False
    ep = fw.load_manifest(save_manifest(tmp_path / 'disabled.json', data))
    assert not fw.trace_audit(ep)['audit_passed']


@pytest.mark.parametrize('first,last', [(0, .1), (9.9, 10), (4, 4.1), (0, 10)])
def test_stage2_tight_minimum_and_edges(first, last):
    clip = fw.ClipSpec(1, 'clip_01', 'clip.mp4', 0, 10, [])
    plan = fw.plan_trim(clip, None, 10, fw.SPEECH_DEFAULTS)
    tight = fw.apply_tight_speech_trim(plan, first, last, fw.SPEECH_DEFAULTS)
    assert 0 <= tight['final'][0] <= first <= last <= tight['final'][1] <= 10
    assert tight['duration'] >= fw.TIGHT_MIN_DURATION
    plan['mode'] = 'locked'
    assert fw.apply_tight_speech_trim(plan, first, last, fw.SPEECH_DEFAULTS) == plan
    assert fw.apply_tight_speech_trim(plan, None, None, fw.SPEECH_DEFAULTS) == plan


def test_stage2_keyframe_preflight_collision_and_pacing_gaps(stage2_media, tmp_path):
    data = stage2_manifest(stage2_media, tmp_path)
    data['voices']['OTHER'] = {'name_fa': 'دیگر'}
    duplicate = {**data['clips'][0], 'id': 'clip_02', 'expected_speakers': ['OTHER'], 'subtitles': []}
    data['clips'].append(duplicate)
    ep = fw.load_manifest(save_manifest(tmp_path / 'collision.json', data))
    assert fw.step1_story_lock(ep)['collisions']
    assert fw.step2_keyframe_preflight(ep)['status'] == 'pass'
    speech = {'first_speech_sec': 0, 'last_speech_sec': 10, 'speech_segments': [[0, 1], [9, 10]]}
    tr = fw.clip_trace(ep, ep.clips[0], visual=None, speech=speech,
                       plan={'duration': 10, 'final': [0, 10]}, fallback=None)
    assert tr[fw.STEP_NAMES[3]]['dead_air_sec'] == 8
    assert tr[fw.STEP_NAMES[3]]['flags'] == ['DEAD_AIR_PACING']


def test_stage2_no_executable_forbidden_keyframe_sanitizer():
    import ast
    forbidden = 'sanitize_' + 'part3_keyframes'
    files = command(['git', '-C', ROOT, 'ls-files', '*.py']).stdout.decode().splitlines()
    for name in files:
        tree = ast.parse((ROOT / name).read_text('utf-8-sig'))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                assert node.name != forbidden, name
            if isinstance(node, ast.Call):
                assert getattr(node.func, 'id', getattr(node.func, 'attr', None)) != forbidden, name


def test_stage2_series_outputs_do_not_collide_and_terminal_spans_fit_evidence():
    episodes = [fw.load_manifest(ROOT / f'pipeline/manifests/fruits_of_power_part{p}.json')
                for p in range(1, 6)]
    assert len({ep.out_dir for ep in episodes}) == 5
    # Rounded last timestamps from original contact sheets; sampler used 16
    # midpoint samples. This is a conservative duration lower bound, NOT ffprobe.
    for p, last_label in [(2, 72.6), (3, 60.6), (4, 66.2), (5, 74.7)]:
        lower_bound = (last_label - .05) * 32 / 31
        assert all(c.source_span[1] < lower_bound for c in episodes[p-1].clips)


def test_stage2_source_band_inpaint_is_local_and_does_not_mutate_input(stage2_media):
    _, _, source, _, _ = stage2_media
    frame = rgb_frame(source, 2.5)
    before = frame.copy()
    out = fw.inpaint_source_subtitle_band(frame)
    np.testing.assert_array_equal(frame, before)
    mask = np.zeros(frame.shape[:2], dtype=bool)
    mask[int(320*.73):int(320*.89), int(180*.08):int(180*.92)] = True
    np.testing.assert_array_equal(frame[~mask], out[~mask])
    assert not np.array_equal(frame, out)


def test_stage2_audio_mismatch_does_not_replace_previous_render(stage2_media, tmp_path, monkeypatch):
    _, flow, source, _, video = stage2_media
    hashes = iter(['a'*64, 'b'*64])
    monkeypatch.setattr(fw, 'audio_stream_sha256', lambda _: next(hashes))
    out = tmp_path / 'previous.mp4'
    out.write_bytes(b'keep previous')
    with pytest.raises(fw.PipelineError, match='changed the native Flow audio'):
        fw.extract_source_fallback_clip(source, (2, 4), flow, out, video=video)
    assert out.read_bytes() == b'keep previous'
    assert not (tmp_path / 'previous.tmp.mp4').exists()


def test_stage2_narrative_keyframe_outputs_are_protected(stage2_media, tmp_path):
    data = stage2_manifest(stage2_media, tmp_path)
    data['clips'][0]['keyframe'] = str(Path(data['out_dir']) / 'clips_subbed/clip_01_subbed.mp4')
    with pytest.raises(fw.PipelineError, match='overwrite'):
        fw.load_manifest(save_manifest(tmp_path / 'overwrite.json', data))


def test_stage2_node_submitter_regressions():
    assert shutil.which('node'), 'Node is required for Flow submitter guard verification'
    proc = command(['node', '--test', ROOT / 'tests/js/submit_flow_batch.test.mjs'])
    assert b'fail 0' in proc.stdout


# Stage 2 continuation: exercise actual CLI failure paths, not just trace helpers.
@pytest.mark.parametrize('change', [
    {'keyframe': None}, {'expected_speakers': []}, {'story_beat': ''},
])
def test_stage2_incomplete_story_metadata_fails_trace_cli(stage2_media, tmp_path, change):
    data = stage2_manifest(stage2_media, tmp_path)
    data['clips'][0].update(change)
    path = save_manifest(tmp_path / 'metadata.json', data)
    out = tmp_path / 'trace.json'
    cli(path, 'trace-audit', '--no-live', '--out-json', out, expected=1)
    report = json.loads(out.read_text())
    assert report['audit_passed'] is False and report['all_passed'] is False
    assert fw.STEP_NAMES[0] in report['blocking_steps']
    assert set(report['clips'][0]['step_trace']) == set(fw.STEP_NAMES)


@pytest.mark.parametrize('missing_keyframe', [True, False])
def test_stage2_actual_build_cannot_sign_off_unresolved_visuals(stage2_media, tmp_path, missing_keyframe):
    data = stage2_manifest(stage2_media, tmp_path)
    if missing_keyframe:
        data['clips'][0]['keyframe'] = str(tmp_path / 'absent.png')
    else:
        data['fallback_to_source_on_visual_fail'] = False
    path = save_manifest(tmp_path / 'blocked.json', data)
    cli(path, 'build', '--no-cta', '--no-contact', expected=1)
    report = json.loads((Path(data['out_dir']) / 'qa_report.json').read_text())
    assert report['all_passed'] is False and report['publication_status'] == 'fail'
    assert report['gates']['automatic']['visual_continuity_resolved'] == 'fail'
    assert report['clips'][0]['fallback']['resolved'] is False
    if missing_keyframe:
        assert report['gates']['automatic']['keyframe_preflight'] == 'fail'


def test_stage2_matching_flow_picture_is_not_replaced(stage2_media, tmp_path):
    _, flow, _, kfs, _ = stage2_media
    data = stage2_manifest(stage2_media, tmp_path)
    data['clips'][0]['keyframe'] = str(kfs['other'])  # exact matching magenta frame
    data['source_video'] = str(tmp_path / 'unneeded-source.mp4')
    before = {p: fw.sha256_file(p) for p in [flow, *kfs.values()]}
    path = save_manifest(tmp_path / 'matching.json', data)
    cli(path, 'build', '--no-cta', '--no-contact')
    report = json.loads((Path(data['out_dir']) / 'qa_report.json').read_text())
    assert report['all_passed'] and report['visual_continuity_passed']
    assert report['clips'][0]['fallback']['resolution'] == 'flow_clip'
    assert report['publication_status'] == 'pending', 'automatic checks are not human approval'
    assert all(v == 'pending' for v in report['gates']['human_review'].values())
    assert not list(Path(data['out_dir']).rglob('*source_bridge.mp4'))
    assert before == {p: fw.sha256_file(p) for p in before}


def test_stage2_hybrid_corrupt_cache_is_rebuilt(stage2_media, tmp_path):
    data = stage2_manifest(stage2_media, tmp_path)
    path = save_manifest(tmp_path / 'cache.json', data)
    cli(path, 'build', '--no-cta', '--no-contact')
    qa = Path(data['out_dir']) / 'qa_report.json'
    report = json.loads(qa.read_text())
    bridge = Path(report['clips'][0]['provenance']['analysed'])
    bridge.write_bytes(b'corrupted cached video')
    cli(path, 'build', '--no-cta', '--no-contact')
    report = json.loads(qa.read_text())
    assert report['all_passed']
    extraction = report['clips'][0]['fallback']['extraction']
    assert extraction['verified']
    assert audio_stream_hash(bridge) == audio_stream_hash(stage2_media[1])
    assert fw.probe_media(bridge)['video']['duration'] == pytest.approx(10, abs=1/24)


@pytest.mark.parametrize('entry', [None, [], good_probe(num_sampled_frames=True),
                                  good_probe(l1_vs_keyframe_start=-1),
                                  good_probe(l1_vs_keyframe_end=256)])
def test_stage2_invalid_probe_shapes_and_ranges_fail_closed(entry):
    with pytest.raises(fw.PipelineError, match='probe'):
        fw.evaluate_probe_entry(entry)
