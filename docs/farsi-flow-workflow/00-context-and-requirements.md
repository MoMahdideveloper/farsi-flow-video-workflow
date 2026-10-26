# Farsi Google Flow Viral Series Workflow — Requirements & Reference Scripts (Conversation 07b71ed0-ec66-4b90-bd00-c3a3a03eaf4b)

## 1. Mission Objective
Design, implement, and test a production-grade, standalone, config-driven Python CLI workflow script (`pipeline/farsi_flow_workflow.py`) and declarative episode manifest JSONs (`pipeline/manifests/series1_part1_whats_her_number.json` and `pipeline/manifests/ugly_chef_part2.json`) plus an automated pytest suite (`tests/test_farsi_flow_workflow.py`) that industrialize the Farsi AI Video Creation & Google Flow Native Farsi localization pipeline from conversation `07b71ed0-ec66-4b90-bd00-c3a3a03eaf4b`.

### Critical Bugs & Pain Points from Conversation `07b71ed0-ec66-4b90-bd00-c3a3a03eaf4b` That MUST Be Solved:
1. **Per-Clip Subtitled Outputs WITH Original Google Flow Audio (`clip_01_subbed.mp4` .. `clip_06_subbed.mp4`)**:
   - In `07b71ed0`, `cv2.VideoWriter` wrote `subbed_s1_p1.mp4` WITHOUT an audio stream, and individual clips (`clip_01.mp4`..`clip_06.mp4`) were only trimmed to `trim720_XX.mp4` without subtitles burned onto each individual clip.
   - When the user asked: *"C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\series1-whats-her-number-farsi\\03_flow_clips\\part1 all parts here their audio is orginal google flow give me those versions just make sure subtitle added"*, there was no per-clip subtitled+audio output!
   - Therefore, `pipeline/farsi_flow_workflow.py` MUST produce **BOTH**:
     a) **Per-clip subtitled MP4 files (`clip_01_subbed.mp4`, `clip_02_subbed.mp4`, ...)** inside the clips directory (and/or `<out_dir>/clips_subbed/`) where each individual clip has its **original Google Flow native Farsi audio (loudness-normalized to `-14 LUFS`, `48kHz` stereo AAC `192k`) muxed with the OpenCV/Pillow burned-in RTL Persian subtitles**!
     b) **Full Episode Concatenated Masters**:
        - `Base_<episode_id>_Flow_Native_Farsi.mp4` (immutable story-only master with top Episode Badge pill in `0.0..3.5s`, speaker-colored RTL subtitles, and original Google Flow native Farsi audio).
        - `Master_<episode_id>_Flow_Native_Farsi.mp4` (when `cta_video` exists, idempotently appends the Kelidbox CTA clip `cta_kelidbox_agnes_subbed.mp4` to `Base_...mp4`; if `--no-cta` is passed or `cta_video` is absent, copies `Base_...mp4` to `Master_...mp4`).
2. **Speech-Safe Audio Boundary Analyzer & Anti-Mid-Word-Cut Protection**:
   - Users reported: *"some words not completely spelled and ai do cut like in middle of it i want to ensure all voice video and ... be ok"*.
   - `pipeline/farsi_flow_workflow.py` MUST include an acoustic speech boundary analyzer (`analyze_clip_speech(mp4_path)`) that decodes 16kHz mono PCM via `ffmpeg`, computes short-time RMS energy (in dBFS at 20ms frames), detects `first_speech_sec` and `last_speech_sec`, and checks whether configured `trim_in` / `trim_out` would clip active speech energy!
   - Support `"speech_safe": "warn"` (preserves curated manifest trim windows while logging speech boundary diagnostics in `qa_report.json`) and `"speech_safe": "auto_expand"` (automatically widens `trim_in` / `trim_out` within `[0, source_duration]` so zero syllables are ever cut off mid-word).
   - Also support multi-segment splicing per clip (`"splice_segments": [[0.0, 5.22], [6.14, 8.60]]` with `acrossfade=d=0.02:c1=tri:c2=tri`, and automatic fallback to `raw_orig_file` if present, e.g. `clip_03_raw_orig.mp4` -> `clip_03.mp4` in Series 1 Part 1).
3. **Persian RTL Typography & Pill Renderer**:
   - Uses `arabic_reshaper.reshape` + `bidi.algorithm.get_display` + `Vazirmatn-Bold.ttf` (auto-resolving font path across Windows `C:\\Users\\LifeCycle\\.gemini\\antigravity\\scratch\\ugly-face-chef-farsi\\03_farsi_audio_tts\\Vazirmatn-Bold.ttf` and Linux DejaVuSans/system fonts during CI tests).
   - Auto-shrinks font size from `27pt` down to `16pt` so pill width `<= frame_width - 84`.
   - Draws rounded dark pill `(12, 14, 22, 210)` with gold border `(255, 215, 80, 220)`, drop shadow, and per-speaker RGB color.
   - Draws Episode Badge pill at `y_center=130` during `0.0 <= t <= 3.5s`.
4. **Complete Deliverables & Automated QA Certification (`qa_report.json`)**:
   - Writes UTF-8-BOM `.srt` (`Master_<episode_id>_Flow_Native_Farsi.srt` and per-clip `.srt`).
   - Writes `Master_<episode_id>_Flow_Native_Farsi_audit.mp3`.
   - Extracts a visual QA contact sheet (`qa_<episode_id>_contact.jpg`) showing frames sampled at the midpoint of every subtitle line + badge + CTA.
   - Writes `qa_report.json` verifying via `ffprobe` that EVERY generated MP4 (`clip_XX_subbed.mp4`, `Base_...mp4`, `Master_...mp4`) has BOTH `video` (`h264`, `720x1280`, `24fps`) and `audio` (`aac`, `48000Hz`, `stereo`) streams, zero A/V duration drift (`|v_dur - a_dur| < 0.15s`), all subtitles within clip bounds, and speech-safe trim handles.

