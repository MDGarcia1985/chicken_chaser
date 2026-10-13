# Runtime configuration reference

`config/runtime.yaml` is the only runtime authority. Load via `contracts.load_config`, regenerate with `python tools/generate_mcu.py`, then rebuild with `python tools/build_host.py`. The shared library refuses to load if its generated configuration digest differs from Python's authority. Do not edit the generated header. Changing any field requires rebuilding; this deliberately avoids unnoticed drift.

| Group | Units / constraints |
|---|---|
| `schema_version`, `prototype_revision` | `1.0.0`, `1`; unsupported values reject |
| `ready_for_autonomous_motion`, `hardware.enabled` | Always false in current schema |
| Hardware motor `in1`, `in2`, `invert` | Verified native pin IDs and polarity; null until inspection |
| `vm_v`, `current_limit_a` | Actual measured volts/board amperes; null until inspection; voltage schema only permits TI operating range |
| Hardware `front_uart`, `front_baud`, `rear_bus`, `rear_address` | Actual supported MCU peripheral selection/settings; null, not guessed defaults |
| Hardware `pwm_bits`, `control_period_ms` | Installed-core resolution and measured schedule; null |
| Hardware verification flags | False; physical evidence and a reviewed device integration/schema update are needed to change |
| Simulation `lease_ms`, `sensor_age_ms`, `reversal_ms` | Local elapsed milliseconds; 150, 250, 100 defaults; physically unvalidated |
| Simulation `clearance_mm` | Millimetres, 400 default; not validated braking distance |
| Simulation `max_duty`, `deadband`, `ramp_per_s` | Normalized duty fraction, dimensionless deadband, fraction/s ramp; 0.25, 0.02, 0.5 |
| Behavior `target_label`, `confidence`, `stable_frames` | Person bench proxy, ≥0.5, 3 unique fresh frames; model labels must be verified for live use |
| Behavior `observation_age_ms` | Capture-to-control bound, 150 ms synthetic default |
| Behavior `gain`, `aim_x`, `deadband` | Dimensionless normalized horizontal error gain, image aim fraction and error deadband; 0.2, 0.5, 0.08 |
| Behavior `max_turn`, `max_forward` | Normalized duty cap; 0.15 and 0.1; sum must not exceed motor limit |
| Behavior `follow_enabled` | False; separate simulation opt-in; no physical deployment permission |
| Behavior `reverse_enabled` | False only; no autonomous reverse |
| Behavior `recording_enabled` | False; opt-in JSONL to ignored `captures/`, quota 1000 frames/session |
| Camera `negotiated_width/height`, `layout`, `view` | Actual negotiated source pixels, single or horizontal stereo layout and chosen single/left/right eye; null |
| Camera `payload_mapping` | After observed payload inspection only: `confidence_key`, `box_key`, `format` (`xyxy` or `xywh`), `units` (`pixels` or `normalized`) |
| Camera `latency_bound_ms` | Measured conservative capture/inference/transport bound when timestamps unavailable; null |

Changing camera metadata alone does not enable live motion. `app_lab/python/main.py` remains diagnostic-only and does not pass raw callbacks into a motor adapter. The pure normalization interface can be validated with saved actual payload fixtures once inspection is complete. Boxes wholly outside the selected stereo eye and boxes crossing the eye boundary are dropped; ambiguous layout is rejected. Width for steering is the processing view, not the combined image.

`config/model_manifest.json` is a valid unresolved manifest. Model identity/weights checksum, installed labels, preprocessing, package versions and evaluation/rollback references remain null or empty until inspected. Binary weights are referenced by artifact path/URI; they are never embedded in configuration. Record an offline dataset split by session, evaluate chicken/proxy confusion and latency, and retain rollback before deploying a model. No online learning or adaptive motor limits exists.
