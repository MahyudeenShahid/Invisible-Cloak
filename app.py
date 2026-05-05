import cv2
import numpy as np
import json
import os
import threading
import time
import webbrowser
from flask import Flask, Response, render_template, request, jsonify
from werkzeug.utils import secure_filename

from core.state import (
    create_state,
    ensure_storage_dirs,
    reset_temporal_state,
    EFFECTS,
    PROFILES_FILE,
    BG_DIR,
    UPLOAD_DIR,
    TEMPORAL_WINDOW_MAX,
)
from core.mediapipe_utils import init_segmentor
from core.scenes import get_scene_factories, generate_builtin_backgrounds
from core.camera import camera_thread_fn, generate_frames

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

state = create_state()
ensure_storage_dirs()

_segmentor, MEDIAPIPE_AVAILABLE, _mp = init_segmentor()

SCENE_FACTORIES = get_scene_factories()
BUILTIN_SCENES = [
    ('beach', '🏖️ Beach', SCENE_FACTORIES['beach']),
    ('space', '🚀 Space', SCENE_FACTORIES['space']),
    ('forest', '🌲 Forest', SCENE_FACTORIES['forest']),
    ('sunset', '🌅 Sunset', SCENE_FACTORIES['sunset']),
    ('city', '🌃 City', SCENE_FACTORIES['city']),
]

generate_builtin_backgrounds(BG_DIR, SCENE_FACTORIES)

camera_thread = threading.Thread(
    target=camera_thread_fn,
    args=(state, _segmentor, _mp, MEDIAPIPE_AVAILABLE),
    daemon=True,
)
camera_thread.start()


def _parse_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in ('1', 'true', 'yes', 'on')
    return False


@app.route('/')
def index():
    scenes = [{'id': s[0], 'label': s[1]} for s in BUILTIN_SCENES]
    return render_template('index.html', effects=EFFECTS, scenes=scenes)


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(state), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/capture_background', methods=['POST'])
def capture_background():
    time.sleep(0.5)
    with state['lock']:
        raw = state.get('raw_frame')
    if raw is not None:
        state['background'] = raw.copy()
        return jsonify({'status': 'ok', 'message': 'Background captured!'})
    return jsonify({'status': 'error', 'message': 'Camera not ready yet, try again'})


@app.route('/toggle', methods=['POST'])
def toggle():
    if state['bg_mode'] == 'invisible' and state['background'] is None:
        return jsonify({'status': 'error', 'message': 'Capture background first!'})
    if state['bg_mode'] == 'virtual' and state['virtual_bg'] is None:
        return jsonify({'status': 'error', 'message': 'Select a virtual background first!'})
    if state['bg_mode'] == 'smart' and not MEDIAPIPE_AVAILABLE:
        return jsonify({'status': 'error', 'message': 'MediaPipe not available. Run: pip install mediapipe'})
    if state['bg_mode'] == 'smart' and state['smart_bg_type'] == 'virtual' and state['virtual_bg'] is None:
        return jsonify({'status': 'error', 'message': 'Select a virtual background first!'})
    if not state['running']:
        reset_temporal_state(state)
    state['running'] = not state['running']
    return jsonify({'status': 'ok', 'running': state['running']})


@app.route('/set_bg_mode', methods=['POST'])
def set_bg_mode():
    mode = request.json.get('mode', 'invisible')
    if mode in ('invisible', 'virtual', 'smart'):
        if mode != state['bg_mode']:
            state['bg_mode'] = mode
            reset_temporal_state(state)
        if state['running']:
            state['running'] = False
    return jsonify({
        'status': 'ok',
        'mode': state['bg_mode'],
        'mediapipe_available': MEDIAPIPE_AVAILABLE,
    })


@app.route('/set_smart_bg_type', methods=['POST'])
def set_smart_bg_type():
    """Set smart-mode background type: blur | virtual | solid"""
    bg_type = request.json.get('type', 'blur')
    if bg_type in ('blur', 'virtual', 'solid'):
        state['smart_bg_type'] = bg_type
    blur_amount = request.json.get('blur_amount')
    if blur_amount is not None:
        k = max(3, int(blur_amount))
        state['smart_blur_amount'] = k if k % 2 == 1 else k + 1
    return jsonify({'status': 'ok', 'smart_bg_type': state['smart_bg_type']})


@app.route('/set_solid_color', methods=['POST'])
def set_solid_color():
    """Set solid background color (r, g, b) for smart mode"""
    data = request.json
    r = int(data.get('r', 0))
    g = int(data.get('g', 177))
    b = int(data.get('b', 64))
    state['solid_color'] = [b, g, r]
    return jsonify({'status': 'ok', 'r': r, 'g': g, 'b': b})


