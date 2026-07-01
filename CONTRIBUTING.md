# Contributing

Thanks for helping build the Air-Gapped NetOps AI copilot.

## Ground rules

- **Air-gap first.** No feature may introduce a runtime dependency on an external network or
  cloud API. The only permitted outbound call is to a local Ollama instance. Any new model,
  dataset, or package must be installable and runnable fully offline.
- **No secrets in the repo.** Use environment variables (see `.env.example`). Never commit
  credentials, tokens, or private keys.

## Dev setup

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 pytest
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

## Branch & PR conventions

- Branch from `master`: `feat/<short-desc>`, `fix/<short-desc>`, `docs/<short-desc>`.
- Reference the issue: `Closes #NN` in the PR description.
- Keep PRs focused; one logical change per PR.
- All tests must pass (`pytest`) and CI must be green before merge.

## Commit messages

Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.

## Code style

- Python: type hints on public functions; keep modules single-responsibility.
- Match surrounding code — naming, comment density, and structure.
- Add or update tests in `backend/tests/` for any behavior change.

## Reporting security issues

See [SECURITY.md](SECURITY.md). Do not open a public issue for vulnerabilities.
