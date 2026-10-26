import os
import sys
import subprocess
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import arabic_reshaper
from bidi.algorithm import get_display

sys.stdout.reconfigure(encoding="utf-8")

PROJ_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\series2-fruits-of-power-farsi"
DL_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\instagram-downloader\downloads\straw.berryjammin"
KF_DIR = os.path.join(PROJ_DIR, "02_keyframes")
TTS_DIR = os.path.join(PROJ_DIR, "03_farsi_audio_tts")
MASTERS_DIR = os.path.join(PROJ_DIR, "05_final_masters")
AUDIT_DIR = os.path.join(PROJ_DIR, "00_audit")
FONT_PATH = os.path.join(TTS_DIR, "Vazirmatn-Bold.ttf")

os.makedirs(MASTERS_DIR, exist_ok=True)

VOICES = {
    "DUKE":       {"color": (195, 165, 255)},
    "LEMONELLA":  {"color": (255, 235, 120)},
    "BANANA":     {"color": (255, 200, 75)},
    "SHADOW_FIG": {"color": (170, 215, 255)},
    "COUNTESS":   {"color": (255, 145, 165)},
    "DOC_PEACH":  {"color": (255, 195, 160)},
    "NARRATOR":   {"color": (220, 240, 255)},
}

PARTS_CONFIG = {
    1: {
        "source_mp4": os.path.join(DL_DIR, "14_2026-10-19_DeqOJQTqU1S.mp4"),
        "title_fa": "میوه‌های قدرت | قسمت اول: خیانت در باران",
        "cover_badge": "قسمت ۱ از ۵ | سریال میوه‌های قدرت",
        "cover_title": "خیانت در عمارت بارانی!",
        "cover_sub": "وقتی دوک بادمجان مچِ لمونلا و موز طلایی رو می‌گیره...",
        "cover_kf": "KF_01_PART1.jpg",
        "qa_sec": 2.0,
        "dialogue": [
            (1,  0.30,  4.20, "DUKE",      "چرا؟! دیگه نمی‌تونم این درد رو تحمل کنم!"),
            (2,  7.20,  9.00, "LEMONELLA", "من باردارم!"),
            (3, 51.20, 54.80, "BANANA",    "بارون رو ببین... داره کل شهر رو فقط برای من تطهیر می‌کنه."),
            (4, 55.10, 58.00, "BANANA",    "حالا تمام دارایی و زندگیت مال منه، دوک!"),
            (5, 58.30, 64.20, "DUKE",      "چرا من؟! خدایا چرا؟! دیگه طاقتش رو ندارم!"),
        ],
    },
    2: {
        "source_mp4": os.path.join(DL_DIR, "13_2026-10-19_Der6ej5KRCT.mp4"),
        "title_fa": "میوه‌های قدرت | قسمت دوم: راز پاکت آزمایش",
        "cover_badge": "قسمت ۲ از ۵ | سریال میوه‌های قدرت",
        "cover_title": "جواب آزمایش دی‌ان‌ای!",
        "cover_sub": "پاکتی که زندگی لمونلا، دوک و موز طلایی رو زیر و رو کرد!",
        "cover_kf": "KF_02_PART2.jpg",
        "qa_sec": 62.5,
        "dialogue": [
            (1,  0.30,  2.60, "BANANA",    "بزن بریم! امشب شبِ ماست!"),
            (2,  4.20,  5.50, "BANANA",    "ووه! عالیه!"),
            (3,  8.10, 10.20, "BANANA",    "توی اون پاکت چی نوشته؟"),
            (4, 11.20, 16.50, "LEMONELLA", "همه فکر می‌کنن من همه‌چیز دارم... ای کاش حقیقت رو می‌دونستن!"),
            (5, 51.20, 54.40, "LEMONELLA", "نه... نه، امکان نداره این درست باشه!"),
            (6, 55.00, 57.50, "BANANA",    "چی شده؟ توی آزمایش چی نوشته؟"),
            (7, 60.20, 65.20, "LEMONELLA", "چطور روت میشه حقیقت رو انکار کنی؟! آزمایش دی‌ان‌ای همه‌چیز رو ثابت می‌کنه، هیولا!"),
            (8, 67.20, 72.80, "LEMONELLA", "وای خدای من، نه... امکان نداره همچین چیزی واقعی باشه!"),
        ],
    },
    3: {
        "source_mp4": os.path.join(DL_DIR, "12_2026-10-19_DesSYDvhdpd.mp4"),
        "title_fa": "میوه‌های قدرت | قسمت سوم: سایه انجیر سیاه",
        "cover_badge": "قسمت ۳ از ۵ | سریال میوه‌های قدرت",
        "cover_title": "ورود رئیس مافیا: انجیر سیاه!",
        "cover_sub": "کفش بلورین در باران و رازی که دوک ازش خبر نداره!",
        "cover_kf": "KF_03_PART3.jpg",
        "qa_sec": 25.0,
        "dialogue": [
            (1,  0.30,  3.20, "LEMONELLA",  "باورم نمیشه... بچه‌مون پسره!"),
            (2,  4.10,  6.30, "LEMONELLA",  "ای کاش بقیه حقیقت رو می‌دونستن..."),
            (3,  7.30, 13.00, "LEMONELLA",  "چطور روت میشه منکر حقیقت بشی؟! آزمایش دی‌ان‌ای همه‌چیز رو ثابت کرد، هیولا!"),
            (4, 13.20, 15.60, "BANANA",     "هاهاها! که چی مثلاً؟!"),
            (5, 22.20, 28.00, "DUKE",       "این نقشه رو ببین لمونلا؛ تزئینات طلای خالص و نمای کامل شهر... بهترین‌ها برای وارثمون!"),
            (6, 31.00, 33.30, "SHADOW_FIG", "و اونا به هیچ‌چیز شک نکردن؟"),
            (7, 33.50, 36.20, "LEMONELLA",  "معلومه که نه... اونا هیچ‌وقت بویی نمی‌برن."),
            (8, 38.20, 41.20, "LEMONELLA",  "باید قبل از اینکه دوک پیدام کنه از اینجا فرار کنم!"),
            (9, 58.20, 60.10, "SHADOW_FIG", "این رو بیرون پیدا کردم."),
            (10, 60.20, 62.30, "LEMONELLA", "وای خدای من، نه!"),
        ],
    },
    4: {
        "source_mp4": os.path.join(DL_DIR, "11_2026-10-19_DesSgm3hnHy.mp4"),
        "title_fa": "میوه‌های قدرت | قسمت چهارم: قرارداد پنهانی",
        "cover_badge": "قسمت ۴ از ۵ | سریال میوه‌های قدرت",
        "cover_title": "قرارداد پنهانی و تهدید بزرگ!",
        "cover_sub": "التماس‌های لمونلا، وسوسه کنتس توت‌فرنگی و فرمان انجیر سیاه!",
        "cover_kf": "KF_04_PART4.jpg",
        "qa_sec": 39.5,
        "dialogue": [
            (1,  0.30,  7.80, "LEMONELLA",  "دوک، قسم می‌خورم نمی‌خواستم اینطوری بشه! فقط یه اشتباه بود! به اعتمادت خیانت کردم و همه‌چیز رو خراب کردم!"),
            (2, 16.20, 19.60, "LEMONELLA",  "این دیگه چیه؟ چرا این قرارداد رو امضا کردی؟"),
            (3, 20.80, 26.80, "COUNTESS",   "لازم نیست امشب تنها بمونی دوکِ عزیزم... تو لیاقتت خیلی بیشتر از این غم و غصه‌ست."),
            (4, 36.80, 43.80, "SHADOW_FIG", "انگار جایگاهت رو فراموش کردی! من مذاکره نمی‌کنم؛ من شرط تعیین می‌کنم، و اولین شرطم اطاعتِ محضِ توئه!"),
            (5, 52.30, 57.60, "LEMONELLA",  "به چه حقی به من پشت می‌کنی؟! وقتی باهات حرف می‌زنم تو چشمام نگاه کن! فکر کردی این یه شوخیه؟!"),
            (6, 57.80, 59.80, "BANANA",     "فکر می‌کنم داری الکی شلوغش می‌کنی."),
        ],
    },
    5: {
        "source_mp4": os.path.join(DL_DIR, "10_2026-10-20_DeugJXCPEYM.mp4"),
        "title_fa": "میوه‌های قدرت | قسمت پنجم (پایان): شوکِ سه‌قلوها!",
        "cover_badge": "قسمت ۵ (پایان) | سریال میوه‌های قدرت",
        "cover_title": "شوک نهایی در بیمارستان: سه‌قلو؟!",
        "cover_sub": "گذشته تاریک کازینو، سه رقیب، و راز سه جنین در سونوگرافی!",
        "cover_kf": "KF_06_PART5_FINALE.jpg",
        "qa_sec": 63.0,
        "dialogue": [
            (1,  0.15,  1.95, "DOC_PEACH", "به نظر می‌رسه یه مشکلِ پیچیده پیش اومده."),
            (2,  2.00,  3.10, "LEMONELLA", "یه مشکل پیچیده؟!"),
            (3,  3.15,  6.10, "BANANA",    "پس من... منم فقط یه اشتباهِ دیگه بودم؟!"),
            (4, 11.00, 13.40, "DUKE",      "تو قبل از من با اون مرد رابطه داشتی؟!"),
            (5, 13.60, 17.80, "NARRATOR",  "قبل از دوک، لمونلا متعلق به دنیایِ تاریکِ انجیر سیاه بود."),
            (6, 40.10, 43.20, "BANANA",    "پس یعنی منم برات فقط یه اشتباهِ دیگه بودم؟!"),
            (7, 46.00, 49.20, "DUKE",      "برام مهم نیست قبل از من کی عاشقت بوده."),
            (8, 54.80, 57.20, "DUKE",      "سریع زنگ بزنید به بیمارستان!"),
            (9, 61.10, 65.10, "DOC_PEACH", "متاسفانه اسکن‌ها یه چیزِ غیرمنتظره رو نشون میدن... یه اتفاقِ عجیب افتاده."),
            (10, 65.20, 68.80, "LEMONELLA", "اتفاق عجیب؟! یعنی چی خانم دکتر؟! حالِ بچه‌م خوبه؟!"),
            (11, 73.80, 76.60, "DOC_PEACH", "توی شکمت سه تا بچه‌ست! سه‌قلو بارداری!"),
        ],
    },
}

