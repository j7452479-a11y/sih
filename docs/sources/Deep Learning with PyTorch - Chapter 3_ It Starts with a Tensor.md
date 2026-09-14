# Chapter 3: It Starts with a Tensor
Deep Learning with PyTorch Authors: Eli Stevens, Luca Antiga, Thomas Viehmann
## 3.1 Introduction: The World as Tensors
Tensors are the fundamental data structures in deep learning and numerical computing frameworks such as PyTorch. A tensor is a generalization of vectors and matrices to an arbitrary number of dimensions. In LiDAR and point cloud processing pipelines, 3D point clouds (N \\times 3), intensity channels (N \\times 4), voxel grids (C \\times D \\times H \\times W), and 2.5D elevation heightmaps (H \\times W) are natively represented as PyTorch tensors.
---
## 3.2 Tensors: Multidimensional Arrays vs. Python Lists
- Python lists store pointers to scattered objects in memory, incurring overhead and lacking cache locality.
- PyTorch tensors wrap contiguous blocks of memory containing unboxed numeric types, backed by C-level allocations.
- A PyTorch tensor provides:
- High-performance SIMD operations.
- Hardware acceleration via CUDA GPUs / MPS.
- Automatic differentiation (autograd).
---
## 3.3 Tensor Storage, Views, Strides, and Offsets
Understanding PyTorch tensor mechanics is essential for vectorizing point cloud and grid algorithms without redundant memory allocations:
1. ***Storage***:
- The raw, flat 1D array of numerical data stored sequentially in memory (`tensor.storage()`).
2. ***Size / Shape***:
- A tuple representing the dimensions along each axis (`tensor.shape` or `tensor.size()`).
3. ***Offset***:
- The index in the storage corresponding to the first element of the tensor (`tensor.storage_offset()`).
4. ***Stride***:
- The number of storage elements that must be skipped to jump to the next element along each dimension (`tensor.stride()`).
- Example: A 2D matrix of shape (3, 4) with row-major layout has strides `(4, 1)`.
5. ***Views vs. Copies***:
- Operations like `tensor.view()`, `tensor.transpose()`, `tensor.permute()`, and narrow slicing create new views over the same underlying storage by modifying size, stride, and offset without copying data.
- Calling `tensor.contiguous()` creates a new storage buffer if strides no longer match sequential memory order.
---
## 3.4 Tensor Data Types and Precision
- Float types: `torch.float32` (standard single precision), `torch.float64` / `torch.double`, `torch.float16` / `torch.bfloat16`.
- Integer types: `torch.int64` / `torch.long` (default for indexing and cluster/bin IDs), `torch.int32`, `torch.int8`, `torch.uint8`.
- Boolean type: `torch.bool` (masks).
- Casting via `tensor.to(torch.float32)` or `tensor.float()`.
---
## 3.5 Tensor Indexing and Vectorized Manipulation for Spatial Data
Efficient point cloud operations rely heavily on tensor indexing patterns:
1. ***Basic Slicing***: `points[:, :3]` extracts 3D coordinates (x, y, z) from an (N, C) point cloud.
2. ***Boolean Masking***: Filtering ground points or spatial bounding boxes:

3. ***Integer / Advanced Indexing***: Gathering selected cluster indices or downsampled point subsets:

4. ***Reshaping and Geometry Transformations***:
- Rigid body transform using homogeneous coordinates: P\_{\\text{transformed}} = (R @ P^T + T)^T or batch matrix multiplication using `torch.bmm` / `torch.matmul`.
---
## 3.6 Hardware Acceleration: Moving to the GPU
- Moving tensors between host CPU and device GPU:

- Device transfers should be minimized; operations like voxelization, height computation, and clustering bin assignments should remain on GPU tensors for high throughput.
---
## 3.7 NumPy Interoperability and Memory Sharing
- Zero-copy tensor conversion between NumPy arrays and PyTorch CPU tensors:
- `torch.from_numpy(numpy_array)` shares underlying memory buffer.
- `tensor.numpy()` returns a NumPy view if on CPU.
- Tensors requiring gradients or on GPU must first be detached and moved:

---
## 3.8 Relevance to LiDAR & Grid Modeling
- High-throughput point-to-voxel quantization: PyTorch indexing, `torch.bucketize`, and `torch.scatter_reduce` allow aggregating thousands of 3D points into elevation grid cells in sub-millisecond execution times without Python `for`-loops.