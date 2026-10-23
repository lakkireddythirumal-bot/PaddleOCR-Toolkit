# PaddleOCR-Toolkit

A standalone OCR service and integration starter for extracting text from images and scanned PDFs, then sending structured results through n8n to Supabase.

> **Isolation:** This is a new project. It does not modify or deploy to your existing production website, GitHub Pages, Cloudflare Worker, or production Supabase tables.

## Features
- FastAPI endpoint for image OCR and scanned PDF OCR
- PaddleOCR engine (English baseline; multilingual configuration can be added)
- JSON output with extracted lines and confidence scores
- Optional n8n workflow pattern
- Supabase SQL schema for OCR job history
- Docker setup for local testing
- Basic health endpoint and tests

## Architecture

```text
Image / scanned PDF
        |
        v
PaddleOCR-Toolkit API  ---> structured JSON
        |                         |
        +-------------------------+
                                  v
                           n8n workflow
                     validate / route / retry
                                  |
                                  v
                         Supabase OCR tables
```

## Recommended environment
Use **Python 3.10** in a virtual environment for the initial PaddleOCR 2.x baseline. Install a compatible PaddlePaddle CPU wheel for your operating system from the official PaddlePaddle installation guide. Do not assume one wheel works on every OS/Python combination.

## 1. Local setup (Windows PowerShell)

Install Python 3.10, then open PowerShell in this folder:

```powershell
py -3.10 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

Install PaddlePaddle CPU using the official command matching your Python version and OS:
https://www.paddlepaddle.org.cn/en/install/quick

Then install the project dependencies:

```powershell
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open http://127.0.0.1:8000/docs and test `POST /ocr`. For n8n running on a different machine/container, `127.0.0.1` is not reachable from that runtime; use a reachable private host or a secure tunnel. Do not expose this API publicly without authentication and request limits.

## 2. Test the service

Health:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

OCR:
- In Swagger UI at `/docs`, use `POST /ocr`
- Upload a PNG/JPG or scanned PDF.
- The endpoint returns text lines, confidence values, and combined text.

## 3. n8n workflow outline

Create a separate workflow named `PaddleOCR - Intake to Supabase`:

1. **Trigger**: Webhook, Gmail, or manual trigger.
2. **Get file**: obtain the image/PDF as binary data.
3. **HTTP Request**:
   - Method: `POST`
   - URL: `http://YOUR_OCR_HOST:8000/ocr`
   - Send Body: `Form-Data`
   - Parameter type: `n8n Binary File`
   - Name: `file`
   - Input Data Field Name: the binary property name, commonly `data`
4. **Edit Fields**: keep `text`, `lines`, `filename`, and `page_count`.
5. **Supabase**: insert one row into `ocr_documents` using the Supabase node, or use an HTTP Request to the Supabase REST API.
6. **Error branch**: log failure status and retry transient errors. Avoid retrying invalid/unsupported files forever.

If n8n runs in Docker on the same Docker network, use the service name such as `http://ocr-api:8000/ocr`. `localhost` inside n8n refers to the n8n container itself.

### Supabase HTTP Request option
- Method: `POST`
- URL: `https://YOUR_PROJECT_REF.supabase.co/rest/v1/ocr_documents`
- Headers:
  - `apikey`: service role key (server-side only)
  - `Authorization`: `Bearer YOUR_SERVICE_ROLE_KEY` (server-side only)
  - `Content-Type`: `application/json`
  - `Prefer`: `return=representation`
- Body: map `source_filename`, `extracted_text`, `ocr_result`, and `status`.

**Security:** Store credentials in n8n credentials or environment variables. Never commit `.env`, API keys, Supabase service-role keys, private documents, or production data. The service-role key bypasses Row Level Security; never put it in a browser or public website.

## 4. Supabase setup
1. Create a separate development project if possible.
2. Open SQL Editor.
3. Run `supabase/schema.sql`.
4. Keep this OCR table separate from existing production tables until tested and reviewed.
5. Decide access policy before enabling client-side reads. The starter schema does not grant anonymous access.

## 5. Production hardening checklist
- Add API authentication (API key or gateway auth).
- Add file-size, page-count, and request-rate limits.
- Add malware scanning and temporary-file cleanup.
- Use private storage for source documents and retention rules.
- Configure Supabase RLS policies based on your actual user model.
- Add structured logs, monitoring, retries, and idempotency keys.
- Validate OCR quality against representative invoices/MIS scans before automating business decisions.
- Treat OCR output as untrusted input; review low-confidence results.
- Do not connect this project to production until you explicitly choose to.

## Project layout

```text
PaddleOCR-Toolkit/
├── app/
│   ├── __init__.py
│   ├── main.py
│   └── ocr_engine.py
├── supabase/schema.sql
├── tests/test_health.py
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## Notes
This starter uses the PaddleOCR 2.x API. PaddlePaddle installation depends on OS, Python version, CPU/GPU, and hardware. If installation fails, follow the official install guide and pin a compatible PaddlePaddle build rather than installing random wheels.
