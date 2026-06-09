import time
import cv2
import numpy as np

from .processing import (
    apply_effect,
    preprocess_frame,
    refine_mask,
    build_hsv_mask,
    temporal_smooth_mask,
)
from .mediapipe_utils import segment_person_mask


def get_cap(state):
    if state.get('cap') is None or not state['cap'].isOpened():
        state['cap'] = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        state['cap'].set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        state['cap'].set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return state['cap']


def _temporal_window(state):
    try:
        return max(1, int(state.get('temporal_window', 1)))
    except (TypeError, ValueError):
        return 1


def _get_person_mask(raw, state, segmentor, mp, mediapipe_available):
    if not mediapipe_available or segmentor is None or mp is None:
        return None
    if not (state.get('bg_mode') == 'smart' or state.get('use_ai_refine', False)):
        return None
    mask = segment_person_mask(segmentor, mp, raw)
    if mask is None:
        return None
    window = _temporal_window(state)
    mask = temporal_smooth_mask(mask.astype(np.float32), state.get('person_mask_history'), window)
    mask = cv2.GaussianBlur(mask, (15, 15), 0)
    return mask


def camera_thread_fn(state, segmentor, mp, mediapipe_available):
    cap = get_cap(state)
    while True:
        ret, raw = cap.read()
        if not ret:
            time.sleep(0.03)
            continue
        raw = cv2.flip(raw, 1)
        h_frame, w_frame = raw.shape[:2]

        pp_raw = preprocess_frame(raw)
        processed = raw

        if state['running']:
            person_mask = _get_person_mask(raw, state, segmentor, mp, mediapipe_available)
            window = _temporal_window(state)
            mode = state['bg_mode']

            if mode in ('invisible', 'virtual'):
                if mode == 'virtual' and state['virtual_bg'] is not None:
                    bg_src = cv2.resize(state['virtual_bg'], (w_frame, h_frame))
                elif mode == 'invisible' and state['background'] is not None:
                    bg_src = state['background']
                else:
                    bg_src = None

                if bg_src is not None:
                    hsv = cv2.cvtColor(pp_raw, cv2.COLOR_BGR2HSV)
                    mask = build_hsv_mask(hsv, state['color_ranges'])
                    mask = refine_mask(mask)

                    mask_f = mask.astype(np.float32) / 255.0
                    if state.get('use_ai_refine', False) and person_mask is not None:
                        mask_f = mask_f * (1.0 - person_mask)
                    mask_f = temporal_smooth_mask(mask_f, state.get('mask_history'), window)

                    mask3 = np.stack([mask_f, mask_f, mask_f], axis=2)
                    raw_f = raw.astype(np.float32)
                    bg_f = bg_src.astype(np.float32)
                    blended = raw_f * (1 - mask3) + bg_f * mask3
                    processed = np.clip(blended, 0, 255).astype(np.uint8)
                    processed = apply_effect(processed, state['effect'])

            elif mode == 'smart' and mediapipe_available and segmentor is not None:
                if person_mask is None:
                    person_mask = _get_person_mask(raw, state, segmentor, mp, mediapipe_available)
                if person_mask is not None:
                    person_mask3 = np.stack([person_mask, person_mask, person_mask], axis=2)

                    bg_type = state['smart_bg_type']
                    if bg_type == 'blur':
                        k = state['smart_blur_amount']
                        k = k if k % 2 == 1 else k + 1
                        bg_layer = cv2.GaussianBlur(raw, (k, k), 0)
                    elif bg_type == 'virtual' and state['virtual_bg'] is not None:
                        bg_layer = cv2.resize(state['virtual_bg'], (w_frame, h_frame))
                    elif bg_type == 'solid':
                        bg_layer = np.full_like(raw, state['solid_color'], dtype=np.uint8)
                    else:
                        bg_layer = cv2.GaussianBlur(raw, (25, 25), 0)

                    raw_f = raw.astype(np.float32)
                    bg_f = bg_layer.astype(np.float32)
                    blended = raw_f * person_mask3 + bg_f * (1 - person_mask3)
                    processed = np.clip(blended, 0, 255).astype(np.uint8)
                    processed = apply_effect(processed, state['effect'])

        with state['lock']:
            state['raw_frame'] = raw.copy()
            state['pp_frame'] = pp_raw.copy()
            state['frame'] = processed.copy()


def generate_frames(state):
    while True:
        with state['lock']:
            frame = state.get('frame')
        if frame is None:
            time.sleep(0.03)
            continue
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.01)
