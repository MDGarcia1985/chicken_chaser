/* File: firmware/core.cpp
 * Purpose: Fail-closed portable motor, range and lease implementation.
 * Owner: Michael Garcia; contributor: Codex / ChatGPT.
 * Contact: Pending confirmation. License: Pending confirmation.
 * Constraints: host simulation cannot establish physical timing or clearance.
 * Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
 */
#include "core.hpp"

namespace chicken {
static int sign(float value) { return (value > 0) - (value < 0); }

/* Purpose: Initialize verified driver inputs stopped before commands.
 * Design: reject same pin and configure both low; no guessed platform API.
 * Workflow: stopped boot before bridge starts. Data Handoff: readiness/zero writes.
 */
bool Driver::begin() {
    if (in1_ == in2_) return false;
    bus_.configure_low(in1_); bus_.configure_low(in2_);
    initialized_=true;
    write({0,0});
    return true;
}

/* Purpose: Write DRV8871 inputs with inactive input cleared first.
 * Design: do not cache stops; invalid request becomes coast, never brake by accident.
 * Workflow: after core enforcement. 
 Data Handoff: native PWM writes through adapter.
 */
void Driver::write(Inputs values) {
    if (!initialized_) return;
    if (!std::isfinite(values.in1) || !std::isfinite(values.in2) ||
        values.in1 < 0 || values.in1 > 1 || values.in2 < 0 || values.in2 > 1 ||
        (values.in1 > 0 && values.in2 > 0 && !(values.in1 == 1 && values.in2 == 1))) values={0,0};
    if (values.in2 == 0) {
        bus_.duty(in2_,0); bus_.duty(in1_,values.in1);
    } else {
        bus_.duty(in1_,values.in1); bus_.duty(in2_,values.in2);
    }
}

/* Purpose: Stop immediately. Design: bypass acceleration and preserve direction
 * history across zero. Workflow: startup/fault/disarm. Data Handoff: zero duty.
 */
void Motor::stop(uint32_t now, bool brake) {
    if (applied_ != 0) stopped_at_ = now;
    applied_ = 0;
    brake_ = brake;
    last_tick_ = now;
    have_tick_ = true;
}

/* Purpose: Slew safe duty. Design: stop interval on polarity change, including
 * commands separated by zero; clamp dt so stalled loops cannot jump duty.
 * Workflow: loop tick with normalized request. Data Handoff: updated applied duty.
 */
void Motor::tick(float requested, uint32_t now) {
    if (!std::isfinite(requested) || requested == 0) { stop(now); return; }
    requested = std::clamp(requested, -config_.max_duty, config_.max_duty);
    if (std::abs(requested) < config_.deadband) { stop(now); return; }
    const int direction = sign(requested);
    if (last_direction_ && direction != last_direction_) {
        if (!waiting_) { stop(now); stopped_at_ = now; waiting_ = true; }
        if (uint32_t(now-stopped_at_) < config_.reversal_ms) return;
    }
    waiting_ = false;
    last_direction_ = direction;
    brake_ = false;
    float dt = have_tick_ ? std::min(uint32_t(now-last_tick_), uint32_t(20))/1000.0f : 0;
    last_tick_ = now;
    have_tick_ = true;
    float step = config_.ramp_per_s*dt;
    applied_ += std::clamp(requested-applied_, -step, step);
}

/* Purpose: Map DRV8871 truth table. Design: 00 coast/sleep, 11 brake,
 * positive IN1 PWM/IN2 low, negative opposite; fast-decay PWM.
 * Workflow: board writer after enforcement. Data Handoff: normalized input duties.
 */
Inputs Motor::inputs() const {
    if (brake_) return {1,1};
    float duty = invert_ ? -applied_ : applied_;
    return duty >= 0 ? Inputs{duty,0} : Inputs{0,-duty};
}

/* Purpose: Parse one UART byte. Design: sliding 9-byte window retains overlapping
 * sync headers; 20 ms inter-byte gap discards partial frame (simulation policy).
 * Workflow: bounded serial poll. Data Handoff: status and distance mm, checksum count.
 */
void Luna::feed(uint8_t byte, uint32_t now) {
    if (size_ && uint32_t(now-last_byte_) > 20) size_ = 0;
    last_byte_ = now;
    if (size_ < 9) bytes_[size_++] = byte;
    if (size_ < 9) return;
    unsigned checksum = 0;
    for (unsigned i=0; i<8; ++i) checksum += bytes_[i];
    if (bytes_[0] == 0x59 && bytes_[1] == 0x59) {
        if ((checksum & 255) == bytes_[8]) {
            unsigned cm = bytes_[2] | (unsigned(bytes_[3]) << 8);
            unsigned strength = bytes_[4] | (unsigned(bytes_[5]) << 8);
            bool valid = strength >= 100 && strength != 65535 && cm >= 20 && cm <= 800;
            sample = {valid ? Validity::valid : Validity::invalid, valid ? cm*10 : 0, now};
            size_ = 0;
            return;
        }
        ++corrupt;
        sample = {Validity::invalid,0,now};
    }
    for (unsigned i=0; i<8; ++i) bytes_[i] = bytes_[i+1];
    size_ = 8;
}

/* Purpose: Expire old samples. Design: local unsigned elapsed handles rollover.
 * Workflow: every loop independent of incoming bytes. Data Handoff: stale status.
 */
void Luna::expire(uint32_t now, uint32_t max_age) {
    if (sample.status == Validity::valid && uint32_t(now-sample.at) >= max_age)
        sample.status = Validity::stale;
}

/* Purpose: Initialize ranging. Design: failure explicit. Workflow: stopped boot.
 * Data Handoff: readiness; hardware adapter must bound begin.
 */
void Rear::initialize() {
    initialized_ = bus_.begin();
    sample.status = initialized_ ? Validity::unavailable : Validity::invalid;
}

/* Purpose: Acquire only ready results. Design: no wait-for-ready loop; status zero
 * required by adapter contract. Workflow: bounded loop. Data Handoff: range status/mm.
 */
void Rear::poll(uint32_t now, uint32_t max_age) {
    if (!initialized_) return;
    if (bus_.ready()) {
        unsigned mm=0, status=1;
        bool ok = bus_.read(mm,status) && status == 0 && mm > 0 && mm <= 2000;
        sample = {ok ? Validity::valid : Validity::invalid, ok ? mm : 0, now};
    }
    if (sample.status == Validity::valid && uint32_t(now-sample.at) >= max_age)
        sample.status = Validity::stale;
}

/* Purpose: Construct stopped authority. Design: invalid config cannot arm.
 * Workflow: boot. Data Handoff: zero motors and fault if bounds are invalid.
 */
Controller::Controller(Config c) : left(c), right(c), config_(c) {
    if (!c.lease_ms || c.lease_ms > 500 || !c.sensor_age_ms || !c.clearance_mm ||
        !c.reversal_ms || !c.observation_age_ms || c.observation_age_ms > 1000 ||
        !std::isfinite(c.max_duty) || c.max_duty <= 0 || c.max_duty > 1 ||
        !std::isfinite(c.deadband) || c.deadband < 0 || c.deadband >= c.max_duty ||
        !std::isfinite(c.ramp_per_s) || c.ramp_per_s <= 0) {
        config_valid_=false; fault="invalid_config";
    }
}

/* Purpose: Revoke authority unconditionally. Design: stop invalidates epoch and arm.
 * Workflow: operator, watchdog or rejected contract. Data Handoff: zero requests/output.
 */
void Controller::stop(uint32_t now, const std::string& reason) {
    armed=false; outstanding_=false; active_=false;
    requested_left=0; requested_right=0;
    left.stop(now); right.stop(now);
    if (!reason.empty()) fault=reason;
}

/* Purpose: Explicit new arm generation. Design: no reconnect rearm; config/fault
 * and sensor prerequisites. Workflow: operator only. Data Handoff: session identity.
 */
bool Controller::arm(uint32_t new_session, uint32_t now, bool prerequisites) {
    if (armed || !config_valid_ || !new_session || new_session > INT32_MAX ||
        generation >= INT32_MAX || !prerequisites || !fault.empty() ||
        !clear(front,now) || !clear(rear,now)) return false;
    stop(now);
    session=new_session; ++generation; ack=0; last_observation_=0; armed=true;
    return true;
}

/* Purpose: Deliberately clear recoverable faults. Design: stopped, healthy inputs
 * required; configuration faults cannot be cleared. Workflow: operator action.
 * Data Handoff: cleared fault only, no automatic arming.
 */
bool Controller::clear_fault(uint32_t now) {
    if (armed || !config_valid_ || !clear(front,now) || !clear(rear,now)) return false;
    fault.clear();
    return true;
}

/* Purpose: Offer one expiring epoch. Design: repeated polls cannot extend it.
 * Workflow: host requests before a NEW observation. Data Handoff: epoch/deadline.
 */
uint32_t Controller::offer(uint32_t now) {
    if (!armed) return 0;
    if (!outstanding_ || uint32_t(now-offered_at_) >= config_.lease_ms) {
        if (epoch >= INT32_MAX) { stop(now,"identity_exhausted"); return 0; }
        ++epoch; offered_at_=now; outstanding_=true;
    }
    return epoch;
}

uint32_t Controller::remaining(uint32_t now) const {
    uint32_t elapsed=uint32_t(now-offered_at_);
    return outstanding_ && elapsed < config_.lease_ms ? config_.lease_ms-elapsed : 0;
}

bool Controller::clear(const Range& r, uint32_t now) const {
    return r.status == Validity::valid && r.mm >= config_.clearance_mm &&
        uint32_t(now-r.at) < config_.sensor_age_ms;
}

/* Purpose: Admit one fresh command. Design: request lifetime never renews the
 * offered deadline; source ID strictly increases, no repeated-heartbeat movement.
 * Workflow: loop-owned validated bridge record. Data Handoff: ack/request or stop.
 */
bool Controller::accept(const Command& c, uint32_t now) {
    auto reject=[&]() { stop(now,"contract_rejected"); return false; };
    if (!armed || c.session != session || c.generation != generation ||
        c.sequence > INT32_MAX || c.observation > INT32_MAX ||
        c.sequence <= ack || c.epoch != epoch || !remaining(now) ||
        c.observation <= last_observation_ || c.observation_age_ms >= config_.observation_age_ms ||
        !c.lifetime_ms || c.lifetime_ms > config_.lease_ms ||
        !std::isfinite(c.left) || !std::isfinite(c.right) ||
        std::abs(c.left) > config_.max_duty || std::abs(c.right) > config_.max_duty ||
        (c.follow && !config_.follow_enabled) ||
        (!c.follow && std::abs(c.left+c.right) > 0.0001f) ||
        (c.left+c.right < -0.0001f)) return reject();
    ack=c.sequence; last_observation_=c.observation;
    active_at_=now;
    active_ms_=std::min({remaining(now),c.lifetime_ms,config_.observation_age_ms-c.observation_age_ms});
    outstanding_=false; active_=true;
    requested_left=c.left; requested_right=c.right;
    tick(now);
    return armed;
}

/* Purpose: Apply watchdog and conservative swept-volume gating before ramping.
 * Design: both beams required for turns, forward front constraint, no autonomous
 * reverse; beams do not prove full turn clearance. Workflow: independent local loop.
 * Data Handoff: immediate stopped outputs on fault; requires explicit rearm.
 */
void Controller::tick(uint32_t now) {
    if (!armed) { left.stop(now); right.stop(now); return; }
    if (!clear(front,now) || !clear(rear,now)) { stop(now,"range_blocked"); return; }
    if (!active_) { left.stop(now); right.stop(now); return; }
    if (uint32_t(now-active_at_) >= active_ms_) { stop(now,"watchdog"); return; }
    left.tick(requested_left,now); right.tick(requested_right,now);
}
}
