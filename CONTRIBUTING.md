# Contributing

1. **Set up:** `uv venv && uv pip install -e ".[dev]"`.
2. **Checks before a pull request:** `ruff check src tests`, `mypy`, `pytest`. Run `mypy` and `pytest` in a
   fresh Python 3.10 environment too: CI installs newer type stubs than a long-lived dev environment.
3. **Never commit data** or third-party PDFs (`.gitignore` already excludes them).
4. **Do not tune the library to match a published figure.** If a figure does not reproduce, record it
   with a note in `src/pyssms/validation/data/*.yaml` and set its `expected` status honestly.
5. Regenerate `docs/validation.md` after any change that can move an estimate.
6. Releases: bump the version in `pyproject.toml` and `src/pyssms/__init__.py`, update `CHANGELOG.md`,
   tag `vX.Y.Z` and publish a GitHub release; the `release` workflow uploads to PyPI.
