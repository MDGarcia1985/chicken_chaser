# Physical validation procedure

All tests below are currently NOT_EXECUTED/BLOCKED on the development host. Keep `ready_for_autonomous_motion` false and hardware enable inhibited. Append actual TEST_LOG entries with date/time, device/core/library versions, wiring photo/reference, commands, measured values and outcome. A failed T1/T2/T3 blocks dependent progression until correction and retest or an owner-authorized, scoped engineering exception.

## 1. Power and stopped startup — next physical test

Disconnect motor outputs/power; identify the actual battery pack, hub compute power path, ground and motor rail. Measure both DRV8871 VM terminals and confirm at least 6.5 V and safe motor/board ratings. Record current-limit resistor/breakout configuration, fuse/physical disconnect and common ground continuity. A reported 5 V motor arrangement is unresolved and cannot be accepted as valid DRV8871 VM. Do not backfeed compute power or assume the hub supplies the motors.

Identify exact board pin assignments and installed UNO Q core before adding an output adapter. Inspect pin/PWM mapping and timer sharing; check output resolution and waveform with motors disconnected. Verify both driver inputs initialize to 00 before bridge/command handling and remain there after boot/reset. A successful compilation is not this test. The current diagnostic sketch does not drive any pins and cannot provide physical stop evidence.

## 2. Independent sensor bring-up

Inspect TF-Luna wiring/levels and a UART distinct from bridge/debug. Confirm actual baud, 8N1 framing, default nine-byte centimetre output and configuration readback. Record raw frames, checksums, weak/overexposure responses, covered beam and disconnection. Confirm range/status timestamps and stale timeout; never treat zero/no-return as clearance.

Inspect the VL53L0X breakout supply, pullups, bus/address and UNO Q-compatible library. Implement the portable `RearBus` using the library's actual asynchronous/status semantics and transaction timeouts. Exercise init failure, invalid range status, I2C disconnection, stale data and valid near/far responses. Record worst-case call time; no wait-for-ready polling loop may stall motor enforcement.

## 3. Raised-track motor tests

Raise and secure the chassis with an accessible physical power disconnect. Implement/bind the verified `OutputBus` and generated verified pin configuration only after steps 1–2. Start disarmed. Test one motor at a time with a short bounded low-duty lease; record input waveform, direction/polarity, rail/current and stop response. Distinguish coast from brake physically. Repeat the other track. Verify ramping, dwell before reversal, emergency stop overriding ramping and reset staying stopped. Do not describe commanded PWM as measured speed.

Measure an independent MCU loop (100 Hz is a target only), including worst-case sensor, PWM and Router load. Confirm mailbox synchronization, newest-only drive record and prioritized stop. Stall/kill Python, break the bridge, replay/out-of-order/wrong-session commands, delay an epoch response and command, and repeatedly heartbeat an old observation. Record actual stop latency at outputs; repeat with each required stale/invalid sensor. Clear fault and rearm deliberately; reconnect alone must never resume motion.

## 4. Vision and turn-only bench test

Run the baseline/probe alone. Confirm negotiated dimensions and stereo eye using targets separately in each view. Capture complete payload records and real model labels/identity/dependencies. Establish frame identity and same-clock capture timestamp or measured conservative end-to-end latency bound. Feed those actual records through the adapter and test known left/center/right positions, duplicate-eye targets, loss, low confidence, multiple crossing targets and long latency. Verify turn sign on the raised chassis before floor use. Neither front nor rear beam proves safe turning volume; use a cleared controlled test area.

## 5. Low-speed floor and optional follow

Begin with a controlled inanimate/proxy target, a clear flat floor, an operator at the disconnect and turn-only mode. Verify loss/ambiguity/obstacle/stop at measured limits. No cliff protection or obstacle-swept-volume coverage is established. Following needs a separate explicit enable after measured stopping distance, clearance thresholds, command/vision freshness, motor limits and sensor behavior are documented. Validate bounded forward centering and stop-on-obstacle; do not infer target range from the front beam. No autonomous reverse or obstacle detours.

Only an explicit owner-approved readiness change supported by physical records may enable later autonomous motion. Animal demonstrations additionally require demonstrated avoidance of contact/distress and controlled operation; present testing establishes none of that behavior.
