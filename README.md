# Lens for Python

Send debug payloads to the [Lens](https://lens.lensapp.eu) desktop app and [Lens Cloud](https://app.lensapp.eu) from any Python project (Django, Flask, FastAPI or plain scripts). No dependencies, just the standard library.

## Install

```bash
pip install lens-debug
```

## Use

```python
from lens_debug import lens

lens("hello", user)                 # send any values
lens([1, 2, 3]).label("my array")   # add a label
lens("careful").red()               # colour the entry
lens.clear()                        # clear the Lens window
```

Colours: `red`, `green`, `blue`, `orange`, `purple`, `gray`.

## Lens Cloud (optional)

To send events straight to [Lens Cloud](https://app.lensapp.eu), no desktop app required, set one
environment variable:

```bash
LENS_PROJECT_KEY=your-project-key-from-lens-cloud
```

With a key set, events go to Lens Cloud at `https://app.lensapp.eu` by default. Set `LENS_CLOUD_URL`
only to point at a self-hosted or local cloud (e.g. `http://localhost:3000`). You can also configure
it in code:

```python
lens.configure(key="your-project-key")  # cloud_url defaults to https://app.lensapp.eu
```

### Channels

Lens sends to two channels, independently toggleable (default on):

```bash
LENS_LOCAL=false   # disable the desktop app -> cloud only
LENS_CLOUD=false   # disable the cloud -> desktop app only
```

Or in code: `lens.configure(local=False)` / `lens.configure(cloud=False)`.

Each event also carries context (Python version, OS, hostname and detected framework) which shows
up as tags in Lens Cloud.

### Caught exceptions

```python
try:
    risky()
except Exception as err:
    lens.exception(err)
```

The exception (with its stack trace) shows up in Lens and can be picked up by the built-in "Summarize errors" AI button.

## Configuration

Lens listens on `127.0.0.1:23600` by default. Override it in code or via environment variables:

```python
lens.configure(host="127.0.0.1", port=23600)
```

```bash
export LENS_HOST=127.0.0.1
export LENS_PORT=23600
```

## Safety

Debugging never blocks or crashes your program: every payload is sent on a daemon thread and all transmission errors are swallowed silently. If the Lens app is not running, calls are simply no-ops.

MIT licensed.
