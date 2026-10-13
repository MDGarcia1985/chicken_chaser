/* File: firmware/core.hpp
 * Purpose: Portable MCU motor, sensor and command-enforcement interfaces.
 * Owner: Michael Garcia; contributor: Codex / ChatGPT.
 * Contact: Pending confirmation. License: Pending confirmation.
 * Constraints: no Arduino pins or hardware assumptions; milliseconds are MCU-local.
 * Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
 */
#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <string>

namespace chicken {
enum class Validity { unavailable, invalid, valid, stale };
struct Range { Validity status{Validity::unavailable}; unsigned mm{0}; uint32_t at{0}; };
struct Config {
    uint32_t lease_ms, sensor_age_ms, clearance_mm, reversal_ms, observation_age_ms;
    float max_duty, deadband, ramp_per_s;
    bool follow_enabled{false};
};
struct Command {
    uint32_t session, sequence, generation, epoch, observation, observation_age_ms, lifetime_ms;
    float left, right;
    bool follow;
};
struct Inputs { float in1, in2; };

/* Purpose: Bind verified pins without coupling portable code to an installed core.
 * Design: implement configure_low with output latch low before enabling output;
 * duty writes must be bounded. Workflow: board adapter only after validation.
 * Data Handoff: native GPIO/PWM, never inferred pins.
 */
class OutputBus {
public:
    virtual ~OutputBus() = default;
    virtual void configure_low(unsigned pin) = 0;
    virtual void duty(unsigned pin, float normalized) = 0;
};
class Driver {
public:
    Driver(OutputBus& bus,unsigned in1,unsigned in2) : bus_(bus),in1_(in1),in2_(in2) {}
    bool begin();
    void write(Inputs values);
private:
    OutputBus& bus_;
    unsigned in1_,in2_;
    bool initialized_{false};
};

/* Purpose: One DRV8871 motor. Design: signed normalized duty, immediate stop and
 * reversal dwell; physical writer belongs to board adapter. Workflow: tick at
 * bounded loop cadence. Data Handoff: input duties, never measured velocity.
 */
class Motor {
public:
    explicit Motor(Config config, bool invert=false) : config_(config), invert_(invert) {}
    void stop(uint32_t now, bool brake=false);
    void tick(float requested, uint32_t now);
    float applied() const { return applied_; }
    Inputs inputs() const;
private:
    Config config_;
    bool invert_, brake_{false}, have_tick_{false}, waiting_{false};
    float applied_{0};
    int last_direction_{0};
    uint32_t last_tick_{0}, stopped_at_{0};
};

/* Purpose: Incremental TF-Luna default 9-byte/cm parser. Design: bounded window,
 * checksum, signal validity and inter-byte expiry. Workflow: at most a configured
 * UART byte budget per loop. Data Handoff: local-timestamped millimetres/status.
 */
class Luna {
public:
    void feed(uint8_t byte, uint32_t now);
    void expire(uint32_t now, uint32_t max_age);
    Range sample;
    unsigned corrupt{0};
private:
    std::array<uint8_t,9> bytes_{};
    unsigned size_{0};
    uint32_t last_byte_{0};
};

/* Purpose: Bounded asynchronous VL53L0X boundary. Design: board-specific I2C
 * implementation must impose transaction timeouts; no blocking read is assumed.
 * Workflow: begin once then poll. Data Handoff: explicit status/mm to enforcement.
 */
class RearBus {
public:
    virtual ~RearBus() = default;
    virtual bool begin() = 0;
    virtual bool ready() = 0;
    virtual bool read(unsigned& mm, unsigned& range_status) = 0;
};
class Rear {
public:
    explicit Rear(RearBus& bus) : bus_(bus) {}
    void initialize();
    void poll(uint32_t now, uint32_t max_age);
    Range sample;
private:
    RearBus& bus_;
    bool initialized_{false};
};

/* Purpose: Final motion authority. Design: MCU-issued one-use epoch, fixed
 * deadline, strict session/sequence/observation identity; replay never renews.
 * Workflow: single control-loop owner; callbacks must use a synchronized mailbox.
 * Data Handoff: applied duties, acknowledgement and fault to telemetry.
 */
class Controller {
public:
    explicit Controller(Config config);
    void stop(uint32_t now, const std::string& reason="");
    bool arm(uint32_t session, uint32_t now, bool prerequisites);
    bool clear_fault(uint32_t now);
    uint32_t offer(uint32_t now);
    bool accept(const Command& command, uint32_t now);
    void tick(uint32_t now);
    Range front, rear;
    Motor left, right;
    bool armed{false};
    std::string fault;
    uint32_t session{0}, generation{0}, ack{0}, epoch{0};
    float requested_left{0}, requested_right{0};
    uint32_t remaining(uint32_t now) const;
private:
    Config config_;
    uint32_t offered_at_{0}, last_observation_{0}, active_at_{0}, active_ms_{0};
    bool outstanding_{false}, active_{false};
    bool config_valid_{true};
    bool clear(const Range& range, uint32_t now) const;
};
}
