import cv2
import numpy as np
import pickle
import json
import os
import threading
import time
import webbrowser
from flask import Flask, Response, render_template, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

# MediaPipe for AI person segmentation (video-call style background removal)
# Uses the new Tasks API (mediapipe >= 0.10 — mp.solutions was removed)
try:
    import urllib.request as _urllib_req
    import mediapipe as mp
    from mediapipe.tasks import python as _mp_python
    from mediapipe.tasks.python import vision as _mp_vision

    _MODEL_URL  = ('https://storage.googleapis.com/mediapipe-models/'
                   'image_segmenter/selfie_segmenter/float16/latest/'
                   'selfie_segmenter.tflite')
    _MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                               'selfie_segmenter.tflite')

    if not os.path.exists(_MODEL_PATH):
        print('[INFO] Downloading MediaPipe selfie segmentation model...')
        _urllib_req.urlretrieve(_MODEL_URL, _MODEL_PATH)
        print(f'[INFO] Model saved → {_MODEL_PATH}')

    _seg_opts  = _mp_vision.ImageSegmenterOptions(
        base_options=_mp_python.BaseOptions(model_asset_path=_MODEL_PATH),
        running_mode=_mp_vision.RunningMode.IMAGE,
        output_confidence_masks=True,
    )
    _segmentor = _mp_vision.ImageSegmenter.create_from_options(_seg_opts)
    MEDIAPIPE_AVAILABLE = True
    print('[INFO] MediaPipe selfie segmentation ready.')
except Exception as _mp_err:
    print(f'[WARN] MediaPipe unavailable: {_mp_err}')
    MEDIAPIPE_AVAILABLE = False
    _segmentor = None

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit

state = {
    'cap': None,
    'background': None,
    'running': False,
    'hsv_min': [0, 0, 0],
    'hsv_max': [179, 255, 255],
    'effect': 'none',
    'frame': None,
    'raw_frame': None,        # latest unprocessed camera frame
    'lock': threading.Lock(),
    # bg_mode: 'invisible' | 'virtual' | 'smart'
    # 'smart' = AI person segmentation (like Zoom/Teams — no cloak needed)
    'bg_mode': 'invisible',
    'virtual_bg': None,       # numpy BGR image used for virtual/smart mode
    'virtual_bg_name': None,  # display name
    # Smart-mode background type: 'blur' | 'virtual' | 'solid'
    'smart_bg_type': 'blur',
    'solid_color': [0, 177, 64],   # BGR green default
    'smart_blur_amount': 25,       # Gaussian blur kernel size (must be odd)
}

