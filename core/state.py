import os
import threading
from collections import deque

EFFECTS = ['none', 'pixelate', 'blur', 'cartoon']
PROFILES_FILE = 'profiles.json'
BG_DIR = os.path.join('static', 'backgrounds')
UPLOAD_DIR = os.path.join('static', 'uploads')
TEMPORAL_WINDOW_DEFAULT = 4
TEMPORAL_WINDOW_MAX = 12


def ensure_storage_dirs():
    os.makedirs(BG_DIR, exist_ok=True)
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def create_state():
    return {
        'cap': None,
        'background': None,
        'running': False,
        'color_ranges': [
            {'hsv_min': [0, 0, 0], 'hsv_max': [0, 0, 0]},
        ],
        'active_range_idx': 0,
        'effect': 'none',
        'frame': None,
        'raw_frame': None,
        'lock': threading.Lock(),
        # bg_mode: 'invisible' | 'virtual' | 'smart'
        'bg_mode': 'invisible',
        'virtual_bg': None,
        'virtual_bg_name': None,
        'smart_bg_type': 'blur',
        'solid_color': [0, 177, 64],
        'smart_blur_amount': 25,
        # Temporal smoothing and AI refinement
        'mask_history': deque(maxlen=TEMPORAL_WINDOW_MAX),
        'person_mask_history': deque(maxlen=TEMPORAL_WINDOW_MAX),
        'temporal_window': TEMPORAL_WINDOW_DEFAULT,
        'use_ai_refine': True,
    }


def reset_temporal_state(state):
    if 'mask_history' in state:
        state['mask_history'].clear()
    if 'person_mask_history' in state:
        state['person_mask_history'].clear()
