"""File: tools/build_host.py
Purpose: Generate validated MCU constants and build the host core/test executable.
Owner: Michael Garcia; contributor: Codex / ChatGPT.
Contact: Pending confirmation. License: Pending confirmation.
Constraints: no device upload; GCC runtime linked statically on Windows.
Related decisions: DEV-2026-10-12-001, DEV-2026-10-12-003.
"""
import os
from pathlib import Path
import shutil
import subprocess
from generate_mcu import generate
from chicken_chaser.contracts import ROOT


def main():
    """Purpose: Produce repeatable host validation binaries.
    Design: explicit argv and check=True, no shell; separate T0 compilation from T1.
    Workflow: run before dry-run/tests. Data Handoff: build files, compiler errors.
    """
    generate()
    compiler = os.getenv("CXX") or shutil.which("g++")
    if not compiler:
        raise RuntimeError("C++17 GCC compiler missing; set CXX")
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    flags = [compiler,"-std=c++17","-Wall","-Wextra","-Werror","-Ifirmware"]
    executable = build / ("core_tests.exe" if os.name == "nt" else "core_tests")
    library = build / ("chicken_host.dll" if os.name == "nt" else "libchicken_host.so")
    subprocess.run(flags+["firmware/core.cpp","tests/core_tests.cpp","-o",str(executable)],cwd=ROOT,check=True)
    shared = ["-shared","-static"] if os.name == "nt" else ["-shared","-fPIC"]
    subprocess.run(flags+shared+["firmware/core.cpp","firmware/host_api.cpp","-o",str(library)],cwd=ROOT,check=True)
    print(f"Built {executable.name} and {library.name}; host simulation only")


if __name__ == "__main__":
    main()
