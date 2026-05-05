import os
import cv2
import numpy as np


def make_beach(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    for y in range(h * 55 // 100):
        t = y / (h * 55 // 100)
        img[y] = [int(200 - 80 * t), int(140 + 60 * t), int(255 - 30 * t)]
    sea_top = h * 45 // 100
    sea_bot = h * 65 // 100
    for y in range(sea_top, sea_bot):
        t = (y - sea_top) / (sea_bot - sea_top)
        img[y] = [int(180 - 60 * t), int(120 + 40 * t), int(80 - 20 * t)]
    for y in range(sea_bot, h):
        t = (y - sea_bot) / (h - sea_bot)
        img[y] = [int(80 + 40 * t), int(160 + 30 * t), int(200 + 30 * t)]
    cv2.circle(img, (w * 3 // 4, h // 5), 40, (80, 220, 255), -1)
    cv2.circle(img, (w * 3 // 4, h // 5), 44, (100, 230, 255), 3)
    return img


def make_space(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    for y in range(h):
        t = y / h
        img[y] = [int(40 + 20 * t), int(5 + 10 * t), int(20 + 10 * t)]
    rng = np.random.default_rng(42)
    for _ in range(300):
        sx, sy = rng.integers(0, w), rng.integers(0, h)
        brightness = int(rng.integers(150, 255))
        cv2.circle(img, (sx, sy), 1, (brightness, brightness, brightness), -1)
    cv2.circle(img, (w // 4, h // 3), 55, (20, 60, 160), -1)
    cv2.circle(img, (w // 4, h // 3), 55, (40, 80, 200), 3)
    cv2.ellipse(img, (w // 4, h // 3), (85, 18), -20, 0, 360, (30, 70, 180), 3)
    return img


def make_forest(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    for y in range(h // 3):
        t = y / (h // 3)
        img[y] = [int(200 - 50 * t), int(220 - 30 * t), int(255 - 60 * t)]
    for y in range(h // 3, h):
        t = (y - h // 3) / (h * 2 // 3)
        img[y] = [int(20 + 10 * t), int(80 - 30 * t), int(10 + 5 * t)]
    for tx in range(40, w, 80):
        height = np.random.default_rng(tx).integers(100, 200)
        pts = np.array(
            [[tx, h // 3 + 60], [tx - 30, h // 3 + 60 + height], [tx + 30, h // 3 + 60 + height]],
            np.int32,
        )
        cv2.fillPoly(img, [pts], (15, int(60 + tx % 40), 10))
    return img


def make_sunset(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    colors = [
        (30, 30, 180),
        (20, 80, 230),
        (10, 140, 255),
        (20, 180, 255),
        (60, 120, 200),
        (80, 80, 120),
    ]
    band = h // len(colors)
    for i, c in enumerate(colors):
        y0, y1 = i * band, min((i + 1) * band, h)
        img[y0:y1] = c
    cv2.circle(img, (w // 2, h // 2), 55, (30, 150, 255), -1)
    return img


def make_city(h=480, w=640):
    img = np.zeros((h, w, 3), np.uint8)
    for y in range(h):
        t = y / h
        img[y] = [int(40 + 20 * t), int(20 + 15 * t), int(10 + 5 * t)]
    rng = np.random.default_rng(7)
    for _ in range(150):
        sx, sy = rng.integers(0, w), rng.integers(0, h // 2)
        cv2.circle(img, (sx, sy), 1, (200, 200, 200), -1)
    building_rng = np.random.default_rng(99)
    bx = 0
    while bx < w:
        bw = int(building_rng.integers(30, 70))
        bh = int(building_rng.integers(80, 280))
        by = h - bh
        shade = int(building_rng.integers(30, 70))
        cv2.rectangle(img, (bx, by), (bx + bw, h), (shade, shade, shade + 10), -1)
        for wy in range(by + 8, h - 10, 18):
            for wx in range(bx + 6, bx + bw - 6, 14):
                if building_rng.random() > 0.4:
                    cv2.rectangle(img, (wx, wy), (wx + 6, wy + 8), (0, 180, 220), -1)
        bx += bw + int(building_rng.integers(2, 8))
    return img


def get_scene_factories():
    return {
        'beach': make_beach,
        'space': make_space,
        'forest': make_forest,
        'sunset': make_sunset,
        'city': make_city,
    }


def generate_builtin_backgrounds(bg_dir, scene_factories):
    for name, fn in scene_factories.items():
        path = os.path.join(bg_dir, f'{name}.jpg')
        if not os.path.exists(path):
            cv2.imwrite(path, fn())
