# Chapter 14: Quadtrees: Non-Uniform Mesh Generation
Computational Geometry: Algorithms and Applications (3rd Edition) Authors: Mark de Berg, Otfried Cheong, Marc van Kreveld, Mark Overmars
## 14.1 Introduction: Uniform vs. Non-Uniform Meshes
A mesh is a decomposition of a continuous geometric domain into simpler geometric elements (polygons or polyhedra, usually triangles in 2D or tetrahedra in 3D).
- ***Uniform meshes*** use cells of uniform size throughout the space. While simple, uniform meshes become computationally intractable and memory-inefficient when point distributions or terrain features have non-uniform densities (e.g., dense point clouds near obstacles vs. sparse returns on open ground).
- ***Non-uniform / graded meshes*** adapt cell resolution dynamically: fine cells where detail, steep gradients, or high point density is present, and coarse cells across flat or empty regions.
- Quadtrees (and their 3D extension, Octrees) provide a hierarchical, recursive spatial partitioning structure that forms the foundation for generating well-behaved, non-uniform meshes.
---
## 14.2 Quadtrees for Point Sets
### 14.2.1 Definition & Structure
- Let U be a square bounding box in the plane. A quadtree decomposes U recursively:
- The root represents the whole bounding box U.
- If a square region C contains more points than a predefined threshold (typically 1 point per leaf), C is partitioned into four equal-sized child quadrants: North-West (NW), North-East (NE), South-West (SW), and South-East (SE).
- The depth of the tree depends on the minimum distance between points. If two points are very close, the quadtree depth can be large.
### 14.2.2 Construction Complexity
- For a set of n points, the depth D of the quadtree is bounded by O(\\log(s/c)), where s is the side length of the bounding box and c is the minimum distance between any pair of points.
- The total number of nodes is O(n D), and constructing the tree takes O(n D) time.
- Using compressed quadtrees, the size can be strictly bounded by O(n), constructed in O(n \\log n) time.
---
## 14.3 Balanced Quadtrees (1-Separated Condition)
To construct a valid, graded triangular mesh without degenerate or skinny triangles (which cause severe numerical instability in finite element analysis and spatial interpolation), the quadtree must be ***balanced***.
### 14.3.1 The Balance Condition (1-Separated)
- A quadtree is ***balanced*** (or satisfies the 1-neighbor / 1-separated condition) if: ***Every leaf cell is adjacent (by edge or vertex) to neighboring leaf cells whose depth differs by at most 1.***
- In terms of cell side lengths, if a leaf cell has size s, all adjacent leaf cells have sizes in the set \\{s/2, s, 2s\\}.
### 14.3.2 Balancing Algorithm
- Start with the raw quadtree.
- While there exists a leaf cell C adjacent to a leaf cell C' such that \\text{depth}(C) > \\text{depth}(C') + 1:
- Subdivide cell C' into four children.
- Check the newly created cells against their neighbors.
- Theorem: Balancing a quadtree with m nodes increases the number of nodes by at most a constant factor, yielding O(m) nodes in O(m) time.
---
## 14.4 From Balanced Quadtrees to Triangular Meshes
Once a balanced quadtree is obtained, it is converted into a conforming triangular mesh:
### 14.4.1 Handling Hanging Nodes & Steiner Points
- When a smaller leaf cell borders a larger leaf cell, the midpoint of the larger cell's edge acts as a ***hanging node*** (T-junction).
- To preserve topology and create a conforming mesh (where the intersection of any two triangles is either empty, a shared vertex, or a shared edge):
1. Insert vertices at all quadtree corners and edge midpoints where subdivisions meet.
2. Subdivide each square leaf cell into triangles based on the number of split edges:
- ***0 split edges***: Triangulate with diagonal cuts or center vertex (4 triangles).
- ***1 split edge***: Connect the split midpoint to the opposite corners or center vertex.
- ***2 split edges***: Connect midpoints to center Steiner point.
- ***3 or 4 split edges***: Connect all midpoints and corners to a central Steiner point (6\\text{--}8 triangles).
### 14.4.2 Mesh Quality & Angle Guarantees
- The balance property directly guarantees that the minimum angle of any resulting triangle is bounded away from zero (e.g., minimum angle \\ge 19.5^\\circ or \\ge 45^\\circ depending on subdivision patterns).
- Maximum angles are also bounded strictly below 180^\\circ, preventing ill-conditioned interpolation.
---
## 14.5 Relevance to LiDAR Terrain & Elevation Modeling
1. ***Adaptive 2.5D Elevation Grids***: Instead of maintaining a uniform high-resolution 2.5D grid across massive geographic scenes, a quadtree adaptively allocates high resolution only where point density or surface roughness (gradient variance) is high.
2. ***Ray-Casting & Spatial Search Acceleration***: Quadtrees provide O(\\log N) spatial indexing for neighbor queries, radius search, and ground-surface point filtering.
3. ***Multi-Resolution Digital Elevation Models (DEM)***: Efficient storage, level-of-detail (LOD) streaming, and triangular surface reconstruction from LiDAR scans.