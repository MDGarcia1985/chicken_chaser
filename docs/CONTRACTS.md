# Runtime contracts — revision 1

Implementation record: DEV-2026-10-12-001/002. JSON Schema draft 2020-12, logical schema version `1.0.0`, prototype revision 1. Master version `0.3.0` describes project metadata, not bridge protocol. Proposed architecture YAML remains a design document.

`tools/create_schemas.py` is the reproducible schema-definition source; generated JSON files are checked in. Every record has a closed shape and explicit version. YAML uses SafeLoader with duplicate-key rejection. JSON Schema plus semantic checks reject nonfinite values, geometry outside the selected image view, duplicate motor pins, motor deadband above its cap and behavioral duty mixing above the cap. Physical hardware enable and autonomous readiness are pinned false in this release. STOP bypasses drive validation and revokes authority even when other contracts/configuration are incomplete.

| Record | Handoff |
|---|---|
| Config | YAML → schema/semantic validation → generated MCU header with SHA-256 |
| Detection | Verified raw payload → `xyxy_pixels_processing_view`, confidence/label, dimensions, frame identity, receipt/capture timing and measured latency bound |
| Lease | MCU session, arm generation, one-use epoch, remaining local deadline in ms |
| Command | Version, session/generation/epoch, sequence, requested turn/follow mode, signed normalized left/right duty, observation identity/age, lifetime ms |
| Telemetry | Session/generation/ack, state, requested/applied duty, each sensor's status/mm/age, fault and synthetic-output flag |
| Model | Identity, referenced artifact/digest, labels, preprocessing, threshold, dependencies, evaluation and rollback reference |

## Deadline handshake

1. Operator explicitly arms a new session/generation with healthy prerequisites. Restart never restores it.
2. Host asks MCU for an epoch **before** acquiring a new observation. MCU stores its local issuance time. Repeated queries return the same epoch and cannot extend its deadline.
3. Host uses a fresh, unique observation and sends a strictly increasing sequence. Acquisition may send zero duty for each new observation so it consumes epochs without motion.
4. MCU checks session/generation, one-use epoch, remaining time, strictly increasing observation/sequence, mode, limits and observation age. It expires the applied command after the minimum of epoch time remaining, requested lifetime and remaining observation-age budget.
5. Consumed epochs cannot be reused. Reordered/replayed/wrong-session/malformed requests stop and latch a fault. Invalid required ranges or expired applied authority immediately stop, bypassing ramping. Clearing a fault never rearms.

A newly requested epoch cannot retroactively authorize an earlier source observation: the production host integration must capture/identify the new observation after the offer. The synthetic runtime does this explicitly. MCU counters alone cannot independently authenticate when a camera image was captured; real frame identity, latency bounds and host integrity are prerequisites. Host-receipt time alone does not establish capture freshness, and unrelated Python/MCU clocks are never subtracted. Capture timestamps in the internal record must already be normalized to the host monotonic clock. Without capture time, measured worst-case inference/transport latency is added to receipt age; without that bound, behavior stops.

Unsigned elapsed arithmetic handles MCU millisecond rollover for short budgets; identities are restricted to positive signed-32-bit counters and exhaustion requires a new controller/session lifecycle. An independent MCU loop must keep executing while Python stalls. The ctypes simulator does not create an independent watchdog process and establishes no device timing.

## Boundaries

The portable `Controller` has a single control-loop owner. The host ABI serializes access with a Python lock. A production Router callback must enqueue a validated fixed-size record in a synchronized latest-only mailbox; STOP must have priority and be processed outside a drive backlog. The current MCU sketch exposes only atomic stopped-state diagnostics; motion RPC marshalling and the physical driver/sensor binding remain blocked pending installed-core inspection.

The inspected upstream Python `Bridge.call(method,*params,timeout=...)` and C++ `Bridge.begin`/`Bridge.provide` APIs inform stopped diagnostic code. Upstream Router uses MessagePack-RPC. JSON fixtures are the logical record representation; no JSON wire format is asserted. Do not make nested synchronous bridge calls inside provided callbacks.

`OutputBus` requires output latches low before output enable and bounded normalized PWM writes. `Driver` configures two distinct verified pins and always repeats stops; it clears inactive input before active PWM. `Motor` maps the DRV8871 truth table, clamps and ramps duty, and enforces a zero interval on reversal. The native UNO Q implementation of `OutputBus` must check PWM capability, resolution, timer sharing and failures. It is intentionally absent until installed APIs/pins are verified; public upstream `analogWrite` can silently fall back to a digital write on unsupported pins.

`RearBus` must implement bounded initialization, readiness and read transactions, with status zero mapped to valid millimetres. The real VL53L0X library's status conventions must be adapted, not assumed from this portable boundary. The TF-Luna parser consumes one byte per call, retains overlapping synchronization headers, verifies checksum, rejects weak/overexposed/invalid distances, discards partial frames after a simulation 20 ms inter-byte gap and ages valid samples locally. A production loop needs an explicit byte/time budget and measured I2C timeout.

## Limits

Both fresh clear beams are required by the conservative simulation controller. Forward requires front clearance; any negative individual track command/turn also requires rear clearance. Full reverse is disabled. Beams do not establish full swept-volume clearance. Following only adds a bounded forward component when centered and separately enabled; ranges constrain proximity, not target identity or calibrated stand-off distance. No encoder feedback or measured velocity is implied.

Target association uses class plus IoU ≥0.1 or centroid displacement ≤0.15 of normalized image dimensions. Multiple matches stop. This is continuity, not guaranteed persistent identity across occlusion/crossing. Missed frames, stale targets or geometry changes reset acquisition. Future localization, flood-fill/frontier planning/A*, and offline model evaluation retain their design-document extension points; they have no active motion authority in this release.
