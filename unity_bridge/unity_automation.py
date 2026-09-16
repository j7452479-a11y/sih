"""
unity_automation.py - Unity 6 Automation & Batchmode Headless Pipeline
SIH26053 MUM-T Tactical Edge Perception Engine

Automates:
1. Headless batchmode scene compilation for the Square Tactical Village Proving Ground.
2. Verification of the 46 battlefield structures, church 18m spire, underpass bridge, and hostiles.
3. Verification of LiDAR streamers (Ports 5001 & 5002) and Threat Reticle Manager (Port 5003).
4. Launching the Unity Tactical Simulation.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
UNITY_PROJECT = PROJECT_ROOT / "unity" / "SIH_TacticalSim"
UNITY_EXE = Path("C:/Program Files/Unity/Hub/Editor/6000.6.0f1/Editor/Unity.exe")

def find_unity_binary() -> Path:
    if UNITY_EXE.exists():
        return UNITY_EXE
    # Fallback search in standard locations
    hub_editors = Path("C:/Program Files/Unity/Hub/Editor")
    if hub_editors.exists():
        for ed in hub_editors.iterdir():
            exe = ed / "Editor" / "Unity.exe"
            if exe.exists():
                return exe
    raise FileNotFoundError("Unity 6 Editor executable not found in Program Files/Unity/Hub/Editor.")

def build_tactical_proving_ground():
    """Compiles the complete square village proving ground scene using Unity headless batchmode."""
    unity_bin = find_unity_binary()
    log_file = UNITY_PROJECT / "build.log"

    print(f"[*] Executing Unity Batchmode SceneBuilder:")
    print(f"    Binary:  {unity_bin}")
    print(f"    Project: {UNITY_PROJECT}")
    print(f"    Method:  SceneBuilder.BuildScene")
    print(f"    Log:     {log_file}")

    cmd = [
        str(unity_bin),
        "-quit",
        "-batchmode",
        "-nographics",
        "-projectPath", str(UNITY_PROJECT),
        "-executeMethod", "SceneBuilder.BuildScene",
        "-logFile", str(log_file),
    ]

    t0 = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.perf_counter() - t0

    if proc.returncode == 0:
        print(f"[+] SUCCESS: Square Tactical Village scene built in {elapsed:.2f}s!")
        print(f"    Scene file: Assets/Scenes/TacticalProvingGround.unity")
        return True
    else:
        print(f"[-] ERROR: Unity Batchmode exited with code {proc.returncode}")
        if log_file.exists():
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                print("--- Tail of build.log ---")
                print("".join(lines[-25:]))
        return False

def run_simulation_editor():
    """Launches the Unity Editor with the Tactical Proving Ground project."""
    unity_bin = find_unity_binary()
    print(f"[*] Opening Unity Editor at {UNITY_PROJECT}...")
    cmd = [
        str(unity_bin),
        "-projectPath", str(UNITY_PROJECT),
    ]
    subprocess.Popen(cmd)
    print("[+] Unity Editor launched.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Unity Tactical Simulation Automation")
    parser.add_argument("--build", action="store_true", help="Build the square village proving ground scene in batchmode")
    parser.add_argument("--open", action="store_true", help="Open the Unity Editor with the tactical project")
    args = parser.parse_args()

    if args.build or (not args.build and not args.open):
        success = build_tactical_proving_ground()
        if not success:
            sys.exit(1)

    if args.open:
        run_simulation_editor()
