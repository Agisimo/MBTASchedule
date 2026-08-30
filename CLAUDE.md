# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A CircuitPython firmware project for an **Adafruit Matrix Portal M4** driving a
64×32 RGB LED matrix. It polls the MBTA V3 API and scrolls the next four Blue
Line departures from Wonderland.

Read `README.md` first — it documents the hardware, the `DATA_SOURCE` query
parameters, known limitations in the current code, and the project's provenance
(it began from [jegamboafuentes/Train_schedule_board](https://github.com/jegamboafuentes/Train_schedule_board),
which is unlicensed).

## There is no build, test, or lint tooling

This is important and non-obvious. Do not look for `package.json`,
`requirements.txt`, `pytest`, `tox`, or a virtualenv — none exist and none
should be added without asking. Specifically:

- **No build step.** `code.py` is deployed as source.
- **No test suite.** The code has hardware dependencies (`board.NEOPIXEL`, the
  matrix panel, the ESP32 co-processor) and cannot run on the host machine.
  `import board` fails outside CircuitPython.
- **No linter configured.** `.vscode/settings.json` only suppresses Pylance's
  `reportMissingModuleSource` / `reportShadowedImports`, because the
  `adafruit_*` modules resolve to stubs rather than real host packages.

Verification means deploying to the board and reading the serial console.
Static reasoning about `code.py` is the only check available in-session.

## Deploying and running

The board mounts as a USB drive named `CIRCUITPY`. Deployment is a file copy:

```bash
cp code.py /Volumes/CIRCUITPY/
cp -r lib fonts /Volumes/CIRCUITPY/
```

CircuitPython **auto-reloads and re-runs `code.py` the moment it is written**,
so a copy is the whole deploy-and-restart cycle. Watch the output over serial:

```bash
screen /dev/tty.usbmodem* 115200     # Ctrl-A K to exit
```

`code.py` prints its fetch results and errors, which is the primary debugging
channel.

## Architecture

**`code.py` is the entire application** — roughly 80 lines, no local imports.
Any change to program behavior happens there.

The control flow is a single `while True` loop that does three things per
iteration: refresh the clock via Adafruit IO every 900s, fetch and format
predictions, then call `matrixportal.scroll_text()` once. The scroll call is
blocking and effectively sets the polling interval — there is no explicit
`sleep`.

**It uses the high-level `MatrixPortal` API**, not the lower-level
`Matrix` / `Network` / `displayio` layer. `matrixportal.add_text()` returns
integer label indices that `set_text(text, index)` writes into. If you consult
the upstream project or older Adafruit guides for reference, note they use the
`displayio.Group` approach and are not directly transferable.

**Display geometry is a hard constraint.** Labels are positioned at
`y = i * 8 + 3` on a 32-pixel-tall panel, which fits exactly four rows (y = 3,
11, 19, 27). Raising `DISPLAY_NUM_GUIDES` past 4 renders rows off-screen unless
the spacing changes too.

**Configuration lives in module-level constants** at the top of `code.py`
(`DISPLAY_NUM_GUIDES`, `DATA_SOURCE`, `FONT`, `TEXT_COLORS`, `SCROLL_DELAY`).
Prefer changing these over threading new parameters through functions.

## Vendored and untracked files

- **`lib/`** is a vendored copy of the Adafruit CircuitPython bundle, mostly
  precompiled `.mpy` bytecode. Treat it as read-only — never edit or hand-patch
  it. Update it by replacing modules from an official bundle release matching
  the board's CircuitPython version.
- **`fonts/`** are BDF bitmaps. `tom-thumb.bdf` (3×5) is the one in use; the
  others are larger alternatives that would reduce the row count.
- **`secrets.py` is gitignored but required at runtime.** It defines a
  `secrets` dict with `ssid`, `password`, `timezone`, `aio_username`, and
  `aio_key`. `MatrixPortal` reads it implicitly at construction — there is no
  explicit import of it in `code.py`. It contains live credentials; never read
  its values into output, commit it, or include it in a diff.
- **`Tblue-dashboard.bmp`** is inherited from the upstream project and is **not
  loaded by the current code**. Do not assume it is live.

## CircuitPython, not CPython

Target is CircuitPython 8.2.4 (see `boot_out.txt` on the board). When writing
code here:

- No `pip`, no third-party packages beyond what is physically in `lib/`.
- The standard library is a small subset. `datetime` is unavailable in core;
  `adafruit_datetime` provides a partial implementation.
- Memory is tight (SAMD51, ~192KB RAM). Avoid accumulating large structures;
  the JSON response is already near the practical ceiling.
- f-strings are supported on 8.x.
- Exceptions on this board are frequently network-related and transient — the
  existing code catches broadly and degrades to placeholder text rather than
  crashing, since a crash means a dark display until physical reset.

## Known issues

`README.md` has a "Known limitations" section listing real defects in the
current code — including that `format_time()` renders the midnight hour as
`0:MM AM`, that the loop re-fetches with no delay, and that a short prediction
list blanks all four rows rather than just the empty ones. These are documented
rather than fixed; check that section before treating one as a new discovery.
