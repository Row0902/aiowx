# aiowx v0.2.1 — CI/CD, security & branching

Run asyncio coroutines with wxPython GUI — now with CI/CD, security scanning, and a structured branching model.

## Quick path

```bash
pip install aiowx==0.2.1
```

Already using it? Update your lockfile:

```bash
uv sync
```

## What's new

| Area | Change |
|------|--------|
| **Continuous Integration** | Matrix tests on Python 3.12–3.14 with type checking (`ty`), lint/format (`ruff`), and coverage (`pytest --cov=src`, ≥80 %). Runs on every push and PR. |
| **Security** | CodeQL Advanced on every push/PR. Ruff bandit (S) rules active. Dependency review blocks vulnerable deps at PR time. |
| **Supply chain** | Dependabot opens grouped PRs weekly. Trusted publishing to PyPI — no secrets needed. |
| **Branching** | `canary` is now the default development branch. `main` is protected with PR-only merges and linear history. Feature branches fork from `canary`. |

## Branch model

```
canary (default)          main (stable)
      │                       │
      ├── feature/x ── PR →   │
      ├── fix/y ────── PR →   │
      └── ... ──────── PR →   │
                              │
        canary ──────── PR → main
```

## Verification checklist

- [ ] CI passes for the three Python versions (3.12, 3.13, 3.14)
- [ ] `ruff check` passes with zero warnings (bandit S rules included)
- [ ] `ty src/` reports no type errors
- [ ] `pytest --cov=src` reports ≥80 % coverage
- [ ] Dependabot PRs run full CI before merge

## Next steps

- Open a PR against `canary` with your feature or fix.
- See `CHANGELOG.md` for the full release history.