## 2. Full Skill Specification (`farsi-viral-series-localization/SKILL.md`)
---
name: farsi-viral-series-localization
description: End-to-end production pipeline and quality-assurance protocol for localizing multi-part viral 3D/AI animation series (Instagram Reels, TikTok, Shorts) into native Persian (Farsi) via Studio Multi-Voice Dubbing and Google Flow (Veo) Native Farsi Generation. Enforces Character Sheet consistency, multi-episode narrative continuity, double-checking every keyframe image for anatomy/identity bugs, listening to every generated audio track to guarantee 100% word-for-word Persian RTL subtitle synchronization, and producing Instagram Publish Kits.
---

# Farsi Viral Series Localization & Multi-Part Production Mastery

Use this skill whenever localizing, dubbing, remastering, or generating multi-part viral short-form video series (e.g., `@straw.berryjammin` 3D animated stories like *The Ugly Face Chef / سرآشپز زشت*) into Persian (Farsi) for Instagram Reels, YouTube Shorts, or TikTok.

---

## 1. Core Principles (The 4 Mandatory QA Gates)

### Gate 1: Multi-Part Story Continuity & Character Sheet Bible
Never treat Part 2, Part 3, Part 4, or Part 5 as isolated videos or repeat Part 1's plot.
1. **Whole-Series Audit First**:
   - Before writing a single line of Farsi script, extract the audio (`partN_orig.mp3`) and visual contact sheets (`contact_partN.jpg`) for **all parts** of the series.
   - Listen to every part's audio and inspect every contact sheet using `read_file` to map the complete multi-episode story arc.
2. **Character Sheet & Continuity Lock**:
   - Inspect the Character Reference Sheets (`FLOW_SHEET_01..N.jpg`) using `read_file` before any generation or dubbing.
   - Lock a **Series Character Table** that remains 100% consistent across all episodes:
     - **Consistent Persian Name**: If the original English series changes a side character's name mid-series (e.g. calling the female bully `"Maya"` in Part 1 and `"Britney"` in Parts 4–5), normalize the name in Farsi (`مایا`) across **all parts** so viewers experience seamless continuity.
     - **Consistent Voice Profile & Subtitle Color**: Assign each character a fixed `edge-tts` voice, speaking rate, pitch offset, and RGB subtitle color across every episode:
       - `AGNES` (`آگنس`): `fa-IR-DilaraNeural`, `rate="+0%"`, `pitch="+10Hz"`, Color `(255, 230, 150)`
       - `MAYA` (`مایا`): `fa-IR-DilaraNeural`, `rate="+10%"`, `pitch="-6Hz"`, Color `(255, 195, 110)`
       - `TONY` (`تونی`): `fa-IR-FaridNeural`, `rate="+12%"`, `pitch="+12Hz"`, Color `(255, 140, 140)`
       - `HENRY` (`سرآشپز هنری`): `fa-IR-FaridNeural`, `rate="-4%"`, `pitch="-14Hz"`, Color `(165, 255, 175)`
       - `DOC` (`دکتر`): `fa-IR-FaridNeural`, `rate="-6%"`, `pitch="-8Hz"`, Color `(160, 235, 255)`
       - `HOST` (`مجری`): `fa-IR-FaridNeural`, `rate="+10%"`, `pitch="+6Hz"`, Color `(255, 215, 90)`
       - `CRITIC` (`منتقد غذا`): `fa-IR-FaridNeural`, `rate="-5%"`, `pitch="-18Hz"`, Color `(200, 220, 255)`
     - **Character Visual State Progression**: Track each character's visual evolution across episodes (e.g., Part 1–2 scarred Agnes -> Part 3 black-masked Master Kitchen Agnes -> Part 4–5 transformed glamorous restaurant-owner Agnes). Record the state at each shot's entry and exit: mask, wardrobe, injuries, props, location, and speaker. A reveal must not occur before its dialogue; a request to remove a mask must begin with the mask present. Track story facts such as names, prize amounts, and surgery costs separately from visual state.

---

### Gate 2: Double-Check Every Keyframe & Reference Image (`read_file` Visual QA)
Never feed an uninspected keyframe into Google Flow or FFmpeg assembly, and **NEVER mix raw source-video frames with Character Sheet keyframes**.
1. **Mandatory Character & Location Sheet Reference Locking**:
   - Every keyframe for Google Flow (`Option 1 + Option B`) **MUST** be generated by passing the exact Character Sheets (`FLOW_SHEET_01_AGNES.jpg`, `FLOW_SHEET_02_TONY.jpg`, `FLOW_SHEET_03_MAYA.jpg`, `FLOW_SHEET_04_HENRY.jpg`) and Location Sheets (`FLOW_LOC_01_PREP_KITCHEN.jpg`, `FLOW_LOC_02_BREAK_TABLE.jpg`, `FLOW_LOC_03_PANTRY_AISLE.jpg`) in `ReferenceImagePaths`.
   - Never add hats or props that distort a character's silhouette from their Character Sheet (e.g., Agnes must always keep her wide round orange-yellow pear head, single green leaf on top of her head, huge round brown doe eyes, white neck-bow, and stained pale-pink apron from `FLOW_SHEET_01_AGNES.jpg`).
2. **Visual Inspection against Character Sheets**:
   - View every generated keyframe (`KF_01..06.jpg`) alongside the character sheets (`FLOW_SHEET_*.jpg`) using `read_file`.
3. **Zero-Defect Checklist**:
   - **Character Identity Drift**: If any character's face shape, eye size, skin texture, leaf/stem, or wardrobe deviates from `FLOW_SHEET_01..04.jpg`, reject and regenerate immediately with explicit `ReferenceImagePaths`.
   - **Anatomy & Physics**: Reject and regenerate any keyframe with extra hands, disembodied floating limbs, merged chef coats/aprons, or distorted props.
   - **Zero Text / Trademarks**: Ensure zero text, subtitles, third-party movie posters (e.g., Shrek), or TV show logos (e.g., MasterChef spiral `m`) appear in any keyframe sent to Google Flow.

