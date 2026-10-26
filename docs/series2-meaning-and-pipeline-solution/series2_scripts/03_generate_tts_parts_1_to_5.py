import asyncio
import os
import sys
import shutil
import subprocess
import numpy as np
import edge_tts

sys.stdout.reconfigure(encoding="utf-8")

PROJ_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\series2-fruits-of-power-farsi"
BRAIN_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\brain\6ed787cb-ee5a-46bf-a8fa-8141a259ceb4"
FLOW_DIR = os.path.join(PROJ_DIR, "01_asset_bible", "flow_sheets")
KF_DIR = os.path.join(PROJ_DIR, "02_keyframes")
TTS_DIR = os.path.join(PROJ_DIR, "03_farsi_audio_tts")
os.makedirs(FLOW_DIR, exist_ok=True)
os.makedirs(KF_DIR, exist_ok=True)
os.makedirs(TTS_DIR, exist_ok=True)

KF_MAP = {
    "kf_01_part1_1792934437293.jpg": "KF_01_PART1.jpg",
    "kf_02_part2_1792934462660.jpg": "KF_02_PART2.jpg",
    "kf_03_part3_1792934496801.jpg": "KF_03_PART3.jpg",
    "kf_04_part4_1792934464191.jpg": "KF_04_PART4.jpg",
    "kf_05_part5_fixed_1792934532758.jpg": "KF_05_PART5.jpg",
    "kf_06_part5_finale_1792934591231.jpg": "KF_06_PART5_FINALE.jpg",
}
for src_n, dst_n in KF_MAP.items():
    sp = os.path.join(BRAIN_DIR, src_n)
    if os.path.exists(sp):
        shutil.copy2(sp, os.path.join(KF_DIR, dst_n))

VOICES = {
    "DUKE":       {"voice": "fa-IR-FaridNeural",  "rate": "-4%",  "pitch": "-10Hz", "color": (195, 165, 255)},
    "LEMONELLA":  {"voice": "fa-IR-DilaraNeural", "rate": "+2%",  "pitch": "+8Hz",  "color": (255, 235, 120)},
    "BANANA":     {"voice": "fa-IR-FaridNeural",  "rate": "+10%", "pitch": "+10Hz", "color": (255, 200, 75)},
    "SHADOW_FIG": {"voice": "fa-IR-FaridNeural",  "rate": "-8%",  "pitch": "-22Hz", "color": (170, 215, 255)},
    "COUNTESS":   {"voice": "fa-IR-DilaraNeural", "rate": "-2%",  "pitch": "-8Hz",  "color": (255, 145, 165)},
    "DOC_PEACH":  {"voice": "fa-IR-DilaraNeural", "rate": "+4%",  "pitch": "-2Hz",  "color": (255, 195, 160)},
    "NARRATOR":   {"voice": "fa-IR-FaridNeural",  "rate": "-2%",  "pitch": "-6Hz",  "color": (220, 240, 255)},
}

