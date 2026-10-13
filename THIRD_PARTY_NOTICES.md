# Attribution and component licenses

Project owner: Michael Garcia (design, planning, research, programming). Codex / ChatGPT contributed drafts, research assistance and agentic implementation. Canonical project contact and project-wide license: Pending confirmation.

| Component | Provenance and disposition |
|---|---|
| DC-Motor-Control | Michael Garcia / M&E Design; reviewed commit `23c73c13026c9115eb902fcecd66f7b8271b6047`; MIT notice retained in `LICENSES/DC-Motor-Control-MIT.txt`. Architectural inspiration; source was not copied into portable core. |
| Console camera baseline | Supplied Arduino s.r.l. and/or affiliated companies example; MPL-2.0 copyright/SPDX retained in `app_lab/python/baseline.py`. |
| Live diagnostic application | Derived from that Arduino baseline; `app_lab/python/main.py` retains MPL-2.0. Modified source is delivered in the repository. |
| Router diagnostic sketch | Uses Arduino Router Bridge example API structure; Arduino attribution/MPL-2.0 retained in `firmware/uno_q/uno_q.ino`. Installed RouterBridge/RPClite dependencies remain external. |
| MPL license | Full text included in `LICENSES/MPL-2.0.txt`, retrieved from SPDX license-list data; original license reference: https://mozilla.org/MPL/2.0/. Covered files remain under MPL; preserve notices and provide covered source when distributing. |
| Host Python dependencies | PyYAML (MIT), jsonschema (MIT), attrs (MIT), referencing (MIT), rpds-py (MIT); distribution notices live in installed packages. `jsonschema-specifications` license and all packaged dependency notices must accompany any redistributed bundle; inspect each installed distribution's license metadata. |
| GCC runtime | Host DLL embeds GCC runtime libraries on Windows; retain applicable runtime licenses and GCC Runtime Library Exception obligations if redistributing binaries. Builds/dependencies are ignored here, not shipped as a project binary bundle. |
| Installed camera/model/Core/VL53L0X library | Actual versions/artifacts and licenses not established; inspect on device and record before deployment/distribution. No model weights bundled or blanket project license assigned. |

Reference review covered `src/main.cpp`, `motor.cpp`, `ultraSonic.cpp`, `display.cpp`, `led.cpp`; `include/motor.h`, `ultraSonic.h`, `display.h`, `led.h`; README, PlatformIO configuration and LICENSE. The reviewed AVR toolchain/COM8/pins/dependencies were not adapted. The 100% startup, invalid-range-to-zero/full-speed behavior, blocking `pulseIn`, conflicting stop/brake comments and automatic reverse maneuver were specifically excluded.

External technical references: [TI DRV8871 datasheet](https://www.ti.com/lit/ds/symlink/drv8871.pdf), [Benewake TF-Luna manual](https://en.benewake.com/uploadfiles/2025/04/20250430174515390.pdf), [Arduino VideoObjectDetection source](https://github.com/arduino/app-bricks-py/blob/main/src/arduino/app_bricks/video_objectdetection/__init__.py), [WebUI source](https://github.com/arduino/app-bricks-py/blob/main/src/arduino/app_bricks/web_ui/web_ui.py), [Python bridge](https://github.com/arduino/app-bricks-py/blob/main/src/arduino/app_utils/bridge.py), [RouterBridge](https://github.com/arduino-libraries/Arduino_RouterBridge), [UNO Q core](https://github.com/arduino/ArduinoCore-zephyr), [Edge Impulse App Lab guidance](https://docs.edgeimpulse.com/hardware/deployments/run-arduino-app-lab#object-detection). Upstream main sources inform scaffolds; none establishes installed-device compatibility.
