import os
import shutil
import subprocess
import cv2
import numpy as np

PROJ_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\series2-fruits-of-power-farsi"
DL_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\instagram-downloader\downloads\straw.berryjammin"
FONT_SRC = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\ugly-face-chef-farsi\03_farsi_audio_tts\Vazirmatn-Bold.ttf"

DIRS = [
    os.path.join(PROJ_DIR, "00_audit"),
    os.path.join(PROJ_DIR, "01_asset_bible", "flow_sheets"),
    os.path.join(PROJ_DIR, "02_keyframes"),
    os.path.join(PROJ_DIR, "03_farsi_audio_tts"),
    os.path.join(PROJ_DIR, "05_final_masters"),
    os.path.join(PROJ_DIR, "scripts"),
]
for d in DIRS:
    os.makedirs(d, exist_ok=True)

if os.path.exists(FONT_SRC):
    shutil.copy2(FONT_SRC, os.path.join(PROJ_DIR, "03_farsi_audio_tts", "Vazirmatn-Bold.ttf"))

PARTS = {
    1: "14_2026-10-19_DeqOJQTqU1S.mp4",
    2: "13_2026-10-19_Der6ej5KRCT.mp4",
    3: "12_2026-10-19_DesSYDvhdpd.mp4",
    4: "11_2026-10-19_DesSgm3hnHy.mp4",
    5: "10_2026-10-20_DeugJXCPEYM.mp4",
}

def extract_part_audit(p_num: int, fname: str):
    src = os.path.join(DL_DIR, fname)
    audit_dir = os.path.join(PROJ_DIR, "00_audit")
    mp3_out = os.path.join(audit_dir, f"part{p_num}_orig.mp3")

    subprocess.run([
        "ffmpeg", "-y", "-i", src,
        "-vn", "-acodec", "libmp3lame", "-b:a", "128k", mp3_out
    ], check=True, capture_output=True)

    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    dur = total_frames / fps
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"Part {p_num} ({fname}): {w}x{h} @ {fps:.2f}fps, duration={dur:.2f}s")

    # 1. Contact sheet (16 frames evenly spaced in 4x4 grid)
    thumbs = []
    for i in range(16):
        t = (i + 0.5) * dur / 16.0
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ret, frame = cap.read()
        if not ret:
            frame = np.zeros((h, w, 3), dtype=np.uint8)
        th = cv2.resize(frame, (270, 480))
        cv2.rectangle(th, (6, 6), (125, 38), (0, 0, 0), -1)
        cv2.putText(th, f"{t:.1f}s", (12, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0, 255, 255), 2)
        thumbs.append(th)

    rows = [np.hstack(thumbs[r*4:(r+1)*4]) for r in range(4)]
    contact = np.vstack(rows)
    cv2.imwrite(os.path.join(audit_dir, f"contact_part{p_num}.jpg"), contact, [int(cv2.IMWRITE_JPEG_QUALITY), 90])

    # 2. Subtitle strip sheet (every 1.0s, y=60%..80% band, 2 columns)
    strips = []
    t = 0.5
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ret, frame = cap.read()
        if not ret:
            break
        y1, y2 = int(h * 0.62), int(h * 0.78)
        crop = frame[y1:y2, :]
        crop_r = cv2.resize(crop, (540, 110))
        cv2.rectangle(crop_r, (4, 4), (105, 34), (0, 0, 0), -1)
        cv2.putText(crop_r, f"{t:.1f}s", (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 255, 255), 2)
        cv2.line(crop_r, (0, 109), (540, 109), (80, 80, 80), 1)
        strips.append(crop_r)
        t += 1.0

    if len(strips) % 2 == 1:
        strips.append(np.zeros_like(strips[0]))
    half = len(strips) // 2
    col1 = np.vstack(strips[:half])
    col2 = np.vstack(strips[half:])
    sub_sheet = np.hstack([col1, col2])
    cv2.imwrite(os.path.join(audit_dir, f"sub_strips_part{p_num}.jpg"), sub_sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 90])
    cap.release()

if __name__ == "__main__":
    for p, fn in PARTS.items():
        extract_part_audit(p, fn)
    print("Audit extraction complete.")
