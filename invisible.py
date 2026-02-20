
import cv2
import time
import numpy as np
import pickle

EFFECTS = ['none', 'pixelate', 'blur', 'cartoon']

def apply_effect(img, effect):
    if effect == 'pixelate':
        h, w = img.shape[:2]
        temp = cv2.resize(img, (w//16, h//16), interpolation=cv2.INTER_LINEAR)
        return cv2.resize(temp, (w, h), interpolation=cv2.INTER_NEAREST)
    elif effect == 'blur':
        return cv2.GaussianBlur(img, (21, 21), 0)
    elif effect == 'cartoon':
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.medianBlur(gray, 7)
        edges = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                      cv2.THRESH_BINARY, 9, 9)
        color = cv2.bilateralFilter(img, 9, 250, 250)
        cartoon = cv2.bitwise_and(color, color, mask=edges)
        return cartoon
    return img

def main():
    # Load HSV color range
    with open('range.pickle','rb') as f:
        t = pickle.load(f)
    lower_red = np.array([t[0],t[1],t[2]])
    upper_red = np.array([t[3],t[4],t[5]])

    cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
    if not cap.isOpened():
        print("Error: Cannot open webcam.")
        return
    time.sleep(2)

    # Capture background
    for i in range(60):
        ret, background = cap.read()
        if not ret:
            print("Error: Failed to capture background.")
            return
    background = np.flip(background, axis=1)

    effect_idx = 0
    print("Press 'e' to change effect. Current effect:", EFFECTS[effect_idx])

    while True:
        ret, img = cap.read()
        if not ret:
            print("Error: Failed to read frame.")
            break
        img = np.flip(img, axis=1)
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        mask1 = cv2.inRange(hsv, lower_red, upper_red)
        mask1 = cv2.morphologyEx(mask1, cv2.MORPH_OPEN, np.ones((3,3), np.uint8))
        mask1 = cv2.morphologyEx(mask1, cv2.MORPH_DILATE, np.ones((3,3), np.uint8))
        mask2 = cv2.bitwise_not(mask1)
        res1 = cv2.bitwise_and(img, img, mask=mask2)
        res2 = cv2.bitwise_and(background, background, mask=mask1)
        final = cv2.addWeighted(res1, 1, res2, 1, 0)
        # Apply selected effect
        final = apply_effect(final, EFFECTS[effect_idx])
        cv2.imshow("Evanesco", final)
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('e'):
            effect_idx = (effect_idx + 1) % len(EFFECTS)
            print("Effect changed to:", EFFECTS[effect_idx])
    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
