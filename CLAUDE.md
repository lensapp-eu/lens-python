# CLAUDE.md

`lens-debug` on PyPI: the public Python client that sends debug payloads to
the Lens desktop app (`127.0.0.1:23600`) and Lens Cloud
(`https://app.lensapp.eu`). Python 3.7+, standard library only.

## Layout

- `lens_debug/__init__.py`: the whole client. Payloads go out on a
  background worker thread and are drained at exit, so `lens()` never blocks
  or raises in the host app.
- `pyproject.toml`: setuptools build, package metadata.

Env vars: `LENS_HOST`, `LENS_PORT`, `LENS_LOCAL`, `LENS_CLOUD`,
`LENS_PROJECT_KEY`, `LENS_CLOUD_URL`.

## Releases

Bump `version` in `pyproject.toml` and `__version__` in
`lens_debug/__init__.py` together, then publish a GitHub Release. The
`Release` workflow builds and uploads through PyPI Trusted Publishing (OIDC,
no token). The trusted publisher on PyPI points at `release.yml`: renaming
that file breaks publishing.
