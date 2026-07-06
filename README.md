# PDF to Excel Extractor

Full-stack app that extracts data from PDF files and exports it to Excel.

## Stack

| Layer    | Tech            |
|----------|-----------------|
| Backend  | FastAPI, Python |
| Frontend | React, Vite     |

## Project structure

```
PDF-ID-Extractor/
├── backend/          # FastAPI API
│   ├── app/
│   │   ├── api/      # Route handlers
│   │   ├── core/     # Config & settings
│   │   ├── models/   # Pydantic schemas
│   │   ├── services/ # PDF & Excel logic
│   │   └── utils/    # Helpers
│   ├── uploads/      # Incoming PDFs
│   └── outputs/      # Generated Excel files
└── frontend/         # React + Vite UI
    └── src/
        ├── components/
        └── services/
```

## Setup

### Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

App: http://localhost:5173

## API overview

| Method | Endpoint               | Description                                      |
|--------|------------------------|--------------------------------------------------|
| GET    | `/`                    | Health check                                     |
| GET    | `/api/health`          | Service health                                   |
| POST   | `/api/extract`         | Upload one or more PDFs, get JSON records        |
| POST   | `/api/download-excel`  | Send records JSON, download `Drivers.xlsx`       |

### `POST /api/extract`

Multipart form field: `files` (one or more PDFs).

Response:

```json
{
  "success": true,
  "records": [
    {
      "name": "",
      "address": "",
      "aadhaar": "",
      "dl_number": "",
      "phone": "",
      "stand": "",
      "pdf_name": ""
    }
  ]
}
```

### `POST /api/download-excel`

Request body:

```json
{
  "records": [
    {
      "name": "",
      "address": "",
      "aadhaar": "",
      "dl_number": "",
      "phone": "",
      "stand": "",
      "pdf_name": ""
    }
  ]
}
```

Response: `Drivers.xlsx` file download.
