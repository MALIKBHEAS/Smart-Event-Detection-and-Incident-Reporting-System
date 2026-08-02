Running backend tests locally

This project uses pytest for unit and integration tests. The repository is structured with a `backend/` package; tests reference that package via PYTHONPATH.

Prerequisites
- Python 3.12
- pip

Recommended (virtualenv)

Bash / macOS / Linux

1. Create and activate a virtual environment:

   python -m venv .venv
   source .venv/bin/activate

2. Install minimal test dependencies:

   pip install --upgrade pip
   pip install pytest pytest-asyncio opencv-python-headless numpy

3. Run tests from the repository root:

   export PYTHONPATH=$(pwd)/backend
   pytest -q

PowerShell (Windows)

1. Create and activate venv:

   python -m venv .venv
   .\.venv\Scripts\Activate.ps1

2. Install deps:

   python -m pip install --upgrade pip
   pip install pytest pytest-asyncio opencv-python-headless numpy

3. Run tests:

   $env:PYTHONPATH = (Resolve-Path .\backend).Path
   pytest -q

Notes about test environment
- Tests are designed to be fast and deterministic and do not require GPU, YOLO models, or RTSP cameras.
- Tests use mocks and lightweight fakes to avoid external dependencies.
- If the project provides a backend/requirements.txt, use it instead of the minimal set above.

How CI executes tests (GitHub Actions)
- The GitHub Actions workflow is located at `.github/workflows/backend-tests.yml`.
- On push and pull_request events the workflow runs on ubuntu-latest and uses Python 3.12.
- Steps executed in CI:
  1. Checkout
  2. Setup Python 3.12
  3. Install dependencies (from backend/requirements.txt if present, otherwise installs minimal test deps)
  4. Set PYTHONPATH to the backend/ directory
  5. Run `pytest -q --junitxml=pytest-results.xml`
  6. Upload `pytest-results.xml` as a build artifact

Required environment variables
- PYTHONPATH: should include the `backend` folder when running tests locally (set by the CI workflow automatically).
- TRACKER_USE_BYTE (optional): Controls default tracker selection in WorkerManager; tests mock tracker creation where appropriate. In CI the workflow sets `TRACKER_USE_BYTE=true`.

Troubleshooting
- If tests fail due to missing native libraries (e.g. opencv), ensure `opencv-python-headless` is installed in your environment.
- If tests import modules that rely on heavy third-party dependencies, consider running only the unit tests (`pytest -q tests/unit`) or install the full backend requirements in a development environment.

Linting and type checking locally

If you want CI to run additional quality checks (linters, type-checks), they are already configured in the repository's CI workflow. Run locally with the following commands:

- Lint with ruff (install via pip install ruff or use backend/requirements-dev.txt):

  python -m pip install --upgrade pip
  pip install ruff
  ruff check .

- Verify formatting (ruff formatter):

  ruff format --check .

- Type check with mypy (uses backend/mypy.ini if present):

  python -m pip install --upgrade pip
  pip install mypy
  mypy --config-file backend/mypy.ini

These checks are executed by GitHub Actions in the `lint` and `type-check` jobs.

Running the backend FastAPI app locally (development)

To run the FastAPI app that wires WorkerManager into the application lifecycle:

1. Install runtime dependencies (FastAPI + ASGI server):

   python -m pip install --upgrade pip
   pip install fastapi uvicorn

2. Run with uvicorn from repository root (PYTHONPATH points at backend):

   export PYTHONPATH=$(pwd)/backend
   uvicorn app.main:app --reload --port 8000

PowerShell (Windows):

   $env:PYTHONPATH = (Resolve-Path .\backend).Path
   uvicorn app.main:app --reload --port 8000

Endpoints exposed (development helpers)
- GET /health/workers -> returns JSON with current worker statuses
- POST /workers/start/{camera_id} -> start worker for camera id
- POST /workers/stop/{camera_id} -> stop worker for camera id

Notes:
- The FastAPI app will create WorkerManager at startup and call start_all(). The manager will attempt to start workers for active cameras found in the database using the configured SessionLocal. For development environments without a DB, you may want to mock or provide a simple session_factory when importing the app.
- Do not run the production app with --reload; use a production ASGI server configuration for deployments.


Using pre-commit hooks locally

A pre-commit configuration is provided in `.pre-commit-config.yaml` to run quick quality checks before commits.

1. Install development dependencies (recommended):

   python -m pip install --upgrade pip
   pip install -r backend/requirements-dev.txt

2. Install pre-commit git hook (run once per clone):

   pre-commit install

3. Run hooks manually on all files:

   pre-commit run --all-files

Notes:
- The configured hooks include ruff (lint), ruff format check, mypy, and basic file checks (trailing whitespace, EOF fixer, and YAML validation).
- The ruff format hook is configured to check formatting without modifying files — run `ruff format` locally to auto-fix.
- Hooks are configured to be fast and avoid running heavy AI or model-loading code.
- If you prefer the pre-commit hooks to run using the versions in `backend/requirements-dev.txt`, install those first.
