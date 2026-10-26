import os
import cv2
import numpy as np

PROJ_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\series2-fruits-of-power-farsi"
DL_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\instagram-downloader\downloads\straw.berryjammin"
AUDIT_DIR = os.path.join(PROJ_DIR, "00_audit")
REFS_DIR = os.path.join(PROJ_DIR, "01_asset_bible", "source_refs")
os.makedirs(REFS_DIR, exist_ok=True)

PARTS = {
    1: "14_2026-10-19_DeqOJQTqU1S.mp4",
    2: "13_2026-10-19_Der6ej5KRCT.mp4",
    3: "12_2026-10-19_DesSYDvhdpd.mp4",
    4: "11_2026-10-19_DesSgm3hnHy.mp4",
    5: "10_2026-10-20_DeugJXCPEYM.mp4",
}

def save_frame(part_num: int, sec: float, out_name: str):
    src = os.path.join(DL_DIR, PARTS[part_num])
    cap = cv2.VideoCapture(src)
    cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000.0)
    ret, frame = cap.read()
    cap.release()
    if ret:
        # Clean any subtitle in lower band (y=66%..86%) before saving reference
        h, w, _ = frame.shape
        cv2.imwrite(os.path.join(REFS_DIR, out_name), frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        print(f"Saved ref: {out_name}")

# Extract clean reference frames for characters & locations
save_frame(1, 18.7, "ref_duke_eggplant.jpg")
save_frame(1, 39.5, "ref_banana_man.jpg")
save_frame(2, 29.3, "ref_lemonella.jpg")
save_frame(3, 56.7, "ref_shadow_fig.jpg")
save_frame(4, 27.7, "ref_strawberry_countess.jpg")
save_frame(5, 69.9, "ref_doc_peach.jpg")
save_frame(1, 43.7, "ref_loc_mansion_courtyard.jpg")
save_frame(5, 31.3, "ref_loc_casino_lounge.jpg")

# Also extract wider subtitle strip sheets (y=65%..86%) every 0.8s for Parts 1-5 so we can read every single subtitle timestamp
for p_num, fname in PARTS.items():
    src = os.path.join(DL_DIR, fname)
    cap = cv2.VideoCapture(src)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    dur = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) / fps
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    strips = []
    t = 0.4
    while t < dur:
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ret, frame = cap.read()
        if not ret:
            break
        y1, y2 = int(h * 0.65), int(h * 0.86)
        crop = frame[y1:y2, :]
        crop_r = cv2.resize(crop, (540, 120))
        cv2.rectangle(crop_r, (4, 4), (105, 34), (0, 0, 0), -1)
        cv2.putText(crop_r, f"{t:.1f}s", (8, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.68, (0, 255, 255), 2)
        cv2.line(crop_r, (0, 119), (540, 119), (80, 80, 80), 1)
        strips.append(crop_r)
        t += 1.0
    cap.release()
    if len(strips) % 2 == 1:
        strips.append(np.zeros_like(strips[0]))
    half = len(strips) // 2
    sub_sheet = np.hstack([np.vstack(strips[:half]), np.vstack(strips[half:])])
    cv2.imwrite(os.path.join(AUDIT_DIR, f"sub_wide_part{p_num}.jpg"), sub_sheet, [int(cv2.IMWRITE_JPEG_QUALITY), 90])

print("Done extracting refs and wide subtitle strips.")
