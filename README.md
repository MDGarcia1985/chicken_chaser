# Chicken Chaser

Prototype **0.1.0**, revision **1**. Production revision remains unset. Autonomous motion readiness remains **false**.

The runnable host application acquires a synthetic person target, retains it by spatial association, computes proportional steering, and sends versioned commands into the actual portable C++ motor-enforcement core. The local operator page shows detection boxes, selected target, behavior, sensor validity/age, requested/applied normalized PWM, faults, arm/disarm, fault clear and stop. It exercises target loss, ambiguity, obstacles and bridge loss without energizing motors.

Physical deployment is incomplete: installed UNO Q APIs, real payloads, pin capabilities, sensor library and electrical/timing evidence are unavailable in this workspace. Hardware enable is rejected by the runtime schema. The UNO Q sketch is a **stopped diagnostic RPC scaffold**, not a GPIO-connected motor application. Do not interpret its acknowledgement as a physical stop or power disconnect. Disconnect motor power while bringing up that scaffold.

## Run on a development host

Requirements: Python 3.11+ and a C++17 GCC compiler (`g++`). Use the source checkout and an editable install; the schemas and runtime authority live in this checkout. A standalone wheel installation is not supported by this revision.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-host.lock
python -m pip install --no-deps -e .
python tools/create_schemas.py
python tools/build_host.py
python -m unittest discover -s tests -v
.\build\core_tests.exe
python -m chicken_chaser.runtime --demo --seconds 3
python -m chicken_chaser.runtime --ui
```

On Linux, activate with `source .venv/bin/activate`, run `./build/core_tests`, and use the same Python commands. `CXX` may point to a GCC executable. The host builder generates the MCU configuration, compiles with `-Wall -Wextra -Werror`, and produces a simulation shared library. It never uploads firmware. Windows embeds GCC runtime dependencies to avoid an unconfigured DLL search path.

Open **http://127.0.0.1:7000** for the desktop view. It starts disarmed; **Arm simulation** explicitly enables the synthetic turn-only demonstration. The scene uses synthetic 640×480 records and synthetic range samples. Switch scenarios to exercise loss/ambiguity/obstacle/watchdog stops. Restore Tracking, clear a latched fault when inputs are healthy, and explicitly rearm. Following is disabled by default. A person proxy is not evidence of chicken recognition.

Controls bind to loopback and require a per-run token and local Host/Origin. Do not expose or proxy the port to a network. Polling status never renews a drive command. Preview is explicitly unavailable: the canvas displays synthetic boxes, not live camera frames.

For this session dependencies were installed into ignored `.deps`. To reproduce that layout in PowerShell, use `$env:PYTHONPATH="$PWD\src;$PWD\.deps"`. Python 3.13 and GCC 15.2.0 were used for the recorded checks. Some sandbox tests needed explicit loopback network access; see TEST_LOG.

## Source and authority

| Location | Responsibility |
|---|---|
| `chicken_chaser_master.yaml` | Canonical inventory, owner hardware statement and original hackathon metadata |
| `config/chicken_chaser_architecture.yaml` | Proposed architecture; not runtime wiring |
| `config/runtime.yaml` | Versioned runtime authority; unresolved hardware values are null |
| `schemas/` and `tools/create_schemas.py` | Generated closed JSON Schemas and their reproducible source |
| `tools/generate_mcu.py`, `firmware/generated_config.hpp` | Validated authority → C++ simulation constants and configuration digest |
| `firmware/core.*`, `firmware/host_api.cpp` | Independent motor drivers, ranging, lease/watchdog enforcement and host ABI |
| `src/chicken_chaser/` | Contracts, perception, target behavior, bridge, runtime, recording and local operator view |
| `app_lab/python/` | Preserved console baseline and stopped live-camera diagnostic WebUI |
| `firmware/uno_q/` | Router Bridge diagnostic scaffold; no physical driver binding |
| `tools/probe_uno.py` | Installed-version/API and raw-payload inspection |
| `tests/` | Host critical regression suite |
| `DEVNOTES.md`, `TEST_LOG.md` | Append-only decisions, failures, retests and explicit device blockers |

The owner-declared `hardware_verified: true` remains in the master, without being extended to any subsystem test. Presentation/publishing are historical deliverables; this implementation does not publish anything. The supplied brief, architecture and standards were preserved.

## Bring up the existing camera on UNO Q

1. Keep motor power disconnected. In the installed App Lab environment, run `app_lab/python/baseline.py` as the only camera application. It preserves automatic camera selection, `Camera(resolution=(640,480), fps=30)`, confidence 0.5, debounce 0, `on_detect_all` and `App.run`.
2. Stop the baseline before probing. Run `python tools/probe_uno.py > captures/device-inventory.json` after creating `captures/`. The inventory reports installed classes, signatures, source, package versions, core and library lists. It does not open a camera.
3. Run the probe separately with `--capture` to stdout or an explicitly chosen private output file. This owns one camera and prints complete callback records and **receipt** timestamps. Do not run it alongside the baseline or diagnostic app. Do not commit sensitive camera records.
4. Inspect actual negotiated frame width/height and stereo arrangement using the installed camera implementation and supported single-owner frame access. Requested 640×480 is not proof of negotiated dimensions. Choose one eye for horizontal stereo; confirm transformation with targets in each eye. Do not create another capture handle.
5. Verify box format, units, field names and capture clock/latency against those records. Only then fill the camera metadata and explicit payload mapping in runtime YAML. `vision.normalize` supports verified `xyxy`/`xywh` and pixels/normalized coordinates; the mapping is intentionally null today. Unknown capture timing without a measured latency bound cannot produce usable steering observations.
6. Inspect installed model labels and preprocessing; fill `config/model_manifest.json` using actual identity, artifact, dependency versions and evaluation/rollback information. `probe_uno.py --weights /actual/model.eim` prints a SHA-256 without storing weights in YAML/JSON. A generic bird class does not establish chicken-specific accuracy.

For WebUI diagnostics, copy/edit the installed working App Lab example and **retain its installed `app.yaml` brick/model declarations**. Add the repository Python package and dependencies to that app environment, use `app_lab/python/main.py`, and retain this repository layout so source schemas/assets can be found. This avoids inventing version-specific App Lab packaging. The diagnostic entrypoint uses the same single camera baseline and a guarded WebUI REST integration; it rejects arming. It requires installed `WebUI(addr, port, assets_dir_path, cors_origins)` and `expose_api`. The source-derived URL is **http://127.0.0.1:7000 on the board**; actual device execution is BLOCKED in TEST_LOG. No supported shared-stream preview has been verified.

Arduino's upstream [WebUI implementation](https://github.com/arduino/app-bricks-py/blob/main/src/arduino/app_bricks/web_ui/web_ui.py) and [Router Bridge](https://github.com/arduino-libraries/Arduino_RouterBridge) informed the scaffold. Installed versions must still be checked. The native Router transport is MessagePack-RPC; JSON Schemas describe logical records, not its wire encoding.

## Wiring and verification

| Component | Required mapping/settings | Current runtime value |
|---|---|---|
| Left DRV8871 | IN1, IN2, PWM capability/resolution, polarity | null, unverified |
| Right DRV8871 | IN1, IN2, PWM capability/resolution, polarity | null, unverified |
| Driver VM / ILIM | Measured supply, current limit and motor/current suitability | null, unverified |
| TF-Luna | Dedicated MCU UART/RX/TX, actual baud/framing/levels and output format | null, unverified |
| VL53L0X | Actual breakout, supply/pullups, bus/SDA/SCL, address, compatible library and bounded I2C transactions | null, unverified |
| Camera | Negotiated dimensions, stereo view, callback mapping, capture timing/latency | null, unverified |
| MCU loop | Period, worst-case execution time, PWM/timer conflicts, watchdog and reversal/stopping time | null, unverified |

DRV8871 VM requires **6.5–45 V**; 5 V at VM is invalid. PWM limiting cannot correct an invalid supply. Verify the actual power topology, motor voltage/current limits and common ground. The IC truth table used by the portable driver is 00 coast/sleep, 10 forward, 01 reverse, 11 brake; see the [TI datasheet](https://www.ti.com/lit/ds/symlink/drv8871.pdf). The breakout and actual physical stop still need verification.

The parser supports TF-Luna's default nine-byte centimetre output, additive checksum and signal-strength validity, normalized to millimetres. The manufacturer's documented UART default is 115200 8N1; these are **not confirmed settings of this sensor**, so runtime baud remains null. See the [Benewake manual](https://en.benewake.com/uploadfiles/2025/04/20250430174515390.pdf). Rear ranging has a host-tested bounded asynchronous adapter contract; a compatible UNO Q library and bus timeout implementation are still required.

Essential unresolved inputs:

- Actual battery/compute/motor rail arrangement, VM measurement, common ground, breakout current limits and ratings.
- Verified MCU motor/UART/I2C pins, motor polarity, PWM/timer capabilities and installed core/library versions.
- Installed detection payload, negotiated image/eye layout, source frame identity and defensible capture-to-control latency bound.
- Actual model identity, labels, weights/preprocessing and intended chicken or bench-proxy target.
- Measured range quality/freshness, loop cadence, stopping/reversal/watchdog limits and clear turn test area.
- Canonical contact and project license confirmation.

Follow [docs/PHYSICAL_VALIDATION.md](docs/PHYSICAL_VALIDATION.md) in order. The next physical test is power/common-ground inspection and VM measurement with motor outputs disconnected. Raised-track motor tests follow verified pins and sensor integration, then bounded floor tests. Software disarm is not a power disconnect. Neither beam proves the complete swept volume of a turn or detects cliffs.

## Behavior and safety contracts

See [docs/CONTRACTS.md](docs/CONTRACTS.md) and [docs/CONFIGURATION.md](docs/CONFIGURATION.md). Boot is disarmed; acquisition emits stopped commands until several unique fresh frames agree. Targets are associated by class, proximity and overlap. Ambiguity/loss stops and requires explicit operator rearm in the connected runtime. Faults require explicit clearing. A new session/generation, ordered sequence, one-use MCU epoch, increasing observation ID and bounded lifetime prevent old queued commands/heartbeats from extending an earlier drive observation.

The control core must run independently on the MCU for real watchdog guarantees. The host shared-library simulation runs in Python's process and cannot guarantee physical stopping after Python termination. Tests exercise continued C++ ticks without new commands; an actual process kill and bridge disconnect remain physical tests.

Simulation thresholds (400 mm clearance, 250 ms sensor age, 150 ms lease/vision age, 0.25 maximum duty, 100 ms reversal dwell) are **physically unvalidated defaults**. Following is separately opt-in; autonomous reverse, mapping, RF, cliff sensors, servo and online learning remain disabled/deferred. Optional observation recording defaults off and stops at 1000 normalized frames per session; records are candidate detections for later labeling, not ground truth or trained weights.

## Attribution and licensing

Michael Garcia: design, planning, research and programming. Codex / ChatGPT: drafts, research assistance and agentic programming against validated schemas. [DC-Motor-Control](https://github.com/MDGarcia1985/DC-Motor-Control/tree/23c73c13026c9115eb902fcecd66f7b8271b6047) was reviewed at commit `23c73c13026c9115eb902fcecd66f7b8271b6047`, including all five sources, four headers, README, PlatformIO configuration and MIT license. Its separated responsibilities inspired this implementation; AVR pins/settings, full-output startup, zero-as-clear sensing and automatic reverse were not carried over.

Arduino-derived baseline/diagnostic example files retain MPL-2.0 notices and source. See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) and `LICENSES/`. Project-wide licensing and canonical contact remain pending confirmation; no blanket license is assigned to all components.
