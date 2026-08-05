# Contributing

## Non-negotiable rules

- **Air-gap first.** No runtime dependency on external networks or cloud APIs. The only permitted outbound call is to a local Ollama instance (`localhost:11434`). Any new model, dataset, or package must be bundleable and runnable fully offline.
- **No secrets.** Use environment variables (see `.env.example`). Never commit credentials, tokens, API keys, or private keys.
- **Tests required.** Every behaviour change needs a test. Coverage must stay ≥70%.

---

## Dev setup

### One-time setup
```bash
# Clone and install dev deps
git clone https://github.com/harsh-pandhe/airgapped-netops-ai
cd airgapped-netops-ai

make install-dev   # installs backend deps + pre-commit hooks
```

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run server
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173
```

### Code quality (run before every commit)
```bash
make fmt        # auto-format with ruff
make lint       # lint check
make typecheck  # mypy type check
make test       # full test suite with coverage
```

Pre-commit hooks run `ruff` and format checks automatically on `git commit`. Install once with `make install-dev`.

---

## Branch strategy

```
master          ← production-ready only; protected; requires PR + CI green
  └─ dev        ← integration; PRs target here, squash-merged to master for releases
       └─ feat/short-desc   ← your feature branch
       └─ fix/short-desc    ← your bugfix branch
       └─ docs/short-desc   ← documentation only
       └─ chore/short-desc  ← dependency bumps, CI, tooling
```

**Rules:**
- Never push directly to `master`. Always PR.
- Branch names: `feat/`, `fix/`, `docs/`, `chore/`, `test/` prefixes only.
- One logical change per PR. Large features → split across multiple PRs.
- Reference the issue in the PR body: `Closes #NN`.
- Squash merge into master; rebase merge into dev.

---

## Commit message format (Conventional Commits)

```
<type>(<scope>): <short description>

[optional body]

[optional footer: Closes #NN]
```

**Types:**

| Type | When |
|------|------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `chore` | Build, CI, dependency changes |
| `perf` | Performance improvement |
| `security` | Security fix or hardening |

**Examples:**
```
feat(ml): add ProcessPoolExecutor for graph traversal to prevent GIL blocking
fix(auth): token expiry check uses < not <= causing premature expiry
test(rag): add citation format regression test
chore(deps): pin requirements.txt to exact versions
```

The pre-commit hook enforces this format at `git commit` time.

---

## Code standards

- **Python:** type hints on all public functions; single-responsibility modules; no `print()` in production code (use `logging`).
- **TypeScript:** strict mode; no `any`; component props typed with interfaces.
- **Tests:** use fixtures from `conftest.py`; never touch production `metrics.db` or data files.
- **Security:** validate all inputs at API boundaries; write audit log entries for privileged operations; no user-controlled data interpolated into shell commands.

---

## Security issues

See [SECURITY.md](SECURITY.md). Do **not** open a public issue for vulnerabilities.