---

### Gate 3: Double-Check Audio & 100% Word-for-Word Subtitle Sync (`read_file` Audio QA)
Subtitles must **never** contain lines that are not spoken in the audio, nor miss words that are spoken.

#### Workflow A: Full-Length Studio Farsi Dub (`Option 2 + Option A`)
1. **Generate Subtitle Timing Strip Sheets (`sub_strips_partN.jpg`)**:
   - Sample the source video's subtitle band (`y=64%..78%`) every `1.2s`, stamp the exact timestamp (`0.6s`, `1.8s`, `3.0s`, ...) on each strip, and stack into a 2-column grid.
   - View `sub_strips_partN.jpg` AND listen to `partN_orig.mp3` via `read_file` to obtain exact start/end timestamps (`st`, `et`) for every spoken line.
2. **Silence-Trimmed & Slot-Fitted TTS**:
   - Trim leading/trailing silence from each `edge-tts` line with `silenceremove` (`-42dB`) and dynamically fit `atempo` (`1.02..1.48`) only when `dur > (et - st)` so Farsi speech starts and ends on the exact lip-movement window.
3. **Stereo Side-Channel BGM Bed + Loudness Normalization**:
   - Suppress original English center vocals during active speech windows while preserving stereo music and sound effects:
     ```text
     pan=stereo|c0=0.55*c0-0.35*c1|c1=0.55*c1-0.35*c0,volume='if(gt(ACTIVE_SPEECH_EXPR,0),0.20,0.72)':eval=frame
     ```
   - Mix the stereo BGM bed with the Farsi dialogue stem in NumPy (`48kHz` float32) and normalize the final mix to `-14 LUFS` (`loudnorm=I=-14:TP=-1.5:LRA=11`).

#### Workflow B: Google Flow (Veo) Native Farsi Video Generation (`Option 1 + Option B`)
Preserve native Flow voices when that workflow is selected. Do not silently replace them with TTS to repair an edit. Check recurring characters for voice identity and delivery consistency, not just correct words.

1. **Automate Google Flow via `profile-bridge`**:
   - Copy the verified clean 9:16 keyframe to the Windows Clipboard using `copy_clip.ps1` (`System.Windows.Forms.Clipboard::SetImage`).
   - Claim the Google Flow tab (`browser_claim_tab`), focus the prompt composer, paste (`Ctrl+V`), wait for upload, type the scene prompt with native Farsi dialogue, click `Start generation`, and download the generated 10s 9:16 clip.
   - Choose the actual supported duration shown for the selected model; probe the downloaded media instead of assuming every clip is 10 seconds. Budget dialogue plus pauses and speech handles before generation. If it will not fit naturally, shorten or split at a complete sentence. For a failed source, use a bounded retry (default two revised attempts per scene within existing authorization), then report the unresolved scene rather than retrying indefinitely.
2. **Fixed Source Provenance**:
   - Record episode/shot ID, exact source path and SHA-256, generation prompt and model, source keyframe/reference hashes, and available Flow project/asset ID. Check download completion and decoding before accepting the asset.
   - Do not pick the newest wildcard match from Downloads. Resolve and verify the exact generated asset, especially when agents share a browser, clipboard, or Downloads directory. Serialize shared clipboard/browser mutations; parallelize local independent work.
   - Keep raw accepted sources immutable. A replacement gets a new identity; invalidate its transcript, trim, subtitle, and downstream QA records.
3. **Post-Generation Audio Verification**:
   - AI video models (Veo / Google Flow) frequently shorten, paraphrase, or omit part of a long dialogue prompt.
   - **Never copy the input prompt directly into the subtitle burner!**
   - Extract and listen to every source clip's audio with an audio-capable tool. Use lossless PCM for timing measurement; compressed listening proxies are optional. `silencedetect`, RMS, VAD, and ASR can locate candidates, but none alone proves that a word or sentence finished. Music, breaths, quiet consonants, and chopping sounds defeat simple amplitude thresholds.
   - Record the actual spoken text, speaker, first and last audible speech times, and whether each sentence finishes naturally. Include hesitations and trailing words when deciding cut points. Listen through both source edges. If the source itself starts or ends mid-word, mark it failed for repair/regeneration; silence or a held frame cannot recover missing speech.
   - Burn only verified actual words. Keep source timestamps and trimmed-local timestamps explicitly separate: `local_time = source_time - trim_in`. Do not guess unseen or unheard text. If audio understanding is unavailable, mark listening/transcription pending and do not claim full audio QA.
4. **Speech-Safe Trimming and Assembly**:
   - Default to retaining the complete source. Trim only verified unwanted material outside speech; never apply a generic one-second settle trim to native dialogue.
   - As starting values, preserve 0.20–0.40 seconds before the first word and 0.35–0.60 seconds after the final word, bounded by actual source duration. Choose longer handles when breaths, reverberation, or dramatic delivery require them. Any unavailable handle or exception needs an explicit review note; padding is not evidence that a sentence is complete.
   - Validate `0 <= trim_in < trim_out <= measured_source_duration`, every subtitle lies within the retained interval, and every verified speech span remains inside it. Cut around complete utterances. Never shorten speech to a subtitle endpoint or an RMS threshold crossing.
   - Use one explicit timeline for video, audio, and subtitles. Probe streams and verify frame/sample rounding, duration, start offsets, and decoded output. Do not use `-shortest` to conceal a duration mismatch.
   - Listen to each rendered trimmed clip, then every join in the final encoded master. Ensure no syllable, breath, or final consonant is removed and no unnatural silence, duplicate audio, click, loudness jump, or A/V drift was introduced. Apply fades only outside speech; crossfades must not overlap unrelated dialogue.
