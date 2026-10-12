# Codex implementation prompt — Chicken Chaser prototype revision 1

Implement the Chicken Chaser application in the current project repository. This is production project work: write the implementation, contracts, documentation, and meaningful tests. Do not use a teaching-only or pseudocode-only workflow.

## Read and respect the project

This project starts with documents only. There is no existing README, AGENTS.md, source tree, or test suite. Do not spend time searching for nonexistent project scaffolding or treat its absence as a blocker. Do not create AGENTS.md unless separately requested.

Read these supplied documents before implementing:
- `chicken_chaser_master.yaml` (normalized successor to the supplied extensionless `chicken_chaser_master`);
- `chicken_chaser_brief.md`;
- `docs/chicken_chaser_architecture.md`;
- `config/chicken_chaser_architecture.yaml`;
- all standards in `docs/`, including `ANNOTATION_STANDARDS.md`, `DEVNOTES_STANDARDS.md`, and `TEST_LOG_STANDARDS.md`.

If the original attachments are still at repository root, place the three standards in docs/ without changing their content. Use one canonical master, updating references rather than keeping contradictory active copies. The normalized master removes the duplicate schema_version and adds the USB camera, TF-Luna UART and VL53L0X I2C interfaces. Preserve its hackathon timestamps, prototype version 0.1.0, prototype_revision 1, production_revision null, and owner-declared hardware_verified value. The proposed architecture does not assert subsystem verification. Keep ready_for_autonomous_motion false until documented physical validation supports an explicit change.

The brief and architecture are implementation-baseline drafts prepared from the owner's directions. Explicit hardware decisions here supersede older contradictory assumptions. Record material reconciliations in DEVNOTES. Null pins, electrical settings and timing values remain unresolved prerequisites that inhibit motion; never guess wiring. The architecture YAML is a design document, not validated runtime configuration. Create and validate runtime schemas before dependent implementation.

Create the README, source layout, machine-readable schemas, meaningful tests, DEVNOTES.md, and TEST_LOG.md as deliverables. Preserve unrelated changes. Historical hackathon deliverables do not require another presentation or authorize publishing. Complete unblocked implementation subject to the test gates; gather essential unresolved hardware questions in one concise list.

Apply the supplied standards literally:
- Source headers identify path, responsibility, owner/contributors, contact, license, relevant constraints and DEV IDs. Use Pending confirmation for genuinely unknown contact/license data. Preserve third-party notices.
- Document material functions with Purpose, Design, Workflow and Data Handoff, including units, errors and side effects as needed.
- DEVNOTES and TEST_LOG are append-only. Never rewrite an existing entry to change status or insert later evidence. Assign new dated IDs and preserve failures.
- Use every required entry section, actual timestamps with timezone, and the exact DEV entry separator of two horizontal rules separated by a blank line. TODO/FIXME references must point to real DEV records.
- T0 validates each new/materially changed implementation file; T1 exercises a usable module; T2 exercises a boundary; T3 checks a milestone. Record actual evidence and distinguish PASS, FAIL, BLOCKED, NOT_EXECUTED, STATIC_ONLY and PARTIAL.
- Failed T1/T2/T3 blocks progression except investigation/correction or an authorized engineering exception documenting scope, risk, owner and resolution condition. Do not self-authorize an exception merely to finish.
- Simulated or static validation does not establish physical behavior. Do not claim device tests, camera accuracy, motor timing or autonomous readiness without evidence.

## Reference implementation to inspect

Inspect https://github.com/MDGarcia1985/DC-Motor-Control including source, headers, README, platformio.ini, and LICENSE. The source reviewed for this prompt was commit 23c73c13026c9115eb902fcecd66f7b8271b6047. Record the commit you actually use.

Useful inspiration:
- Separate motor, ranging, status, and application responsibilities.
- A signed motor-command interface and configurable deadband.
- Timed state transitions and rate-limited sensing.
- Avoid redundant hardware writes where doing so cannot suppress a required stop.

Adapt carefully:
- The reference targets an Uno R3, L293D, HC-SR04, OLED, and RGB LED. Chicken Chaser uses UNO Q, two DRV8871s, UART TF-Luna, and VL53L0X. Do not copy AVR settings, COM8, pin assignments, or unrelated peripheral dependencies.
- Reference setup commands 100% motor output. Our startup must be stopped and disarmed.
- Reference ranging collapses invalid/time-out measurements to zero and treats zero as a clear path/full speed. Our measurements must distinguish valid, invalid, stale, and unavailable.
- Reference pulseIn() can block for its timeout despite nonblocking descriptions. Keep our control loop and sensor handling bounded.
- Reference stop/coast/brake comments conflict for the L293D configuration. Implement the DRV8871 behavior from its verified truth table.
- Do not carry over the automatic reverse maneuver triggered by a large distance. Recovery must be explicit and clearance-aware.

