#!/usr/bin/env python3
"""
Builds Gemini 3.8 Flash TTS multi-speaker master video copies for Stories 7, 8, and 9:
- Preserves existing *_Flow_Native_Farsi.mp4 masters untouched.
- Muxes each clip's Gemini 3.8 Flash TTS WAV (Koda + Neno male voices) with the
  720x1280 24fps H.264 subtitle-burned video streams (-14 LUFS loudnorm, 48kHz stereo).
- Produces:
  1. Per-clip copies: 05_final_masters/story{7,8,9}/clips_subbed_gemini_tts/clip_0{1..6}_subbed.mp4
     and story{7,8,9}/flow_clips/clip_0{1..6}_gemini_tts_subbed.mp4
  2. Base copies (48s story-only): 05_final_masters/story{7,8,9}/Base_Story{7,8,9}_*_GeminiTTS_Farsi.mp4
  3. Master copies (58s story + CTA): 05_final_masters/story{7,8,9}/Master_Story{7,8,9}_*_GeminiTTS_Farsi.mp4
  4. Audit MP3s: 05_final_masters/story{7,8,9}/Master_Story{7,8,9}_*_GeminiTTS_Farsi_audit.mp3
"""

import json
import shutil
import subprocess
from pathlib import Path

S4_ROOT = Path(r"C:\Users\LifeCycle\.gemini\antigravity\scratch\series4-viral-6-stories-farsi")
MASTERS_ROOT = S4_ROOT / "05_final_masters"


def run_cmd(cmd: list[str]) -> None:
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"Command failed ({res.returncode}): {' '.join(cmd)}\n{res.stderr}")


def probe_duration(path: Path) -> float:
    res = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=True,
    )
    return float(res.stdout.strip())


