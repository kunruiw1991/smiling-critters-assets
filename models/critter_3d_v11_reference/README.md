# CatNap v11 — geometry and stitching checkpoint

Private checkpoint saved before experimenting with alternative rendering materials.

## Restore

Unzip `CatNap-Final-v11.blend.zip` and open the resulting file with Blender 4.5.7 LTS. This is the authoritative editable scene, including geometry, individual stitch curves, procedural materials, lights and cameras. No previous model versions are required to open it.

- `CatNap-Final-v11.glb.zip`: portable mesh export, with actual stitch geometry.
- `CatNap-Final-v11.usdz.zip`: iPad preview model.
- `Front.png`, `Three-quarter.png`, `Back.png`, `Stitch-detail.png`: checkpoint renders.
- `SHA256-manifest.json`: SHA-256 checksums of the original uncompressed deliverables.
- `build-scripts.zip`: development scripts for provenance. These retain original local paths and earlier-version dependencies; they are not a standalone rebuild package. Restore from the included Blender scene.

## Checkpoint scope

Approved head/body/tail and v10 crescent geometry; v11 stitching and textile surface adjustments. Static model without rigging, animation or strand-based fur. Procedural Blender texture detail may be simplified in GLB/USDZ. Back seam placement is an inferred construction detail because the reference does not show the back.

Create a new scene copy or commit before material experiments; retain this initial checkpoint for restoration.

Reference: https://poppyplaytime.com/pages/catnap

Character rights belong to their respective owners. This repository is private and no third-party character license is granted.