Preserve MIT notices for reused reference code. Preserve Arduino MPL-2.0 attribution and applicable obligations for derived example code; document component licenses rather than assigning one blanket license without review.

## Hardware and scope

- One Arduino UNO Q: Python on Debian for vision/behavior; C++ on the STM32 for real-time motor control, ranging, and motion inhibition.
- One Waveshare AR0144 Stereo USB Camera (A), connected by USB-C through the Acer hub. It is already automatically detected as CCB Camera by the supplied script. Real detection callbacks have been observed.
- One front TF-Luna using **UART**, not I2C.
- One rear VL53L0X ToF sensor using I2C; verify the actual breakout supply and pull-up requirements.
- Two nominal 7.5 V brushed DC motors, independently driven by two DRV8871 boards.
- Battery pack and Acer USB hub. Resolve the actual motor and compute power arrangement from project wiring. DRV8871 VM requires at least 6.5 V; 5 V at VM is not a valid operating configuration. Motor PWM limiting does not change that supply requirement.
- No wheel encoders are established. PWM is a command, not measured velocity.
- Servo tilt, limit switches, four harvested cliff sensors, RF positioning, and mapping are outside this minimal build unless current authoritative project documents explicitly enable them. Do not invent their presence or verification.

## Preserve the working vision baseline

Start from this user-tested Python example. Keep automatic camera selection and the existing working capture path unless evidence requires a change. The baseline is console-only; it does not contain a Web UI.

```python
# SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
#
# SPDX-License-Identifier: MPL-2.0

# Example app to detect objects in a video stream from the camera and log the results to the console.

from arduino.app_utils import App, Logger
from arduino.app_bricks.video_objectdetection import VideoObjectDetection
from arduino.app_peripherals.camera import Camera

CONFIDENCE_THRESHOLD = 0.5
logger = Logger("VideoObjectDetectionApp")

camera = Camera(resolution=(640, 480), fps=30)

detection_stream = VideoObjectDetection(
    camera=camera,
    confidence=CONFIDENCE_THRESHOLD,
    debounce_sec=0.0,
)

def send_detections_to_console(detections: dict):
    for key, values in detections.items():
        for value in values:
            logger.info(
                f"Detected {key} with confidence {value.get('confidence', 'N/A')}"
            )

detection_stream.on_detect_all(send_detections_to_console)

App.run()
```

Reference: https://docs.edgeimpulse.com/hardware/deployments/run-arduino-app-lab#object-detection

Inspect the installed App Lab/Brick versions and their real API. Capture complete detection records before defining the adapter. Do not invent bounding-box field names or assume older label-to-confidence callback semantics. Define a validated internal detection record containing label, confidence, box/centroid, coordinate convention, frame dimensions, frame identifier, and available timing information.

Confirm the negotiated image dimensions and stereo layout. If the stream contains two eye views, establish the correct processing view and coordinate transform; avoid duplicate targets and steering toward the combined image center by mistake. Preserve a single owner of camera capture. Do not open a competing camera connection just to provide preview.

Determine whether capture timestamps are available. Receipt time is not capture time. Record inference/transport latency limitations and reject stale observations using a defensible freshness mechanism. Keep queues bounded and prefer the newest observation.

Use the installed model first. Verify its labels: a generic bird label is not a demonstrated chicken-specific classifier. Make target class configurable, with a person/proxy option for bench validation. Keep model identity, weights artifact reference, checksum when accessible, labels, preprocessing, confidence threshold, and dependency versions in a manifest. YAML/JSON reference weight files; they do not contain numerical weights.

## C++ responsibilities

Implement separate DRV8871 motor instances with configurable pins, polarity, PWM limits, and deadband. Verify UNO Q pin capabilities, PWM API/resolution, and timer conflicts against the installed core. Use the correct target toolchain; do not assume the reference PlatformIO AVR configuration works.

Initialize physical outputs to the stopped state before handling commands. Provide explicit coast/stop and brake semantics, bounded acceleration, and a stop interval before reversal. A stop/fault must override ramping immediately at the command level. Software disarm must not be presented as a physical power disconnect.

Implement a bounded incremental TF-Luna UART parser using the manufacturer's protocol. Verify baud rate, framing, checksum, distance units, signal-quality validity, and sensor configuration. Handle partial frames, corrupt frames, garbage bytes, resynchronization, and timeouts. Timestamp valid samples locally. Reserve the correct MCU UART without conflicting with the bridge/debug connection.

