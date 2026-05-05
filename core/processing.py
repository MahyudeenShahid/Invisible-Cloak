import cv2
import numpy as np


def apply_effect(img, effect):
    if effect == 'pixelate':
        h, w = img.shape[:2]
        temp = cv2.resize(img, (max(1, w // 16), max(1, h // 16)), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
    if effect == 'blur':
        return cv2.GaussianBlur(img, (21, 21), 0)
    if effect == 'cartoon':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 7)
        edges = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9
        )
        color = cv2.bilateralFilter(img, 9, 250, 250)
        return cv2.bitwise_and(color, color, mask=edges)
    return img


def preprocess_frame(frame):
    """
    Advanced preprocessing for lighting and noise.
    1. Denoise with Bilateral Filter (preserves edges better than Gaussian)
    2. Normalize illumination using CLAHE in LAB color space
    """
    denoised = cv2.bilateralFilter(frame, 9, 75, 75)
    lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    return enhanced


def refine_mask(mask):
    """
    Advanced morphological cleanup for the binary cloak mask.
    Uses elliptical kernels for more organic shaping.
    """
    kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_large, iterations=2)
    mask = cv2.GaussianBlur(mask, (7, 7), 0)
    return mask


def build_hsv_mask(hsv, color_ranges):
    mask = np.zeros(hsv.shape[:2], np.uint8)
    for cr in color_ranges:
        _m = cv2.inRange(hsv, np.array(cr['hsv_min']), np.array(cr['hsv_max']))
        mask = cv2.bitwise_or(mask, _m)
    return mask


def temporal_smooth_mask(mask_f, history, window):
    if history is None:
        return mask_f
    try:
        window = int(window)
    except (TypeError, ValueError):
        window = 1
    if window <= 1:
        return mask_f
    history.append(mask_f)
    if len(history) < window:
        return mask_f
    stacked = np.stack(list(history), axis=2)
    return np.mean(stacked, axis=2).astype(np.float32)
