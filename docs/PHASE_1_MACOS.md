# Phase 1 — architecture and macOS setup

Goal: open the React UI, paste a synthetic job, save it through FastAPI into PostgreSQL, and confirm it survives a backend restart. There is no API subscription or LLM cost for this phase.

## 1. Check installed tools

Open Terminal on your Mac and run each command:

```bash
uname -m
git --version
python3 --version
node --version
npm --version
docker --version
docker compose version
```

`arm64` means Apple silicon; `x86_64` means Intel. Use the matching Docker Desktop installer. This starter targets Python 3.12+ and Node 22.12+; Vite's official minimum also allows supported Node 20 releases, but the starter deliberately specifies 22.12+. Prefer a supported Node LTS release meeting that requirement.

If tools are missing:

- Git: `xcode-select --install` installs Apple's command-line developer tools when absent.
- Python: install Python 3.12 or newer from [python.org](https://www.python.org/downloads/macos/).
- Node: use an LTS installer from [nodejs.org](https://nodejs.org/en/download).
- Docker Desktop: use [Docker's Mac instructions](https://docs.docker.com/desktop/setup/install/mac-install/), then launch Docker Desktop and wait until the engine is running. Existing SQL Server containers can remain; this PostgreSQL setup uses port 5433.
- VS Code: use [the Mac installer](https://code.visualstudio.com/docs/setup/mac). Install the Microsoft Python extension. In the command palette, run **Shell Command: Install 'code' command in PATH** if you want `code .` in Terminal.

Close/reopen Terminal after installers so PATH updates take effect. If `python3` still resolves to an older system Python, use the installed version's command (for example `python3.12`) in step 4. No Homebrew installation is required by this guide.

## 2. Put the starter in a project folder

Download and unzip `Project_5_Phase_1_Starter.zip` using Finder. The ZIP contains the `career-application-agent` directory. Move that directory into `~/Projects/`; do not move or overwrite your résumé or HTCMF files.

If needed, create the destination first:

```bash
mkdir -p ~/Projects
```

After moving the extracted directory:

```bash
cd ~/Projects/career-application-agent
open -a "Visual Studio Code" .
```

The ZIP excludes `.git`, virtual environments, downloaded dependencies and private content. Git will be initialized on your Mac in step 8.

## 3. Configure and start PostgreSQL

From the project root:

```bash
cp .env.example .env
```

Open `.env` in VS Code. Replace `replace-with-your-local-password` in BOTH `POSTGRES_PASSWORD` and `DATABASE_URL` with the same local password. For this beginner setup, use a long randomly generated alphanumeric password to avoid URL encoding issues. Keep `.env` private.

Then run:

```bash
docker compose up -d db
docker compose ps
```

Wait until the `db` service is healthy. If it is still starting, run `docker compose ps` again. PostgreSQL is available at localhost:5433. Its data is stored in a named Docker volume, independent of the container process. Application tables do not exist until step 4.

Docker initializes the password only for a new database volume. Changing `.env` later does not change an existing database account password. Use a deliberate database password change when real data exists.

## 4. Install backend dependencies and apply the migration

From the project root:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

If the starter includes `requirements.lock.txt`, you can use `python -m pip install -r requirements.lock.txt` before installing the editable package with `python -m pip install --no-deps -e .`. The lock records exact versions tested in the build environment; the editable project file records compatible ranges.

Use a small Python call to load the local `.env` for the migration rather than trying to source a URL containing shell punctuation:

```bash
python -c 'from dotenv import load_dotenv; load_dotenv("../.env"); from alembic.config import main; main(argv=["upgrade", "head"])'
```

`python-dotenv` is installed as an explicit project dependency. Alembic applies migration `0001`, creating `jobs`. Running the same upgrade again is safe and should make no further change.

Select `backend/.venv/bin/python` in VS Code using **Python: Select Interpreter**. This isolates the project's packages from other Python projects.

## 5. Start FastAPI — Terminal A

Keep Terminal A in `backend/` with the virtual environment active:

```bash
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 --env-file ../.env
```

Leave this process running. Open [API docs](http://127.0.0.1:8000/docs), [health](http://127.0.0.1:8000/health) and [readiness](http://127.0.0.1:8000/ready).

- Health: expect `status: ok` and `submission_enabled: false`.
- Readiness: expect `status: ready`. If not, check Docker and the migration.

## 6. Start React — Terminal B

Open a second terminal tab/window:

```bash
cd ~/Projects/career-application-agent/frontend
npm ci
npm run dev
```

If no `package-lock.json` is included, use `npm install` once instead of `npm ci`; commit the generated lock. Open [the application](http://127.0.0.1:5173). Vite forwards `/api` requests to FastAPI locally.

## 7. Check the smallest functional slice

Use this synthetic example, not a real vacancy:

- Company: Demo Healthcare
- Job title: Implementation Specialist
- Description: Remote healthcare implementation role requiring SQL, stakeholder communication, data validation, and workflow analysis.
- Source: Pasted job description
- URL: leave blank

Click **Save job**. It should appear under Saved opportunities; expand its description. Paste the identical job again: expect a duplicate message and one saved record.

Restart ONLY FastAPI with Ctrl+C in Terminal A and rerun step 5. Refresh React: the job should remain. This is the PostgreSQL persistence acceptance check.

To inspect records directly, run this in Terminal C from the project root:

```bash
docker compose exec db psql -U career -d career_agent -c 'SELECT id, company, title, created_at FROM jobs ORDER BY created_at DESC;'
```

These user/database arguments match `.env.example`; adjust them if you chose different names.

Run API tests in a third terminal; they use an isolated in-memory database and do not touch your PostgreSQL records:

```bash
cd ~/Projects/career-application-agent/backend
source .venv/bin/activate
pytest -q
```

Compile the frontend:

```bash
cd ~/Projects/career-application-agent/frontend
npm run build
```

Phase 1 is complete on your Mac when intake, duplicate handling, readiness, persistence after restart, tests and the frontend build succeed. Test success alone does not establish that your Mac's database connection works.

## 8. Initialize Git without committing private material

From the project root:

```bash
cd ~/Projects/career-application-agent
mkdir -p private/sources private/generated
git init -b main
git check-ignore .env private/sources/example.docx
git add .gitignore .env.example compose.yaml README.md backend frontend docs
git diff --cached --stat
git status --short
```

Inspect the staged list. It should contain code, documentation and dependency locks, with no `.env`, `private/`, `node_modules/` or `.venv/`. Then:

```bash
git commit -m "Initialize Project 5 job intake foundation"
git switch -c phase-2-verified-evidence
```

If Git asks for identity, configure your preferred author name and email for this repository. No GitHub remote has been created or pushed by this starter. Later, create an empty repository named `career-application-agent`, connect its exact URL and push after reviewing the files. Do not copy real résumés into a public commit.

## 9. Stop and resume

Ctrl+C stops each development server. From the project root:

```bash
docker compose stop db
```

This keeps the database volume. To resume, `docker compose up -d db`, then repeat steps 5 and 6; activate the backend environment first. Avoid commands that delete the Docker volume when it contains records you want to preserve.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| Cannot connect to Docker | Launch Docker Desktop; confirm engine startup; run `docker info`. |
| Port 5433 occupied | Choose another host port in `compose.yaml` and update `DATABASE_URL` to match. |
| Port 8000 occupied | Stop the other process, or change both the API port and Vite proxy target. |
| Port 5173 occupied | Stop the other Vite process; strict port mode deliberately reports the collision. |
| DATABASE_URL missing | Start Uvicorn with `--env-file ../.env` from `backend/`. |
| Password authentication failed | Confirm both password entries match; check whether a database volume was initialized with an older password. |
| jobs table missing | Run the Alembic upgrade against the same `.env`. |
| UI says Failed to fetch / proxy error | Check both development servers and the API readiness URL. |
| npm reports unsupported engine | Install a supported Node release satisfying the specified minimum. |
| code command missing | Use `open -a "Visual Studio Code" .` or install VS Code's shell command. |

## What follows

Next, review the actual current HTCMF and master résumés and build the verified evidence catalog. They have not been loaded or modified during Phase 1. Source copies and generated outputs will be stored separately, and uncertainty must be resolved before tailoring claims.

## Primary references

- [FastAPI first steps](https://fastapi.tiangolo.com/tutorial/first-steps/)
- [FastAPI virtual environments](https://fastapi.tiangolo.com/virtual-environments/)
- [Vite getting started and Node requirements](https://vite.dev/guide/)
- [SQLAlchemy PostgreSQL and psycopg dialect](https://docs.sqlalchemy.org/en/20/dialects/postgresql.html)
- [Alembic migration tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [Docker Desktop for Mac](https://docs.docker.com/desktop/setup/install/mac-install/)

Commands assume the supplied directory layout and local configuration. This build environment is Linux, so macOS installation, Docker Desktop and end-to-end PostgreSQL operation still need the checks above on your Mac.
