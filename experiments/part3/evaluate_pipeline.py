import os
import sys
import time
import numpy as np
import cv2
import json
from collections import deque

# Add parent directory to path so we can import core modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from core.processing import preprocess_frame, refine_mask, build_hsv_mask, temporal_smooth_mask

def generate_synthetic_test_suite(num_frames=30):
    """
    Generates a synthetic sequence of frames simulating a green cloak with different DIP challenges:
    1. Perfect conditions (constant green, clean background)
    2. Shadow/Highlight (illumination gradient across the frame)
    3. Sensor Noise (additive Gaussian noise)
    4. Motion & Temporal Jitter (flicker on mask edges)
    """
    width, height = 640, 480
    bg = np.zeros((height, width, 3), dtype=np.uint8)
    # Background is a wooden texture / brown color
    bg[:] = [40, 60, 80] # BGR
    
    # Define a static person shape and a green cloak shape
    # Ground truth cloak mask (a central circle of radius 100)
    gt_mask = np.zeros((height, width), dtype=np.uint8)
    cv2.circle(gt_mask, (width // 2, height // 2), 120, 255, -1)
    
    # Green cloak base color (HSV: H=60, S=200, V=200)
    green_bgr = np.uint8([[[0, 200, 0]]])
    green_hsv = cv2.cvtColor(green_bgr, cv2.COLOR_BGR2HSV)[0][0]
    
    frames_perfect = []
    frames_shadow = []
    frames_noise = []
    frames_temporal = []
    
    # Green color range: H in [35, 85], S in [100, 255], V in [100, 255]
    color_ranges = [{'hsv_min': [35, 80, 80], 'hsv_max': [85, 255, 255]}]
    
    for idx in range(num_frames):
        # 1. Perfect Frame
        frame = bg.copy()
        frame[gt_mask == 255] = [20, 220, 20] # bright green
        frames_perfect.append(frame)
        
        # 2. Shadow/Highlight Frame (simulate gradient shadow from left to right)
        shadow_frame = frame.copy().astype(np.float32)
        shadow_grad = np.linspace(0.4, 1.2, width).reshape(1, width, 1)
        shadow_frame = shadow_frame * shadow_grad
        shadow_frame = np.clip(shadow_frame, 0, 255).astype(np.uint8)
        frames_shadow.append(shadow_frame)
        
        # 3. Noise Frame (simulate sensor noise, std_dev = 25)
        noise = np.random.normal(0, 25, frame.shape).astype(np.float32)
        noise_frame = frame.astype(np.float32) + noise
        noise_frame = np.clip(noise_frame, 0, 255).astype(np.uint8)
        frames_noise.append(noise_frame)
        
        # 4. Temporal Jitter Frame (simulate edge flicker and moving noise)
        temp_mask = np.zeros((height, width), dtype=np.uint8)
        # Random radius perturbation to simulate edge jitter
        jitter_radius = 120 + int(5 * np.sin(idx * 0.5) + np.random.normal(0, 2))
        cv2.circle(temp_mask, (width // 2, height // 2), jitter_radius, 255, -1)
        
        temp_frame = bg.copy()
        temp_frame[temp_mask == 255] = [20, 220, 20]
        # Add slight noise
        noise_t = np.random.normal(0, 10, temp_frame.shape).astype(np.float32)
        temp_frame = np.clip(temp_frame.astype(np.float32) + noise_t, 0, 255).astype(np.uint8)
        frames_temporal.append((temp_frame, temp_mask))
        
    return {
        'perfect': (frames_perfect, gt_mask),
        'shadow': (frames_shadow, gt_mask),
        'noise': (frames_noise, gt_mask),
        'temporal': frames_temporal, # contains a tuple of (frame, mask_gt) per frame
        'color_ranges': color_ranges
    }

def evaluate_baseline(frames, color_ranges):
    """
    Standard HSV Masking:
    - No preprocessing
    - Standard cv2.inRange
    - Basic morphological open (3x3 rect) and dilate (3x3 rect)
    - No temporal smoothing, no feathering
    """
    masks = []
    times = []
    
    lower = np.array(color_ranges[0]['hsv_min'])
    upper = np.array(color_ranges[0]['hsv_max'])
    kernel = np.ones((3, 3), np.uint8)
    
    for frame in frames:
        t0 = time.perf_counter()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, lower, upper)
        # Basic morphology matching invisible.py
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_DILATE, kernel)
        t1 = time.perf_counter()
        
        masks.append(mask)
        times.append((t1 - t0) * 1000.0) # ms
        
    return masks, np.mean(times)

def evaluate_him(frames, color_ranges, window_size=5):
    """
    Hybrid Intelligence Masking (HIM):
    - Bilateral filter & CLAHE in LAB
    - Logical OR multi-range HSV thresholding
    - Elliptical morphology (Open 3x3, Close 7x7) + Gaussian blur (7x7)
    - Temporal smoothing with mask history
    """
    masks = []
    times = []
    history = deque(maxlen=window_size)
    
    for frame in frames:
        t0 = time.perf_counter()
        
        # Stage 1: Preprocess (Denoise + CLAHE)
        pp_frame = preprocess_frame(frame)
        
        # Stage 2: HSV threshold
        hsv = cv2.cvtColor(pp_frame, cv2.COLOR_BGR2HSV)
        mask = build_hsv_mask(hsv, color_ranges)
        
        # Stage 3: Morphology & Edge Refinement
        mask = refine_mask(mask)
        
        # Stage 5: Temporal Smoothing
        mask_f = mask.astype(np.float32) / 255.0
        mask_f = temporal_smooth_mask(mask_f, history, window_size)
        
        # Rescale back to 0-255 for comparison
        refined_mask = (mask_f * 255.0).astype(np.uint8)
        
        t1 = time.perf_counter()
        
        masks.append(refined_mask)
        times.append((t1 - t0) * 1000.0) # ms
        
    return masks, np.mean(times)

def calculate_iou(pred_mask, gt_mask):
    """Calculates Intersection over Union (IoU) for binary masks."""
    pred_bin = (pred_mask > 127).astype(np.uint8)
    gt_bin = (gt_mask > 127).astype(np.uint8)
    
    intersection = np.logical_and(pred_bin, gt_bin).sum()
    union = np.logical_or(pred_bin, gt_bin).sum()
    
    if union == 0:
        return 1.0 if intersection == 0 else 0.0
    return intersection / union

def calculate_temporal_variance(mask_sequence):
    """Calculates average variance per pixel across the mask sequence to measure flicker."""
    stacked = np.stack(mask_sequence, axis=2).astype(np.float32) / 255.0
    variance = np.var(stacked, axis=2)
    return float(np.mean(variance))

def calculate_edge_gradient_smoothness(mask):
    """
    Measures edge smoothness. A feathered mask will have a smooth gradient transition
    from 0 to 255, whereas a hard mask will have sharp 0 to 255 changes.
    We compute the spatial gradient magnitude of the mask and analyze its distribution.
    For soft/feathered masks, the gradients are spread out, meaning a higher standard deviation of
    gradients in the transition zone or a broader transition band.
    Specifically, we measure the percentage of pixels in transition (values between 10 and 245).
    """
    transition_pixels = np.logical_and(mask > 10, mask < 245).sum()
    total_pixels = mask.size
    return (transition_pixels / total_pixels) * 100.0

def main():
    print("Initializing synthetic test suite...")
    suite = generate_synthetic_test_suite(num_frames=30)
    color_ranges = suite['color_ranges']
    
    results = {}
    
    # ------------------ TEST 1: PERFECT CONDITIONS ------------------
    frames, gt = suite['perfect']
    m_base, t_base = evaluate_baseline(frames, color_ranges)
    m_him, t_him = evaluate_him(frames, color_ranges)
    
    results['perfect'] = {
        'baseline': {
            'iou': float(np.mean([calculate_iou(m, gt) for m in m_base])),
            'fps': float(1000.0 / t_base),
            'latency_ms': float(t_base),
            'transition_percent': float(np.mean([calculate_edge_gradient_smoothness(m) for m in m_base])),
            'temporal_variance': calculate_temporal_variance(m_base)
        },
        'him': {
            'iou': float(np.mean([calculate_iou(m, gt) for m in m_him])),
            'fps': float(1000.0 / t_him),
            'latency_ms': float(t_him),
            'transition_percent': float(np.mean([calculate_edge_gradient_smoothness(m) for m in m_him])),
            'temporal_variance': calculate_temporal_variance(m_him)
        }
    }
    
    # ------------------ TEST 2: SHADOW / LIGHTING GRADIENT ------------------
    frames, gt = suite['shadow']
    m_base, t_base = evaluate_baseline(frames, color_ranges)
    m_him, t_him = evaluate_him(frames, color_ranges)
    
    results['shadow'] = {
        'baseline': {
            'iou': float(np.mean([calculate_iou(m, gt) for m in m_base])),
            'latency_ms': float(t_base),
            'temporal_variance': calculate_temporal_variance(m_base)
        },
        'him': {
            'iou': float(np.mean([calculate_iou(m, gt) for m in m_him])),
            'latency_ms': float(t_him),
            'temporal_variance': calculate_temporal_variance(m_him)
        }
    }
    
    # ------------------ TEST 3: NOISY ENVIRONMENT ------------------
    frames, gt = suite['noise']
    m_base, t_base = evaluate_baseline(frames, color_ranges)
    m_him, t_him = evaluate_him(frames, color_ranges)
    
    results['noise'] = {
        'baseline': {
            'iou': float(np.mean([calculate_iou(m, gt) for m in m_base])),
            'latency_ms': float(t_base),
            'temporal_variance': calculate_temporal_variance(m_base)
        },
        'him': {
            'iou': float(np.mean([calculate_iou(m, gt) for m in m_him])),
            'latency_ms': float(t_him),
            'temporal_variance': calculate_temporal_variance(m_him)
        }
    }
    
    # ------------------ TEST 4: TEMPORAL JITTER & FLICKER ------------------
    temp_frames = [f[0] for f in suite['temporal']]
    temp_gts = [f[1] for f in suite['temporal']]
    m_base, t_base = evaluate_baseline(temp_frames, color_ranges)
    m_him, t_him = evaluate_him(temp_frames, color_ranges)
    
    results['temporal'] = {
        'baseline': {
            'iou': float(np.mean([calculate_iou(m_base[i], temp_gts[i]) for i in range(len(m_base))])),
            'latency_ms': float(t_base),
            'temporal_variance': calculate_temporal_variance(m_base)
        },
        'him': {
            'iou': float(np.mean([calculate_iou(m_him[i], temp_gts[i]) for i in range(len(m_him))])),
            'latency_ms': float(t_him),
            'temporal_variance': calculate_temporal_variance(m_him)
        }
    }
    
    # Save visual snapshots of the test conditions for user inspection
    dir_path = os.path.dirname(__file__)
    cv2.imwrite(os.path.join(dir_path, 'frame_1_perfect.png'), suite['perfect'][0][0])
    cv2.imwrite(os.path.join(dir_path, 'frame_2_shadow.png'), suite['shadow'][0][0])
    cv2.imwrite(os.path.join(dir_path, 'frame_3_noise.png'), suite['noise'][0][0])
    cv2.imwrite(os.path.join(dir_path, 'frame_4_temporal.png'), suite['temporal'][0][0])
    print(f"Saved sample test frames to {dir_path}")

    # Print results to stdout and write to file
    print("\n================ EVALUATION SUMMARY ================")
    for condition, methods in results.items():
        print(f"\nCondition: {condition.upper()}")
        for method_name, metrics in methods.items():
            print(f"  {method_name.upper()}:")
            for metric_name, val in metrics.items():
                print(f"    {metric_name}: {val:.5f}")
                
    output_path = os.path.join(dir_path, 'results.json')
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=4)
    print(f"\nResults successfully written to {output_path}")

if __name__ == '__main__':
    main()

