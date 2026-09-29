# Contributing to Project F.L.A.R.E. (SIH26053)
### **Foveated LiDAR Architecture for Robotic Edge-perception**

Thank you for your interest in contributing to **Project F.L.A.R.E. (Foveated LiDAR Architecture for Robotic Edge-perception)**! This repository contains a production-grade, mathematically grounded perception pipeline coupled with a high-fidelity Unity 6 tactical simulation environment.

---

## 🛠️ Development Environment Setup

### 1. Prerequisites
- **Python:** 3.11 or higher
- **C# / Unity:** Unity 6 (6000.x) with Universal Render Pipeline (URP)
- **Git LFS:** Required for handling large mesh assets and binary models

### 2. Python Environment Setup
```bash
git clone https://github.com/j7452479-a11y/sih.git
cd sih

python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Running Unit & Integration Tests
Before submitting any pull request, ensure all tests pass:
```bash
pytest tests/ -v
```

---

## 📐 Coding Guidelines

### Python Core Math & Perception (`core_math/`, `tracking/`, `ingestion/`)
- **Deterministic Latency:** Algorithms must maintain $\ge 20\text{ Hz}$ update rate ($< 50\text{ ms}$ loop duration, target $< 10\text{ ms}$).
- **Vectorized Operations:** Avoid pure Python nested loops over point clouds; leverage NumPy/PyTorch vectorized indexing and tensor broadcasting.
- **Zero-Copy Ingestion:** Ensure network datagram buffers avoid excessive copies to preserve high throughput on SWaP hardware.
- **Strict Typing & Docstrings:** All public functions must include type annotations and mathematical docstrings detailing inputs, outputs, and equations.

### Unity 6 Simulation (`unity_bridge/`, `unity/SIH_TacticalSim/`)
- **Burst Compiler & C# Jobs:** Raycasting and point cloud serialization should utilize Unity's C# Job System with NativeArrays to avoid GC allocations during simulation frames.
- **Coordinate Consistency:** Unity uses a left-handed coordinate system ($Y$-up). The perception engine expects right-handed ENU coordinates ($Z$-up). Ensure proper frame transformations are maintained in streamer bridges.

---

## 🚀 Submitting Pull Requests
1. Fork the repository and create your feature branch: `git checkout -b feat/your-feature-name`.
2. Commit your changes with conventional commit messages (`feat:`, `fix:`, `docs:`, `perf:`).
3. Ensure CI tests pass locally.
4. Open a pull request against the `main` branch using the provided PR template.
