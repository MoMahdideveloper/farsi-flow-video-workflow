import os
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\instagram-downloader\downloads\straw.berryjammin"
PROJ_DIR = r"C:\Users\LifeCycle\.gemini\antigravity\scratch\series2-fruits-of-power-farsi"
AUDIT_DIR = os.path.join(PROJ_DIR, "00_audit")
os.makedirs(AUDIT_DIR, exist_ok=True)

EPISODES = {
    1: ("14_2026-10-19_DeqOJQTqU1S.mp4", [5.8, 10.4, 14.6, 18.7, 39.5, 47.9]),
    2: ("13_2026-10-19_Der6ej5KRCT.mp4", [7.0, 21.1, 30.4, 35.1, 58.5, 72.6]),
    3: ("12_2026-10-19_DesSYDvhdpd.mp4", [5.9, 17.6, 26.8, 33.3, 41.1, 56.7]),
    4: ("11_2026-10-19_DesSgm3hnHy.mp4", [10.7, 18.0, 27.7, 32.0, 49.1, 61.9]),
    5: ("10_2026-10-20_DeugJXCPEYM.mp4", [7.2, 10.8, 31.3, 45.8, 60.2, 69.9]),
}

def count_sub_glyphs(bgr: np.ndarray) -> int:
    h, w, _ = bgr.shape
    roi = bgr[int(h * 0.72):int(h * 0.90), int(w * 0.08):int(w * 0.92)]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    # White or bright yellow subtitle text
    white_mask = (roi[:, :, 0] > 210) & (roi[:, :, 1] > 210) & (roi[:, :, 2] > 210)
    yellow_mask = (hsv[:, :, 0] >= 15) & (hsv[:, :, 0] <= 38) & (hsv[:, :, 1] > 130) & (hsv[:, :, 2] > 200)
    mask = ((white_mask | yellow_mask).astype(np.uint8)) * 255
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    score = 0
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        if 4 <= area <= 1400 and bw < 95 and bh < 65:
            score += area
    return score

def clean_sub_band(bgr: np.ndarray) -> np.ndarray:
    out = bgr.copy()
    h, w, _ = out.shape
    y1, y2 = int(h * 0.73), int(h * 0.89)
    x1, x2 = int(w * 0.08), int(w * 0.92)
    roi = out[y1:y2, x1:x2]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
    white_mask = (roi[:, :, 0] > 210) & (roi[:, :, 1] > 210) & (roi[:, :, 2] > 210)
    yellow_mask = (hsv[:, :, 0] >= 15) & (hsv[:, :, 0] <= 38) & (hsv[:, :, 1] > 130) & (hsv[:, :, 2] > 200)
    mask = ((white_mask | yellow_mask).astype(np.uint8)) * 255
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
    text_mask = np.zeros_like(mask)
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        bw = stats[i, cv2.CC_STAT_WIDTH]
        bh = stats[i, cv2.CC_STAT_HEIGHT]
        if 4 <= area <= 1400 and bw < 95 and bh < 65:
            text_mask[labels == i] = 255
    if np.count_nonzero(text_mask) > 12:
        dil = cv2.dilate(text_mask, np.ones((7, 7), np.uint8), iterations=2)
        inp = cv2.inpaint(roi, dil, 5, cv2.INPAINT_TELEA)
        out[y1:y2, x1:x2] = inp
    return out

def extract_best_frame(cap, fps, total_frames, target_sec):
    center_idx = min(total_frames - 1, max(0, int(round(target_sec * fps))))
    cap.set(cv2.CAP_PROP_POS_FRAMES, center_idx)
    ret, center_frame = cap.read()
    if not ret:
        raise RuntimeError(f"Failed at {target_sec}s")
    ref_top = center_frame[:int(center_frame.shape[0] * 0.55), :, :].astype(np.float32)
    best_frame = center_frame
    best_score = count_sub_glyphs(center_frame)
    best_idx = center_idx

    for offset in range(-18, 19):
        idx = center_idx + offset
        if 0 <= idx < total_frames:
            cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
            r, frm = cap.read()
            if not r:
                continue
            cand_top = frm[:int(frm.shape[0] * 0.55), :, :].astype(np.float32)
            if np.mean(np.abs(ref_top - cand_top)) < 14.0:
                sc = count_sub_glyphs(frm)
                if sc < best_score:
                    best_score = sc
                    best_frame = frm
                    best_idx = idx

    if best_score > 20:
        best_frame = clean_sub_band(best_frame)
    return best_frame, best_idx / fps, best_score

def main():
    all_sheets = []
    for part_num, (vid_name, timestamps) in EPISODES.items():
        vpath = os.path.join(SRC_DIR, vid_name)
        cap = cv2.VideoCapture(vpath)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        kf_dir = os.path.join(PROJ_DIR, f"part{part_num}", "keyframes")
        os.makedirs(kf_dir, exist_ok=True)

        thumbs = []
        for i, ts in enumerate(timestamps, 1):
            frm, actual_t, sc = extract_best_frame(cap, fps, total_frames, ts)
            out_p = os.path.join(kf_dir, f"KF_{i:02d}.jpg")
            cv2.imwrite(out_p, frm, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            print(f"Part {part_num} KF_{i:02d}.jpg -> t={actual_t:.2f}s (glyph_score={sc})")
            pil_t = Image.fromarray(cv2.cvtColor(frm, cv2.COLOR_BGR2RGB)).resize((360, 640))
            draw = ImageDraw.Draw(pil_t)
            draw.rectangle([8, 8, 220, 44], fill=(0, 0, 0))
            draw.text((14, 14), f"P{part_num} KF_{i:02d} ({actual_t:.1f}s)", fill=(255, 230, 100))
            thumbs.append(pil_t)

        if part_num == 1:
            # Extract CTA keyframe of Duke Eggplant looking straight at the camera
            frm_cta, t_cta, sc_cta = extract_best_frame(cap, fps, total_frames, 21.8)
            cta_p = os.path.join(PROJ_DIR, "02_keyframes", "KF_CTA_DUKE.jpg")
            cv2.imwrite(cta_p, frm_cta, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
            print(f"Saved CTA Keyframe: {cta_p} (t={t_cta:.2f}s)")

        cap.release()

        # Build 6-panel contact sheet for this part
        sheet = Image.new("RGB", (360 * 3, 640 * 2), (20, 20, 20))
        for idx, th in enumerate(thumbs):
            r, c = divmod(idx, 3)
            sheet.paste(th, (c * 360, r * 640))
        sheet_p = os.path.join(AUDIT_DIR, f"verify_kfs_part{part_num}.jpg")
        sheet.save(sheet_p, quality=90)
        all_sheets.append(sheet_p)

if __name__ == "__main__":
    main()
