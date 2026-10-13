# Chicken Chaser — proposed architecture

Revision: 1 • Status: implementation baseline draft • Updated: 2026-10-12  
Companions: `../chicken_chaser_brief.md`, `../chicken_chaser_master.yaml`, `../config/chicken_chaser_architecture.yaml`

## Separation of concerns

| Concern | Owner | Responsibility |
|---|---|---|
| Vision | Debian / Python | One camera owner, detection adapter, model manifest |
| Target association | Debian / Python | Select target, retain association, reject ambiguity/staleness |
| Behavior | Debian / Python | Acquire, align, follow, stop; bounded differential commands |
| Operator interface | Debian / Python | Status, explicit arming, stop, diagnostics; preview only through supported existing capture path |
| Transport | Python + C++ | Supported UNO Q bridge; validated, versioned request/telemetry contracts |
| Actuation | MCU / C++ | Two DRV8871 drivers, polarity, PWM bounds, ramping, direction transitions |
| Ranging | MCU / C++ | TF-Luna UART parser, VL53L0X I2C adapter, bounded acquisition |
| Motion inhibition | MCU / C++ | Local watchdog, stale/invalid ranges, faults, disarm and startup stop |
| Mapping and learning | Debian / Python, deferred | Occupancy-grid planning and offline model lifecycle |

The MCU remains authoritative over motor outputs even when Linux requests motion. No Linux task may bypass its limits. A high-level failure must not leave the last drive command active indefinitely.

## Known working camera path

Use the exact supplied Python baseline embedded in `../chicken_chaser_codex_prompt.md`: `Camera(resolution=(640, 480), fps=30)`, `VideoObjectDetection(camera=camera, confidence=0.5, debounce_sec=0.0)`, `on_detect_all(...)`, then `App.run()`. Preserve automatic USB detection. The callback used by the working example is a dictionary of labels to lists of records with a confidence field.

Inspect actual callback records and installed library versions before extracting boxes. Neither box key names nor timestamp units are established here. Normalize to one internal detection format. Determine negotiated dimensions and whether the image is a single eye or combined stereo view. Steering coordinates must refer to the chosen view. Do not infer calibrated depth from USB enumeration or open a second capture handle for a preview.

## Target behavior

States: DISARMED, ACQUIRING, TRACKING, TARGET_LOST, BLOCKED, FAULT. Boot into DISARMED. Arming requires validated configuration, live bridge/session, healthy required sensors, cleared faults, and explicit operator intent. Acquisition holds zero output until a stable target is selected. TRACKING initially permits turn-to-center only; follow is separately enabled after physical validation. Any invalid target association stops movement. Faults require deliberate clearing and rearming; reconnecting or rebooting never resumes old motion.

For an image width W and target center cx, use normalized horizontal error `e = 2*cx/W - 1`. Apply a configurable deadband and bounded proportional turn command. Verify sign against actual left/right polarity on the raised chassis. Establish association using class plus box overlap or centroid proximity across recent frames; confidence alone is not identity. Require stable observations before initial acquisition or reacquisition.

For follow mode, gate forward command on target centering, fresh observations, acceptable range, and measured stopping margin. Mix forward and turn commands into left/right signed normalized duty requests and clamp consistently. These are duty requests, not measured wheel velocities. No encoders or closed-loop speed estimate are assumed. Do not use unrestricted reverse to recover a lost target. Start with a stop on an obstacle rather than an unvalidated detour.

## Sensors and motor layer

The TF-Luna uses a dedicated MCU UART when supported by the verified board pin mapping. Parse incrementally without blocking the control loop. Verify the vendor frame format, checksum, units, signal-quality rules, baud rate and electrical levels. Distinguish no frame, malformed frame, weak reading, out-of-range measurement, and valid distance; zero is never an implicit clear path.

The rear VL53L0X uses I2C. Verify its actual breakout and library, address, timing budget and error/status conventions. Bound transaction time and report freshness independently of the forward sensor. Neither sensor provides complete swept-volume or cliff coverage; turn-in-place also needs a physically clear test area.

Each DRV8871 module receives two control inputs and independently drives one motor. Pin mapping, PWM capability, polarity, current-limit configuration and power rail are unresolved. Verify the IC operating range and board implementation, including the reported 5 V setup, before enabling output. Derive coast/brake behavior from the manufacturer's truth table and distinguish commanded stop from physically measured stopping. Use ramping and a stopped interval before direction reversal; determine timings by bench validation.