@app.route('/smart_status', methods=['GET'])
def smart_status():
    return jsonify({
        'mediapipe_available': MEDIAPIPE_AVAILABLE,
        'smart_bg_type': state['smart_bg_type'],
        'smart_blur_amount': state['smart_blur_amount'],
        'solid_color_rgb': [state['solid_color'][2], state['solid_color'][1], state['solid_color'][0]],
        'virtual_bg_name': state['virtual_bg_name'],
    })


@app.route('/pipeline_status', methods=['GET'])
def pipeline_status():
    return jsonify({
        'use_ai_refine': state.get('use_ai_refine', False),
        'temporal_window': state.get('temporal_window', 1),
        'mediapipe_available': MEDIAPIPE_AVAILABLE,
    })


@app.route('/set_pipeline', methods=['POST'])
def set_pipeline():
    data = request.json or {}
    changed = False

    if 'use_ai_refine' in data:
        new_val = _parse_bool(data.get('use_ai_refine'))
        if new_val != state.get('use_ai_refine', False):
            state['use_ai_refine'] = new_val
            changed = True

    if 'temporal_window' in data:
        try:
            window = int(data.get('temporal_window'))
        except (TypeError, ValueError):
            window = state.get('temporal_window', 1)
        window = max(1, min(window, TEMPORAL_WINDOW_MAX))
        if window != state.get('temporal_window', 1):
            state['temporal_window'] = window
            changed = True

    if changed:
        reset_temporal_state(state)

    return jsonify({
        'status': 'ok',
        'use_ai_refine': state.get('use_ai_refine', False),
        'temporal_window': state.get('temporal_window', 1),
    })


@app.route('/set_builtin_bg', methods=['POST'])
def set_builtin_bg():
    name = request.json.get('name')
    for scene_id, label, fn in BUILTIN_SCENES:
        if scene_id == name:
            path = os.path.join(BG_DIR, f'{name}.jpg')
            img = cv2.imread(path)
            if img is None:
                img = fn()
                cv2.imwrite(path, img)
            state['virtual_bg'] = img
            state['virtual_bg_name'] = label
            return jsonify({'status': 'ok', 'name': label})
    return jsonify({'status': 'error', 'message': 'Scene not found'})


@app.route('/upload_bg', methods=['POST'])
def upload_bg():
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'No file uploaded'})
    f = request.files['file']
    if f.filename == '':
        return jsonify({'status': 'error', 'message': 'Empty filename'})
    filename = secure_filename(f.filename)
    save_path = os.path.join(UPLOAD_DIR, filename)
    f.save(save_path)
    img = cv2.imread(save_path)
    if img is None:
        return jsonify({'status': 'error', 'message': 'Invalid image file'})
    state['virtual_bg'] = img
    state['virtual_bg_name'] = filename
    return jsonify({'status': 'ok', 'name': filename, 'url': f'/static/uploads/{filename}'})


@app.route('/bg_status', methods=['GET'])
def bg_status():
    return jsonify({
        'bg_mode': state['bg_mode'],
        'virtual_bg_name': state['virtual_bg_name'],
        'has_virtual_bg': state['virtual_bg'] is not None,
    })


@app.route('/set_hsv', methods=['POST'])
def set_hsv():
    data = request.json
    idx = int(data.get('idx', state['active_range_idx']))
    idx = max(0, min(idx, len(state['color_ranges']) - 1))
    state['color_ranges'][idx]['hsv_min'] = [int(data['h_min']), int(data['s_min']), int(data['v_min'])]
    state['color_ranges'][idx]['hsv_max'] = [int(data['h_max']), int(data['s_max']), int(data['v_max'])]
    return jsonify({'status': 'ok'})


@app.route('/set_effect', methods=['POST'])
def set_effect():
    effect = request.json.get('effect', 'none')
    if effect in EFFECTS:
        state['effect'] = effect
    return jsonify({'status': 'ok'})


