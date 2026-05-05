import os
import cv2


def init_segmentor():
    try:
        import urllib.request as _urllib_req
        import mediapipe as mp
        from mediapipe.tasks import python as _mp_python
        from mediapipe.tasks.python import vision as _mp_vision

        model_url = (
            'https://storage.googleapis.com/mediapipe-models/'
            'image_segmenter/selfie_segmenter/float16/latest/'
            'selfie_segmenter.tflite'
        )
        root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        model_path = os.path.join(root_dir, 'selfie_segmenter.tflite')

        if not os.path.exists(model_path):
            print('[INFO] Downloading MediaPipe selfie segmentation model...')
            _urllib_req.urlretrieve(model_url, model_path)
            print(f'[INFO] Model saved -> {model_path}')

        seg_opts = _mp_vision.ImageSegmenterOptions(
            base_options=_mp_python.BaseOptions(model_asset_path=model_path),
            running_mode=_mp_vision.RunningMode.IMAGE,
            output_confidence_masks=True,
        )
        segmentor = _mp_vision.ImageSegmenter.create_from_options(seg_opts)
        print('[INFO] MediaPipe selfie segmentation ready.')
        return segmentor, True, mp
    except Exception as err:
        print(f'[WARN] MediaPipe unavailable: {err}')
        return None, False, None


def segment_person_mask(segmentor, mp, frame_bgr):
    if segmentor is None or mp is None:
        return None
    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
    result = segmentor.segment(mp_img)
    if not result.confidence_masks:
        return None
    return result.confidence_masks[0].numpy_view().copy()
