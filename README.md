# spotter-routing

## Backend: run locally

Requires Python 3.11. Run from the repo root (PowerShell shown):

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
Copy-Item backend\.env.example backend\.env
```

Edit `backend/.env` and set these three values. Leaving `SECRET_KEY` blank breaks the app, because a blank value replaces the local fallback:

```
SECRET_KEY=any-non-empty-value-for-local-use
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
