# Migration notes

Source repository: https://github.com/F1r0R0/djangoapp

Target repository: https://github.com/W1llAnn/Project_workshop_2s

Migration branch: import-from-djangoapp

The migration is performed in a separate branch. The `main` branch is not changed directly.

## Migrated parts

- Project documentation: `README.md`, `DEPLOY.md`.
- Existing documentation already matching source: `architecture.md`, `Market_research.md`.
- Deployment configuration: `docker-compose.dev.yml`, `docker-compose.prod.yml`, `Makefile`, `nginx/default.conf`, `.env.prod.example`.
- Django backend: `backend/core`, `backend/habits`, `backend/static`, `backend/templates`, `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/conftest.py`, `backend/manage.py`.
- UI assets and presentation materials checked against source: `first_ui_prototype`, `image`, `tags`, `project_presentation`. No file changes were needed because they already matched `source/main`.

## Safety adjustments

- Real `.env` files were not copied or committed.
- `.env.prod.example` keeps only placeholder values.
- Default production superuser credentials were removed from `docker-compose.prod.yml`; production values are required through environment variables.
- A hardcoded Django `SECRET_KEY` from the source settings was replaced with a local-development placeholder.
- The `seed_demo` command no longer stores or prints a fixed demo password. Use `DEMO_USER_PASSWORD` or `--password` when a known demo password is required.

## Local verification

- Python version: `Python 3.13.1`.
- Virtual environment: `python -m venv .venv` completed. A pre-existing ignored `backend/.venv` was reused and not committed.
- Dependencies: `pip install -r requirements.txt` completed after allowing network access to PyPI.
- Initial `python manage.py migrate` tried to use Postgres host `db` because an ignored local `backend/.environment` exists in this working copy.
- SQLite verification: `USE_SQLITE=True python manage.py migrate` completed successfully.
- Demo data: `USE_SQLITE=True python manage.py seed_demo --reset` completed successfully.
- Server check: `USE_SQLITE=True python manage.py runserver 127.0.0.1:8000` started successfully and was stopped.

## Cleanup

- Generated `backend/db.sqlite3` was removed after verification.
- Generated `__pycache__` directories were removed after verification.
- Ignored local files remain uncommitted: `backend/.environment`, `backend/.venv`, `data/`.

## Manual checks before merge

- Review production environment values before deployment: `SECRET_KEY`, `POSTGRES_PASSWORD`, `DJANGO_SUPERUSER_*`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS`.
- Decide whether local developers should keep using `backend/.environment` or prefer explicit `USE_SQLITE=True` for local SQLite checks.
- Run Docker dev/prod smoke tests in an environment with Docker available.
- Review the large backend import, especially settings, migrations, and UI flows, before merging the pull request.

## Windows local startup

Run these commands from PowerShell:

```powershell
cd "D:\Магистратура_Урфу\Проектный парктикум _2\Main_repo\Git\Project_workshop_2s\backend"
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py migrate
python manage.py seed_demo --reset --password demo-local-pass
python manage.py runserver 127.0.0.1:8000
```

Open http://127.0.0.1:8000/.

Demo login after the command above: `demo` / `demo-local-pass`.

For later runs:

```powershell
cd "D:\Магистратура_Урфу\Проектный парктикум _2\Main_repo\Git\Project_workshop_2s\backend"
.\.venv\Scripts\Activate.ps1
python manage.py runserver 127.0.0.1:8000
```

If `OperationalError: no such table: auth_user` appears, stop the server with
`Ctrl+C`, run `python manage.py migrate`, and start the server again.

On Windows local startup, SQLite is now the default database backend. Docker
development and production still opt into PostgreSQL explicitly with
`USE_SQLITE=False`.

## Public preview with ngrok

Start Django locally:

```powershell
cd "D:\Магистратура_Урфу\Проектный парктикум _2\Main_repo\Git\Project_workshop_2s\backend"
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver 127.0.0.1:8000
```

In another PowerShell window, expose it:

```powershell
ngrok http 8000
```

Open the `https://...ngrok-free.app` URL shown by ngrok. Local hosts and
`*.ngrok-free.app` are allowed in Django settings for preview use.
