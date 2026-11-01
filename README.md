# spotter-routing

## Backend: run locally

Requires Python 3.11. Run from the repo root (PowerShell shown):

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
