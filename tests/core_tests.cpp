/* File: tests/core_tests.cpp
 * Purpose: Execute motor/range/watchdog failure regressions on the host.
 * Owner: Michael Garcia; contributor: Codex / ChatGPT.
 * Contact: Pending confirmation. License: Pending confirmation.
 * Constraints: simulation only; assertions stay enabled. DEV-2026-10-12-002.
 */
#include "core.hpp"
#include "generated_config.hpp"
#include <cassert>
#include <iostream>
#include <limits>
#include <vector>
using namespace chicken;

/* Purpose: Build vendor-format test bytes. Design: checksum across first 8 bytes.
 * Workflow: parser fixture. Data Handoff: UART frame, not a device observation.
 */
std::array<uint8_t,9> frame(unsigned cm, unsigned strength=1000) {
    std::array<uint8_t,9> b{0x59,0x59,uint8_t(cm),uint8_t(cm>>8),uint8_t(strength),uint8_t(strength>>8),0,0,0};
    for (int i=0;i<8;++i) b[8]=uint8_t(b[8]+b[i]);
    return b;
}

/* Purpose: Execute parser error cases. Design: partial/corrupt/garbage/gap and weak
 * readings must never become clear path. Workflow: T1. Data Handoff: assertions.
 */
void parser_tests() {
    Luna l;
    auto b=frame(120);
    for (int i=0;i<4;++i) l.feed(b[i],1);
    assert(l.sample.status==Validity::unavailable);
    for (int i=4;i<9;++i) l.feed(b[i],2);
    assert(l.sample.status==Validity::valid && l.sample.mm==1200);
    l.expire(252,250); assert(l.sample.status==Validity::stale);
    b[8]^=1;
    for (auto byte:b) l.feed(byte,253);
    assert(l.corrupt==1 && l.sample.status==Validity::invalid);
    for (int i=0;i<37;++i) l.feed(uint8_t(i),254);
    for (auto byte:frame(100)) l.feed(byte,255);
    assert(l.sample.status==Validity::valid && l.sample.mm==1000);
    for (auto byte:frame(100,99)) l.feed(byte,256);
    assert(l.sample.status==Validity::invalid);
    for (auto byte:frame(100,65535)) l.feed(byte,257);
    assert(l.sample.status==Validity::invalid);
    for (auto byte:frame(0)) l.feed(byte,258);
    assert(l.sample.status==Validity::invalid);
    for (int i=0;i<4;++i) l.feed(frame(100)[i],259);
    for (int i=4;i<9;++i) l.feed(frame(100)[i],300);
    assert(l.sample.status!=Validity::valid);
    for (auto byte:frame(150)) l.feed(byte,301);
    assert(l.sample.status==Validity::valid && l.sample.mm==1500);
}

/* Purpose: Exercise motor and truth-table outputs. Design: immediate stop/ramp/dwell
 * and inversion checked separately. Workflow: T1. Data Handoff: assertion failures.
 */
void motor_tests() {
    Motor m(SIM_CONFIG);
    assert(m.applied()==0 && m.inputs().in1==0 && m.inputs().in2==0);
    m.tick(.25f,0); m.tick(.25f,20);
    assert(m.applied()>0 && m.applied()<=.01f);
    m.tick(-.25f,21); assert(m.applied()==0);
    m.tick(-.25f,120); assert(m.applied()==0);
    m.tick(-.25f,121); assert(m.applied()<0);
    m.stop(122,true); assert(m.inputs().in1==1 && m.inputs().in2==1);
    m.stop(123); assert(m.inputs().in1==0 && m.inputs().in2==0);
    m.tick(.25f,124); assert(m.applied()==0);
    m.tick(.25f,224); assert(m.applied()>0);
    m.tick(std::numeric_limits<float>::quiet_NaN(),225); assert(m.applied()==0);
    Motor inverted(SIM_CONFIG,true);
    inverted.tick(.25f,0); inverted.tick(.25f,20);
    assert(inverted.inputs().in1==0 && inverted.inputs().in2>0);
}

class FakeOutputs : public OutputBus {
public:
    std::vector<std::pair<unsigned,float>> writes;
    void configure_low(unsigned pin) override { writes.push_back({pin,0}); }
    void duty(unsigned pin,float value) override { writes.push_back({pin,value}); }
};

/* Purpose: Verify physical-output abstraction ordering. Design: independent two
 * drivers, repeated stops cannot be cached away. Workflow: host T1 boundary mock.
 * Data Handoff: ordered writes; no actual GPIO evidence.
 */
void driver_tests() {
    FakeOutputs outputs;
    Driver a(outputs,1,2), b(outputs,3,4);
    assert(a.begin() && b.begin());
    for (auto write:outputs.writes) assert(write.second==0);
    outputs.writes.clear(); a.write({0,.2f});
    assert(outputs.writes[0].first==1 && outputs.writes[0].second==0);
    a.write({0,0}); auto size=outputs.writes.size(); a.write({0,0});
    assert(outputs.writes.size()==size+2);
    a.write({1,1}); assert(outputs.writes.back().second==1);
    a.write({.1f,.2f}); assert(outputs.writes.back().second==0);
    Driver invalid(outputs,5,5); assert(!invalid.begin());
}