Implement bounded VL53L0X acquisition using a library compatible with the UNO Q core. Handle initialization failure, invalid range status, I2C failure, and stale data. Normalize distance to a single documented unit.

Run motion enforcement at a documented configurable rate, with a 100 Hz target only if measured execution supports it. Keep bridge callbacks short and transfer commands safely to the control loop. A stalled Python process, broken bridge, expired command, invalid configuration, or required stale sensor must inhibit the relevant motion. Do not assume a rear beam proves clearance for a turn or that either beam provides full obstacle coverage.

## Python behavior

Implement a small state machine: DISARMED, ACQUIRING, TRACKING, TARGET_LOST, BLOCKED, and FAULT, or equivalent states consistent with repository standards.

Acquire a configured target across several fresh detections. Associate by class, spatial proximity, and box overlap; retain the selected target instead of switching to the highest-confidence object each frame. Stop on ambiguous association or target loss. Document that this does not guarantee persistent identity after occlusion or crossing targets.

Implement proportional visual steering with configurable aim point, deadband, gain, maximum turn command, and maximum forward command. Compute horizontal error from the actual processing-view coordinates. Start with a turn-only test mode; add slow forward following as a separate explicitly enabled mode. Do not infer physical velocity from PWM.

The front TF-Luna acts as a proximity constraint, not automatically as target distance. Gate forward motion on fresh valid front clearance and usable vision. Gate reverse on fresh valid rear clearance; autonomous reverse is disabled by default. Conservative threshold defaults must be labeled unvalidated and become part of the physical test record.

For this revision, use reactive target steering and stop-on-obstacle behavior. Preserve mapping/flood-fill/A* as documented future extensions; do not let them delay the working vision-to-motor path. Capture optional labeled observations for later model improvement, with recording off by default. Keep online weight updates and reinforcement learning out of the running motor-control loop.

## Contracts and bridge

Use versioned YAML for authoritative configuration and JSON Schema for runtime/configuration validation. Generate or validate the MCU configuration from the same authority to prevent drift. Validate ranges, units, required pins, feature flags, sensor freshness budgets, motor limits, and supported schema versions.

Use the actual supported UNO Q Python/C++ Router Bridge APIs. Define the logical message contract independently from transport encoding: native bridge RPC may use MessagePack, so do not claim JSON is its wire format.

Commands must include session/sequence identity, requested mode, bounded signed left/right commands, source observation identity/freshness information, and a bounded lifetime. Telemetry must include applied commands, state, sensor validity and age, faults, and acknowledgement information.

Implement sequence/session rejection, a local MCU watchdog, and a freshness strategy that prevents delayed queued commands or repeated heartbeats from renewing an old movement observation. Do not compare unrelated Python and MCU monotonic clocks without synchronization. Document and test the chosen deadline/lease handshake or equivalent mechanism.

## Operator interface and validation

Provide a minimal local status view using the installed supported WebUI integration: detection/selected target, sensor status, commanded versus applied PWM, mode, faults, arm/disarm, and stop. Add live preview through the existing supported stream only if available; clearly report if preview support is unavailable. Do not assume adding the detection Brick automatically creates a website. Document the actual URL/port. Motion controls must not be exposed unauthenticated beyond the intended local setup.

Build a dry-run mode that exercises perception, state transitions, and command contracts without energizing motors. Hardware readiness remains false until physical checks are recorded.

Test meaningful failure cases: UART checksum/resynchronization, stale and invalid range, detection-coordinate conversion, target loss, ambiguous targets, command bounds, startup stop, reversal, replay/out-of-order commands, delayed commands, bridge loss, and Python termination. Run available builds and schema checks. Distinguish simulated tests, compilation, and actual on-device verification.

Document physical verification steps: confirm supply and common ground; verify pins and polarity; test each track raised with short bounded commands; confirm stop/watchdog; validate sensor responses; then perform low-speed floor tracking. Record actual results without claiming tests that were not run.

## Completion and attribution

Implement incrementally: contracts and configuration; stopped motor layer and sensors; bridge; preserved vision adapter; target steering; operator view; integration validation and documentation. Continue until all implementable work is complete. Do not stop after merely proposing an architecture.

Update the README, wiring/pin table, setup/run instructions, configuration reference, architecture/contract documentation, and all development/test records required by docs/. List remaining physical configuration gaps and provide exact verification steps. Leave unknown hardware values unresolved and motion disabled while still delivering a buildable dry-run path where feasible.

Credit Michael Garcia for design, planning, research, and programming. Credit Codex/ChatGPT for drafts, research assistance, and agentic programming against validated schemas. Attribute external code and models accurately.

Finish with a concise report of implemented behavior, changed files, checks performed, failures or blockers, and the next physical test. Do not claim autonomous readiness from a successful build alone.