5. **Idempotent Finishing**:
   - Build any CTA version from an explicitly recorded immutable story-only master plus one exact CTA asset. Never append to a file that might already contain the CTA, and never infer a clean base by blindly removing a fixed number of seconds.
   - Use a temporary output, verify exactly one CTA and expected duration, then promote the verified file. Preserve previous outputs until the replacement passes. Re-running the same inputs must not append another CTA or progressively re-encode the last output.

---

### Gate 4: Persian RTL Typography & Instagram Publish Kit Verification
1. **RTL Shaping on Windows (`PIL` without `libraqm`)**:
   - Always shape Persian text before passing to Pillow:
     ```python
     import arabic_reshaper
     from bidi.algorithm import get_display

     def shape_fa(text: str) -> str:
         return get_display(arabic_reshaper.reshape(text))
     ```
   - Use `Vazirmatn-Bold.ttf` and auto-fit font size (`25pt` down to `16pt`) so the pill box (`max_lw <= w - 52`) never overflows the 9:16 frame width.
2. **Final Visual & Audio QA Before Delivery**:
   - Extract verification frames from active dialogue timestamps in the final `.mp4` and inspect them with `read_file` to confirm clean inpainting, centered RTL Persian text, and proper speaker colors.
   - Inspect shot starts, middles, ends, and every transition against the character/state ledger. Sparse stills do not establish frame-by-frame review or lip-sync quality.
   - Listen to the complete final encoded master with its video and subtitles, including any CTA. Verify sentence completion, speaker attribution, subtitle text/timing, voice continuity, scene continuity, and intelligibility. A source-audio listen before editing does not certify the final master.
   - Save a QA record tied to exact source/output hashes: probe results, measured speech spans, transcript, cut decisions, subtitle validation, visual review, final listening, and unresolved issues. Distinguish automatic checks from human/audio-capable review. Use `pass`, `fail`, or `pending`; never present missing review as passed. Revalidate affected stages after any source, trim, subtitle, or CTA change.
   - Provide a complete **Instagram Publish Kit** for each episode:
     - Final Master `.mp4` (with burned-in RTL subtitles) + Clean `.srt` file
     - 9:16 Instagram Reel Cover (`Cover_PartN_Ugly_Chef_Farsi.jpg`) with episode badge and hook title
     - Episode-connected Persian caption, viral hashtags, and engagement pinned comment linking to the next part.


