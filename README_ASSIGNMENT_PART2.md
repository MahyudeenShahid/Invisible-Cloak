# Assignment 3: Algorithm Development and Evaluation (Part-2)

## Project Title: Invisible Cloak with AI Smart Segmentation

## Note
Preprocessing (Part-1) was completed in Assignment 2. This document focuses on Part-2: algorithm evaluation, problem analysis, and a new algorithm design. Some parts are implemented in the project code.

---

## Q1. Problem Identification and Algorithm Devised

### a) Evaluation of Existing Algorithms

We evaluated two baseline approaches using Python and OpenCV. Testing was done on a real webcam in three common situations: bright light, shadows, and mixed lighting. We judged each method on:

- Mask accuracy (does it capture the cloak/person correctly?)
- Edge quality (smooth edges vs jagged edges)
- Temporal stability (flicker between frames)
- Real-time speed (can it run near 30 FPS?)

#### 1) Color-Based HSV Masking (Traditional Method)
- **How it works:** Detect a color range (green/blue cloak) in HSV, then replace those pixels with a captured background.
- **Strengths:** Very fast, simple, and real-time.
- **Weaknesses:** Lighting changes shift HSV values. Fabric folds create darker tones that fall outside the range. Similar colors in the background can be mistaken as cloak.

#### 2) MediaPipe Selfie Segmentation (AI Method)
- **How it works:** A pre-trained model predicts a person mask and separates foreground from background.
- **Strengths:** Works without a special cloak and handles complex clothing.
- **Weaknesses:** Edges can be jagged and unstable in motion. Hair and fine details are often unstable. It removes the entire person, so it cannot create a partial invisibility effect like a cloak.

---

### b) Problems Identified

From the evaluation, we identified these real problems:

1) **Lighting sensitivity:** HSV masking fails in shadows and strong highlights.
2) **Mask holes and speckles:** Noise creates missing pixels and random dots in the cloak area.
3) **Edge jitter (flicker):** Masks change between frames even when the user is still.
4) **Hard edges:** The final blend looks digital because the boundary is too sharp.

---

## Our Devised Algorithm: Hybrid Intelligence Masking (HIM)

The goal of HIM is to make the invisibility effect stable, lighting-robust, and natural. It combines image normalization, refined morphology, and smoother blending.

### Detailed Algorithm Steps

1) **Stage 1: Illumination Normalization (Preprocessing)**
   - Convert the input to LAB color space.
   - Apply CLAHE to the L channel to reduce shadow and highlight issues.
   - Convert back to BGR before HSV thresholding.
   - **Why:** HSV thresholds remain stable when lighting is normalized.

2) **Stage 2: Primary Mask Generation**
   - Convert the preprocessed frame to HSV.
   - Apply multiple HSV ranges (if needed) to capture different tones of the cloak.
   - Combine these ranges with a logical OR operation.

3) **Stage 3: Structural Mask Refinement**
   - Apply morphological opening (remove noise speckles).
   - Apply morphological closing (fill holes inside the cloak).
   - Use elliptical kernels for organic cloth shapes.

4) **Stage 4: Edge Feathering**
   - Apply Gaussian blur to the refined mask.
   - Blend the foreground and background using the soft mask.
   - **Why:** This creates a realistic transition instead of a hard cut.

5) **Stage 5: Temporal Smoothing (Implemented)**
   - Keep a short history of masks.
   - Only change a pixel if most recent frames agree.
   - **Why:** This removes flicker without heavy computation.

6) **Stage 6: AI Validation (Implemented)**
   - Use the AI person mask to prevent masking the face or body when needed.
   - **Why:** This avoids accidental removal of human skin or clothing that matches cloak color.

---

## Implementation Status (In This Project)

### Implemented in code
The following parts of HIM are implemented in the refactored pipeline modules (not inside app.py directly):

- **Stage 1:** Preprocessing with Bilateral Filter and CLAHE in LAB (see [core/processing.py](core/processing.py)).
- **Stage 3:** Morphological opening and closing using elliptical kernels (see [core/processing.py](core/processing.py)).
- **Stage 4:** Edge feathering with Gaussian blur and alpha blending (see [core/processing.py](core/processing.py)).
- **Stage 5:** Temporal smoothing using a short mask history window (see [core/processing.py](core/processing.py)).
- **Stage 6:** AI + HSV fusion to suppress background false positives (see [core/camera.py](core/camera.py)).
- **Integration:** HSV masking runs on the preprocessed frame and uses the refined mask (see [core/camera.py](core/camera.py)).

---

## Implementation Snippet (From Project Code)

From [core/processing.py](core/processing.py):

```python
def preprocess_frame(frame):
   # Denoise while keeping edges
   denoised = cv2.bilateralFilter(frame, 9, 75, 75)

   # Normalize lighting
   lab = cv2.cvtColor(denoised, cv2.COLOR_BGR2LAB)
   l, a, b = cv2.split(lab)
   clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
   cl = clahe.apply(l)
   limg = cv2.merge((cl, a, b))
   enhanced = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
   return enhanced

def refine_mask(mask):
   # Elliptical kernels for organic shapes
   kernel_small = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
   kernel_large = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))

   mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_small, iterations=1)
   mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_large, iterations=2)
   mask = cv2.GaussianBlur(mask, (7, 7), 0)
   return mask
```

From [core/camera.py](core/camera.py):

```python
mask_f = mask.astype(np.float32) / 255.0
if state.get('use_ai_refine', False) and person_mask is not None:
   mask_f = mask_f * person_mask
mask_f = temporal_smooth_mask(mask_f, state.get('mask_history'), window)
```

---

## Conclusion
This detailed evaluation shows why basic HSV masking and plain AI segmentation are not enough in real-world conditions. Our HIM algorithm fixes the main weaknesses with preprocessing, refined morphology, temporal smoothing, and AI validation. The full pipeline is implemented in the project and addresses the real-world problems identified in our evaluation.
