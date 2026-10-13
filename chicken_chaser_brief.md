# Chicken Chaser — project brief

Document revision: 1 • Updated: 2026-10-12 • Status: implementation baseline draft  
Prototype revision: 1 • Prototype version: 0.1.0 • Production revision: null  
Owner: Michael Garcia • Autonomous motion readiness: false

## Purpose

Build a tracked vehicle that identifies a selected visual target, turns toward it as it moves, and optionally follows at a controlled stand-off distance. The intended target is a chicken. Chicken-specific recognition is an objective, not a verified capability of the installed detector. Initial controlled demonstrations may use a supported proxy class or an inanimate target. Operation around animals must avoid contact, pursuit that causes distress, and uncontrolled motion.

This is production project development with explicit contracts and verification, not a learning exercise. The physical build remains prototype revision 1; production revision is intentionally unset.

## Current evidence

The vehicle has been assembled using a salvaged tracked drivetrain, cardboard structure, zip ties, hot glue, and screw-mounted components. The presentation is reported complete. The UNO Q has successfully started the USB camera as `CCB Camera`; the supplied Arduino Python example has emitted person, laptop, TV, cat, and dog detections. Those observations establish capture and inference activity, not classification accuracy, chicken recognition, tracking, or autonomous driving.

The source master declares `hardware_verified: true`; retain this as the owner's general statement without extending it to individual untested capabilities. Motor operation was last described as a 5 V prototype arrangement. Verify the actual rail at the DRV8871 VM terminals against the manufacturer's operating range before enabling motion. The final wiring, power topology, pin assignments, and sensor integration are not established by these documents.

## Hardware baseline

| Component | Quantity | Role / interface |
|---|---:|---|
| Arduino UNO Q | 1 | Debian Python AI and behavior; MCU C++ real-time control |
| Waveshare AR0144 Stereo USB Camera (A) | 1 | USB-C through Acer hub; automatic camera discovery |
| TF-Luna | 1 | Forward distance measurement over UART |
| VL53L0X | 1 | Rear distance measurement over I2C |
| Brushed DC motor, nominal 7.5 V | 2 | Independent left/right tracked drive |
| DRV8871 breakout | 2 | One bidirectional motor driver per motor |
| Battery pack | 1 | Power source; final specifications and rail routing unresolved |
| Acer USB hub | 1 | USB connectivity; power/data capabilities to verify |

Do not assume encoders, calibrated stereo depth, a scanning LiDAR, or globally referenced position. TF-Luna provides one range along its beam, not a room scan or a target identity. A previous 65 W power bank and 2S battery were discussed; the active pack and connections must be recorded from the actual build.

## Prototype scope

1. Reproduce the working console detection example unchanged before extending it.
2. Establish validated configuration, model metadata, and message contracts.
3. Bring up motors and range sensors independently under MCU control, stopped and disarmed at startup.
4. Demonstrate target acquisition and turn-to-center using a stable target association and camera-frame error.
5. Add bounded forward following only after motor, freshness, range, and stop behavior are physically verified.
6. Provide operator status, explicit arm/disarm, emergency stop behavior, dry-run mode, and durable verification records.

Do not auto-reverse around obstacles or continue moving when a target disappears. A target class match does not prove persistent identity. Stop when association is ambiguous or observations become stale. Range sensing inhibits unsafe movement; it does not prove that a measured surface belongs to the selected visual target.

## Architecture and planning

Python owns camera capture, detection adaptation, target association, behavior, and operator interaction. C++ owns both motor outputs, UART/I2C sensor acquisition, command validation, watchdogs, and final motion inhibition. Use the UNO Q's supported bridge with versioned logical contracts; confirm installed APIs before implementation.

The first navigation capability is lightweight image-based steering with obstacle stops. A later mapping run may use flood fill over a validated occupancy grid, with A* for goal-directed routes. Reliable pose estimation and suitable spatial observations are prerequisites. Camera and LiDAR positioning remain future development; the present single-beam sensor and uncalibrated camera do not establish a mapping solution.

Learning is initially an offline workflow: deliberately collect examples, label and split data, train/evaluate a candidate, version weights and preprocessing, and deploy only a validated model with rollback. No online weight changes or adaptive safety limits during driving.

## Deferred scope

Mapping/localization and flood-fill exploration; RF/UWB positioning (one REYAX RYUW122 was available and explicitly excluded from this demo); camera tilt servo and limit switches; four harvested Roomba cliff sensors; calibrated stereo depth; automatic obstacle detours. Preserve extension points without implementing or declaring these features present by default.

## Acceptance evidence

Required demonstrations are: repeatable camera startup; valid sensor frames with invalid/stale handling; each motor's direction and stopped state; MCU stop on expired commands, bridge loss, reset, and operator disarm; stable target centering; loss-of-target stop; and obstacle stop within measured operating limits. Follow mode requires additional stand-off and stopping-distance validation. No assumed PASS results. Keep autonomous readiness false until physical evidence supports an explicit update.

## Governing documents and authorship

`chicken_chaser_master.yaml` owns inventory and project metadata. `docs/chicken_chaser_architecture.md` explains architecture, and `config/chicken_chaser_architecture.yaml` records proposed responsibilities and unresolved runtime settings. The configuration is a design contract, not a ready-to-run wiring file. Implemented schemas must reject missing motion prerequisites.

Follow all supplied standards in `docs/`: `ANNOTATION_STANDARDS.md`, `DEVNOTES_STANDARDS.md`, and `TEST_LOG_STANDARDS.md`. The implementation agent creates README, source, schemas, DEVNOTES, and TEST_LOG; none are assumed to preexist.

Michael Garcia: design, planning, research, programming. Codex / ChatGPT: drafts, research assistance, and agentic programming against validated schemas. Original project material is dual-licensed under MIT or MPL-2.0, at the recipient's option; see `LICENSE`. Preserve licenses for reused material. Canonical contact remains pending confirmation.

References: [DC Motor Control](https://github.com/MDGarcia1985/DC-Motor-Control), [Edge Impulse / Arduino App Lab](https://docs.edgeimpulse.com/hardware/deployments/run-arduino-app-lab#object-detection).

Hackathon metadata remains as supplied in the master: October 9–11, 2026, 14:00–14:00 fixed MST (UTC−07:00), 48 hours. These supplied values differ from earlier conversation times and are retained rather than silently converted. Historical presentation and publishing deliverables do not authorize automatic publication or require rebuilding the completed presentation.