## 3. Reference Script 1: `assemble_series1_part1_flow_master.py` (Series 1 Part 1 — What's Her Number?)
```python
import os, shutil, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

BASE = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\series1-whats-her-number-farsi"
CLIPS_DIR = os.path.join(BASE, "03_flow_clips", "part1")
OUT_DIR = os.path.join(BASE, "05_final_masters")
FONT_PATH = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\ugly-face-chef-farsi\03_farsi_audio_tts\Vazirmatn-Bold.ttf"
CTA_SUBBED = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\ugly-face-chef-farsi\05_final_masters\cta_kelidbox_agnes_subbed.mp4"

VOICES = {
    "MOM":   {"color": (215, 165, 255)},
    "DOC":   {"color": (165, 255, 185)},
    "CHLOE": {"color": (255, 165, 210)},
    "LIAM":  {"color": (255, 220, 110)},
    "ELLA":  {"color": (130, 255, 220)},
    "RUBY":  {"color": (255, 205, 150)},
}

CLIPS = [
    ("clip_01.mp4", 0.00, 9.40, [
        (0.10, 4.90, "MOM",   "دکتر، این یکی ده از دهه! پس چرا عدد خواهرش معلوم نیست؟"),
        (5.10, 9.20, "DOC",   "موهاش روشو پوشونده، تا هجده سالگی نباید کنار بره."),
    ]),
    ("clip_02.mp4", 0.50, 8.90, [
        (0.70, 3.80, "CHLOE", "تو مدرسه به هیچ‌کس نگو ما خواهریم!"),
        (4.20, 7.90, "CHLOE", "همه منو به عنوان ده از ده می‌شناسند!"),
    ]),
    ("clip_03.mp4", 0.50, 7.50, [
        (0.60, 3.00, "LIAM",  "سلام! تو دختر جدیده‌ای، درسته؟"),
        (3.85, 6.10, "LIAM",  "افتخار میدی ناهار رو با هم بشینیم؟"),
        (6.30, 6.95, "ELLA",  "اوهوم..."),
    ]),
    ("clip_04.mp4", 0.60, 9.40, [
        (0.30, 4.40, "RUBY",  "الان رسماً همه دارن درباره اون دختر جدیده حرف می‌زنن!"),
        (4.80, 7.60, "RUBY",  "فکر کنم لیام عاشقش شده!"),
    ]),
    ("clip_05.mp4", 1.10, 9.80, [
        (0.30, 2.10, "ELLA",  "اگه کلویی راست بگه چی؟"),
        (3.10, 4.10, "ELLA",  "صبر کن..."),
        (4.25, 8.50, "ELLA",  "فردا هجده سالم می‌شه و بالاخره می‌تونم عدد روی پیشونیم رو ببینم؟"),
    ]),
    ("clip_06.mp4", 0.40, 8.40, [
        (0.30, 1.90, "ELLA",  "سلام هجده سالگی!"),
        (2.10, 4.70, "ELLA",  "تمام عمرم منتظر این لحظه بودم"),
        (4.95, 7.75, "ELLA",  "تا بالاخره عدد روی پیشونیم رو ببینم..."),
    ]),
]

def shape_fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))

def fmt_srt(sec: float) -> str:
    ms = int(round((sec - int(sec)) * 1000))
    s = int(sec) % 60
    m = (int(sec) // 60) % 60
    h = int(sec) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def draw_rtl_pill(frame_bgr: np.ndarray, text_fa: str, y_center: int = 1040, font_size: int = 26, text_color=(255, 255, 255, 255)) -> np.ndarray:
    h, w, _ = frame_bgr.shape
    pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    shaped = shape_fa(text_fa)
    cur_size = font_size
    while cur_size >= 16:
        font = ImageFont.truetype(FONT_PATH, cur_size)
        bbox = draw.textbbox((0, 0), shaped, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw <= w - 84:
            break
        cur_size -= 2

    pad_x, pad_y = 22, 12
    rx0 = max(16, (w - tw) // 2 - pad_x)
    ry0 = y_center - th // 2 - pad_y
    rx1 = min(w - 16, (w + tw) // 2 + pad_x)
    ry1 = y_center + th // 2 + pad_y

    draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=16, fill=(12, 14, 22, 210), outline=(255, 215, 80, 220), width=2)
    tx = (w - tw) // 2 - bbox[0]
    ty = y_center - th // 2 - bbox[1]
    draw.text((tx + 2, ty + 2), shaped, font=font, fill=(0, 0, 0, 230))
    draw.text((tx, ty), shaped, font=font, fill=text_color)

    combined = Image.alpha_composite(pil_img, overlay).convert("RGB")
    return cv2.cvtColor(np.array(combined), cv2.COLOR_RGB2BGR)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    # 1. Re-splice clip_03 at [0..5.22] + [6.14..8.60] so 'افتخار میدی' is 100% complete
    c3 = os.path.join(CLIPS_DIR, "clip_03.mp4")
    c3_orig = os.path.join(CLIPS_DIR, "clip_03_raw_orig.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", c3_orig,
        "-filter_complex",
        "[0:v]trim=0:5.22,setpts=PTS-STARTPTS[v0];"
        "[0:v]trim=6.14:8.60,setpts=PTS-STARTPTS[v1];"
        "[v0][v1]concat=n=2:v=1:a=0[v];"
        "[0:a]atrim=0:5.22,asetpts=PTS-STARTPTS[a0];"
        "[0:a]atrim=6.14:8.60,asetpts=PTS-STARTPTS[a1];"
        "[a0][a1]acrossfade=d=0.02:c1=tri:c2=tri[a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
        c3, "-loglevel", "error"
    ], check=True)

    trimmed_paths = []
    global_subs = []
    t_offset = 0.0

    for idx, (fn, t_start, t_end, subs) in enumerate(CLIPS, 1):
        src = os.path.join(CLIPS_DIR, fn)
        dur = t_end - t_start
        tr_vid = os.path.join(CLIPS_DIR, f"trim720_{idx:02d}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", src,
            "-ss", f"{t_start:.2f}", "-t", f"{dur:.2f}",
            "-vf", "scale=720:1280:flags=lanczos,fps=24",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            tr_vid, "-loglevel", "error"
        ], check=True)
        trimmed_paths.append(tr_vid)
        for s0, s1, spk, txt in subs:
            global_subs.append((t_offset + s0, t_offset + s1, spk, txt))
        t_offset += dur

    concat_list = os.path.join(CLIPS_DIR, "concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in trimmed_paths:
            f.write(f"file '{p}'\n")

    raw_concat = os.path.join(CLIPS_DIR, "raw_concat_s1_p1.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", raw_concat, "-loglevel", "error"
    ], check=True)

    cap = cv2.VideoCapture(raw_concat)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp_sub_vid = os.path.join(CLIPS_DIR, "subbed_s1_p1.mp4")
    writer = cv2.VideoWriter(tmp_sub_vid, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    f_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        t = f_idx / fps
        if t <= 3.5:
            frame = draw_rtl_pill(frame, "قسمت اول: عدد سرنوشت", y_center=130, font_size=28, text_color=(255, 225, 110, 255))
        for s0, s1, spk, txt in global_subs:
            if s0 <= t <= s1:
                c_rgb = VOICES[spk]["color"]
                frame = draw_rtl_pill(frame, txt, y_center=int(h * 0.84), font_size=27, text_color=(*c_rgb, 255))
                break
        writer.write(frame)
        f_idx += 1
    cap.release()
    writer.release()

    base_mp4 = os.path.join(OUT_DIR, "Base_Series1_Part1_Flow_Native_Farsi.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", tmp_sub_vid, "-i", raw_concat,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        base_mp4, "-loglevel", "error"
    ], check=True)

    final_mp4 = os.path.join(OUT_DIR, "Master_Series1_Part1_Flow_Native_Farsi.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", base_mp4,
        "-i", CTA_SUBBED,
        "-filter_complex", "[0:v]fps=24,format=yuv420p[v0];[1:v]fps=24,format=yuv420p[v1];[0:a]aresample=48000[a0];[1:a]aresample=48000[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
        "-map", "[v]", "-map", "[a]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        final_mp4, "-loglevel", "error"
    ], check=True)

    cta_subs = [
        (t_offset + 0.10, t_offset + 3.60, "ELLA", "برای دیدن قسمت بعدی همین الان پیج رو فالو کن!"),
        (t_offset + 3.80, t_offset + 7.85, "ELLA", "راستی کل این انیمیشن با اکانت‌های هوش مصنوعی سایت کلیدباکس ساخته شده!"),
    ]
    all_subs = global_subs + cta_subs
    final_srt = os.path.join(OUT_DIR, "Master_Series1_Part1_Flow_Native_Farsi.srt")
    with open(final_srt, "w", encoding="utf-8-sig") as f:
        for i, (s0, s1, spk, txt) in enumerate(all_subs, 1):
            f.write(f"{i}\n{fmt_srt(s0)} --> {fmt_srt(s1)}\n{txt}\n\n")

    audit_mp3 = os.path.join(OUT_DIR, "Master_Series1_Part1_Flow_Native_Farsi_audit.mp3")
    subprocess.run([
        "ffmpeg", "-y", "-i", final_mp4, "-vn", "-af", "aresample=async=1",
        "-c:a", "libmp3lame", "-b:a", "128k", audit_mp3, "-loglevel", "error"
    ], check=True)
    print(f"Rendered {final_mp4} ({os.path.getsize(final_mp4)/1024/1024:.2f} MB)")

if __name__ == "__main__":
    main()

```

