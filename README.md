# 🧥 Invisible Cloak

> A real-time Harry Potter-style invisibility cloak effect powered by Python, OpenCV, and a modern web interface. Now with **Teleport Mode** — replace your cloak with a virtual scene like a beach, space, or city!

![InvisibleGif](https://github.com/abd-shoumik/Invisible-Cloak/blob/master/Invisible.gif)

---

## 📋 Table of Contents

- [How It Works](#how-it-works)
- [Modes](#modes)
- [Project Structure](#project-structure)
- [File Descriptions](#file-descriptions)
- [Setup & Installation](#setup--installation)
- [How to Run](#how-to-run)
- [Using the Web App](#using-the-web-app)
- [Requirements](#requirements)

---

## 💡 How It Works

The invisibility effect works using **HSV (Hue, Saturation, Value) color masking**:

1. A background frame is captured when the cloak is absent.
2. Each new frame is analyzed in HSV color space to detect the cloak color.
3. Pixels matching the cloak color are replaced with the selected background.
4. The result is a seamless effect — the person holding the cloak appears to vanish or teleport.

---

## 🎭 Modes

| Mode | Description |
|---|---|
| 🕶️ **Invisible** | Classic mode — cloak area shows the real captured background |
| 🌄 **Teleport** | Cloak area is replaced with a virtual scene (beach, space, city, etc.) |

In **Teleport mode**, pick from 5 built-in scenes or upload your own photo as the background.

---

## 🗂 Project Structure

```
Invisible-Cloak/
│
├── app.py                      ← Flask web app (main entry point)
├── cloak_gui.py                ← PyQt5 desktop GUI (alternative)
├── invisible.py                ← Classic command-line invisibility script
├── color_range_detector.py     ← Classic command-line HSV color picker
│
├── templates/
│   └── index.html              ← Web UI HTML template
│
├── static/
│   ├── style.css               ← Web UI stylesheet
│   ├── script.js               ← Web UI JavaScript logic
│   ├── backgrounds/            ← Built-in scene images (auto-generated)
│   └── uploads/                ← User-uploaded background images
│
├── requirements.txt            ← Python dependencies
├── profiles.json               ← Saved color profiles (auto-generated)
└── range.pickle                ← Saved HSV range (auto-generated)
```

---

## 📄 File Descriptions

### `app.py` — Flask Web Backend
The main entry point for the **web application**. It:
- Streams live webcam video to the browser via MJPEG (`/video_feed`).
- Auto-generates 5 built-in scene backgrounds on startup (beach, space, forest, sunset, city).
- Provides REST API endpoints for all actions:
  - `POST /capture_background` — Captures the background frame (Invisible mode).
  - `POST /toggle` — Starts or stops the effect.
  - `POST /set_hsv` — Updates the HSV color range.
  - `POST /set_effect` — Switches the visual effect (none/pixelate/blur/cartoon).
  - `POST /pick_color` — Auto-detects HSV values from a pixel clicked on the video.
  - `POST /set_bg_mode` — Switches between `invisible` and `virtual` modes.
  - `POST /set_builtin_bg` — Selects a built-in scene as virtual background.
  - `POST /upload_bg` — Uploads a custom image as virtual background.
  - `GET  /bg_status` — Returns current mode and active background name.
  - `GET  /profiles` — Returns all saved color profiles.
  - `POST /save_profile` — Saves current HSV settings as a named profile.
  - `POST /load_profile` — Loads a previously saved profile.
  - `POST /delete_profile` — Deletes a saved profile.
- Automatically opens the browser when started.
- Uses a background thread to safely share the latest video frame.

---

### `templates/index.html` — Web UI Layout
The HTML template served by Flask. It contains:
- A **live video feed** panel (click anywhere to auto-pick a color).
- A **mode toggle** (Invisible / Teleport).
- A **scene grid** (5 built-in backgrounds + custom upload) shown in Teleport mode.
- **HSV sliders** to fine-tune the cloak color range.
- A **sensitivity slider** to control color tolerance when clicking to pick.
- An **effect selector** (none, pixelate, blur, cartoon).
- Buttons to **capture background**, **start/stop** the effect.
- A **profiles panel** to save, load, and delete named color settings.
- A status badge (ON/OFF) in the header.

---

### `static/style.css` — Web UI Styles
A clean, minimal CSS stylesheet that gives the web app a modern look:
- Responsive two-column layout (video + controls panel).
- Mode toggle button group with active state styling.
- Scene grid tiles with background image previews.
- Dashed upload button and selected background indicator.
- Custom-styled sliders, buttons, cards, and profile list items.
- Color-coded status indicators and smooth hover/transition effects.

---

### `static/script.js` — Web UI JavaScript
Handles all frontend interactivity without any frameworks:
- Mode toggle switches between Invisible and Teleport panels.
- Scene tile clicks send the selected background to the server.
- Custom image upload via `FormData` and `/upload_bg`.
- Listens to slider changes and debounces HSV updates.
- Handles button clicks for capture, toggle, effect, and profiles.
- Sends `(x, y)` click coordinates to auto-pick HSV values from the video.
- Dynamically renders the saved profiles list with load/delete buttons.
- Updates slider labels and the status badge in real time.

---

### `cloak_gui.py` — PyQt5 Desktop GUI
A standalone desktop application (alternative to the web app). Features:
- Live camera preview inside the GUI window.
- Click on the preview image to auto-pick the cloak color.
- HSV sliders for manual fine-tuning.
- Effect dropdown (none, pixelate, blur, cartoon).
- Buttons to capture background, start/stop invisibility, and save HSV range to `range.pickle`.

---

### `invisible.py` — Classic Invisibility Script
The original command-line invisibility script. It:
- Loads HSV bounds from `range.pickle` (saved by `color_range_detector.py`).
- Captures the background over the first 60 frames.
- Applies the cloak mask each frame and blends background pixels.
- Supports effect switching with the `e` key and quit with `q`.
- Designed for users who prefer running scripts directly without a GUI.

---

### `color_range_detector.py` — Classic HSV Color Picker
A PyQt5 GUI tool for calibrating the cloak color. It:
- Opens a live webcam feed with an HSV preview overlay.
- Shows six sliders (H/S/V min and max) to define the color range.
- Renders a real-time preview of the mask on the video.
- Saves the chosen HSV range to `range.pickle` when you click **Save Range**.
- Used together with `invisible.py` in the classic workflow.

---

### `requirements.txt` — Python Dependencies

| Package | Purpose |
|---|---|
| `opencv-python` | Webcam capture, image processing, HSV masking |
| `opencv-contrib-python` | Extra OpenCV modules |
| `numpy` | Array operations for frame manipulation |
| `flask` | Web server and API for the web app |
| `PyQt5` | Desktop GUI (cloak_gui.py & color_range_detector.py) |
| `imutils` | Convenience functions for OpenCV |
| `scipy` | Scientific computing utilities |

---

## ⚙️ Setup & Installation

**Requirements:** Python 3.9 or newer (Python 3.13+ supported).

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

### 🕶️ Invisible Mode

| Step | Action |
|---|---|
| 1 | Stand away from the camera and click **Capture Background** |
| 2 | Click on your cloak in the live video to auto-detect its color |
| 3 | Adjust the **Sensitivity** slider if needed |
| 4 | Fine-tune the HSV sliders manually for better accuracy |
| 5 | Choose a fun **effect** (pixelate, blur, cartoon) |
| 6 | Save settings as a **profile** for reuse |
| 7 | Click **Start** and hold up your cloak! |

### 🌄 Teleport Mode

| Step | Action |
|---|---|
| 1 | Click **Teleport** in the mode toggle |
| 2 | Select a built-in scene (🏖️ Beach, 🚀 Space, 🌲 Forest, 🌅 Sunset, 🌃 City) |
| 3 | Or click **Upload your own** to use any photo as background |
| 4 | Click on your cloak in the live video to pick its color |
| 5 | Click **Start** — your cloak now shows the virtual scene! |

---

*Say **Evanesco** 🧙 and disappear — or teleport to the beach!* 🏖️

---

## 💡 How It Works

The invisibility effect works using **HSV (Hue, Saturation, Value) color masking**:

1. A background frame is captured when the cloak is absent.
2. Each new frame is analyzed in HSV color space to detect the cloak color.
3. Pixels matching the cloak color are replaced with the corresponding background pixels.
4. The result is a seamless "invisible" effect — the person holding the cloak appears to vanish.

---

## 🗂 Project Structure

```
Invisible-Cloak/
│
├── app.py                  ← Flask web app (main entry point)
├── cloak_gui.py            ← PyQt5 desktop GUI (alternative)
├── invisible.py            ← Classic command-line invisibility script
├── color_range_detector.py ← Classic command-line HSV color picker
│
├── templates/
│   └── index.html          ← Web UI HTML template
│
├── static/
│   ├── style.css           ← Web UI stylesheet
│   └── script.js           ← Web UI JavaScript logic
│
├── requirements.txt        ← Python dependencies
├── profiles.json           ← Saved color profiles (auto-generated)
└── range.pickle            ← Saved HSV range (auto-generated)
```

---

## 📄 File Descriptions

### `app.py` — Flask Web Backend
The main entry point for the **web application**. It:
- Streams live webcam video to the browser via MJPEG (`/video_feed`).
- Provides REST API endpoints for all actions:
  - `POST /capture_background` — Captures the background frame.
  - `POST /toggle` — Starts or stops the invisibility effect.
  - `POST /set_hsv` — Updates the HSV color range from sliders.
  - `POST /set_effect` — Switches the visual effect (none/pixelate/blur/cartoon).
  - `POST /pick_color` — Auto-detects HSV values from a clicked pixel on the video.
  - `GET /profiles` — Returns all saved color profiles.
  - `POST /save_profile` — Saves current HSV settings as a named profile.
  - `POST /load_profile` — Loads a previously saved profile.
  - `POST /delete_profile` — Deletes a saved profile.
- Automatically opens the browser when started.
- Uses a background thread to safely share the latest video frame.

---

### `templates/index.html` — Web UI Layout
The HTML template served by Flask. It contains:
- A **live video feed** panel (click anywhere to pick a color).
- **HSV sliders** to fine-tune the cloak color range.
- A **sensitivity slider** to control color tolerance when clicking to pick.
- An **effect selector** (none, pixelate, blur, cartoon).
- Buttons to **capture background**, **start/stop** the effect.
- A **profiles panel** to save, load, and delete named color settings.
- A status badge (ON/OFF) in the header.

---

### `static/style.css` — Web UI Styles
A clean, minimal CSS stylesheet that gives the web app a modern look:
- Responsive two-column layout (video + controls panel).
- Custom-styled sliders, buttons, cards, and profile list items.
- Color-coded status indicators and smooth hover transitions.

---

### `static/script.js` — Web UI JavaScript
Handles all frontend interactivity without any frameworks:
- Listens to slider changes and debounces HSV updates to the server.
- Handles button clicks for capture, toggle, effect selection, and profiles.
- Sends `(x, y)` click coordinates to the server to auto-pick HSV values.
- Dynamically renders the saved profiles list with load/delete buttons.
- Updates slider labels and the status badge in real time.

---

### `cloak_gui.py` — PyQt5 Desktop GUI
A standalone desktop application (alternative to the web app). Features:
- Live camera preview inside the GUI window.
- Click on the preview image to auto-pick the cloak color.
- HSV sliders for manual fine-tuning.
- Effect dropdown (none, pixelate, blur, cartoon).
- Buttons to capture background, start/stop invisibility, and save HSV range to `range.pickle`.

---

### `invisible.py` — Classic Invisibility Script
The original command-line invisibility script. It:
- Loads HSV bounds from `range.pickle` (saved by `color_range_detector.py`).
- Captures the background over the first 60 frames.
- Applies the cloak mask each frame and blends background pixels.
- Supports effect switching with the `e` key and quit with `q`.
- Designed for users who prefer running scripts directly without a GUI.

---

### `color_range_detector.py` — Classic HSV Color Picker
A PyQt5 GUI tool for calibrating the cloak color. It:
- Opens a live webcam feed with an HSV preview overlay.
- Shows six sliders (H/S/V min and max) to define the color range.
- Renders a real-time preview of the mask on the video.
- Saves the chosen HSV range to `range.pickle` when you click **Save Range**.
- Used together with `invisible.py` in the classic workflow.

---

### `requirements.txt` — Python Dependencies

| Package | Purpose |
|---|---|
| `opencv-python` | Webcam capture, image processing, HSV masking |
| `opencv-contrib-python` | Extra OpenCV modules |
| `numpy` | Array operations for frame manipulation |
| `flask` | Web server and API for the web app |
| `PyQt5` | Desktop GUI (cloak_gui.py & color_range_detector.py) |
| `imutils` | Convenience functions for OpenCV |
| `scipy` | Scientific computing utilities |

---

## ⚙️ Setup & Installation

**Requirements:** Python 3.9 or newer (Python 3.13+ supported).

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

| Step | Action |
|---|---|
| 1 | Stand away from the camera and click **Capture Background** |
| 2 | Click on your cloak in the live video to auto-detect its color |
| 3 | Adjust the **Sensitivity** slider if needed |
| 4 | Fine-tune the HSV sliders manually for better accuracy |
| 5 | Choose a fun **effect** (pixelate, blur, cartoon) |
| 6 | Save settings as a **profile** for reuse |
| 7 | Click **Start Invisibility** and hold up your cloak! |

---

*Say **Evanesco** 🧙 and disappear!*