@app.route('/pick_color', methods=['POST'])
def pick_color():
    data = request.json
    with state['lock']:
        frame = state.get('raw_frame')
        if frame is None:
            frame = state.get('frame')
    if frame is None:
        return jsonify({'status': 'error', 'message': 'No frame available'})
    h_frame, w_frame = frame.shape[:2]
    x = int(float(data['x']) * w_frame)
    y = int(float(data['y']) * h_frame)
    x = max(0, min(x, w_frame - 1))
    y = max(0, min(y, h_frame - 1))
    bgr = frame[y, x]
    hsv = cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
    h, s, v = int(hsv[0]), int(hsv[1]), int(hsv[2])
    sens = int(data.get('sensitivity', 20))
    result = {
        'h_min': max(0, h - sens),
        's_min': max(0, s - sens * 2),
        'v_min': max(0, v - sens * 2),
        'h_max': min(179, h + sens),
        's_max': min(255, s + sens * 2),
        'v_max': min(255, v + sens * 2),
        'hsv': [h, s, v],
    }
    idx = state['active_range_idx']
    state['color_ranges'][idx]['hsv_min'] = [result['h_min'], result['s_min'], result['v_min']]
    state['color_ranges'][idx]['hsv_max'] = [result['h_max'], result['s_max'], result['v_max']]
    return jsonify({'status': 'ok', **result})


@app.route('/profiles', methods=['GET'])
def get_profiles():
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE) as f:
            return jsonify(json.load(f))
    return jsonify({})


@app.route('/save_profile', methods=['POST'])
def save_profile():
    name = request.json.get('name', 'default').strip()
    if not name:
        return jsonify({'status': 'error', 'message': 'Profile name cannot be empty'})
    profiles = {}
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE) as f:
            profiles = json.load(f)
    profiles[name] = {
        'color_ranges': state['color_ranges'],
        'hsv_min': state['color_ranges'][0]['hsv_min'],
        'hsv_max': state['color_ranges'][0]['hsv_max'],
        'effect': state['effect'],
    }
    with open(PROFILES_FILE, 'w') as f:
        json.dump(profiles, f, indent=2)
    return jsonify({'status': 'ok', 'profiles': profiles})


@app.route('/load_profile', methods=['POST'])
def load_profile():
    name = request.json.get('name')
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE) as f:
            profiles = json.load(f)
        if name in profiles:
            p = profiles[name]
            if 'color_ranges' in p:
                state['color_ranges'] = p['color_ranges']
            else:
                state['color_ranges'] = [
                    {'hsv_min': p.get('hsv_min', [0, 0, 0]), 'hsv_max': p.get('hsv_max', [179, 255, 255])}
                ]
            state['active_range_idx'] = 0
            state['effect'] = p.get('effect', 'none')
            return jsonify({'status': 'ok', 'color_ranges': state['color_ranges'], 'active_idx': 0, **p})
    return jsonify({'status': 'error', 'message': 'Profile not found'})


@app.route('/delete_profile', methods=['POST'])
def delete_profile():
    name = request.json.get('name')
    if os.path.exists(PROFILES_FILE):
        with open(PROFILES_FILE) as f:
            profiles = json.load(f)
        if name in profiles:
            del profiles[name]
            with open(PROFILES_FILE, 'w') as f:
                json.dump(profiles, f, indent=2)
            return jsonify({'status': 'ok', 'profiles': profiles})
    return jsonify({'status': 'error', 'message': 'Profile not found'})


@app.route('/color_ranges', methods=['GET'])
def get_color_ranges():
    return jsonify({
        'status': 'ok',
        'ranges': state['color_ranges'],
        'active_idx': state['active_range_idx'],
    })


@app.route('/add_color_range', methods=['POST'])
def add_color_range():
    if len(state['color_ranges']) >= 6:
        return jsonify({'status': 'error', 'message': 'Maximum 6 colors allowed'})
    state['color_ranges'].append({'hsv_min': [0, 0, 0], 'hsv_max': [179, 255, 255]})
    new_idx = len(state['color_ranges']) - 1
    state['active_range_idx'] = new_idx
    return jsonify({'status': 'ok', 'ranges': state['color_ranges'], 'active_idx': new_idx})


@app.route('/delete_color_range', methods=['POST'])
def delete_color_range():
    idx = int(request.json.get('idx', 0))
    if len(state['color_ranges']) <= 1:
        return jsonify({'status': 'error', 'message': 'Must keep at least one color'})
    state['color_ranges'].pop(idx)
    state['active_range_idx'] = max(0, min(state['active_range_idx'], len(state['color_ranges']) - 1))
    return jsonify({'status': 'ok', 'ranges': state['color_ranges'], 'active_idx': state['active_range_idx']})


@app.route('/set_active_range', methods=['POST'])
def set_active_range():
    idx = int(request.json.get('idx', 0))
    idx = max(0, min(idx, len(state['color_ranges']) - 1))
    state['active_range_idx'] = idx
    cr = state['color_ranges'][idx]
    return jsonify({'status': 'ok', 'active_idx': idx, **cr})


if __name__ == '__main__':
    def open_browser():
        time.sleep(1)
        webbrowser.open('http://127.0.0.1:5000')

    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, threaded=True)