def build_story(story_num: int) -> dict:
    story_key = f"story{story_num}"
    story_dir = S4_ROOT / story_key
    master_dir = MASTERS_ROOT / story_key
    qa_path = master_dir / "qa_report.json"

    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    episode_id = qa["episode_id"]
    base_flow_mp4 = Path(qa["deliverables"]["base_mp4"])
    base_flow_srt = Path(qa["deliverables"]["base_srt"])
    master_flow_mp4 = Path(qa["deliverables"]["master_mp4"])
    master_flow_srt = Path(qa["deliverables"]["master_srt"])

    work_dir = master_dir / "_work_gemini_tts"
    work_dir.mkdir(parents=True, exist_ok=True)

    clips_out_dir = master_dir / "clips_subbed_gemini_tts"
    clips_out_dir.mkdir(parents=True, exist_ok=True)

    norm_wavs: list[Path] = []
    clip_durations: list[float] = []

    print(f"\n=== Building {episode_id} ({story_key}) with Gemini 3.8 Flash TTS ===")

    for idx in range(1, 7):
        subbed_mp4 = master_dir / "clips_subbed" / f"clip_0{idx}_subbed.mp4"
        subbed_srt = master_dir / "clips_subbed" / f"clip_0{idx}_subbed.srt"
        raw_wav = story_dir / "gemini_tts" / f"clip_0{idx}.wav"
        if not raw_wav.exists():
            raise FileNotFoundError(f"Missing Gemini TTS WAV: {raw_wav}")

        vdur = probe_duration(subbed_mp4)
        clip_durations.append(vdur)
        fade_start = max(0.0, vdur - 0.06)

        trimmed_wav = work_dir / f"clip_0{idx}_trimmed.wav"
        run_cmd(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-i",
                str(raw_wav),
                "-af",
                "silenceremove=start_periods=1:start_silence=0.05:start_threshold=-40dB,"
                "areverse,silenceremove=start_periods=1:start_silence=0.10:start_threshold=-40dB,areverse",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                str(trimmed_wav),
            ]
        )
        speech_dur = probe_duration(trimmed_wav)
        target_max = vdur - 0.12
        tempo_filter = ""
        if speech_dur > target_max:
            tempo = min(1.35, max(1.01, speech_dur / (vdur - 0.15)))
            tempo_filter = f"atempo={tempo:.4f},"
            print(f"  [clip_0{idx}] speech_dur={speech_dur:.2f}s > {target_max:.2f}s -> applying {tempo_filter[:-1]}")

        norm_wav = work_dir / f"clip_0{idx}_gemini_norm.wav"
        af_chain = (
            f"{tempo_filter}"
            f"aresample=48000,"
            f"pan=stereo|c0=c0|c1=c0,"
            f"loudnorm=I=-14:TP=-1.5:LRA=11,"
            f"apad,"
            f"atrim=0:{vdur:.6f},"
            f"afade=t=out:st={fade_start:.6f}:d=0.06"
        )
        run_cmd(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-i",
                str(trimmed_wav),
                "-af",
                af_chain,
                "-ar",
                "48000",
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                str(norm_wav),
            ]
        )
        norm_wavs.append(norm_wav)

        out_clip_mp4 = clips_out_dir / f"clip_0{idx}_subbed.mp4"
        run_cmd(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-i",
                str(subbed_mp4),
                "-i",
                str(norm_wav),
                "-map",
                "0:v:0",
                "-map",
                "1:a:0",
                "-c:v",
                "copy",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                "-ar",
                "48000",
                "-ac",
                "2",
                "-movflags",
                "+faststart",
                str(out_clip_mp4),
            ]
        )
        if subbed_srt.exists():
            shutil.copy2(subbed_srt, clips_out_dir / f"clip_0{idx}_subbed.srt")

        mirror_clip_mp4 = story_dir / "flow_clips" / f"clip_0{idx}_gemini_tts_subbed.mp4"
        shutil.copy2(out_clip_mp4, mirror_clip_mp4)
        print(f"  [clip_0{idx}] muxed {out_clip_mp4.name} (dur={vdur:.3f}s)")

    # Concatenate the 6 normalized WAVs into base_gemini_audio.wav
    concat_base_txt = work_dir / "concat_base_wavs.txt"
    concat_base_txt.write_text(
        "\n".join(f"file '{w.as_posix()}'" for w in norm_wavs) + "\n",
        encoding="utf-8",
    )
    base_audio_wav = work_dir / "base_gemini_audio.wav"
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_base_txt),
            "-c:a",
            "pcm_s16le",
            str(base_audio_wav),
        ]
    )

    base_out_mp4 = master_dir / f"Base_{episode_id}_GeminiTTS_Farsi.mp4"
    base_out_srt = master_dir / f"Base_{episode_id}_GeminiTTS_Farsi.srt"
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-i",
            str(base_flow_mp4),
            "-i",
            str(base_audio_wav),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(base_out_mp4),
        ]
    )
    if base_flow_srt.exists():
        shutil.copy2(base_flow_srt, base_out_srt)

    # Extract CTA audio tail from Master_Flow_Native_Farsi.mp4 starting at base duration
    base_dur = probe_duration(base_flow_mp4)
    cta_tail_wav = work_dir / "cta_tail.wav"
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-ss",
            f"{base_dur:.6f}",
            "-i",
            str(master_flow_mp4),
            "-vn",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(cta_tail_wav),
        ]
    )

    concat_master_txt = work_dir / "concat_master_wavs.txt"
    concat_master_txt.write_text(
        f"file '{base_audio_wav.as_posix()}'\nfile '{cta_tail_wav.as_posix()}'\n",
        encoding="utf-8",
    )
    master_audio_wav = work_dir / "master_gemini_audio.wav"
    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_master_txt),
            "-c:a",
            "pcm_s16le",
            str(master_audio_wav),
        ]
    )

    master_out_mp4 = master_dir / f"Master_{episode_id}_GeminiTTS_Farsi.mp4"
    master_out_srt = master_dir / f"Master_{episode_id}_GeminiTTS_Farsi.srt"
    audit_out_mp3 = master_dir / f"Master_{episode_id}_GeminiTTS_Farsi_audit.mp3"

    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-i",
            str(master_flow_mp4),
            "-i",
            str(master_audio_wav),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(master_out_mp4),
        ]
    )
    if master_flow_srt.exists():
        shutil.copy2(master_flow_srt, master_out_srt)

    run_cmd(
        [
            "ffmpeg",
            "-y",
            "-hide_banner",
            "-i",
            str(master_out_mp4),
            "-vn",
            "-c:a",
            "libmp3lame",
            "-b:a",
            "128k",
            str(audit_out_mp3),
        ]
    )

    print(
        f"  [DONE] Base: {base_out_mp4.name} ({base_out_mp4.stat().st_size} bytes)\n"
        f"         Master: {master_out_mp4.name} ({master_out_mp4.stat().st_size} bytes)\n"
        f"         Audit MP3: {audit_out_mp3.name} ({audit_out_mp3.stat().st_size} bytes)"
    )
    return {
        "story": story_key,
        "episode_id": episode_id,
        "base_mp4": str(base_out_mp4),
        "master_mp4": str(master_out_mp4),
        "audit_mp3": str(audit_out_mp3),
    }


def main() -> None:
    results = []
    for s in (7, 8, 9):
        results.append(build_story(s))
    print("\nALL 3 GEMINI 3.8 FLASH TTS MASTER COPIES BUILT SUCCESSFULLY!")
    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
