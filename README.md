# 🧥 Invisible Cloak

> A real-time Harry Potter-style invisibility cloak effect powered by Python, OpenCV, and a modern web interface. Now with **Virtual Mode**, **Smart AI Segmentation**, and **multi-color cloak support** (up to 6 colors at once).

![InvisibleGif](https://github.com/abd-shoumik/Invisible-Cloak/blob/master/Invisible.gif)

---

## 📋 Table of Contents

- [How It Works](#how-it-works)
- [Modes](#modes)
- [Pipeline Controls](#pipeline-controls)
- [Project Structure](#project-structure)
- [File Descriptions](#file-descriptions)
- [Setup & Installation](#setup--installation)
- [How to Run](#how-to-run)
- [Using the Web App](#using-the-web-app)
- [Requirements](#requirements)

---

## 💡 How It Works

The invisibility effect is built on a robust HSV + AI pipeline:

1. Capture a background frame when the cloak is not visible.
2. Preprocess each frame (denoise + CLAHE) for stable lighting.
3. Convert to HSV and detect **one or more cloak colors**.
4. Refine the mask with morphology and soft edge blending.
5. Optionally apply **temporal smoothing** to reduce flicker.
6. Optionally use **AI refine** (person mask) to suppress false positives.
7. Blend the cloak pixels with the selected background.

---

## 🎭 Modes

| Mode | Description |
|---|---|
| 🕶️ **Cloak** | Classic invisibility using a captured background. Supports **multi-color cloak**. |
| 🌄 **Virtual** | Same cloak mask, but replaced with a virtual scene. |
| 🤖 **Smart AI** | No cloak needed. Uses MediaPipe person segmentation with blur/virtual/solid backgrounds. |

---

## ⚙️ Pipeline Controls

These controls appear in **Smart AI** mode and are disabled while the system is running:

- **AI refine mask:** Uses the AI person mask to clean HSV results.
- **Temporal smoothing window (1–12):** Higher values reduce flicker but add slight delay.

---

## 🗂 Project Structure

```
Invisible-Cloak/
│
├── app.py                      ← Flask web app (main entry point)
├── core/                       ← Processing pipeline and utilities
│   ├── camera.py               ← Camera thread + processing pipeline
│   ├── processing.py           ← Preprocess, mask refine, smoothing, effects
│   ├── mediapipe_utils.py      ← MediaPipe model init + segmentation
│   ├── scenes.py               ← Built-in background generators
│   └── state.py                ← Shared state + constants
│
├── templates/
│   └── index.html              ← Web UI layout
│
├── static/
│   ├── style.css               ← Web UI stylesheet
│   ├── script.js               ← Web UI JavaScript
│   ├── backgrounds/            ← Built-in scene images (auto-generated)
│   └── uploads/                ← User-uploaded scenes
│
├── cloak_gui.py                ← PyQt5 desktop GUI (alternative)
├── invisible.py                ← Classic command-line invisibility script
├── color_range_detector.py     ← Classic HSV color picker
│
├── selfie_segmenter.tflite     ← MediaPipe model (auto-downloaded)
├── profiles.json               ← Saved color profiles (auto-generated)
├── requirements.txt            ← Python dependencies
└── range.pickle                ← Saved HSV range (auto-generated)
```

---

## 📄 File Descriptions

### `app.py` — Flask Web Backend
Main entry point for the **web app**. It:
- Streams video to the browser via MJPEG (`/video_feed`).
- Handles mode switching and background selection.
- Exposes REST endpoints including:
  - `POST /capture_background`
  - `POST /toggle`
  - `POST /set_bg_mode`
  - `POST /set_smart_bg_type`
  - `POST /set_solid_color`
  - `POST /set_builtin_bg`
  - `POST /upload_bg`
  - `GET  /bg_status`
  - `GET  /smart_status`
  - `GET  /pipeline_status`
  - `POST /set_pipeline`
  - `POST /set_hsv`
  - `POST /pick_color`
  - `POST /set_effect`
  - `GET  /profiles`
  - `POST /save_profile`
  - `POST /load_profile`
  - `POST /delete_profile`

### `core/` — Processing Pipeline
- `camera.py`: Dedicated camera thread + mode handling (cloak, virtual, smart AI).
- `processing.py`: Preprocessing, HSV mask, temporal smoothing, and effects.
- `mediapipe_utils.py`: MediaPipe model download/init and segmentation helper.
- `scenes.py`: Built-in background generators (beach, space, forest, sunset, city).
- `state.py`: Shared state and constants.

### `templates/index.html` — Web UI Layout
Contains:
- Live video feed and fullscreen toggle.
- Mode selector (Cloak / Virtual / Smart AI).
- Smart AI controls (blur/scene/solid).
- Pipeline controls (AI refine toggle, temporal window slider).
- Multi-color cloak chips and HSV sliders.
- Effects, profiles, and status badge.

### `static/style.css` — Web UI Styles
Modern glassmorphism theme with:
- Card-based layout.
- Custom sliders and toggles.
- Smart AI tabs and color presets.
- Responsive layout and animations.

### `static/script.js` — Web UI Logic
Handles:
- Mode switching and panel visibility.
- Background selection and upload.
- HSV slider sync and multi-color chips.
- Smart AI settings and pipeline toggles.
- Profiles load/save/delete.

---

## ⚙️ Setup & Installation

**Requirements:** Python 3.9+ (3.13+ supported)

```sh
# 1. Clone the repository
git clone https://github.com/MahyudeenShahid/Invisible-Cloak.git
cd Invisible-Cloak

# 2. Create a virtual environment
python -m venv .venv

# 3. Activate it
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt
```

---

## 🚀 How to Run

### Option 1 — Web App (Recommended)
```sh
python app.py
```
Browser opens automatically at **http://127.0.0.1:5000**

### Option 2 — Desktop GUI
```sh
python cloak_gui.py
```

### Option 3 — Classic Scripts
```sh
# Step 1: Pick your cloak color
python color_range_detector.py

# Step 2: Run the invisibility effect
python invisible.py
```

---

## 🌐 Using the Web App

### 🕶️ Cloak Mode (Multi-Color)

| Step | Action |
|---|---|
| 1 | Stand away from the camera and click **Capture Background** |
| 2 | Click on your cloak in the live video to auto-detect its color |
| 3 | Click **＋ Add Color** to add more cloak colors (up to 6) |
| 4 | Adjust **Sensitivity** and fine-tune HSV sliders if needed |
| 5 | Select an effect (pixelate, blur, cartoon) |
| 6 | Save settings as a profile for reuse |
| 7 | Click **Initialize System** to start |

### 🌄 Virtual Mode

| Step | Action |
|---|---|
| 1 | Switch to **Virtual** mode |
| 2 | Choose a built-in scene or upload a custom background |
| 3 | Pick cloak colors like in Cloak mode |
| 4 | Start the system |

### 🤖 Smart AI Mode

| Step | Action |
|---|---|
| 1 | Switch to **Smart AI** mode |
| 2 | Choose **Blur**, **Scene**, or **Solid** background type |
| 3 | (Optional) Enable **AI refine mask** and adjust **Temporal smoothing** |
| 4 | Start the system |

---

## ✅ Requirements

| Package | Purpose |
|---|---|
| `opencv-python` | Webcam capture, image processing, HSV masking |
| `opencv-contrib-python` | Extra OpenCV modules |
| `numpy` | Array operations |
| `flask` | Web server and API |
| `mediapipe` | Smart AI segmentation |
| `PyQt5` | Desktop GUI tools |
| `imutils` | Convenience functions |
| `scipy` | Scientific computing utilities |

---

*Say **Evanesco** 🧙 and disappear — now with AI precision!*