The MCU loop should be deterministic and bounded. A nominal 100 Hz design target may guide scheduling, but achievable timing must be measured; do not publish it as verified. Sensor freshness, braking margin and watchdog expiry are explicit validated settings, not inferred from that target rate.

## Contracts and bridge

YAML holds human-authored configuration. JSON Schema defines machine-validatable configuration and message shapes; use a single authoritative schema source with generated bindings or an equivalent conformance strategy. YAML must load with duplicate-key rejection. JSON fixtures exercise the same contracts. Do not duplicate constants independently across Python and C++.

Use the installed UNO Q bridge API and document the actual transport/serialization. JSON describes logical records and fixtures; it does not require JSON on the wire if the supported bridge uses another encoding. Maintain bounded queues and prioritize STOP; do not allow backlog to replay old drive requests.

| Logical record | Required semantics |
|---|---|
| Drive request | Schema version, session, sequence, arm generation, bounded left/right duty, short validity lease |
| Stop/disarm | Unconditional reduction of motion authority; idempotent; cannot wait behind drive backlog |
| Telemetry | Sequence/session, MCU state, commanded duties, sensor values/status/ages, fault reason |
| Detection | Label, confidence, box and coordinate convention, view dimensions, observation identity, freshness metadata |
| Model manifest | Artifact URI/path, digest when available, model identity, labels, preprocessing, version, evaluation and rollback reference |

Use MCU-local monotonic time for command expiry. Sequence numbers prevent reordering but do not prove freshness. Establish session handshaking plus bounded transport latency or an MCU-issued expiring command epoch so delayed old commands cannot renew authority. Do not compare timestamps from unrelated host clocks without synchronization. Keep command freshness distinct from vision freshness: a newly transmitted command derived from an old frame must still be rejected by behavior gating. When capture timing is unavailable, document that limitation and validate the conservative freshness policy.

Invalid contracts reject motion; schema mismatch, NaN/infinite duty values, unknown sessions and old sequences cannot extend a lease. Restart clears arming. STOP remains available even when configuration is incomplete.

## Planning and mapping extension

The initial planner is reactive visual steering with range-based stops; it has no global pose or map. A future mapping run can use flood fill/BFS to label reachable free cells and select reachable frontiers, with A* to route to a chosen goal. Inflate obstacles by the robot footprint and measured margin, and conservatively exclude unknown cells from normal navigation. Frontier sensing must occur from known-free positions.

Flood fill does not create a map. Before this extension, establish a pose source, coordinate frames and calibrated sensor transforms, uncertainty, occupancy updates, and loop-closure/drift strategy appropriate to the actual sensors. TF-Luna is single-beam and camera stereo calibration is unverified. Implement interfaces and disabled configuration for the extension; do not simulate successful localization in real operation.

## Learning and weights

Use an offline, versioned protocol: collect intentionally enabled samples; label; split by recording session to prevent leakage; train a candidate; evaluate chicken/proxy confusion, false positives, missed targets and inference latency; approve a manifest; deploy atomically; retain rollback. Verify actual installed labels before asserting chicken recognition. No autonomous weight modification, safety-threshold learning, or automatic deployment during motion. Keep binary weights separate from YAML/JSON; the manifest references and identifies them.

## Delivery sequence and standards

1. Normalize supplied metadata and establish schemas; reproduce console detection.
2. Build MCU drivers and host-testable parsers/validators with stopped defaults.
3. Integrate the bridge in dry-run mode with malformed, stale and disconnected cases.
4. Validate sensor and motor hardware independently, then turn-to-center.
5. Validate controlled following and operator stops; retain readiness false until physical evidence exists.
6. Treat mapping, learning automation, servo, cliff sensing and RF positioning as deferred milestones.

Follow every standard in `docs/`. Source headers and function documentation follow ANNOTATION_STANDARDS. Record material decisions in append-only DEVNOTES; record executed checks and limitations in append-only TEST_LOG. T0 is required for changed implementation files, T1 for usable modules, T2 for boundaries and T3 for milestones. Failed T1/T2/T3 blocks progression except corrective work or an authorized documented exception. Host simulations cannot establish device timing, electrical suitability, actual stopping distance or physical autonomy.

## Outstanding implementation inputs

Actual GPIO/UART/I2C assignment; final supply wiring and VM voltage; breakout current-limit configuration; installed App Lab/core/library versions; actual detection payload and image layout; measurable stop latency; sensor validity and timeout settings; chosen target labels and model artifact; canonical contact. Original project material is dual-licensed under MIT OR MPL-2.0; see `../LICENSE`. Leave unresolved motion-critical values null and inhibit arming. These gaps do not justify invented values or a false hardware PASS.
