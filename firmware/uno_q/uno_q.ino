/* SPDX-FileCopyrightText: Copyright (C) Arduino s.r.l. and/or its affiliated companies
 * SPDX-License-Identifier: MPL-2.0
 * File: firmware/uno_q/uno_q.ino
 * Purpose: Stopped Router Bridge bring-up scaffold; no physical GPIO binding.
 * Owner: Michael Garcia; upstream API example: Arduino; contributor: Codex / ChatGPT.
 * Contact: Pending confirmation. License: MPL-2.0 (derived API example).
 * Constraints: target build unverified; disconnect motor power for bring-up.
 * Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
 */
#include <Arduino_RouterBridge.h>
#include <atomic>

std::atomic<bool> stopped{true};

/* Purpose: Unconditional stopped-state request. Design: callback updates atomic
 * flag only, never blocks or writes unverified pins. Workflow: cc_stop RPC.
 * Data Handoff: acknowledgement of logical disarm, NOT physical power isolation.
 */
bool request_stop() {
    stopped.store(true);
    return true;
}

/* Purpose: Report that motion is inhibited. Design: no arming/drive RPC provided.
 * Workflow: diagnostic query. Data Handoff: always-disarmed flag.
 */
bool is_disarmed() { return stopped.load(); }

/* Purpose: Start diagnostic RPC after logical stopped initialization.
 * Design: supplied upstream Router API; installed version must be verified.
 * Workflow: boot. Data Handoff: stop/disarmed RPCs only; no GPIO touched.
 */
void setup() {
    stopped.store(true);
    Bridge.begin();
    Bridge.provide("cc_stop",request_stop);
    Bridge.provide("cc_is_disarmed",is_disarmed);
}

/* Purpose: Preserve inhibited motion. Design: no blocking acquisition or callbacks.
 * Workflow: Arduino loop. Data Handoff: logical stopped state only.
 */
void loop() { stopped.store(true); }
