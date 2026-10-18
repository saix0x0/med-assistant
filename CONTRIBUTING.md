# Contributing

Thanks for your interest in Med Assistant.

## Getting set up

```bash
bash run.sh                          # app on http://localhost:8077, mock mode
.venv/bin/python -m pytest -q        # unit tests
```

No API key is needed for development: the mock provider runs everything offline.

## Making a change

1. Open an issue first for anything larger than a small fix, so the approach can
   be agreed before you write code.
2. Fork the repository and create a branch from `main`.
3. Keep model calls inside `app/providers/`. Decisions about medicines (matching,
   dosing, expiry, verdicts) belong in `app/core/` and must be covered by tests.
4. Run the tests, then open a pull request describing what changed and why.

Changes to `main` go through pull requests and require passing CI.

## Code of conduct

This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
