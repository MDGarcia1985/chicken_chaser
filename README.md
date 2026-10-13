# Chicken Chaser

Chicken Chaser was built for UAT’s 2026 AI Hackathon to explore how computer
vision can support autonomous ground vehicles through object recognition,
path planning, and sensor fusion.

The first prototype uses an Arduino UNO Q, a Waveshare AR0144 Stereo USB
Camera, a TF-Luna LiDAR module connected over UART, two DRV8871 motor-driver
breakout boards, and two DC motors. Supporting hardware includes a 65 W
USB power bank and an Acer USB hub.

Camera capture and object detection have been demonstrated on the UNO Q.
Autonomous motion, path planning, and sensor fusion remain under development.

The platform is intended to support different configurations and eventually
scale to larger vehicles. My broader goal is a modular rural robotic
workhorse that can be adapted to specific tasks.

The hackathon use case was more immediate: keeping my free-range chickens
off the porch—and their droppings off the furniture.

## Software

Chicken Chaser uses the
[video object detection example for Arduino App Lab](https://docs.edgeimpulse.com/hardware/deployments/run-arduino-app-lab#object-detection),
repository standards I have developed through previous projects, and YAML
specifications describing the hardware, repository structure, and intended
behavior.

I prefer YAML because it is easy to inspect and allows configuration
parameters to change without modifying the underlying source code, where
the implementation supports those parameters.

I plan to codify my standards as reusable agent skills so they can be
applied consistently across projects. The standards documents will remain
available to explain contribution requirements to human collaborators.

### Modular Architecture

My approach to modular development was inspired by pytest and its Pluggy
plugin system. I was interested in how a shared framework could support
such a wide variety of tests and extensions.

The intended architecture uses a plugin manager, hook specifications,
registration, and dispatch to connect modules through defined interfaces.
Modules can be added or replaced as long as they satisfy those interfaces
and their dependencies.

Think of it as a tree: the core provides the trunk, and individual
capabilities form the branches. The goal is to extend the system without
rewriting its foundation.

## Future Use Cases and Configurations

I see Chicken Chaser as the beginning of a potentially commercial modular
robotics platform. Possible applications include:

- Snow plowing.
- Non-contact wildlife deterrence.
- Manure transport.
- Fertilizer distribution.
- General hauling and rural property maintenance.

Larger platforms may share architectural patterns and software components,
but will require hardware-specific engineering, configuration, and validation.

## Repository Organization

The repository currently centers on project specifications and documentation.

At the root:

- `README.md` — Project overview and current status.
- `chicken_chaser_brief.md` — Project purpose, scope, and requirements.
- `chicken_chaser_master.yaml` — Master project specification.
- `chicken_chaser_codex_prompt.md` — Agent implementation instructions.
- `LICENSE` — License terms.

Supporting directories:

- `docs/` — Development standards and architecture documentation.
- `config/` — Architecture and configuration files, including
  `chicken_chaser_architecture.yaml`. Future configurations may use YAML,
  JSON, or TOML.

Read the project brief and master specification before implementing changes.
Contributions must follow the applicable standards in `docs/`.

## Right to Repair

I intend for this project’s firmware and software to remain open source.
I believe in the right to repair and want users to be able to inspect,
maintain, modify, and extend the systems they own.

See `LICENSE` for the terms governing use, modification, and distribution.

## License

Original Chicken Chaser code and documentation are dual-licensed under the
[MIT License](LICENSE-MIT) or the [Mozilla Public License 2.0](LICENSE-MPL-2.0),
at your option. SPDX identifier: `MIT OR MPL-2.0`.

Third-party material retains its own licenses and notices, including Arduino
examples licensed under MPL-2.0. See [LICENSE](LICENSE) for scope and terms.

Copyright © 2026 Michael Garcia.

## Acknowledgements

Portions of this project were developed with assistance from large language
models (LLMs). All concepts, planning, YAML specifications, and substantive
written content originated with the author. AI assistance was limited to
research, editing for clarity and accuracy, and code review and generation
under the author’s direction.

AI operated within author-defined specifications, skills, and parameters.
The author retained decision-making authority and responsibility for
reviewing and validating the final work.