def shape_fa(text: str) -> str:
    return get_display(arabic_reshaper.reshape(text))

def fmt_srt_time(sec: float) -> str:
    ms = int(round((sec - int(sec)) * 1000))
    s = int(sec) % 60
    m = (int(sec) // 60) % 60
    h = int(sec) // 3600
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

def get_dur(path: str) -> float:
    out = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1", path
    ], text=True).strip()
    return float(out)

def inpaint_subtitle_band(rgb: np.ndarray) -> np.ndarray:
    h, w, _ = rgb.shape
    y1, y2 = int(h * 0.65), int(h * 0.85)
    x1, x2 = int(w * 0.08), int(w * 0.92)
    roi = rgb[y1:y2, x1:x2]
    r, g, b = roi[:, :, 0], roi[:, :, 1], roi[:, :, 2]
    bright = ((r > 210) & (g > 210) & (b > 210)) | ((r > 210) & (g > 165) & (b < 125))
    dark_outline = (r < 42) & (g < 42) & (b < 42)
    dark_dil = cv2.dilate(dark_outline.astype(np.uint8) * 255, np.ones((5, 5), np.uint8), iterations=1) > 0
    stroke_verified = (bright & dark_dil).astype(np.uint8) * 255
    num_l, labels, stats, _ = cv2.connectedComponentsWithStats(stroke_verified, connectivity=8)
    mask = np.zeros_like(stroke_verified)
    for i in range(1, num_l):
        area = stats[i, cv2.CC_STAT_AREA]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        if 3 <= area <= 1100 and bw < 95 and bh < 50:
            mask[labels == i] = 255
    if np.count_nonzero(mask) > 10:
        dil = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)
        inp = cv2.inpaint(cv2.cvtColor(roi, cv2.COLOR_RGB2BGR), dil, 4, cv2.INPAINT_TELEA)
        rgb[y1:y2, x1:x2] = cv2.cvtColor(inp, cv2.COLOR_BGR2RGB)
    return rgb