EFFECTS = ['none', 'pixelate', 'blur', 'cartoon']
PROFILES_FILE = 'profiles.json'
BG_DIR = os.path.join('static', 'backgrounds')
UPLOAD_DIR = os.path.join('static', 'uploads')
os.makedirs(BG_DIR, exist_ok=True)
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ── Built-in scene generators ──────────────────────────────────────────────────
def _make_beach(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    # Sky: deep blue → pale blue
    for y in range(h * 55 // 100):
        t = y / (h * 55 // 100)
        img[y] = [int(200 - 80*t), int(140 + 60*t), int(255 - 30*t)]
    # Sea: teal band
    sea_top = h * 45 // 100
    sea_bot = h * 65 // 100
    for y in range(sea_top, sea_bot):
        t = (y - sea_top) / (sea_bot - sea_top)
        img[y] = [int(180 - 60*t), int(120 + 40*t), int(80 - 20*t)]
    # Sand: warm gradient
    for y in range(sea_bot, h):
        t = (y - sea_bot) / (h - sea_bot)
        img[y] = [int(80 + 40*t), int(160 + 30*t), int(200 + 30*t)]
    # Sun
    cv2.circle(img, (w*3//4, h//5), 40, (80, 220, 255), -1)
    cv2.circle(img, (w*3//4, h//5), 44, (100, 230, 255), 3)
    return img

def _make_space(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    # Deep space gradient
    for y in range(h):
        t = y / h
        img[y] = [int(40 + 20*t), int(5 + 10*t), int(20 + 10*t)]
    # Stars
    rng = np.random.default_rng(42)
    for _ in range(300):
        sx, sy = rng.integers(0, w), rng.integers(0, h)
        brightness = int(rng.integers(150, 255))
        cv2.circle(img, (sx, sy), 1, (brightness, brightness, brightness), -1)
    # Big star / planet
    cv2.circle(img, (w//4, h//3), 55, (20, 60, 160), -1)
    cv2.circle(img, (w//4, h//3), 55, (40, 80, 200), 3)
    # Saturn-like ring
    cv2.ellipse(img, (w//4, h//3), (85, 18), -20, 0, 360, (30, 70, 180), 3)
    return img

def _make_forest(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    # Sky at top
    for y in range(h//3):
        t = y / (h//3)
        img[y] = [int(200 - 50*t), int(220 - 30*t), int(255 - 60*t)]
    # Forest floor
    for y in range(h//3, h):
        t = (y - h//3) / (h * 2//3)
        img[y] = [int(20 + 10*t), int(80 - 30*t), int(10 + 5*t)]
    # Trees (simple triangles)
    for tx in range(40, w, 80):
        height = np.random.default_rng(tx).integers(100, 200)
        pts = np.array([[tx, h//3 + 60], [tx - 30, h//3 + 60 + height], [tx + 30, h//3 + 60 + height]], np.int32)
        cv2.fillPoly(img, [pts], (15, int(60 + tx % 40), 10))
    return img

def _make_sunset(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    colors = [(30, 30, 180), (20, 80, 230), (10, 140, 255), (20, 180, 255), (60, 120, 200), (80, 80, 120)]
    band = h // len(colors)
    for i, c in enumerate(colors):
        y0, y1 = i*band, min((i+1)*band, h)
        img[y0:y1] = c
    cv2.circle(img, (w//2, h//2), 55, (30, 150, 255), -1)
    return img

def _make_city(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    # Night sky
    for y in range(h):
        t = y / h
        img[y] = [int(40 + 20*t), int(20 + 15*t), int(10 + 5*t)]
    # Stars
    rng = np.random.default_rng(7)
    for _ in range(150):
        sx, sy = rng.integers(0, w), rng.integers(0, h//2)
        cv2.circle(img, (sx, sy), 1, (200, 200, 200), -1)
    # Buildings
    building_rng = np.random.default_rng(99)
    bx = 0
    while bx < w:
        bw = int(building_rng.integers(30, 70))
        bh = int(building_rng.integers(80, 280))
        by = h - bh
        shade = int(building_rng.integers(30, 70))
        cv2.rectangle(img, (bx, by), (bx + bw, h), (shade, shade, shade + 10), -1)
        # Windows
        for wy in range(by + 8, h - 10, 18):
            for wx in range(bx + 6, bx + bw - 6, 14):
                if building_rng.random() > 0.4:
                    cv2.rectangle(img, (wx, wy), (wx+6, wy+8), (0, 180, 220), -1)
        bx += bw + int(building_rng.integers(2, 8))
    return img

BUILTIN_SCENES = [
    ('beach',  '🏖️ Beach',  _make_beach),
    ('space',  '🚀 Space',  _make_space),
    ('forest', '🌲 Forest', _make_forest),
    ('sunset', '🌅 Sunset', _make_sunset),
    ('city',   '🌃 City',   _make_city),
]

def generate_builtin_backgrounds():
    for name, _, fn in BUILTIN_SCENES:
        path = os.path.join(BG_DIR, f'{name}.jpg')
        if not os.path.exists(path):
            cv2.imwrite(path, fn())

generate_builtin_backgrounds()


def get_cap():
    if state['cap'] is None or not state['cap'].isOpened():
        state['cap'] = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        state['cap'].set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        state['cap'].set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    return state['cap']


def apply_effect(img, effect):
    if effect == 'pixelate':
        h, w = img.shape[:2]
        temp = cv2.resize(img, (max(1, w // 16), max(1, h // 16)), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
    elif effect == 'blur':
        return cv2.GaussianBlur(img, (21, 21), 0)
    elif effect == 'cartoon':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 7)
        edges = cv2.adaptiveThreshold(
            gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 9, 9)
        color = cv2.bilateralFilter(img, 9, 250, 250)
        return cv2.bitwise_and(color, color, mask=edges)
    return img


# ── Dedicated camera reader thread ────────────────────────────────────────────
# All cap.read() calls happen here — no other code touches the camera.
def camera_thread_fn():
    cap = get_cap()
    while True:
        ret, raw = cap.read()
        if not ret:
            time.sleep(0.03)
            continue
        raw = cv2.flip(raw, 1)
        h_frame, w_frame = raw.shape[:2]

        processed = raw

        if state['running']:
            mode = state['bg_mode']

            # ── CLOAK mode (HSV masking) ─────────────────────────────────────
            if mode in ('invisible', 'virtual'):
                if mode == 'virtual' and state['virtual_bg'] is not None:
                    bg_src = cv2.resize(state['virtual_bg'], (w_frame, h_frame))
                elif mode == 'invisible' and state['background'] is not None:
                    bg_src = state['background']
                else:
                    bg_src = None

                if bg_src is not None:
                    hsv = cv2.cvtColor(raw, cv2.COLOR_BGR2HSV)
                    mask = cv2.inRange(hsv, np.array(state['hsv_min']), np.array(state['hsv_max']))
                    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, np.ones((5, 5), np.uint8), iterations=2)
                    mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, np.ones((5, 5), np.uint8), iterations=1)
                    mask = cv2.GaussianBlur(mask, (7, 7), 0)
                    mask3 = cv2.merge([mask, mask, mask]).astype(np.float32) / 255.0
                    raw_f   = raw.astype(np.float32)
                    bg_f    = bg_src.astype(np.float32)
                    blended = raw_f * (1 - mask3) + bg_f * mask3
                    processed = np.clip(blended, 0, 255).astype(np.uint8)
                    processed = apply_effect(processed, state['effect'])

            # ── SMART mode (MediaPipe AI segmentation — no cloak needed) ─────
            elif mode == 'smart' and MEDIAPIPE_AVAILABLE and _segmentor is not None:
                rgb = cv2.cvtColor(raw, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                result = _segmentor.segment(mp_img)
                if result.confidence_masks:
                    # confidence_masks[0]: float32 h×w, 1=person, 0=background
                    person_mask = result.confidence_masks[0].numpy_view().copy()
                    # Smooth the edges for a natural look
                    person_mask = cv2.GaussianBlur(person_mask, (15, 15), 0)
                    person_mask3 = np.stack([person_mask]*3, axis=2)  # h×w×3

                    bg_type = state['smart_bg_type']

                    if bg_type == 'blur':
                        k = state['smart_blur_amount']
                        k = k if k % 2 == 1 else k + 1  # must be odd
                        bg_layer = cv2.GaussianBlur(raw, (k, k), 0)

                    elif bg_type == 'virtual' and state['virtual_bg'] is not None:
                        bg_layer = cv2.resize(state['virtual_bg'], (w_frame, h_frame))

                    elif bg_type == 'solid':
                        bg_layer = np.full_like(raw, state['solid_color'], dtype=np.uint8)

                    else:
                        # Fallback to blur if nothing set
                        bg_layer = cv2.GaussianBlur(raw, (25, 25), 0)

                    raw_f    = raw.astype(np.float32)
                    bg_f     = bg_layer.astype(np.float32)
                    blended  = raw_f * person_mask3 + bg_f * (1 - person_mask3)
                    processed = np.clip(blended, 0, 255).astype(np.uint8)
                    processed = apply_effect(processed, state['effect'])

        with state['lock']:
            state['raw_frame'] = raw.copy()
            state['frame'] = processed.copy()


camera_thread = threading.Thread(target=camera_thread_fn, daemon=True)
camera_thread.start()


def generate_frames():
    # Just encode the latest processed frame — no cap.read() here
    while True:
        with state['lock']:
            frame = state.get('frame')
        if frame is None:
            time.sleep(0.03)
            continue
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        yield (b'--frame\r\nContent-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        time.sleep(0.01)


@app.route('/')
def index():
    scenes = [{'id': s[0], 'label': s[1]} for s in BUILTIN_SCENES]
    return render_template('index.html', effects=EFFECTS, scenes=scenes)


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/capture_background', methods=['POST'])
def capture_background():
    # Wait briefly to ensure camera thread has warmed up
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
    state['running'] = not state['running']
    return jsonify({'status': 'ok', 'running': state['running']})


@app.route('/set_bg_mode', methods=['POST'])
def set_bg_mode():
    mode = request.json.get('mode', 'invisible')
    if mode in ('invisible', 'virtual', 'smart'):
        state['bg_mode'] = mode
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
    state['solid_color'] = [b, g, r]   # store as BGR
    return jsonify({'status': 'ok', 'r': r, 'g': g, 'b': b})


@app.route('/smart_status', methods=['GET'])
def smart_status():
    return jsonify({
        'mediapipe_available': MEDIAPIPE_AVAILABLE,
        'smart_bg_type': state['smart_bg_type'],
        'smart_blur_amount': state['smart_blur_amount'],
        # Return solid color as RGB for display
        'solid_color_rgb': [state['solid_color'][2], state['solid_color'][1], state['solid_color'][0]],
        'virtual_bg_name': state['virtual_bg_name'],
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
    state['hsv_min'] = [int(data['h_min']), int(data['s_min']), int(data['v_min'])]
    state['hsv_max'] = [int(data['h_max']), int(data['s_max']), int(data['v_max'])]
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
        # Use raw (unprocessed) frame so we pick from the real camera image
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
    state['hsv_min'] = [result['h_min'], result['s_min'], result['v_min']]
    state['hsv_max'] = [result['h_max'], result['s_max'], result['v_max']]
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
        'hsv_min': state['hsv_min'],
        'hsv_max': state['hsv_max'],
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
            state['hsv_min'] = p['hsv_min']
            state['hsv_max'] = p['hsv_max']
            state['effect'] = p.get('effect', 'none')
            return jsonify({'status': 'ok', **p})
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


if __name__ == '__main__':
    # Auto-open browser after 1 second
    def open_browser():
        time.sleep(1)
        webbrowser.open('http://127.0.0.1:5000')
    threading.Thread(target=open_browser, daemon=True).start()
    app.run(debug=False, threaded=True)