## 4. Reference Script 2: `06_assemble_part2_flow_master.py` (Ugly Chef Part 2)
```python
import os, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

BASE = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\ugly-face-chef-farsi"
CLIPS_DIR = os.path.join(BASE, "part2", "flow_clips")
OUT_DIR = os.path.join(BASE, "05_final_masters")
FONT_PATH = os.path.join(BASE, "03_farsi_audio_tts", "Vazirmatn-Bold.ttf")

VOICES = {
    "AGNES": {"color": (255, 230, 150)},
    "MAYA":  {"color": (255, 195, 110)},
    "TONY":  {"color": (255, 140, 140)},
    "HENRY": {"color": (165, 255, 175)},
    "DOC":   {"color": (160, 235, 255)},
    "HOST":  {"color": (255, 215, 90)},
}

CLIPS = [
    ("clip_01.mp4", 0.00, 8.30, [
        (0.15, 4.05, "DOC",   "این عمل ریسک بالایی داره و هزینه‌ش هفت هزار دلاره."),
        (4.70, 8.10, "AGNES", "هفت هزار دلار؟! من فقط یه کمک‌آشپزم!"),
    ]),
    ("clip_02.mp4", 1.50, 6.50, [
        (0.40, 3.80, "AGNES", "کاش منم خوشگل بودم..."),
    ]),
    ("clip_03.mp4", 1.50, 8.21, [
        (0.30, 3.10, "AGNES", "مسابقه بزرگ آشپزی؟!"),
        (3.20, 6.55, "AGNES", "جایزه‌ش دقیقاً همون پولیه که واسه عمل صورتم لازم دارم!"),
    ]),
    ("clip_04.mp4", 0.80, 7.50, [
        (0.20, 3.60, "AGNES", "سرآشپز هنری، می‌شه این جمعه رو مرخصی بگیرم؟"),
        (4.10, 6.40, "HENRY", "البته آگنس، مشکلی نیست!"),
    ]),
    ("clip_05.mp4", 1.20, 9.80, [
        (0.30, 4.25, "TONY",  "مرخصی واسه چی؟ می‌خوای بری مسابقه ملکه زیبایی شرکت کنی؟!"),
        (4.65, 8.45, "MAYA",  "آره، جایزه ترسناک‌ترین صورت سال رو می‌بره!"),
    ]),
    ("clip_06.mp4", 1.20, 7.60, [
        (0.30, 6.00, "AGNES", "صبر کنید و ببینید... من برنده این مسابقه می‌شم و به همه‌تون نشون می‌دم!"),
    ]),
]

def shape_fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))

def fmt_srt(sec: float) -> str:
    ms = int(round((sec - int(sec)) * 1000))
    s = int(sec) % 60
    m = (int(sec) // 60) % 60
    h = int(sec) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def draw_rtl_pill(frame_bgr: np.ndarray, text_fa: str, y_center: int = 1040, font_size: int = 26, text_color=(255, 255, 255, 255)) -> np.ndarray:
    h, w, _ = frame_bgr.shape
    pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    shaped = shape_fa(text_fa)
    cur_size = font_size
    while cur_size >= 16:
        font = ImageFont.truetype(FONT_PATH, cur_size)
        bbox = draw.textbbox((0, 0), shaped, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw <= w - 84:
            break
        cur_size -= 2

    pad_x, pad_y = 22, 12
    rx0 = max(16, (w - tw) // 2 - pad_x)
    ry0 = y_center - th // 2 - pad_y
    rx1 = min(w - 16, (w + tw) // 2 + pad_x)
    ry1 = y_center + th // 2 + pad_y

    draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=16, fill=(12, 14, 22, 210), outline=(255, 215, 80, 220), width=2)
    tx = (w - tw) // 2 - bbox[0]
    ty = y_center - th // 2 - bbox[1]
    draw.text((tx + 2, ty + 2), shaped, font=font, fill=(0, 0, 0, 230))
    draw.text((tx, ty), shaped, font=font, fill=text_color)

    combined = Image.alpha_composite(pil_img, overlay).convert("RGB")
    return cv2.cvtColor(np.array(combined), cv2.COLOR_RGB2BGR)

def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    trimmed_paths = []
    global_subs = []
    t_offset = 0.0

    for idx, (fn, t_start, t_end, subs) in enumerate(CLIPS, 1):
        src = os.path.join(CLIPS_DIR, fn)
        dur = t_end - t_start
        tr_vid = os.path.join(CLIPS_DIR, f"trim720_{idx:02d}.mp4")
        subprocess.run([
            "ffmpeg", "-y", "-i", src,
            "-ss", f"{t_start:.2f}", "-t", f"{dur:.2f}",
            "-vf", "scale=720:1280:flags=lanczos,fps=24",
            "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            tr_vid, "-loglevel", "error"
        ], check=True)
        trimmed_paths.append(tr_vid)
        for s0, s1, spk, txt in subs:
            global_subs.append((t_offset + s0, t_offset + s1, spk, txt))
        t_offset += dur

    concat_list = os.path.join(CLIPS_DIR, "concat_list.txt")
    with open(concat_list, "w", encoding="utf-8") as f:
        for p in trimmed_paths:
            f.write(f"file '{p}'\n")

    raw_concat = os.path.join(CLIPS_DIR, "raw_concat_part2_720.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", raw_concat, "-loglevel", "error"
    ], check=True)

    cap = cv2.VideoCapture(raw_concat)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp_sub_vid = os.path.join(CLIPS_DIR, "subbed_video_part2_720.mp4")
    writer = cv2.VideoWriter(tmp_sub_vid, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    f_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        t = f_idx / fps
        if t <= 3.5:
            frame = draw_rtl_pill(frame, "قسمت دوم: سرآشپز زشت", y_center=130, font_size=28, text_color=(255, 225, 110, 255))
        for s0, s1, spk, txt in global_subs:
            if s0 <= t <= s1:
                c_rgb = VOICES[spk]["color"]
                frame = draw_rtl_pill(frame, txt, y_center=int(h * 0.84), font_size=27, text_color=(*c_rgb, 255))
                break
        writer.write(frame)
        f_idx += 1
    cap.release()
    writer.release()

    final_mp4 = os.path.join(OUT_DIR, "Master_Part2_Flow_Native_Farsi.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", tmp_sub_vid, "-i", raw_concat,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy", "-movflags", "+faststart",
        final_mp4, "-loglevel", "error"
    ], check=True)

    final_srt = os.path.join(OUT_DIR, "Master_Part2_Flow_Native_Farsi.srt")
    with open(final_srt, "w", encoding="utf-8-sig") as f:
        for i, (s0, s1, spk, txt) in enumerate(global_subs, 1):
            f.write(f"{i}\n{fmt_srt(s0)} --> {fmt_srt(s1)}\n{txt}\n\n")

    print(f"Rendered {final_mp4} ({os.path.getsize(final_mp4)/1024/1024:.2f} MB, {t_offset:.2f}s)")

if __name__ == "__main__":
    main()

```