def build_cover(part_num: int):
    cfg = PARTS_CONFIG[part_num]
    kf_path = os.path.join(KF_DIR, cfg["cover_kf"])
    cov_pil = Image.open(kf_path).convert("RGBA")
    w, h = cov_pil.size
    cov_ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    cdraw = ImageDraw.Draw(cov_ov)

    badge_s = shape_fa(cfg["cover_badge"])
    ctitle = shape_fa(cfg["cover_title"])
    csub = shape_fa(cfg["cover_sub"])

    f_bd = ImageFont.truetype(FONT_PATH, 26)
    f_ct = ImageFont.truetype(FONT_PATH, 42)
    f_cs = ImageFont.truetype(FONT_PATH, 24)

    # Top episode badge
    bb = cdraw.textbbox((0, 0), badge_s, font=f_bd)
    bw, bh = bb[2] - bb[0], bb[3] - bb[1]
    bx1 = (w - bw) // 2 - 24
    bx2 = (w + bw) // 2 + 24
    by1 = int(h * 0.06)
    by2 = by1 + bh + 24
    cdraw.rounded_rectangle([bx1, by1, bx2, by2], radius=16, fill=(25, 12, 45, 230), outline=(255, 215, 90, 245), width=3)
    cdraw.text(((w - bw) // 2 - bb[0], by1 + 10 - bb[1]), badge_s, font=f_bd, fill=(255, 230, 120, 255))

    # Bottom hook title card
    bt = cdraw.textbbox((0, 0), ctitle, font=f_ct)
    bs = cdraw.textbbox((0, 0), csub, font=f_cs)
    tw1, th1 = bt[2] - bt[0], bt[3] - bt[1]
    tw2, th2 = bs[2] - bs[0], bs[3] - bs[1]
    box_w = min(w - 28, max(tw1, tw2) + 48)
    cx1 = (w - box_w) // 2
    cx2 = (w + box_w) // 2
    cy1 = int(h * 0.74)
    cy2 = cy1 + th1 + th2 + 52
    cdraw.rounded_rectangle([cx1, cy1, cx2, cy2], radius=22, fill=(10, 10, 20, 232), outline=(255, 210, 80, 245), width=3)
    cdraw.text(((w - tw1) // 2 - bt[0], cy1 + 14 - bt[1]), ctitle, font=f_ct, fill=(255, 225, 95, 255))
    cdraw.text(((w - tw2) // 2 - bs[0], cy1 + 28 + th1 - bs[1]), csub, font=f_cs, fill=(255, 255, 255, 255))

    cov_out = os.path.join(MASTERS_DIR, f"Cover_Part{part_num}_Fruits_of_Power_Farsi.jpg")
    Image.alpha_composite(cov_pil, cov_ov).convert("RGB").save(cov_out, quality=95)
    print(f"Saved Cover: {cov_out}")

def process_part(part_num: int):
    cfg = PARTS_CONFIG[part_num]
    src_mp4 = cfg["source_mp4"]
    dialogue = cfg["dialogue"]
    p_tts_dir = os.path.join(TTS_DIR, f"part{part_num}")

    build_cover(part_num)

    # 1. Write SRT
    srt_out = os.path.join(MASTERS_DIR, f"Master_Part{part_num}_Fruits_of_Power_Farsi.srt")
    with open(srt_out, "w", encoding="utf-8") as f:
        for idx, st, et, spk, text in dialogue:
            f.write(f"{idx}\n{fmt_srt_time(st)} --> {fmt_srt_time(et)}\n{text}\n\n")

    # 2. Build Master Studio Audio (-14 LUFS with ducked stereo side-channel BGM bed)
    bgm_bed = os.path.join(p_tts_dir, f"part{part_num}_bgm_bed.wav")
    vol_expr = "+".join([f"between(t,{st:.2f},{et:.2f})" for _, st, et, _, _ in dialogue])
    subprocess.run([
        "ffmpeg", "-y", "-i", src_mp4,
        "-af", f"pan=stereo|c0=0.55*c0-0.35*c1|c1=0.55*c1-0.35*c0,volume='if(gt({vol_expr},0),0.18,0.72)':eval=frame",
        "-ar", "48000", "-ac", "2", bgm_bed
    ], check=True, capture_output=True)

    total_sec = get_dur(src_mp4)
    sr = 48000
    total_samples = int(total_sec * sr) + sr
    master_vo = np.zeros((total_samples, 2), dtype=np.float32)

    for idx, st, et, spk, _ in dialogue:
        wav_p = os.path.join(p_tts_dir, f"line_{idx:02d}.wav")
        raw_bytes = subprocess.check_output([
            "ffmpeg", "-v", "error", "-i", wav_p,
            "-f", "f32le", "-acodec", "pcm_f32le", "-ar", str(sr), "-ac", "2", "-"
        ])
        samples = np.frombuffer(raw_bytes, dtype=np.float32).reshape(-1, 2)
        start_idx = int(round(st * sr))
        end_idx = min(total_samples, start_idx + len(samples))
        master_vo[start_idx:end_idx] += samples[:end_idx - start_idx] * 1.42

    vo_track_wav = os.path.join(p_tts_dir, f"part{part_num}_vo_stem.wav")
    proc = subprocess.Popen([
        "ffmpeg", "-y", "-f", "f32le", "-ar", str(sr), "-ac", "2", "-i", "-",
        "-c:a", "pcm_s16le", vo_track_wav
    ], stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    proc.communicate(input=master_vo[:int(total_sec * sr)].tobytes())

    master_wav = os.path.join(p_tts_dir, f"part{part_num}_master_fa.wav")
    subprocess.run([
        "ffmpeg", "-y", "-i", bgm_bed, "-i", vo_track_wav,
        "-filter_complex", "[0:a][1:a]amix=inputs=2:duration=first:normalize=0,loudnorm=I=-14:TP=-1.5:LRA=11[aout]",
        "-map", "[aout]", "-ar", "48000", "-ac", "2", master_wav
    ], check=True, capture_output=True)

    # 3. Clean video + burn shaped RTL Persian subtitles
    cap = cv2.VideoCapture(src_mp4)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    font_title = ImageFont.truetype(FONT_PATH, 24)
    title_shaped = shape_fa(cfg["title_fa"])

    shaped_subs = []
    for idx, st, et, spk, text in dialogue:
        words = text.split(" ")
        if len(text) > 36 and len(words) >= 6:
            mid = len(words) // 2
            lines_s = [shape_fa(" ".join(words[:mid])), shape_fa(" ".join(words[mid:]))]
        else:
            lines_s = [shape_fa(text)]
        shaped_subs.append((st, et, spk, lines_s))

    temp_silent_mp4 = os.path.join(p_tts_dir, f"temp_part{part_num}_sub.mp4")
    ff_proc = subprocess.Popen([
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{w}x{h}", "-pix_fmt", "rgb24", "-r", str(fps),
        "-i", "-",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "18", "-pix_fmt", "yuv420p",
        temp_silent_mp4
    ], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)

    f_idx = 0
    qa_frame_saved = False
    qa_target_sec = cfg["qa_sec"]

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        t = f_idx / fps
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb = inpaint_subtitle_band(rgb)

        pil_img = Image.fromarray(rgb).convert("RGBA")
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        if 0.4 <= t <= 3.4:
            bbox = draw.textbbox((0, 0), title_shaped, font=font_title)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            bx1 = max(12, (w - tw) // 2 - 20)
            by1 = int(h * 0.08)
            bx2 = min(w - 12, (w + tw) // 2 + 20)
            by2 = by1 + th + 22
            draw.rounded_rectangle([bx1, by1, bx2, by2], radius=14, fill=(15, 12, 28, 215), outline=(255, 215, 95, 235), width=2)
            draw.text(((w - tw) // 2 - bbox[0], by1 + 10 - bbox[1]), title_shaped, font=font_title, fill=(255, 238, 170, 255))

        for st, et, spk, lines_s in shaped_subs:
            if st <= t <= et:
                color = VOICES[spk]["color"]
                cur_sz = 24
                while cur_sz >= 15:
                    f_sub = ImageFont.truetype(FONT_PATH, cur_sz)
                    line_dims = [draw.textbbox((0, 0), ln, font=f_sub) for ln in lines_s]
                    max_lw = max(b[2] - b[0] for b in line_dims)
                    if max_lw <= w - 48:
                        break
                    cur_sz -= 1
                line_h = cur_sz + 10
                total_th = len(lines_s) * line_h
                cy = int(h * 0.755)
                px1 = max(12, (w - max_lw) // 2 - 20)
                px2 = min(w - 12, (w + max_lw) // 2 + 20)
                py1 = cy - total_th // 2 - 11
                py2 = cy + total_th // 2 + 13
                draw.rounded_rectangle([px1, py1, px2, py2], radius=14, fill=(10, 12, 18, 225), outline=(color[0], color[1], color[2], 205), width=2)
                for li, ln in enumerate(lines_s):
                    b = line_dims[li]
                    lw = b[2] - b[0]
                    lx = (w - lw) // 2 - b[0]
                    ly = py1 + 10 + li * line_h - b[1]
                    draw.text((lx + 2, ly + 2), ln, font=f_sub, fill=(0, 0, 0, 245))
                    draw.text((lx, ly), ln, font=f_sub, fill=(color[0], color[1], color[2], 255))
                break

        comp = Image.alpha_composite(pil_img, overlay).convert("RGB")
        comp_np = np.array(comp)
        if not qa_frame_saved and t >= qa_target_sec:
            qa_path = os.path.join(AUDIT_DIR, f"qa_master_part{part_num}.jpg")
            Image.fromarray(comp_np).save(qa_path, quality=95)
            qa_frame_saved = True

        ff_proc.stdin.write(comp_np.tobytes())
        f_idx += 1

    cap.release()
    ff_proc.stdin.close()
    ff_proc.wait()

    final_out = os.path.join(MASTERS_DIR, f"Master_Part{part_num}_Fruits_of_Power_Farsi.mp4")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", temp_silent_mp4,
        "-i", master_wav,
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        final_out
    ], check=True, capture_output=True)
    print(f"[MASTER PART {part_num} DONE] -> {final_out}")

if __name__ == "__main__":
    for p in [1, 2, 3, 4, 5]:
        process_part(p)
    print("All 5 Master Videos and Covers rendered successfully!")