/* Purpose: Supply simulation-only clearance. Design: two fresh beams required.
 * Workflow: controller fixture. Data Handoff: local samples.
 */
void clear_ranges(Controller& c,uint32_t now) {
    c.front={Validity::valid,1000,now}; c.rear={Validity::valid,1000,now};
}

/* Purpose: Command acceptance and fault regression. Design: deadlines local to MCU,
 * no host clock comparisons. Workflow: T1/T3. Data Handoff: assertion results.
 */
void controller_tests() {
    Controller c(SIM_CONFIG);
    assert(!c.armed && c.left.applied()==0);
    assert(!c.arm(1,0,true));
    clear_ranges(c,0); assert(c.arm(1,0,true));
    auto e=c.offer(0); assert(c.offer(50)==e && c.remaining(50)==100);
    Command request{1,1,c.generation,e,1,0,150,.1f,-.1f,false};
    assert(c.accept(request,50));
    c.tick(70); assert(c.left.applied()>0);
    c.tick(150); assert(!c.armed && c.left.applied()==0 && c.fault=="watchdog");
    assert(!c.arm(1,151,true));
    clear_ranges(c,151); assert(c.clear_fault(151)); assert(c.arm(2,151,true));
    assert(!c.accept(request,152)); assert(c.left.applied()==0);
    clear_ranges(c,200); assert(c.clear_fault(200)); assert(c.arm(3,200,true));
    e=c.offer(200); request={3,1,c.generation,e,2,0,150,.1f,-.1f,false};
    assert(!c.accept(request,350)); // expired even though command claims age zero
    clear_ranges(c,400); assert(c.clear_fault(400)); assert(c.arm(4,400,true));
    request={4,1,c.generation,c.offer(400),3,0,150,.1f,-.1f,false};
    assert(c.accept(request,400));
    request.sequence=2; request.epoch=c.offer(410);
    assert(!c.accept(request,410)); // heartbeat cannot reuse observation
    clear_ranges(c,500); assert(c.clear_fault(500)); assert(c.arm(5,500,true));
    request={5,1,c.generation,c.offer(500),4,0,150,.26f,-.26f,false};
    assert(!c.accept(request,500));
    clear_ranges(c,600); assert(c.clear_fault(600)); assert(c.arm(6,600,true));
    c.front.status=Validity::invalid; c.tick(601); assert(!c.armed);
    clear_ranges(c,700); assert(c.clear_fault(700)); assert(c.arm(7,700,true));
    c.tick(950); assert(!c.armed && c.fault=="range_blocked");
    Config invalid=SIM_CONFIG; invalid.max_duty=std::numeric_limits<float>::quiet_NaN();
    Controller bad(invalid); clear_ranges(bad,0); bad.stop(0);
    assert(!bad.clear_fault(0) && !bad.arm(1,0,true));
    clear_ranges(c,1000); assert(c.clear_fault(1000)); assert(c.arm(8,1000,true));
    request={8,1,c.generation,c.offer(1000),5,0,150,.1f,.1f,true};
    assert(!c.accept(request,1000)); // follow flag disabled in authority
    Controller rollover(SIM_CONFIG); clear_ranges(rollover,UINT32_MAX-50);
    assert(rollover.arm(9,UINT32_MAX-50,true));
    request={9,1,rollover.generation,rollover.offer(UINT32_MAX-50),1,0,150,.1f,-.1f,false};
    assert(rollover.accept(request,UINT32_MAX-50));
    rollover.tick(100); assert(!rollover.armed);
}

class FakeRear : public RearBus {
public:
    bool initialized{true}, available{false}, ok{true}; unsigned mm{1000}, status{0};
    bool begin() override { return initialized; }
    bool ready() override { return available; }
    bool read(unsigned& out,unsigned& code) override { out=mm; code=status; return ok; }
};

/* Purpose: Rear adapter status/error regression. Design: no device accuracy claim.
 * Workflow: public interface T1. Data Handoff: assertions.
 */
void rear_tests() {
    FakeRear b; Rear r(b); r.initialize(); r.poll(0,250);
    assert(r.sample.status==Validity::unavailable);
    b.available=true; r.poll(1,250); assert(r.sample.status==Validity::valid);
    b.status=1; r.poll(2,250); assert(r.sample.status==Validity::invalid);
    b.status=0; b.ok=false; r.poll(3,250); assert(r.sample.status==Validity::invalid);
    b.ok=true; r.poll(4,250); b.available=false; r.poll(254,250); assert(r.sample.status==Validity::stale);
    b.initialized=false; r.initialize(); assert(r.sample.status==Validity::invalid);
}

/* Purpose: Run regression gate. Design: fail process on any violated invariant.
 * Workflow: test runner. Data Handoff: durable stdout/exit status.
 */
int main() {
    parser_tests(); motor_tests(); driver_tests(); controller_tests(); rear_tests();
    std::cout << "PASS: parser, motor, driver outputs, controller/watchdog, rear adapter (host simulation)\n";
}
