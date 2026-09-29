## 📝 Description
Please include a summary of the changes and the related issue/feature.

## 🎯 Target Subsystem
- [ ] Core Math & Foveated Grid (`core_math/`)
- [ ] Multi-Level Surface (MLS) & Void Carving (`core_math/`)
- [ ] Multi-Target Tracking & Kalman Filter (`tracking/`)
- [ ] Ingestion & Jitter Buffer (`ingestion/`)
- [ ] C2 Server & Web Telemetry (`c2_interface/`)
- [ ] Unity 6 Simulation & C# Job Bridges (`unity_bridge/`, `unity/`)
- [ ] Deep Learning Sparse CNN & TensorRT (`deep_learning/`)
- [ ] Automotive Civilian EV Perception (`simulate_civilian_ev.py`)

## 🧪 Verification & Testing
- [ ] PyTest suite passes (`pytest tests/ -v`)
- [ ] Verified at 20 Hz update rate with $< 10\text{ ms}$ processing latency
- [ ] Memory footprint benchmark verified ($< 15\text{ MB}$ RAM consumption)
- [ ] C# Unity bridge scripts compile cleanly in Unity 6
