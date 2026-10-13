/* File: firmware/host_api.cpp
 * Purpose: C ABI boundary for Python simulation using the actual C++ core.
 * Owner: Michael Garcia; contributor: Codex / ChatGPT.
 * Contact: Pending confirmation. License: Pending confirmation.
 * Constraint: never writes GPIO; single locked caller. DEV-2026-10-12-002.
 */
#include "core.hpp"
#include "generated_config.hpp"
#ifdef _WIN32
#define API __declspec(dllexport)
#else
#define API
#endif
using chicken::Controller;
using chicken::Validity;
extern "C" {
/* Purpose: Create/destroy simulator. 
 * Design: opaque owner. 
 * Workflow: bridge init/close.
 * Data Handoff: pointer owned by Python; no hardware effects.
 */
API void* cc_create() { return new Controller(SIM_CONFIG); }
API void cc_destroy(void* ptr) { delete static_cast<Controller*>(ptr); }
API const char* cc_config_hash() { return CONFIG_SHA256; }
/* Purpose: Supply simulated range evidence. Design: explicit validity enum and
 * timestamp. Workflow: fixture source. Data Handoff: mm to C++ enforcement.
 */
API void cc_range(void* ptr, int rear, int status, unsigned mm, uint32_t now) {
    auto& c=*static_cast<Controller*>(ptr);
    (rear ? c.rear : c.front)={static_cast<Validity>(status),mm,now};
}
/* Purpose: Expose loop-owned authority actions. Design: caller serializes access.
 * Workflow: host dry-run boundary. Data Handoff: ack, epochs and applied outputs.
 */
API int cc_arm(void* ptr,uint32_t session,uint32_t now) { return static_cast<Controller*>(ptr)->arm(session,now,true); }
API int cc_clear(void* ptr,uint32_t now) { return static_cast<Controller*>(ptr)->clear_fault(now); }
API void cc_stop(void* ptr,uint32_t now) { static_cast<Controller*>(ptr)->stop(now); }
API uint32_t cc_offer(void* ptr,uint32_t now) { return static_cast<Controller*>(ptr)->offer(now); }
API uint32_t cc_remaining(void* ptr,uint32_t now) { return static_cast<Controller*>(ptr)->remaining(now); }
API uint32_t cc_generation(void* ptr) { return static_cast<Controller*>(ptr)->generation; }
API uint32_t cc_session(void* ptr) { return static_cast<Controller*>(ptr)->session; }
API uint32_t cc_ack(void* ptr) { return static_cast<Controller*>(ptr)->ack; }
API int cc_armed(void* ptr) { return static_cast<Controller*>(ptr)->armed; }
API const char* cc_fault(void* ptr) { return static_cast<Controller*>(ptr)->fault.c_str(); }
API float cc_left(void* ptr) { return static_cast<Controller*>(ptr)->left.applied(); }
API float cc_right(void* ptr) { return static_cast<Controller*>(ptr)->right.applied(); }
API void cc_tick(void* ptr,uint32_t now) { static_cast<Controller*>(ptr)->tick(now); }
/* Purpose: Translate already schema-validated logical command. Design: fixed typed
 * ABI, C++ rechecks all motion semantics. Workflow: command boundary.
 * Data Handoff: acceptance, ack and loop-applied state.
 */
API int cc_command(void* ptr,uint32_t session,uint32_t sequence,uint32_t generation,
    uint32_t epoch,uint32_t observation,uint32_t age,uint32_t lifetime,float left,float right,int follow,uint32_t now) {
    chicken::Command c{session,sequence,generation,epoch,observation,age,lifetime,left,right,follow != 0};
    return static_cast<Controller*>(ptr)->accept(c,now);
}
}
