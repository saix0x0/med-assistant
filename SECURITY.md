# Security policy

## Reporting a vulnerability

Please report security issues privately through
[GitHub's private vulnerability reporting](https://github.com/saix0x0/med-assistant/security/advisories/new)
rather than in a public issue. Include steps to reproduce and the affected
version or commit. You can expect an acknowledgement within a few days.

## Handling secrets

- API keys are read only from a local `.env` file, which is gitignored and never
  committed. `.env.example` lists the variables with empty values.
- Secret scanning with push protection is enabled on this repository, so commits
  containing recognised credentials are blocked.
- The public deployment configuration runs in mock mode and holds no keys.

## Supported versions

Security fixes are applied to the `main` branch.
