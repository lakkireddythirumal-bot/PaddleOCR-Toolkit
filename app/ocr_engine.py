from functools import lru_cache
from paddleocr import PaddleOCR

@lru_cache(maxsize=4)
def get_engine(lang: str = "en") -> PaddleOCR:
    # PaddleOCR downloads model weights on first run if not already cached.
    return PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)

def extract_lines(image):
    """Return normalized OCR lines from a PIL image using PaddleOCR 2.x."""
    import numpy as np

    engine = get_engine()
    array = np.array(image.convert("RGB"))
    raw = engine.ocr(array, cls=True)
    lines = []
    for page in (raw or []):
        for item in (page or []):
            try:
                points, recognition = item
                text, confidence = recognition
                lines.append({
                    "text": str(text),
                    "confidence": float(confidence),
                    "box": [[float(x), float(y)] for x, y in points],
                })
            except (TypeError, ValueError, IndexError):
                # Ignore malformed engine rows rather than failing the whole document.
                continue
    return lines
