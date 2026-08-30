# MBTA Display

A CircuitPython project for the **Adafruit Matrix Portal M4** that shows upcoming
MBTA train departures on a 64×32 RGB LED matrix. It polls the
[MBTA V3 API](https://api-v3.mbta.com/) and scrolls the next few departure
times, one colored line per train.

As configured, it shows the next four **Blue Line** departures from
**Wonderland** (`place-wondl`) with `direction_id=0` — westbound, toward
Bowdoin. Wonderland is the eastern terminus, so that is every departing train.

`MBTA SCHEDULE.mp4` in the repo root is a recording of the display running.

This project was inspired by Jorge Enrique Gamboa Fuentes's
[Train_schedule_board](https://github.com/jegamboafuentes/Train_schedule_board).
See [Credits and provenance](#credits-and-provenance).

## Hardware

- [Adafruit Matrix Portal M4](https://www.adafruit.com/product/4745)
- A 64×32 RGB LED matrix panel
- 5V power supply rated for the matrix (a 64×32 panel can draw ~2–4A at full
  brightness)

Developed against CircuitPython 8.2.4:


## Repository layout

| Path                  | Description                                                              |
| --------------------- | ------------------------------------------------------------------------ |
| `code.py`             | The whole program. CircuitPython runs it automatically on boot.          |
| `lib/`                | CircuitPython library bundle — copy verbatim to the board.               |
| `fonts/`              | BDF bitmap fonts. `tom-thumb.bdf` (3×5) is the one `code.py` uses.       |
| `Tblue-dashboard.bmp` | Bitmap asset for the display.                                            |
| `MBTA SCHEDULE.mp4`   | Demo recording of the display in operation.                              |
| `.vscode/settings.json` | Pylance paths and CircuitPython board version for editing in VS Code.  |
| `.gitignore`          | Excludes `secrets.py`, `boot_out.txt`, `.DS_Store`, and the `.MOV` demo. |

`secrets.py` lives on the board but is **deliberately not tracked in git** — it
holds Wi-Fi and Adafruit IO credentials.

## Setup

1. **Flash CircuitPython** onto the Matrix Portal M4 (8.x). Double-tap the reset
   button, drag the `.uf2` onto the `MATRIXBOOT` drive, and the board reappears
   as `CIRCUITPY`.

2. **Copy the project files** to the root of `CIRCUITPY`:

   ```
   code.py
   lib/
   fonts/
   ```

3. **Create `secrets.py`** on the board:

   ```python
   secrets = {
       "ssid": "YOUR_WIFI_SSID",
       "password": "YOUR_WIFI_PASSWORD",
       "timezone": "America/New_York",
       "aio_username": "YOUR_ADAFRUIT_IO_USERNAME",
       "aio_key": "YOUR_ADAFRUIT_IO_KEY",
   }
   ```

   A free [Adafruit IO](https://io.adafruit.com/) account supplies the time
   service used by `get_local_time()`. `timezone` must be a
   [tz database name](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones).

4. **Power the board.** It runs `code.py` on boot. Connect to the USB serial
   console (`screen /dev/tty.usbmodem* 115200` on macOS, or the Mu editor) to
   watch the status output.

## Configuration

All tunable values are constants at the top of `code.py`:

| Constant             | Default              | Purpose                                                                                |
| -------------------- | -------------------- | -------------------------------------------------------------------------------------- |
| `DISPLAY_NUM_GUIDES` | `4`                  | How many upcoming trains to display. One text row each.                                |
| `DATA_SOURCE`        | Blue Line @ Wonderland | MBTA predictions query. See below.                                                   |
| `FONT`               | `/fonts/tom-thumb.bdf` | Label font. Swap for `6x10.bdf` or `helvR10.bdf` for larger text and fewer rows.     |
| `TEXT_COLORS`        | red, blue, purple, green | Per-row colors, cycled with `i % len(TEXT_COLORS)`.                                |
| `SCROLL_DELAY`       | `0.03`               | Seconds between scroll steps. Lower is faster.                                         |

### Targeting a different stop or line

`DATA_SOURCE` is a URL-encoded MBTA predictions query. The parameters that
matter:

| Parameter              | Meaning                                                    |
| ---------------------- | ---------------------------------------------------------- |
| `filter[stop]`         | Stop ID, e.g. `place-wondl` for Wonderland.                |
| `filter[route]`        | Route ID, e.g. `Blue`, `Red`, `Orange`, `CR-Newburyport`.  |
| `filter[direction_id]` | `0` or `1`. Meaning is route-specific.                     |
| `page[limit]`          | Max predictions returned.                                  |
| `sort`                 | `departure_time` puts the soonest train first.             |

Find stop IDs with a browser:

```
https://api-v3.mbta.com/stops?filter[route]=Blue
```

Confirm which `direction_id` you want by checking `direction_destinations` on
the route:

```
https://api-v3.mbta.com/routes/Blue
```



## How it works

1. On startup — and every 900 seconds after — `matrixportal.get_local_time()`
   syncs the board clock through Adafruit IO. A failure is retried rather than
   fatal.
2. `get_train_times()` fetches the predictions endpoint and pulls
   `attributes.departure_time` from the first `DISPLAY_NUM_GUIDES` results.
3. `format_time()` splits the ISO-8601 timestamp (`2025-02-06T19:15:00-05:00`)
   and reformats it as `7:15 PM`.
4. `update_display()` writes `Train N: 7:15 PM` into each label.
5. `matrixportal.scroll_text(SCROLL_DELAY)` scrolls all rows once, then the loop
   repeats from step 2.

On an API error the display shows `Train N: Error`; if fewer predictions come
back than requested, it shows `Train N: No Data`.

## Known limitations

These are real behaviors of the current `code.py`, worth knowing before you
extend it:

- **Midnight hour renders as `0:MM AM`.** `format_time()` maps hours above 12
  down by 12 but never maps hour `0` up to `12`, so 12:15 AM displays as
  `0:15 AM`.
- **No delay between API calls.** The loop re-fetches on every scroll cycle, so
  the request rate is bounded only by how long a scroll pass takes. The MBTA API
  rate-limits unkeyed clients; a `time.sleep()` or a fetch interval check would
  be gentler.
- **All-or-nothing fallback.** If the API returns fewer than
  `DISPLAY_NUM_GUIDES` predictions — common late at night — *every* row shows
  `No Data`, including rows that had a valid train.
- **The synced clock is not actually used for display.** Times are formatted
  straight from the API strings, so `get_local_time()` only matters if you add
  countdown ("arriving in 4 min") logic later.
- **UTC-offset parsing assumes a negative offset.** `format_time()` strips the
  offset by splitting on `-`, which works for US Eastern but would fail east of
  Greenwich.
- **`page[limit]=6`** fetches six predictions while only four are displayed.

## Troubleshooting

| Symptom                                | Likely cause                                                                             |
| -------------------------------------- | ---------------------------------------------------------------------------------------- |
| Blank display, no serial output        | `code.py` not at the root of `CIRCUITPY`, or the board is in safe mode — check `boot_out.txt`. |
| `ImportError: no module named 'adafruit_matrixportal'` | `lib/` missing or incomplete on the board.                               |
| Status NeoPixel stuck                  | Wi-Fi association failing. Verify `ssid`/`password` and that the network is 2.4 GHz.     |
| `Time sync failed, retrying`           | Bad `aio_username`/`aio_key`, or an invalid `timezone` string.                            |
| All rows read `Error`                  | MBTA API unreachable or the query is malformed — paste `DATA_SOURCE` into a browser to test. |
| All rows read `No Data`                | Fewer predictions available than `DISPLAY_NUM_GUIDES` (service ended for the night).      |
| Flickering or dim panel                | Power supply undersized for the matrix.                                                   |

## Security note

`secrets.py` is gitignored, but the file on your board holds a live Wi-Fi
password and Adafruit IO key in plaintext. Never commit it, and rotate the
Adafruit IO key from your account page if it is ever exposed.

## Credits and provenance

This project was inspired by and began from Jorge Enrique Gamboa Fuentes's
**[Train_schedule_board](https://github.com/jegamboafuentes/Train_schedule_board)**,
an MBTA arrival board for the same Matrix Portal hardware. Jorge wrote up the
original build [on Medium](https://jegamboafuentes.medium.com/i-created-my-own-subway-arrival-board-with-real-time-data-to-dont-miss-my-train-anymore-28bfded312c0).
Full credit for the original concept goes there.

What carried over from that project:

- The MBTA predictions query structure in `DATA_SOURCE` — the same stop
  (`place-wondl`), route (`Blue`), and `direction_id`.
- `Tblue-dashboard.bmp`, a background bitmap from the original project. It is
  not currently loaded by `code.py`.

What is different here:

- The display logic was rewritten against the high-level
  `adafruit_matrixportal.MatrixPortal` API instead of the lower-level
  `Matrix` / `Network` / `displayio` approach used upstream.
- Departures are shown as **absolute clock times** (`7:15 PM`) on scrolling
  labels, rather than as a **countdown in minutes** on static labels.
- Four trains are rendered from a loop, instead of three tracked individually.

### Third-party components

| Component | Source | Terms |
| --- | --- | --- |
| `lib/adafruit_*` | [Adafruit CircuitPython Bundle](https://github.com/adafruit/Adafruit_CircuitPython_Bundle) | MIT |
| `fonts/tom-thumb.bdf` | Robey Pointer | MIT |
| `fonts/6x10.bdf` | X.org misc-fixed | Public domain |
| `fonts/helvB12.bdf`, `fonts/helvR10.bdf` | Adobe Systems / Digital Equipment Corporation | Permissive X11 font license; the embedded copyright notice must be retained |
| Upstream project | [jegamboafuentes/Train_schedule_board](https://github.com/jegamboafuentes/Train_schedule_board) | No license specified by the author |

## References

- [MBTA V3 API documentation](https://api-v3.mbta.com/docs/swagger/index.html)
- [Adafruit MatrixPortal M4 guide](https://learn.adafruit.com/adafruit-matrixportal-m4)
- [`adafruit_matrixportal` library docs](https://docs.circuitpython.org/projects/matrixportal/en/latest/)