# Tuple format: (idx, st, et, speaker, subtitle_text, tts_text)
DIALOGUE_BIBLE = {
    1: [
        (1,  0.30,  4.20, "DUKE",      "چرا؟! دیگه نمی‌تونم این درد رو تحمل کنم!", "چرا؟! دیگه نمی‌تونم این درد رو تحمل کنم!"),
        (2,  7.20,  9.00, "LEMONELLA", "من باردارم!", "من باردارم!"),
        (3, 51.20, 54.80, "BANANA",    "بارون رو ببین... داره کل شهر رو فقط برای من تطهیر می‌کنه.", "بارون رو ببین... داره کل شهر رو فقط برای من تطهیر می‌کنه."),
        (4, 55.10, 58.00, "BANANA",    "حالا تمام دارایی و زندگیت مال منه، دوک!", "حالا تمام دارایی و زندگیت مال منه، دوک!"),
        (5, 58.30, 64.20, "DUKE",      "چرا من؟! خدایا چرا؟! دیگه طاقتش رو ندارم!", "چرا من؟! خدایا چرا؟! دیگه طاقتش رو ندارم!"),
    ],
    2: [
        (1,  0.30,  2.60, "BANANA",    "بزن بریم! امشب شبِ ماست!", "بزن بریم! امشب شبِ ماست!"),
        (2,  4.20,  5.50, "BANANA",    "ووه! عالیه!", "ووه! عالیه!"),
        (3,  8.10, 10.20, "BANANA",    "توی اون پاکت چی نوشته؟", "توی اون پاکت چی نوشته؟"),
        (4, 11.20, 16.50, "LEMONELLA", "همه فکر می‌کنن من همه‌چیز دارم... ای کاش حقیقت رو می‌دونستن!", "همه فکر می‌کنن من همه‌چیز دارم... ای کاش حقیقت رو می‌دونستن!"),
        (5, 51.20, 54.40, "LEMONELLA", "نه... نه، امکان نداره این درست باشه!", "نه... نه، امکان نداره این درست باشه!"),
        (6, 55.00, 57.50, "BANANA",    "چی شده؟ توی آزمایش چی نوشته؟", "چی شده؟ توی آزمایش چی نوشته؟"),
        (7, 60.20, 65.20, "LEMONELLA", "چطور روت میشه حقیقت رو انکار کنی؟! آزمایش دی‌ان‌ای همه‌چیز رو ثابت می‌کنه، هیولا!", "چطور روت میشه حقیقت رو انکار کنی؟! آزمایشِ دی اِن اِی همه‌چیز رو ثابت می‌کنه، هیولا!"),
        (8, 67.20, 72.80, "LEMONELLA", "وای خدای من، نه... امکان نداره همچین چیزی واقعی باشه!", "وای خدای من، نه... امکان نداره همچین چیزی واقعی باشه!"),
    ],
    3: [
        (1,  0.30,  3.20, "LEMONELLA",  "باورم نمیشه... بچه‌مون پسره!", "باورم نمیشه... بچه‌مون پسره!"),
        (2,  4.10,  6.30, "LEMONELLA",  "ای کاش بقیه حقیقت رو می‌دونستن...", "ای کاش بقیه حقیقت رو می‌دونستن..."),
        (3,  7.30, 13.00, "LEMONELLA",  "چطور روت میشه منکر حقیقت بشی؟! آزمایش دی‌ان‌ای همه‌چیز رو ثابت کرد، هیولا!", "چطور روت میشه منکر حقیقت بشی؟! آزمایشِ دی اِن اِی همه‌چیز رو ثابت کرد، هیولا!"),
        (4, 13.20, 15.60, "BANANA",     "هاهاها! که چی مثلاً؟!", "هاهاها! که چی مثلاً؟!"),
        (5, 22.20, 28.00, "DUKE",       "این نقشه رو ببین لمونلا؛ تزئینات طلای خالص و نمای کامل شهر... بهترین‌ها برای وارثمون!", "این نقشه رو ببین لمونلا؛ تزئینات طلای خالص و نمای کامل شهر... بهترین‌ها برای وارثمون!"),
        (6, 31.00, 33.30, "SHADOW_FIG", "و اونا به هیچ‌چیز شک نکردن؟", "و اونا به هیچ‌چیز شک نکردن؟"),
        (7, 33.50, 36.20, "LEMONELLA",  "معلومه که نه... اونا هیچ‌وقت بویی نمی‌برن.", "معلومه که نه... اونا هیچ‌وقت بویی نمی‌برن."),
        (8, 38.20, 41.20, "LEMONELLA",  "باید قبل از اینکه دوک پیدام کنه از اینجا فرار کنم!", "باید قبل از اینکه دوک پیدام کنه از اینجا فرار کنم!"),
        (9, 58.20, 60.10, "SHADOW_FIG", "این رو بیرون پیدا کردم.", "این رو بیرون پیدا کردم."),
        (10, 60.20, 62.30, "LEMONELLA", "وای خدای من، نه!", "وای خدای من، نه!"),
    ],
    4: [
        (1,  0.30,  7.80, "LEMONELLA",  "دوک، قسم می‌خورم نمی‌خواستم اینطوری بشه! فقط یه اشتباه بود! به اعتمادت خیانت کردم و همه‌چیز رو خراب کردم!", "دوک، قسم می‌خورم نمی‌خواستم اینطوری بشه! فقط یه اشتباه بود! به اعتمادت خیانت کردم و همه‌چیز رو خراب کردم!"),
        (2, 16.20, 19.60, "LEMONELLA",  "این دیگه چیه؟ چرا این قرارداد رو امضا کردی؟", "این دیگه چیه؟ چرا این قرارداد رو امضا کردی؟"),
        (3, 20.80, 26.80, "COUNTESS",   "لازم نیست امشب تنها بمونی دوکِ عزیزم... تو لیاقتت خیلی بیشتر از این غم و غصه‌ست.", "لازم نیست امشب تنها بمونی دوکِ عزیزم... تو لیاقتت خیلی بیشتر از این غم و غصه‌ست."),
        (4, 36.80, 43.80, "SHADOW_FIG", "انگار جایگاهت رو فراموش کردی! من مذاکره نمی‌کنم؛ من شرط تعیین می‌کنم، و اولین شرطم اطاعتِ محضِ توئه!", "انگار جایگاهت رو فراموش کردی! من مذاکره نمی‌کنم؛ من شرط تعیین می‌کنم، و اولین شرطم اطاعتِ محضِ توئه!"),
        (5, 52.30, 57.60, "LEMONELLA",  "به چه حقی به من پشت می‌کنی؟! وقتی باهات حرف می‌زنم تو چشمام نگاه کن! فکر کردی این یه شوخیه؟!", "به چه حقی به من پشت می‌کنی؟! وقتی باهات حرف می‌زنم تو چشمام نگاه کن! فکر کردی این یه شوخیه؟!"),
        (6, 57.80, 59.80, "BANANA",     "فکر می‌کنم داری الکی شلوغش می‌کنی.", "فکر می‌کنم داری الکی شلوغش می‌کنی."),
    ],
    5: [
        (1,  0.15,  1.95, "DOC_PEACH", "به نظر می‌رسه یه مشکلِ پیچیده پیش اومده.", "به نظر می‌رسه یه مشکلِ پیچیده پیش اومده."),
        (2,  2.00,  3.10, "LEMONELLA", "یه مشکل پیچیده؟!", "یه مشکلِ پیچیده؟!"),
        (3,  3.15,  6.10, "BANANA",    "پس من... منم فقط یه اشتباهِ دیگه بودم؟!", "پس من... منم فقط یه اشتباهِ دیگه بودم؟!"),
        (4, 11.00, 13.40, "DUKE",      "تو قبل از من با اون مرد رابطه داشتی؟!", "تو قبل از من با اون مرد رابطه داشتی؟!"),
        (5, 13.60, 17.80, "NARRATOR",  "قبل از دوک، لمونلا متعلق به دنیایِ تاریکِ انجیر سیاه بود.", "قبل از دوک، لمونلا متعلق به دنیایِ تاریکِ انجیر سیاه بود."),
        (6, 40.10, 43.20, "BANANA",    "پس یعنی منم برات فقط یه اشتباهِ دیگه بودم؟!", "پس یعنی منم برات فقط یه اشتباهِ دیگه بودم؟!"),
        (7, 46.00, 49.20, "DUKE",      "برام مهم نیست قبل از من کی عاشقت بوده.", "برام مهم نیست قبل از من کی عاشقت بوده."),
        (8, 54.80, 57.20, "DUKE",      "سریع زنگ بزنید به بیمارستان!", "سریع زنگ بزنید به بیمارستان!"),
        (9, 61.10, 65.10, "DOC_PEACH", "متاسفانه اسکن‌ها یه چیزِ غیرمنتظره رو نشون میدن... یه اتفاقِ عجیب افتاده.", "متاسفانه اسکن‌ها یه چیزِ غیرمنتظره رو نشون میدن... یه اتفاقِ عجیب افتاده."),
        (10, 65.20, 68.80, "LEMONELLA", "اتفاق عجیب؟! یعنی چی خانم دکتر؟! حالِ بچه‌م خوبه؟!", "اتفاق عجیب؟! یعنی چی خانم دکتر؟! حالِ بچه‌م خوبه؟!"),
        (11, 73.80, 76.60, "DOC_PEACH", "توی شکمت سه تا بچه‌ست! سه‌قلو بارداری!", "توی شکمت سِه تا بچه‌ست! سِه قُلو بارداری!"),
    ],
}

