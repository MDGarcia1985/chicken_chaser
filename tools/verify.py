"""File: tools/verify.py
Purpose: Repeat the host milestone gate and preserve executable evidence.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: hardware checks remain separate; no inferred physical PASS.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-002.
"""
import compileall
import json
import os
from pathlib import Path
import subprocess
import sys
from chicken_chaser.contracts import ROOT, load_config, validate


def run(args, log):
    """Purpose: Execute a gate and capture actual output. Design: subprocess argv,
    timeout and failure stops progression. Workflow: verification command.
    Data Handoff: stdout/stderr evidence and nonzero exception on failure.
    """
    result=subprocess.run(args,cwd=ROOT,text=True,capture_output=True,timeout=60)
    log.write("COMMAND: "+repr(args)+"\n"+result.stdout+result.stderr+f"\nEXIT: {result.returncode}\n")
    log.flush()
    print(result.stdout+result.stderr,end="")
    if result.returncode:
        raise RuntimeError(f"Gate failed: {args}")


def main():
    """Purpose: Validate host milestone. Design: syntax/schema before runtime and
    operator integration, preserve log without rewriting TEST_LOG.
    Workflow: python tools/verify.py. Data Handoff: build/verification.txt and exit.
    """
    for folder in ("src","tools","tests","app_lab"):
        if not compileall.compile_dir(ROOT/folder,quiet=1):
            raise RuntimeError("Python compilation failed")
    load_config()
    validate("model",json.loads((ROOT/"config/model_manifest.json").read_text()))
    executable=ROOT/"build"/("core_tests.exe" if os.name=="nt" else "core_tests")
    (ROOT/"build").mkdir(exist_ok=True)
    with (ROOT/"build/verification.txt").open("w",encoding="utf-8") as log:
        log.write("HOST SIMULATION; physical outputs are disabled.\n")
        run([sys.executable,"tools/build_host.py"],log)
        run([str(executable)],log)
        run([sys.executable,"-m","unittest","discover","-s","tests","-v"],log)
        run([sys.executable,"-m","chicken_chaser.runtime","--demo","--seconds",".5"],log)
    print("Host milestone gate complete. Device/physical validation remains blocked.")


if __name__ == "__main__":
    main()
