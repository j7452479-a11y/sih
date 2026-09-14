# Robotec GPU Lidar (RGL): System Architecture & UE5 Integration Guide
Developed by Robotec.AI — Real-Time Raycasting via NVIDIA OptiX and CUDA
---
## 1. Overview and Core Philosophy
Simulating modern LiDAR sensors (e.g., Ouster OS1-128, Hesai Pandar128, Velodyne Alpha Prime) at full scan rates requires casting 50,000 to 200,000+ rays per frame at 10–20 Hz. Traditional CPU-bound physics raycasts (such as PhysX or Unreal's `LineTraceMultiByChannel`) stall the game thread, causing severe frame drops.
Robotec GPU Lidar (RGL) offloads the entire raycasting and point-cloud filtering pipeline to the GPU using ***NVIDIA OptiX 7.x*** hardware RT Cores (Turing, Ampere, Ada Lovelace, Blackwell) and custom ***CUDA*** kernels.
---
## 2. OptiX & Hardware-Accelerated Ray Tracing Architecture
### 2.1 Acceleration Structures (BVH)
- ***Geometry Acceleration Structures (GAS)***:
- Each static or dynamic 3D mesh in the simulation world (terrain, buildings, vehicles, foliage) is represented as triangle meshes uploaded directly to GPU memory.
- OptiX builds and traverses Bounding Volume Hierarchies (BVH) directly on dedicated GPU RT cores.
- ***Instance Acceleration Structures (IAS)***:
- Dynamic entities (such as moving UGVs, drones, pedestrians, rotating sensor heads) are instanced with affine transformation matrices (4 \\times 3 or 4 \\times 4).
- Updating vehicle poses only requires updating the top-level IAS matrix pointers on the GPU, avoiding expensive full-mesh re-triangulation on the CPU.
### 2.2 Ray Generation & Sensor Geometry
- ***Configurable Firing Patterns***:
- Rays are defined by origin offsets and direction vectors: \\mathbf{r}(t) = \\mathbf{o} + t \\mathbf{d}, parameterized in sensor-local spherical coordinates (\\theta\_{\\text{azimuth}}, \\phi\_{\\text{elevation}}, r\_{\\text{range}}).
- Supports spinning LiDARs, solid-state LiDARs (MEMS/prism scanning), and custom foveated beam distributions.
- ***Ray Tracing Pipeline***:
- `optixLaunch()` triggers parallel ray generation threads across CUDA streaming multiprocessors (SMs).
- Ray-triangle intersection tests are evaluated directly in hardware.
- Closest-hit programs retrieve hit distances, surface normals, instance IDs, and material properties (intensity, reflectivity).
- Miss programs handle rays exceeding maximum sensor range or escaping into the skybox without generating false obstacle returns.
---
## 3. Asynchronous Execution and Graph-Based Processing Pipeline
RGL organizes point-cloud processing into an ***asynchronous Directed Acyclic Graph (DAG)*** of nodes executing on CUDA streams:
1. ***Raytrace Node***: Launches OptiX kernels and generates raw hit buffers.
2. ***Transform Node***: Applies sensor-to-vehicle or vehicle-to-world coordinate transformations directly on GPU memory using SE(3) homogeneous matrices: \\mathbf{p}\_{\\text{world}} = R\_{\\text{sensor}}^{\\text{world}} \\mathbf{p}\_{\\text{sensor}} + \\mathbf{t}\_{\\text{sensor}}^{\\text{world}}
3. ***Filter Nodes***:
- ***Range Filter***: Prunes points outside \[r\_{\\min}, r\_{\\max}\].
- ***Ray Miss Removal***: Eliminates non-return rays.
- ***Gaussian Noise Node***: Simulates atmospheric and sensor beam divergence noise: \\tilde{r} = r + \\mathcal{N}(0, \\sigma\_r^2)
- ***Velocity Distortion (Motion Distortion) Node***: Corrects or injects rolling-shutter beam distortion caused by vehicle velocity during a single 360^\\circ revolution.
4. ***Spatial Downsampling & Format Conversion***:
- Voxel grid downsampling or format conversion (e.g., XYZ, XYZIR, PointXYZL with semantic labels).
5. ***Output Nodes***:
- Publishes directly via ROS 2 / Agnocast zero-copy shared memory, writes to PCD files, or shares CUDA pointers with PyTorch.
---
## 4. Unreal Engine 5 (UE5) Integration Workflow
### 4.1 Bridging the Game Engine and GPU Lidar
1. ***Scene Geometry Synchronization***:
- Static mesh components and Landscape terrain vertices are extracted once and cached into OptiX GAS.
- Dynamic actor transforms (e.g., UGV crawler pose, drone position, enemy vehicles) are synced at each tick to the OptiX IAS.
2. ***Non-Blocking Asynchronous Simulation Loop***:
- UE5 `Tick()` updates actor kinematics and submits the LiDAR raycast job to an asynchronous CUDA stream.
- The game rendering thread (Lumen/Nanite) and CPU game loop continue uninterrupted without waiting for raycast completion.
- Results are retrieved in subsequent frames or processed directly in GPU memory using CUDA-to-DirectX/Vulkan/PyTorch interop.
3. ***Multi-Agent Simulation (MUM-T Drone + Crawler)***:
- Multiple sensors (e.g., aerial downward-facing LiDAR on the drone, forward horizontal LiDAR on the crawler) run concurrently on the same GPU without thread contention.
- Shared GPU memory avoids duplicate scene representation across vehicles.
---
## 5. Performance Characteristics
- ***Throughput***: Capable of raytracing >10^7 rays/second on NVIDIA RTX GPUs.
- ***CPU Overhead***: < 1\\,\\text{ms} CPU time per frame, as computation is restricted to transform uploads and kernel dispatches.
- ***Memory Footprint***: Substantially smaller than maintaining dense 3D voxel grids or allocating separate PhysX query structures.