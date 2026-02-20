# How to Run Invisible Cloak

## 1. Install Dependencies

First, make sure you have Python 3.9 or newer (Python 3.13+ supported). Then, install all required packages:

```sh
pip install -r requirements.txt
```

## 2. Launch the All-in-One GUI

Simply run:

```sh
python cloak_gui.py
```

### Features in the GUI:
- Adjust HSV sliders to select the cloak color
- Choose fun effects (none, pixelate, blur, cartoon)
- Capture the background (click 'Capture Background' with no one in front of the camera)
- Start/stop the invisibility effect
- Save your HSV color range for future use

## 3. (Optional) Advanced Usage

You can still use the classic scripts if you want:

- For HSV color selection (classic):
  ```sh
  python color_range_detector.py
  ```
- For invisibility effect (classic):
  ```sh
  python invisible.py
  ```

## Troubleshooting
- Make sure your webcam is connected and not used by another app.
- If you see errors about missing packages, re-run the pip install command.
- For best results, use a solid-colored cloak and a well-lit background.

---
Enjoy your magic cloak!