## 5. Reference Script 3: `10_append_kelidbox_flow_cta.py`
```python
import os, subprocess
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

BASE = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\ugly-face-chef-farsi"
OUT_DIR = os.path.join(BASE, "05_final_masters")
FONT_PATH = os.path.join(BASE, "03_farsi_audio_tts", "Vazirmatn-Bold.ttf")

def shape_fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))

def fmt_srt(sec: float) -> str:
    ms = int(round((sec - int(sec)) * 1000))
    s = int(sec) % 60
    m = (int(sec) // 60) % 60
    h = int(sec) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def draw_rtl_pill(frame_bgr: np.ndarray, text_fa: str, y_center: int = 1040, font_size: int = 26, text_color=(255, 230, 150, 255)) -> np.ndarray:
    h, w, _ = frame_bgr.shape
    pil_img = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)).convert("RGBA")
    overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    shaped = shape_fa(text_fa)
    cur_size = font_size
    while cur_size >= 16:
        font = ImageFont.truetype(FONT_PATH, cur_size)
        bbox = draw.textbbox((0, 0), shaped, font=font)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        if tw <= w - 84:
            break
        cur_size -= 2

    pad_x, pad_y = 22, 12
    rx0 = max(16, (w - tw) // 2 - pad_x)
    ry0 = y_center - th // 2 - pad_y
    rx1 = min(w - 16, (w + tw) // 2 + pad_x)
    ry1 = y_center + th // 2 + pad_y

    draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=16, fill=(12, 14, 22, 210), outline=(255, 215, 80, 220), width=2)
    tx = (w - tw) // 2 - bbox[0]
    ty = y_center - th // 2 - bbox[1]
    draw.text((tx + 2, ty + 2), shaped, font=font, fill=(0, 0, 0, 230))
    draw.text((tx, ty), shaped, font=font, fill=text_color)

    combined = Image.alpha_composite(pil_img, overlay).convert("RGB")
    return cv2.cvtColor(np.array(combined), cv2.COLOR_RGB2BGR)

def build_subbed_cta(src_mp4: str, out_mp4: str, subs: list):
    norm_mp4 = src_mp4.replace(".mp4", "_norm720.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", src_mp4,
        "-vf", "scale=720:1280:flags=lanczos,fps=24",
        "-af", "loudnorm=I=-14:TP=-1.5:LRA=11",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        norm_mp4, "-loglevel", "error"
    ], check=True)

    cap = cv2.VideoCapture(norm_mp4)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    tmp_vid = src_mp4.replace(".mp4", "_tmp_vid.mp4")
    writer = cv2.VideoWriter(tmp_vid, cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    f_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        t = f_idx / fps
        for s0, s1, txt in subs:
            if s0 <= t <= s1:
                frame = draw_rtl_pill(frame, txt, y_center=int(h * 0.84), font_size=27, text_color=(255, 230, 150, 255))
                break
        writer.write(frame)
        f_idx += 1
    cap.release()
    writer.release()

    subprocess.run([
        "ffmpeg", "-y", "-i", tmp_vid, "-i", norm_mp4,
        "-map", "0:v:0", "-map", "1:a:0",
        "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        out_mp4, "-loglevel", "error"
    ], check=True)

def get_duration(mp4_path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", mp4_path
    ]).decode().strip()
    return float(out)

def main():
    cta_a_src = os.path.join(OUT_DIR, "cta_kelidbox_agnes.mp4")
    cta_b_src = os.path.join(OUT_DIR, "cta_kelidbox_finale.mp4")
    cta_a_sub = os.path.join(OUT_DIR, "cta_kelidbox_agnes_subbed.mp4")
    cta_b_sub = os.path.join(OUT_DIR, "cta_kelidbox_finale_subbed.mp4")

    subs_a = [
        (0.10, 3.60, "برای دیدن قسمت بعدی همین الان پیج رو فالو کن!"),
        (3.80, 7.85, "راستی کل این انیمیشن با اکانت‌های هوش مصنوعی سایت کلیدباکس ساخته شده!"),
    ]
    subs_b = [
        (0.15, 3.60, "برای دیدن قسمت بعدی همین الان پیج رو فالو کن!"),
        (3.85, 7.85, "راستی کل این انیمیشن با اکانت‌های هوش مصنوعی سایت کلیدباکس ساخته شده!"),
    ]

    build_subbed_cta(cta_a_src, cta_a_sub, subs_a)
    build_subbed_cta(cta_b_src, cta_b_sub, subs_b)

    for part_num in [2, 3, 4, 5]:
        master_mp4 = os.path.join(OUT_DIR, f"Master_Part{part_num}_Flow_Native_Farsi.mp4")
        base_backup = os.path.join(OUT_DIR, f"Base_NoCTA_Part{part_num}_Flow_Native_Farsi.mp4")
        if not os.path.exists(base_backup):
            os.replace(master_mp4, base_backup)

        base_dur = get_duration(base_backup)
        cta_to_use = cta_a_sub if part_num in [2, 3, 4] else cta_b_sub
        subs_to_use = subs_a if part_num in [2, 3, 4] else subs_b

        subprocess.run([
            "ffmpeg", "-y",
            "-i", base_backup,
            "-i", cta_to_use,
            "-filter_complex", "[0:v]fps=24,format=yuv420p[v0];[1:v]fps=24,format=yuv420p[v1];[0:a]aresample=48000[a0];[1:a]aresample=48000[a1];[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]",
            "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
            "-movflags", "+faststart",
            master_mp4, "-loglevel", "error"
        ], check=True)

        srt_path = os.path.join(OUT_DIR, f"Master_Part{part_num}_Flow_Native_Farsi.srt")
        if os.path.exists(srt_path):
            with open(srt_path, "r", encoding="utf-8-sig") as f:
                content = f.read().strip()
            if "کلیدباکس" not in content:
                blocks = [b for b in content.split("\n\n") if b.strip()]
                next_idx = len(blocks) + 1
                for s0, s1, txt in subs_to_use:
                    blocks.append(f"{next_idx}\n{fmt_srt(base_dur + s0)} --> {fmt_srt(base_dur + s1)}\n{txt}")
                    next_idx += 1
                with open(srt_path, "w", encoding="utf-8-sig") as f:
                    f.write("\n\n".join(blocks) + "\n\n")

        new_dur = get_duration(master_mp4)
        print(f"Updated Part {part_num}: {master_mp4} ({os.path.getsize(master_mp4)/1024/1024:.2f} MB, {new_dur:.2f}s)")

if __name__ == "__main__":
    main()

```

