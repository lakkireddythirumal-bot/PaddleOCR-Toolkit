import io
import os
import secrets
from typing import List

import fitz
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from PIL import Image, UnidentifiedImageError

from app.ocr_engine import extract_lines

APP_NAME = os.getenv("APP_NAME", "PaddleOCR-Toolkit")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "15"))
MAX_PDF_PAGES = int(os.getenv("MAX_PDF_PAGES", "10"))
OCR_API_KEY = os.getenv("OCR_API_KEY", "").strip()
MAX_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_TYPES = {"image/png", "image/jpeg", "image/webp", "application/pdf"}

app = FastAPI(title=APP_NAME, version="0.1.0")

def check_api_key(provided: str | None):
    if OCR_API_KEY and not secrets.compare_digest(provided or "", OCR_API_KEY):
        raise HTTPException(status_code=401, detail="Invalid or missing API key")

def ocr_pil_image(image: Image.Image) -> List[dict]:
    return extract_lines(image)

@app.get("/health")
def health():
    return {"status": "ok", "service": APP_NAME}

@app.post("/ocr")
async def ocr_document(
    file: UploadFile = File(...),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
):
    check_api_key(x_api_key)
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Upload PNG, JPG, WEBP, or PDF")
    data = await file.read(MAX_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=413, detail=f"File exceeds {MAX_UPLOAD_MB} MB limit")

    filename = (file.filename or "upload").replace("\\", "/").split("/")[-1][:200]
    pages_out = []
    try:
        if content_type == "application/pdf":
            try:
                pdf = fitz.open(stream=data, filetype="pdf")
            except Exception as exc:
                raise HTTPException(status_code=400, detail="Invalid or unreadable PDF") from exc
            if pdf.page_count > MAX_PDF_PAGES:
                raise HTTPException(status_code=413, detail=f"PDF exceeds {MAX_PDF_PAGES} page limit")
            for index, page in enumerate(pdf):
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
                lines = ocr_pil_image(image)
                pages_out.append({"page": index + 1, "lines": lines,
                                  "text": "\n".join(row["text"] for row in lines)})
            pdf.close()
        else:
            try:
                image = Image.open(io.BytesIO(data)).convert("RGB")
            except (UnidentifiedImageError, OSError) as exc:
                raise HTTPException(status_code=400, detail="Invalid or unreadable image") from exc
            lines = ocr_pil_image(image)
            pages_out.append({"page": 1, "lines": lines,
                              "text": "\n".join(row["text"] for row in lines)})
    except HTTPException:
        raise
    except Exception as exc:
        # Avoid returning local paths or internal stack traces to API callers.
        raise HTTPException(status_code=500, detail="OCR processing failed; inspect server logs") from exc

    full_text = "\n\n".join(p["text"] for p in pages_out)
    confidences = [row["confidence"] for p in pages_out for row in p["lines"]]
    return {
        "filename": filename,
        "content_type": content_type,
        "page_count": len(pages_out),
        "text": full_text,
        "average_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "pages": pages_out,
    }