def get_dur(path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ], text=True).strip()
    return float(out)

def trim_wav_numpy(raw_mp3: str, trim_wav: str, sr: int = 48000):
    raw_bytes = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", raw_mp3,
        "-f", "f32le", "-acodec", "pcm_f32le", "-ar", str(sr), "-ac", "2", "-"
    ])
    samples = np.frombuffer(raw_bytes, dtype=np.float32).reshape(-1, 2)
    env = np.max(np.abs(samples), axis=1)
    active = np.where(env > 0.0012)[0]
    if len(active) > 0:
        s_idx = max(0, int(active[0]) - int(0.03 * sr))
        e_idx = min(len(samples), int(active[-1]) + int(0.12 * sr))
        samples = samples[s_idx:e_idx]
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-",
        "-c:a", "pcm_s16le", trim_wav
    ], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
    proc.communicate(input=samples.tobytes())

async def synth_all():
    for part_num, lines in DIALOGUE_BIBLE.items():
        p_dir = os.path.join(TTS_DIR, f"part{part_num}")
        os.makedirs(p_dir, exist_ok=True)
        for idx, st, et, spk, sub_text, tts_text in lines:
            raw_mp3 = os.path.join(p_dir, f"line_{idx:02d}_raw.mp3")
            trim_wav = os.path.join(p_dir, f"line_{idx:02d}_trim.wav")
            fit_wav = os.path.join(p_dir, f"line_{idx:02d}.wav")
            fit_mp3 = os.path.join(p_dir, f"line_{idx:02d}_final.mp3")

            vcfg = VOICES[spk]
            comm = edge_tts.Communicate(tts_text, vcfg["voice"], rate=vcfg["rate"], pitch=vcfg["pitch"])
            await comm.save(raw_mp3)

            trim_wav_numpy(raw_mp3, trim_wav)

            dur = get_dur(trim_wav)
            slot_dur = max(0.5, et - st)
            af_chain = ["highpass=f=75"]
            tempo = 1.0
            if dur > slot_dur:
                tempo = min(1.48, max(1.02, dur / (slot_dur - 0.02)))
                af_chain.insert(0, f"atempo={tempo:.3f}")
            subprocess.run([
                "ffmpeg", "-y", "-i", trim_wav,
                "-af", ",".join(af_chain),
                "-ar", "48000", "-ac", "2", fit_wav
            ], check=True, capture_output=True)
            subprocess.run([
                "ffmpeg", "-y", "-i", fit_wav,
                "-acodec", "libmp3lame", "-b:a", "128k", fit_mp3
            ], check=True, capture_output=True)
            final_dur = get_dur(fit_wav)
            print(f"P{part_num} L{idx:02d} [{spk}] slot={slot_dur:.2f}s | final={final_dur:.2f}s (tempo={tempo:.2f}x)")

if __name__ == "__main__":
    asyncio.run(synth_all())