## 6. Reference Script 4: `set_flow_clipboard.py`
```python
import sys
import subprocess

PROMPTS = {
    "sc1_bullying": (
        "Create a 9:16 vertical 3D Pixar animated video from this image. "
        "The smooth yellow mango female chef in white giggles behind her hand and speaks in native Persian (Farsi): "
        "«هی آگنس! فکری به حال این قیافه‌ت کردی؟» "
        "Then the plump red tomato chef in black smirks and speaks in native Persian (Farsi): "
        "«واقعاً! همین که نگاهت می‌کنم اشتهام کور می‌شه!» "
        "The sad blemished pear girl slicing cucumbers looks down tearfully. Expressive lip-sync in Persian, warm cinematic kitchen lighting."
    ),
    "sc1_henry_scolds": (
        "Create a 9:16 vertical 3D Pixar animated video from this image. "
        "The giant muscular green broccoli head chef points angrily at the sweating red tomato chef and shouts in authoritative native Persian (Farsi): "
        "«ساکت شید! شما اینجایید که آشپزی کنید یا مسخره بازی دربیارید؟ زود برگردید سر کارتون!» "
        "The red tomato chef gulps in fear while the small pear girl watches in shock. Expressive Persian lip-sync, dramatic kitchen lighting."
    ),
    "sc2_break_table": (
        "Create a 9:16 vertical 3D Pixar animated video from this image. "
        "At the kitchen break table, the red tomato chef and yellow mango chef point and laugh at the crying pear girl, speaking in native Persian (Farsi): "
        "«آشپزی مال آدمای خوش‌قیافه‌ست، نه تو! تو فقط باید ظرف بشوری!» "
        "In the background doorway, the muscular broccoli head chef steps forward angrily and shouts in native Persian (Farsi): "
        "«کافیه! همه برن بیرون به جز آگنس!»"
    ),
    "sc3_pantry_comfort": (
        "Create a 9:16 vertical 3D Pixar animated video from this image. "
        "In the warm dimly lit pantry aisle, the muscular green broccoli head chef kneels beside the crying pear girl, places a gentle hand on her shoulder, and speaks warmly in native Persian (Farsi): "
        "«به حرفاشون گوش نکن آگنس. استعداد واقعی توی قلب و دستای توئه، نه توی ظاهرت. یه روز همه طعم غذای تو رو می‌فهمن.» "
        "The pear girl looks up at him with hopeful tearful eyes."
    ),
    "sc3_agnes_vow": (
        "Create a 9:16 vertical 3D Pixar animated video from this image. "
        "Standing alone in the warm pantry aisle under the tungsten bulb, the small blemished pear girl wipes away her tear, smiles with fierce determination, and speaks softly in native Persian (Farsi): "
        "«حق با سرآشپزه... من تسلیم نمی‌شم. به همه‌شون ثابت می‌کنم که بهترین سرآشپز می‌شم!» "
        "Subtle cinematic push-in camera movement."
    ),
    "opt2_extracted_sc1": (
        "Animate this exact 9:16 3D frame into a video with native Persian (Farsi) dialogue. "
        "The red tomato chef in black and yellow mango chef in white mock the sad blemished pear girl slicing cucumbers, speaking in native Persian (Farsi): "
        "«هی آگنس! فکری به حال این قیافه‌ت کردی؟ همین که نگاهت می‌کنم اشتهام کور می‌شه!» "
        "The pear girl looks down sadly while slicing cucumbers."
    )
}

if __name__ == "__main__":
    key = sys.argv[1]
    text = PROMPTS[key]
    # Use UTF-16LE with BOM for Windows clip.exe
    subprocess.run(["clip"], input=text.encode("utf-16le"), check=True)
    print(f"Clipboard set to prompt: {key} ({len(text)} chars)")

```
