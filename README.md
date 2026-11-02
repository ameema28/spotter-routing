# spotter-routing

## Backend: run locally

Requires Python 3.11 or 3.12. Run from the repo root (PowerShell shown):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend/.env` and set these two values. `SECRET_KEY` can stay blank locally, because it has a development fallback:

```
DEBUG=True
MAPBOX_TOKEN=your-mapbox-token
```

Then run the tests and the server:

```powershell
cd backend
pytest
python manage.py runserver
```

Check it at http://127.0.0.1:8000/api/health/, which returns `{"status":"ok"}`.

## Frontend: run locally

Requires Node 20.19+ or 22.12+ (Vite 8; built with Node 24). From the repo root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open http://localhost:5173. `.env` points at the live API (`VITE_API_URL=https://spotter-routing-api.vercel.app`); for a local backend set it to `http://127.0.0.1:8000`. Other scripts: `npm run test`, `npm run lint`, `npm run build`.

The basemap is OpenFreeMap's Positron style and needs no key.

## Deploy

The backend is live at https://spotter-routing-api.vercel.app. It runs on Vercel Hobby as one Python function (Python 3.12, pinned in `backend/.python-version`).

1. Import the GitHub repo into Vercel and set **Root Directory** to `backend`. Vercel detects Django from `manage.py` and runs `collectstatic` itself.
2. Set these environment variables:

| Name | Value |
|---|---|
| `SECRET_KEY` | A new random key, never the local one |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | The deployment domain, without `https://` |
| `CSRF_TRUSTED_ORIGINS` | The deployment URL, with `https://` |
| `CORS_ALLOWED_ORIGINS` | The frontend origin(s), comma-separated |
| `MAPBOX_TOKEN` | Your Mapbox token |
| `CACHE_DIR` | `/tmp/spotter-cache`, because the rest of the filesystem is read-only |

Cached weather on Vercel is temporary and local to an instance. Searches still work without it, at the cost of a fresh weather fetch.

**Fallback host:** `render.yaml` deploys the same code to Render's free tier with gunicorn. Render's free service sleeps after 15 idle minutes and takes about a minute to wake. Leave `CACHE_DIR` unset there.
