#!/usr/bin/env python3
"""
Native Blender 4.3 Builder, Rigging, Animation & Cycles Studio Renderer (v2 Calibrated)
for Hoppy Hopscotch (#012 Official Plush Base Model - Smiling Critters).

Run headless via:
  /tmp/blender/blender -b --factory-startup --threads 8 --python-exit-code 1 -P /tmp/smiling-critters-assets/models/build_hoppy_hopscotch_blender.py
"""

import os
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, noise

OUT_DIR = "/tmp/smiling-critters-assets/models"
ANIM_DIR = "/tmp/smiling-critters-assets/animations"
WORK_DIR = "/tmp/work_hoppy"
FART_FRAMES_DIR = os.path.join(WORK_DIR, "frames")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANIM_DIR, exist_ok=True)
os.makedirs(FART_FRAMES_DIR, exist_ok=True)

BLEND_PATH = os.path.join(OUT_DIR, "hoppy_hopscotch_plush_base_model.blend")
GLB_PATH = os.path.join(OUT_DIR, "hoppy_hopscotch_plush_base_model.glb")
OBJ_PATH = os.path.join(OUT_DIR, "hoppy_hopscotch_plush_base_model.obj")
RENDER_FRONT_PATH = os.path.join(OUT_DIR, "hoppy_hopscotch_blender_cycles_render.png")
RENDER_PREVIEW_PATH = os.path.join(OUT_DIR, "hoppy_hopscotch_3d_preview.png")


# ==============================================================================
# 1. SCENE RESET & HELPER UTILITIES
# ==============================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

main_col = bpy.data.collections.new("HoppyHopscotch_Plush_Rig")
scene.collection.children.link(main_col)

studio_col = bpy.data.collections.new("Studio_Lighting_And_Stage")
scene.collection.children.link(studio_col)


def set_bsdf_input(bsdf, value, *names):
    for name in names:
        if name in bsdf.inputs:
            bsdf.inputs[name].default_value = value
            return True
    return False


def srgb_to_linear(c):
    if c <= 0.04045:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def hex_to_rgba(hex_val, alpha=1.0):
    r = srgb_to_linear(((hex_val >> 16) & 0xFF) / 255.0)
    g = srgb_to_linear(((hex_val >> 8) & 0xFF) / 255.0)
    b = srgb_to_linear((hex_val & 0xFF) / 255.0)
    return (r, g, b, alpha)


def to_b_vec(x, y_up, z_fwd):
    return Vector((float(x), float(-z_fwd), float(y_up)))


def head_front_z(x, y_up):
    nx = x / 0.72
    ny = (y_up - 1.88) / 0.56
    r2 = min(0.94, nx * nx + ny * ny)
    return 0.62 * math.sqrt(max(0.06, 1.0 - r2))


def upper_smile_y(x):
    t = max(-1.0, min(1.0, x / 0.52))
    return 1.765 + 0.110 * (t * t) - 0.020 * (t ** 4)


def lower_smile_y(x):
    t = max(-1.0, min(1.0, x / 0.52))
    return 1.425 + 0.435 * (t * t)


def plush_fleece_displacement(p_world):
    """Subtle multi-octave 3D plush fleece micro-fuzz displacement."""
    q1 = Vector((p_world.x * 8.0, p_world.y * 8.0, p_world.z * 8.0))
    q2 = Vector((p_world.x * 18.0 + 2.3, p_world.y * 18.0 - 1.5, p_world.z * 18.0 + 1.9))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    return 0.010 * n1 + 0.005 * abs(n2)


# ==============================================================================
# 2. PROCEDURAL CYCLES / GLTF PBR MATERIALS (HOPPY HOPSCOTCH PALETTE + FART CLOUD)
# ==============================================================================
def create_plush_material(name, hex_color, roughness=0.86, spec_ior=0.10,
                          sheen=0.22, sheen_tint_mult=1.05,
                          bump_scale=65.0, bump_strength=0.14,
                          metallic=0.0, coat=0.0, coat_rough=0.05,
                          subsurface=0.0, emission_strength=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out = nodes.new(type="ShaderNodeOutputMaterial")
    out.location = (420, 0)

    bsdf = nodes.new(type="ShaderNodeBsdfPrincipled")
    bsdf.location = (80, 0)
    rgba = hex_to_rgba(hex_val=hex_color)
    set_bsdf_input(bsdf, rgba, "Base Color")
    set_bsdf_input(bsdf, roughness, "Roughness")
    set_bsdf_input(bsdf, metallic, "Metallic")
    set_bsdf_input(bsdf, spec_ior, "Specular IOR Level", "Specular")
    set_bsdf_input(bsdf, sheen, "Sheen Weight", "Sheen")
    set_bsdf_input(bsdf, 0.78, "Sheen Roughness")
    set_bsdf_input(
        bsdf,
        (min(1.0, rgba[0] * sheen_tint_mult),
         min(1.0, rgba[1] * sheen_tint_mult),
         min(1.0, rgba[2] * sheen_tint_mult), 1.0),
        "Sheen Tint"
    )
    if coat > 0.0:
        set_bsdf_input(bsdf, coat, "Coat Weight", "Clearcoat")
        set_bsdf_input(bsdf, coat_rough, "Coat Roughness", "Clearcoat Roughness")
    if subsurface > 0.0:
        set_bsdf_input(bsdf, subsurface, "Subsurface Weight", "Subsurface")
    if emission_strength > 0.0:
        set_bsdf_input(bsdf, rgba, "Emission Color", "Emission")
        set_bsdf_input(bsdf, emission_strength, "Emission Strength")

    if bump_strength > 0.0:
        tex_coord = nodes.new(type="ShaderNodeTexCoord")
        tex_coord.location = (-650, -180)

        noise_node = nodes.new(type="ShaderNodeTexNoise")
        noise_node.location = (-420, -180)
        noise_node.inputs["Scale"].default_value = bump_scale
        noise_node.inputs["Detail"].default_value = 10.0
        noise_node.inputs["Roughness"].default_value = 0.74

        bump = nodes.new(type="ShaderNodeBump")
        bump.location = (-180, -180)
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.018

        links.new(tex_coord.outputs["Object"], noise_node.inputs["Vector"])
        links.new(noise_node.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


MATS = {
    # Bright emerald/mint-green plush fleece bunny body (#34B857 calibrated for Cycles AgX)
    "BodyGreen": create_plush_material(
        "Hoppy_Plush_Body_Green", 0x24A848, roughness=0.86, spec_ior=0.09,
        sheen=0.22, sheen_tint_mult=1.08, bump_scale=72.0, bump_strength=0.16, subsurface=0.02
    ),
    # Pastel mint-green belly, inner ears & paw pads (#A7F3D0 calibrated for Cycles AgX)
    "PastelMint": create_plush_material(
        "Hoppy_Pastel_Mint_Accent", 0x76E4B0, roughness=0.84, spec_ior=0.10,
        sheen=0.20, sheen_tint_mult=1.04, bump_scale=82.0, bump_strength=0.12, subsurface=0.02
    ),
    # Darker forest-green feet bottoms, ear tips, inner ear center & paw cuffs (#1E7E38)
    "ForestGreen": create_plush_material(
        "Hoppy_Forest_Green_Dark", 0x126628, roughness=0.88, spec_ior=0.08,
        sheen=0.18, sheen_tint_mult=1.06, bump_scale=76.0, bump_strength=0.15
    ),
    # Cute pink triangular rabbit nose & tongue (#F472B6)
    "NosePink": create_plush_material(
        "Hoppy_Rabbit_Nose_Pink", 0xEC4899, roughness=0.72, spec_ior=0.14,
        sheen=0.20, sheen_tint_mult=1.05, bump_scale=95.0, bump_strength=0.08, subsurface=0.03
    ),
    # Stark bright white plush buck teeth (#FFFFFF)
    "ToothWhite": create_plush_material(
        "Hoppy_Buck_Teeth_White", 0xFFFFFF, roughness=0.46, spec_ior=0.30,
        sheen=0.18, sheen_tint_mult=1.0, bump_scale=110.0, bump_strength=0.03,
        coat=0.12, emission_strength=0.05
    ),
    # Iconic Bright Yellow Lightning Bolt Pendant (#FFD60A)
    "PendantYellow": create_plush_material(
        "Hoppy_Lightning_Pendant_Yellow", 0xFFB700, roughness=0.30, spec_ior=0.30,
        sheen=0.15, sheen_tint_mult=1.05, bump_scale=120.0, bump_strength=0.02,
        coat=0.25, emission_strength=0.06
    ),
    # Deep jet-black glossy acrylic dome eyes
    "EyeGloss": create_plush_material(
        "Hoppy_Eye_Acrylic_Black", 0x020203, roughness=0.04, spec_ior=0.12,
        sheen=0.0, bump_strength=0.0, coat=0.30, coat_rough=0.015
    ),
    # Studio catchlight highlight on eyes
    "CatchlightWhite": create_plush_material(
        "Hoppy_Eye_Catchlight_White", 0xFFFFFF, roughness=0.05, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, emission_strength=0.38
    ),
    # Pitch-black recessed mouth cavity
    "MouthVoidBlack": create_plush_material(
        "Hoppy_Mouth_Cavity_Black", 0x010102, roughness=0.99, spec_ior=0.01,
        sheen=0.0, bump_strength=0.0
    ),
    # Metallic zipper teeth & golden collar clasp
    "ZipperMetal": create_plush_material(
        "Hoppy_Zipper_Gold_Metal", 0xD99B06, roughness=0.24, spec_ior=0.45,
        sheen=0.0, bump_strength=0.0, metallic=0.90, coat=0.25
    ),
    # Dark zipper tape backing & pendant outline border
    "ZipperTrack": create_plush_material(
        "Hoppy_Zipper_Track_Dark", 0x0B0C0E, roughness=0.88, spec_ior=0.05,
        sheen=0.08, bump_strength=0.06
    ),
    # 3D Cartoon Fart Cloud Materials (Vibrant Toxic Lime, Neon Blast Core, Lavender Swirl)
    "FartCloudLime": create_plush_material(
        "Hoppy_Fart_Cloud_Lime", 0x38D61C, roughness=0.68, spec_ior=0.16,
        sheen=0.40, sheen_tint_mult=1.15, bump_scale=24.0, bump_strength=0.22,
        subsurface=0.30, emission_strength=0.22
    ),
    "FartCloudNeon": create_plush_material(
        "Hoppy_Fart_Cloud_Neon_YellowGreen", 0xB8FF29, roughness=0.45, spec_ior=0.22,
        sheen=0.35, sheen_tint_mult=1.1, bump_scale=30.0, bump_strength=0.14,
        subsurface=0.22, emission_strength=0.42
    ),
    "FartCloudPurple": create_plush_material(
        "Hoppy_Fart_Cloud_Purple", 0x9333EA, roughness=0.62, spec_ior=0.18,
        sheen=0.38, sheen_tint_mult=1.1, bump_scale=28.0, bump_strength=0.18,
        subsurface=0.22, emission_strength=0.26
    ),
}


# ==============================================================================
# 3. HOPPY HOPSCOTCH GEOMETRY BUILDER (BMESH + SKIN WEIGHTS)
# ==============================================================================
master_bm = bmesh.new()
deform_layer = master_bm.verts.layers.deform.verify()

# 25-Bone Armature (HoppyHopscotch_Armature)
BONE_NAMES = [
    "Root",
    "Pelvis",
    "Spine",
    "Chest",
    "Tail",
    "Head",
    "Jaw",
    "Eyelid.L",
    "Eyelid.R",
    "Ear.L",
    "Ear.R",
    "SkullPendant",
    "Shoulder.L",
    "Arm.L",
    "HandHoof.L",
    "Shoulder.R",
    "Arm.R",
    "HandHoof.R",
    "Leg.L",
    "FootHoof.L",
    "Leg.R",
    "FootHoof.R",
    "FartCloud.1",
    "FartCloud.2",
    "FartCloud.3",
]
BONE_IDX = {name: i for i, name in enumerate(BONE_NAMES)}

MAT_KEYS = [
    "BodyGreen",
    "PastelMint",
    "ForestGreen",
    "NosePink",
    "ToothWhite",
    "PendantYellow",
    "EyeGloss",
    "CatchlightWhite",
    "MouthVoidBlack",
    "ZipperMetal",
    "ZipperTrack",
    "FartCloudLime",
    "FartCloudNeon",
    "FartCloudPurple",
]
MAT_LIST = [MATS[k] for k in MAT_KEYS]
MAT_IDX = {k: i for i, k in enumerate(MAT_KEYS)}


def append_bmesh_part(part_bm, mat_key_or_fn, weight_fn):
    v_map = {}
    v_orig = {}
    for v in part_bm.verts:
        ox, oy, oz = v.co.x, v.co.y, v.co.z
        nv = master_bm.verts.new(to_b_vec(ox, oy, oz))
        weights = weight_fn(ox, oy, oz)
        dvert = nv[deform_layer]
        for bname, w in weights.items():
            if w > 1e-4:
                dvert[BONE_IDX[bname]] = float(w)
        v_map[v] = nv
        v_orig[v] = (ox, oy, oz)

    for f in part_bm.faces:
        try:
            nf = master_bm.faces.new([v_map[v] for v in f.verts])
            if callable(mat_key_or_fn):
                cx = sum(v_orig[v][0] for v in f.verts) / len(f.verts)
                cy = sum(v_orig[v][1] for v in f.verts) / len(f.verts)
                cz = sum(v_orig[v][2] for v in f.verts) / len(f.verts)
                mkey = mat_key_or_fn(cx, cy, cz)
                nf.material_index = MAT_IDX[mkey]
            else:
                nf.material_index = MAT_IDX[mat_key_or_fn]
            nf.smooth = True
        except ValueError:
            pass
    part_bm.free()


def make_uv_sphere_bm(rx, ry, rz, cx=0.0, cy=0.0, cz=0.0,
                      u_segs=28, v_segs=20, rot_euler=(0.0, 0.0, 0.0),
                      deform_fn=None, world_deform_fn=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=u_segs, v_segments=v_segs, radius=1.0)
    rot_m = Euler(rot_euler, 'XYZ').to_matrix().to_4x4()
    center = Vector((cx, cy, cz))
    for v in bm.verts:
        n_local = v.co.normalized()
        p = Vector((v.co.x * rx, v.co.y * ry, v.co.z * rz))
        if deform_fn is not None:
            p = deform_fn(p)
        p_world = (rot_m @ p) + center
        if world_deform_fn is not None:
            n_world = (rot_m @ n_local).normalized()
            p_world = world_deform_fn(p_world, n_world)
        v.co = p_world
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def make_beveled_box_bm(sx, sy, sz, cx, cy, cz, bevel_frac=0.14):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    bmesh.ops.bevel(
        bm,
        geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
        offset=min(sx, sy, sz) * bevel_frac,
        offset_type='OFFSET',
        segments=2,
        profile=0.7,
        affect='EDGES'
    )
    for v in bm.verts:
        v.co += Vector((cx, cy, cz))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def make_torus_tube_bm(curve_pts, radius_fn, radial_segs=14, closed=False):
    bm = bmesh.new()
    n_pts = len(curve_pts)
    rings = []
    for i, pt in enumerate(curve_pts):
        p = Vector(pt)
        if closed:
            p_prev = Vector(curve_pts[(i - 1) % n_pts])
            p_next = Vector(curve_pts[(i + 1) % n_pts])
            tangent = (p_next - p_prev).normalized()
        else:
            if i == 0:
                tangent = (Vector(curve_pts[i + 1]) - p).normalized()
            elif i == n_pts - 1:
                tangent = (p - Vector(curve_pts[i - 1])).normalized()
            else:
                tangent = (Vector(curve_pts[i + 1]) - Vector(curve_pts[i - 1])).normalized()

        up_ref = Vector((0, 0, 1)) if abs(tangent.z) < 0.85 else Vector((0, 1, 0))
        normal = tangent.cross(up_ref).normalized()
        binormal = tangent.cross(normal).normalized()

        t = i / max(1, (n_pts if closed else n_pts - 1))
        r = radius_fn(t) if callable(radius_fn) else float(radius_fn)

        ring = []
        for j in range(radial_segs):
            ang = 2.0 * math.pi * j / radial_segs
            offset = normal * (math.cos(ang) * r) + binormal * (math.sin(ang) * r)
            ring.append(bm.verts.new(p + offset))
        rings.append(ring)

    n_rings = len(rings)
    limit = n_rings if closed else n_rings - 1
    for i in range(limit):
        r1 = rings[i]
        r2 = rings[(i + 1) % n_rings]
        for j in range(radial_segs):
            jn = (j + 1) % radial_segs
            bm.faces.new([r1[j], r2[j], r2[jn], r1[jn]])

    if not closed:
        c_start = bm.verts.new(Vector(curve_pts[0]))
        for j in range(radial_segs):
            jn = (j + 1) % radial_segs
            bm.faces.new([c_start, rings[0][jn], rings[0][j]])
        c_end = bm.verts.new(Vector(curve_pts[-1]))
        for j in range(radial_segs):
            jn = (j + 1) % radial_segs
            bm.faces.new([c_end, rings[-1][j], rings[-1][jn]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def make_sharp_extruded_polygon_bm(poly_xy, z_front, depth):
    """
    Create a crisp 3D extruded polygon mesh with support vertices near corners
    so Catmull-Clark SUBSURF preserves sharp zig-zag Lightning Bolt edges!
    """
    bm = bmesh.new()
    dense_xy = []
    n_corners = len(poly_xy)
    for i in range(n_corners):
        p0 = Vector(poly_xy[i])
        p1 = Vector(poly_xy[(i + 1) % n_corners])
        # Cluster points near corners (0.0, 0.06, 0.25, 0.50, 0.75, 0.94) so corners stay sharp
        for t in (0.0, 0.07, 0.30, 0.70, 0.93):
            pt = p0.lerp(p1, t)
            dense_xy.append((pt.x, pt.y))

    n = len(dense_xy)
    front_outer = [bm.verts.new((x, y, z_front + depth * 0.50)) for x, y in dense_xy]
    front_edge = [bm.verts.new((x, y, z_front + depth * 0.42)) for x, y in dense_xy]
    back_edge = [bm.verts.new((x, y, z_front - depth * 0.42)) for x, y in dense_xy]
    back_outer = [bm.verts.new((x, y, z_front - depth * 0.50)) for x, y in dense_xy]

    for i in range(n):
        inext = (i + 1) % n
        bm.faces.new([front_outer[i], front_edge[i], front_edge[inext], front_outer[inext]])
        bm.faces.new([front_edge[i], back_edge[i], back_edge[inext], front_edge[inext]])
        bm.faces.new([back_edge[i], back_outer[i], back_outer[inext], back_edge[inext]])

    f_front = bm.faces.new(front_outer)
    f_back = bm.faces.new(list(reversed(back_outer)))
    bmesh.ops.triangulate(bm, faces=[f_front, f_back])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


# ------------------------------------------------------------------------------
# 3.1 WIDE SMILING CRITTERS BUNNY HEAD & CHEEK FUR TUFTS (#012 PLUSH SILHOUETTE)
# ------------------------------------------------------------------------------
def head_world_deform(p_w, n_w):
    # Recess the front of head_core strictly inside the wide smiling mouth opening
    # so the black mouth cavity sits cleanly inside the head with zero edge clipping!
    if p_w.z > 0.15 and abs(p_w.x) < 0.49:
        y_low = lower_smile_y(p_w.x) + 0.015
        y_high = upper_smile_y(p_w.x) - 0.010
        if y_low < p_w.y < y_high:
            p_w.z -= 0.065
    return p_w + n_w * (plush_fleece_displacement(p_w) * 0.40)


head_core_bm = make_uv_sphere_bm(
    0.72, 0.56, 0.62, cx=0.0, cy=1.88, cz=0.0,
    u_segs=40, v_segs=30,
    world_deform_fn=head_world_deform
)
append_bmesh_part(head_core_bm, "BodyGreen", lambda x, y, z: {"Head": 1.0})

# Cute bunny cheek fur tufts on left & right sides (from 052_HoppyHopscotch.webp) + top crown tuft
for side in (-1, 1):
    for (cy_off, cz_off, sx, sy, sz, rot_z) in [
        (1.88, 0.10, 0.13, 0.060, 0.08, -side * 0.28),
        (1.79, 0.12, 0.11, 0.052, 0.07, -side * 0.45),
    ]:
        tuft_bm = make_uv_sphere_bm(
            sx, sy, sz,
            cx=side * 0.69, cy=cy_off, cz=cz_off,
            u_segs=16, v_segs=12,
            rot_euler=(0.0, 0.0, rot_z)
        )
        append_bmesh_part(tuft_bm, "BodyGreen", lambda x, y, z: {"Head": 1.0})

top_tuft_bm = make_uv_sphere_bm(
    0.10, 0.065, 0.08, cx=0.0, cy=2.43, cz=0.06,
    u_segs=14, v_segs=10, rot_euler=(-0.15, 0.0, 0.0)
)
append_bmesh_part(top_tuft_bm, "BodyGreen", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.2 TALL UPRIGHT LONG BUNNY RABBIT EARS (`Ear.L`, `Ear.R`) — SEAMLESS 1-PIECE PADDLE
#     (Bright Green Base + Dipped Forest-Green Top Third + Pastel Mint Inner Ears)
# ------------------------------------------------------------------------------
for side in (-1, 1):
    ear_bone = "Ear.L" if side == 1 else "Ear.R"
    base_x = side * 0.23
    base_y = 2.34
    base_z = -0.02
    # In #012_Hoppy_Hopscotch_Plushie.webp, viewer-left ear (`Ear.R`, x < 0) stands upright
    # and viewer-right ear (`Ear.L`, x > 0) tilts jauntily outward!
    tilt_z = -0.32 if side == 1 else 0.06
    tilt_x = 0.04

    rot_ear = Euler((tilt_x, 0.0, tilt_z), 'XYZ').to_matrix()
    rot_ear_inv = rot_ear.inverted()
    ear_pivot = Vector((base_x, base_y, base_z))
    ear_center = ear_pivot + (rot_ear @ Vector((0.0, 0.45, 0.0)))

    def ear_weight_fn(x, y, z, eb=ear_bone):
        if y < 2.42:
            return {"Head": 0.45, eb: 0.55}
        return {eb: 0.95, "Head": 0.05}

    # Single seamless long bunny ear paddle (ry = 0.49) with smooth rabbit ear taper
    def ear_paddle_deform(p):
        # u in [0, 1] from bottom root (-0.49) to top tip (+0.49)
        u = max(0.0, min(1.0, (p.y + 0.49) / 0.98))
        # Taper narrower at root (u=0 -> 0.62), widest at upper-middle (u=0.65 -> 1.06), rounded top
        width_profile = 0.62 + 0.44 * math.sin(math.pi * (u ** 0.72))
        p.x *= width_profile
        if p.z > 0:
            # Smooth concave scoop on the lower-middle front face for the inner ear
            r_in = max(0.0, 1.0 - (p.x / 0.16) ** 2 - ((p.y + 0.06) / 0.36) ** 2)
            p.z *= (1.0 - 0.50 * r_in)
        return p

    def ear_mat_selector(cx, cy, cz, piv=ear_pivot, r_inv=rot_ear_inv):
        local_p = r_inv @ (Vector((cx, cy, cz)) - piv)
        # Top 32% of the long bunny ear is dipped ForestGreen (#1E7E38), lower 68% is BodyGreen (#34B857)
        if local_p.y > 0.61:
            return "ForestGreen"
        return "BodyGreen"

    ear_paddle_bm = make_uv_sphere_bm(
        0.215, 0.49, 0.092,
        cx=ear_center.x, cy=ear_center.y, cz=ear_center.z,
        u_segs=32, v_segs=32,
        rot_euler=(tilt_x, 0.0, tilt_z),
        deform_fn=ear_paddle_deform
    )
    append_bmesh_part(ear_paddle_bm, ear_mat_selector, ear_weight_fn)

    # Pastel Mint-Green (`PastelMint` #A7F3D0) Inner Ear Cushion Frame
    ear_mint_center = ear_pivot + (rot_ear @ Vector((0.0, 0.39, 0.046)))
    ear_mint_bm = make_uv_sphere_bm(
        0.132, 0.31, 0.035,
        cx=ear_mint_center.x, cy=ear_mint_center.y, cz=ear_mint_center.z,
        u_segs=24, v_segs=18,
        rot_euler=(tilt_x, 0.0, tilt_z)
    )
    append_bmesh_part(ear_mint_bm, "PastelMint", ear_weight_fn)

    # Deep Forest-Green (`ForestGreen` #1E7E38) Inner Ear Center Groove
    ear_core_center = ear_pivot + (rot_ear @ Vector((0.0, 0.39, 0.066)))
    ear_core_bm = make_uv_sphere_bm(
        0.092, 0.26, 0.024,
        cx=ear_core_center.x, cy=ear_core_center.y, cz=ear_core_center.z,
        u_segs=20, v_segs=16,
        rot_euler=(tilt_x, 0.0, tilt_z)
    )
    append_bmesh_part(ear_core_bm, "ForestGreen", ear_weight_fn)


# ------------------------------------------------------------------------------
# 3.3 GLOSSY BLACK EYES, CATCHLIGHTS, EYELIDS & ARCHED BROWS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    lid_bone = "Eyelid.L" if side == 1 else "Eyelid.R"
    ex = side * 0.220
    ey = 1.985
    ez = 0.530

    eye_bm = make_uv_sphere_bm(
        0.152, 0.165, 0.116,
        cx=ex, cy=ey, cz=ez,
        u_segs=30, v_segs=22,
        rot_euler=(-0.05, side * 0.15, -side * 0.08)
    )
    append_bmesh_part(eye_bm, "EyeGloss", lambda x, y, z: {"Head": 1.0})

    # Primary crisp white oval catchlight
    hi1_bm = make_uv_sphere_bm(
        0.034, 0.050, 0.014,
        cx=ex - side * 0.030, cy=ey + 0.034, cz=ez + 0.108,
        u_segs=14, v_segs=10,
        rot_euler=(-0.10, side * 0.12, 0.0)
    )
    append_bmesh_part(hi1_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Secondary tiny lower sparkle catchlight
    hi2_bm = make_uv_sphere_bm(
        0.015, 0.017, 0.010,
        cx=ex + side * 0.036, cy=ey - 0.040, cz=ez + 0.104,
        u_segs=10, v_segs=8
    )
    append_bmesh_part(hi2_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Upper plush eyelid rim (weighted to Eyelid.L / Eyelid.R for blinking & fart-strain squint)
    lid_pts = []
    for k in range(15):
        t = -1.0 + 2.0 * k / 14.0
        lx = ex + t * 0.154
        ly = ey + 0.142 * math.cos(t * 1.15)
        lz = ez + 0.092 * math.cos(t * 0.9)
        lid_pts.append((lx, ly, lz))
    lid_bm = make_torus_tube_bm(
        lid_pts,
        lambda t: 0.020 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=10, closed=False
    )
    append_bmesh_part(lid_bm, "ForestGreen", lambda x, y, z, b=lid_bone: {b: 0.90, "Head": 0.10})

    # Cute high arched eyebrow (from 052_HoppyHopscotch.webp)
    brow_pts = []
    for k in range(13):
        t = -1.0 + 2.0 * k / 12.0
        bx = ex + t * 0.135
        by = ey + 0.230 + 0.036 * (1.0 - t * t) - side * 0.015 * t
        bz = head_front_z(bx, by) + 0.012
        brow_pts.append((bx, by, bz))
    brow_bm = make_torus_tube_bm(
        brow_pts,
        lambda t: 0.014 * math.sin(math.pi * (0.1 + 0.8 * t)),
        radial_segs=8, closed=False
    )
    append_bmesh_part(brow_bm, "ZipperTrack", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.4 PINK TRIANGULAR RABBIT NOSE, WIDE HAPPY GRIN, BUCK TEETH & PINK TONGUE
# ------------------------------------------------------------------------------
def nose_triangle_deform(p):
    t_y = (p.y + 0.055) / 0.11
    p.x *= (0.38 + 0.85 * max(0.0, min(1.2, t_y)))
    return p


nose_bm = make_uv_sphere_bm(
    0.076, 0.052, 0.046,
    cx=0.0, cy=1.855, cz=0.625,
    u_segs=22, v_segs=16,
    rot_euler=(-0.12, 0.0, 0.0),
    deform_fn=nose_triangle_deform
)
append_bmesh_part(nose_bm, "NosePink", lambda x, y, z: {"Head": 1.0})


def build_conformed_mouth_cavity_bm():
    """
    Build mouth cavity strictly bounded between lower_smile_y(x) and upper_smile_y(x)
    so zero black vertices ever protrude outside the green smiling lips!
    """
    bm = bmesh.new()
    nx_steps = 36
    ny_steps = 14
    grid = []
    for iy in range(ny_steps + 1):
        v_frac = iy / ny_steps
        row = []
        for ix in range(nx_steps + 1):
            u_frac = -1.0 + 2.0 * ix / nx_steps
            ux = u_frac * 0.505
            y_bot = lower_smile_y(ux) + 0.008
            y_top = upper_smile_y(ux) - 0.006
            uy = y_bot + (y_top - y_bot) * v_frac
            uz = head_front_z(ux, uy) - 0.012
            row.append(bm.verts.new((ux, uy, uz)))
        grid.append(row)

    for iy in range(ny_steps):
        for ix in range(nx_steps):
            v1 = grid[iy][ix]
            v2 = grid[iy][ix + 1]
            v3 = grid[iy + 1][ix + 1]
            v4 = grid[iy + 1][ix]
            bm.faces.new([v1, v2, v3, v4])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


mouth_bm = build_conformed_mouth_cavity_bm()
append_bmesh_part(
    mouth_bm, "MouthVoidBlack",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.74 - y) * 3.0)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.74 - y) * 3.0))}
)

# Cute pink plush tongue inside lower mouth cavity
tongue_bm = make_uv_sphere_bm(
    0.155, 0.072, 0.030,
    cx=0.0, cy=1.515, cz=head_front_z(0.0, 1.515) - 0.002,
    u_segs=20, v_segs=14,
    rot_euler=(0.38, 0.0, 0.0)
)
append_bmesh_part(tongue_bm, "NosePink", lambda x, y, z: {"Jaw": 0.85, "Head": 0.15})

# Upper and Lower Green Plush Smiling Lip Rims
upper_lip_pts = []
for k in range(37):
    t = -1.0 + 2.0 * k / 36.0
    lx = t * 0.525
    ly = upper_smile_y(lx)
    lz = head_front_z(lx, ly) + 0.024 * (1.0 - 0.32 * t * t)
    upper_lip_pts.append((lx, ly, lz))

upper_lip_bm = make_torus_tube_bm(
    upper_lip_pts,
    lambda t: 0.038 + 0.012 * math.sin(math.pi * t),
    radial_segs=14, closed=False
)
append_bmesh_part(upper_lip_bm, "BodyGreen", lambda x, y, z: {"Head": 0.90, "Jaw": 0.10})

lower_lip_pts = []
for k in range(41):
    t = -1.0 + 2.0 * k / 40.0
    lx = t * 0.525
    ly = lower_smile_y(lx)
    lz = head_front_z(lx, ly) + 0.020 * (1.0 - 0.30 * t * t)
    lower_lip_pts.append((lx, ly, lz))

lower_lip_bm = make_torus_tube_bm(
    lower_lip_pts,
    lambda t: 0.034 + 0.010 * math.sin(math.pi * t),
    radial_segs=14, closed=False
)
append_bmesh_part(
    lower_lip_bm, "BodyGreen",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.74 - y) * 2.8)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.74 - y) * 2.8))}
)

# Smile corner cheek creases
for side in (-1, 1):
    cheek_pts = []
    for k in range(11):
        t = k / 10.0
        cx = side * (0.495 + 0.042 * math.sin(math.pi * t))
        cy = 1.79 + 0.12 * (1.0 - t)
        cz = head_front_z(cx, cy) + 0.018
        cheek_pts.append((cx, cy, cz))
    cheek_bm = make_torus_tube_bm(cheek_pts, 0.030, radial_segs=10, closed=False)
    append_bmesh_part(cheek_bm, "BodyGreen", lambda x, y, z: {"Head": 0.92, "Jaw": 0.08})

# Twin White Bunny Buck Teeth inside the wide happy grin!
for side in (-1, 1):
    tx = side * 0.060
    ty = 1.695
    tz = head_front_z(tx, ty) + 0.002

    def tooth_deform(p, s=side):
        if p.y < 0:
            p.x *= (1.0 + 0.16 * min(1.0, (p.y / -0.095) ** 2))
        if p.y < -0.092:
            p.y = -0.092 + (p.y + 0.092) * 0.25
        if s * p.x < -0.056:
            p.x = -s * (0.056 + (abs(p.x) - 0.056) * 0.08)
        return p

    tooth_bm = make_uv_sphere_bm(
        0.064, 0.112, 0.030,
        cx=tx, cy=ty, cz=tz,
        u_segs=22, v_segs=16,
        rot_euler=(-0.26, 0.0, 0.0),
        deform_fn=tooth_deform
    )
    append_bmesh_part(tooth_bm, "ToothWhite", lambda x, y, z: {"Head": 0.95, "Jaw": 0.05})


# ------------------------------------------------------------------------------
# 3.5 PEAR-SHAPED GREEN PLUSH TORSO, PASTEL MINT BELLY, ZIPPER & LIGHTNING PENDANT
# ------------------------------------------------------------------------------
def build_torso_bm():
    bm = bmesh.new()
    u_segs = 38
    profile = [
        (0.00, 0.48), (0.20, 0.50), (0.36, 0.55), (0.46, 0.65),
        (0.50, 0.78), (0.50, 0.92), (0.47, 1.06), (0.43, 1.20),
        (0.37, 1.32), (0.31, 1.40), (0.24, 1.45), (0.00, 1.47)
    ]
    rings = []
    for r_rad, ry in profile:
        if r_rad < 1e-4:
            rings.append([bm.verts.new((0.0, ry, 0.0))])
        else:
            ring = []
            for iu in range(u_segs):
                ang = 2.0 * math.pi * iu / u_segs
                vx = math.cos(ang) * r_rad
                vz = math.sin(ang) * r_rad * 0.88
                ring.append(bm.verts.new((vx, ry, vz)))
            rings.append(ring)

    bot_v = rings[0][0]
    for iu in range(u_segs):
        iun = (iu + 1) % u_segs
        bm.faces.new([bot_v, rings[1][iun], rings[1][iu]])

    for ir in range(1, len(rings) - 2):
        r1 = rings[ir]
        r2 = rings[ir + 1]
        for iu in range(u_segs):
            iun = (iu + 1) % u_segs
            bm.faces.new([r1[iu], r2[iu], r2[iun], r1[iun]])

    top_v = rings[-1][0]
    for iu in range(u_segs):
        iun = (iu + 1) % u_segs
        bm.faces.new([top_v, rings[-2][iu], rings[-2][iun]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def torso_weights(x, y, z):
    if y < 0.76:
        t = max(0.0, min(1.0, (y - 0.48) / 0.28))
        return {"Pelvis": 1.0 - 0.5 * t, "Spine": 0.5 * t}
    elif y < 1.10:
        t = (y - 0.76) / 0.34
        return {"Pelvis": max(0.0, 0.5 - t), "Spine": 1.0 - abs(t - 0.5), "Chest": max(0.0, t - 0.3)}
    else:
        t = min(1.0, (y - 1.10) / 0.35)
        return {"Spine": max(0.0, 0.5 * (1.0 - t)), "Chest": 0.5 + 0.5 * t}


def torso_mat_selector(cx, cy, cz):
    # Pastel Mint-Green Belly Patch (#A7F3D0) integrated directly onto the front tummy surface
    # so the black collar zipper sits cleanly ON TOP OF the belly without ever being occluded!
    if cz > 0.18:
        nx = cx / 0.27
        ny = (cy - 0.90) / 0.31
        if nx * nx + ny * ny <= 1.0:
            return "PastelMint"
    return "BodyGreen"


torso_bm = build_torso_bm()
append_bmesh_part(torso_bm, torso_mat_selector, torso_weights)


def torso_front_z(y, x=0.0):
    t = max(0.0, min(1.0, (y - 0.52) / (1.42 - 0.52)))
    r = 0.34 + 0.16 * math.sin(math.pi * (t ** 0.72)) - 0.08 * t
    x_ratio = min(0.92, abs(x) / max(0.10, r))
    return r * 0.88 * math.sqrt(max(0.05, 1.0 - x_ratio * x_ratio))


# Fluffy Round Puffball Bunny Tail (`Tail` bone on back of lower pelvis)
tail_puffs = [
    (0.00, 0.68, -0.45, 0.18, 0.17, 0.18, "BodyGreen"),
    (-0.10, 0.72, -0.48, 0.11, 0.11, 0.11, "BodyGreen"),
    (0.10, 0.72, -0.48, 0.11, 0.11, 0.11, "BodyGreen"),
    (0.00, 0.78, -0.47, 0.12, 0.11, 0.11, "PastelMint"),
    (0.00, 0.60, -0.47, 0.11, 0.10, 0.11, "ForestGreen"),
    (0.00, 0.69, -0.55, 0.13, 0.13, 0.12, "PastelMint"),
]
for tx, ty, tz, rx, ry, rz, mkey in tail_puffs:
    tp_bm = make_uv_sphere_bm(rx, ry, rz, cx=tx, cy=ty, cz=tz, u_segs=16, v_segs=12)
    append_bmesh_part(tp_bm, mkey, lambda x, y, z: {"Tail": 0.90, "Pelvis": 0.10})

# Black Collar Zipper Track & Metallic Zipper Hardware (prominently visible on front chest & belly!)
zip_pts = [(0.0, 0.54 + (1.38 - 0.54) * k / 24.0, torso_front_z(0.54 + (1.38 - 0.54) * k / 24.0) + 0.012)
           for k in range(25)]
zip_track_bm = make_torus_tube_bm(zip_pts, 0.028, radial_segs=10, closed=False)
append_bmesh_part(zip_track_bm, "ZipperTrack", torso_weights)

for i in range(32):
    zy = 0.56 + (1.36 - 0.56) * (i / 31.0)
    zz = torso_front_z(zy) + 0.026
    zx = (0.010 if (i % 2 == 0) else -0.010)
    t_bm = make_beveled_box_bm(0.032, 0.012, 0.018, zx, zy, zz)
    append_bmesh_part(t_bm, "ZipperMetal", torso_weights)

slider_bm = make_beveled_box_bm(0.064, 0.076, 0.042, 0.0, 1.325, 0.415)
append_bmesh_part(slider_bm, "ZipperMetal", lambda x, y, z: {"Chest": 0.7, "SkullPendant": 0.3})

clasp_bm = make_beveled_box_bm(0.042, 0.062, 0.036, 0.0, 1.268, 0.435)
append_bmesh_part(clasp_bm, "ZipperMetal", lambda x, y, z: {"SkullPendant": 1.0})

# Iconic Crisp Zig-Zag Bright Yellow Lightning Bolt Pendant (`SkullPendant` bone)
bolt_poly_outer = [
    (0.045, 1.265),
    (-0.165, 1.035),
    (-0.028, 1.035),
    (-0.115, 0.795),
    (0.168, 1.078),
    (0.028, 1.078),
]
bolt_border_bm = make_sharp_extruded_polygon_bm(bolt_poly_outer, z_front=0.462, depth=0.028)
append_bmesh_part(bolt_border_bm, "ZipperTrack", lambda x, y, z: {"SkullPendant": 1.0})

bolt_poly_inner = [
    (0.036, 1.242),
    (-0.140, 1.046),
    (-0.012, 1.046),
    (-0.094, 0.828),
    (0.142, 1.066),
    (0.014, 1.066),
]
bolt_yellow_bm = make_sharp_extruded_polygon_bm(bolt_poly_inner, z_front=0.474, depth=0.032)
append_bmesh_part(bolt_yellow_bm, "PendantYellow", lambda x, y, z: {"SkullPendant": 1.0})


# ------------------------------------------------------------------------------
# 3.6 SPLAYED PLUSH BUNNY ARMS, DARK GREEN HAND PAWS & PASTEL MINT PAW PADS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    sh_bone = "Shoulder.L" if side == 1 else "Shoulder.R"
    arm_bone = "Arm.L" if side == 1 else "Arm.R"
    paw_bone = "HandHoof.L" if side == 1 else "HandHoof.R"

    arm_pts = []
    for k in range(13):
        t = k / 12.0
        ax = side * (0.29 + 0.36 * t)
        ay = 1.28 - 0.34 * t + 0.02 * math.sin(math.pi * t)
        az = 0.04 + 0.05 * t
        arm_pts.append((ax, ay, az))

    arm_bm = make_torus_tube_bm(
        arm_pts,
        lambda t: 0.132 * (1.0 + 0.05 * t),
        radial_segs=18, closed=False
    )

    def arm_weight_fn(x, y, z, sb=sh_bone, ab=arm_bone, pb=paw_bone):
        dist = max(0.0, min(1.0, (abs(x) - 0.29) / 0.42))
        if dist < 0.35:
            return {"Chest": 0.35 * (1.0 - dist / 0.35), sb: 0.65, ab: 0.35 * (dist / 0.35)}
        elif dist < 0.85:
            return {ab: 0.85, sb: 0.15}
        else:
            return {ab: 0.50, pb: 0.50}

    append_bmesh_part(arm_bm, "BodyGreen", arm_weight_fn)

    # Darker Emerald-Green Hand Paw Cuff (`ForestGreen` #1E7E38)
    paw_pts = []
    for k in range(11):
        t = k / 10.0
        px = side * (0.63 + 0.20 * t)
        py = 0.96 - 0.20 * t
        pz = 0.09 + 0.03 * t
        paw_pts.append((px, py, pz))

    def paw_radius(t):
        if t < 0.15:
            return 0.136 + 0.014 * (t / 0.15)
        elif t < 0.72:
            return 0.150 + 0.008 * math.sin(math.pi * (t - 0.15) / 0.57)
        else:
            u = (t - 0.72) / 0.28
            return 0.150 * math.sqrt(max(0.02, 1.0 - u * u))

    paw_bm = make_torus_tube_bm(paw_pts, paw_radius, radial_segs=18, closed=False)
    append_bmesh_part(
        paw_bm, "ForestGreen",
        lambda x, y, z, pb=paw_bone, ab=arm_bone: {pb: 0.90, ab: 0.10}
    )

    # Pastel Mint-Green Palm Paw Pad (`PastelMint` #A7F3D0)
    pad_bm = make_uv_sphere_bm(
        0.075, 0.088, 0.035,
        cx=side * 0.73, cy=0.85, cz=0.225,
        u_segs=14, v_segs=10,
        rot_euler=(0.0, side * 0.25, -side * 0.65)
    )
    append_bmesh_part(pad_bm, "PastelMint", lambda x, y, z, pb=paw_bone: {pb: 1.0})


# ------------------------------------------------------------------------------
# 3.7 PLUMP BUNNY LEGS, ROUNDED FOREST-GREEN FEET BOTTOMS & PASTEL PAW PADS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    leg_bone = "Leg.L" if side == 1 else "Leg.R"
    foot_bone = "FootHoof.L" if side == 1 else "FootHoof.R"

    leg_pts = []
    for k in range(13):
        t = k / 12.0
        lx = side * (0.23 + 0.06 * t)
        ly = 0.62 - 0.38 * t
        lz = 0.02 + 0.06 * t
        leg_pts.append((lx, ly, lz))

    leg_bm = make_torus_tube_bm(
        leg_pts,
        lambda t: 0.172 * (1.0 - 0.04 * t),
        radial_segs=18, closed=False
    )

    def leg_weight_fn(x, y, z, lb=leg_bone, fb=foot_bone):
        if y > 0.48:
            return {"Pelvis": 0.45, lb: 0.55}
        elif y > 0.24:
            return {lb: 0.90, fb: 0.10}
        else:
            return {lb: 0.25, fb: 0.75}

    append_bmesh_part(leg_bm, "BodyGreen", leg_weight_fn)

    fx = side * 0.30
    fy = 0.165
    fz = 0.145

    def foot_deform(p):
        if p.y < -0.04:
            p.y = -0.145 + (p.y + 0.145) * 0.22
        return p

    foot_bm = make_uv_sphere_bm(
        0.215, 0.175, 0.225,
        cx=fx, cy=fy, cz=fz,
        u_segs=24, v_segs=16,
        rot_euler=(0.08, side * 0.12, 0.0),
        deform_fn=foot_deform
    )
    append_bmesh_part(
        foot_bm, "ForestGreen",
        lambda x, y, z, fb=foot_bone, lb=leg_bone: {fb: 0.92, lb: 0.08}
    )

    fpad_bm = make_uv_sphere_bm(
        0.135, 0.110, 0.045,
        cx=fx + side * 0.015, cy=fy - 0.005, cz=fz + 0.195,
        u_segs=18, v_segs=12,
        rot_euler=(0.12, side * 0.12, 0.0)
    )
    append_bmesh_part(fpad_bm, "PastelMint", lambda x, y, z, fb=foot_bone: {fb: 1.0})

    fseam_pts = []
    for k in range(13):
        t = -1.0 + 2.0 * k / 12.0
        sx = fx + t * 0.205
        sy = fy - 0.015 - 0.025 * (1.0 - t * t)
        sz = fz + 0.220 * math.sqrt(max(0.05, 1.0 - 0.75 * t * t))
        fseam_pts.append((sx, sy, sz))
    fseam_bm = make_torus_tube_bm(fseam_pts, 0.009, radial_segs=8, closed=False)
    append_bmesh_part(fseam_bm, "ZipperTrack", lambda x, y, z, fb=foot_bone: {fb: 1.0})


# ------------------------------------------------------------------------------
# 3.8 3D SCULPTED CARTOON FART CLOUD CLUSTER (WEIGHTED TO FartCloud.1 / .2 / .3)
# ------------------------------------------------------------------------------
fart_stage1_puffs = [
    (0.00, 0.68, -0.52, 0.12, 0.11, 0.14, "FartCloudNeon"),
    (0.00, 0.69, -0.66, 0.18, 0.16, 0.18, "FartCloudLime"),
    (-0.10, 0.72, -0.70, 0.14, 0.13, 0.14, "FartCloudLime"),
    (0.10, 0.66, -0.70, 0.14, 0.13, 0.14, "FartCloudLime"),
]
for idx, (fx, fy, fz, rx, ry, rz, mkey) in enumerate(fart_stage1_puffs):
    def fc1_disp(p_w, n_w, s=idx):
        return p_w + n_w * (plush_fleece_displacement(p_w + Vector((s * 1.1, 0.0, s * 0.7))) * 2.2)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=16, v_segs=12, world_deform_fn=fc1_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.1": 1.0})

ring_pts = []
for k in range(24):
    ang = 2.0 * math.pi * k / 24.0
    ring_pts.append((0.25 * math.cos(ang), 0.69 + 0.25 * math.sin(ang), -0.64))
shock_ring_bm = make_torus_tube_bm(ring_pts, 0.038, radial_segs=10, closed=True)
append_bmesh_part(shock_ring_bm, "FartCloudNeon", lambda x, y, z: {"FartCloud.1": 1.0})

fart_stage2_puffs = [
    (0.00, 0.76, -0.94, 0.28, 0.26, 0.28, "FartCloudLime"),
    (-0.20, 0.82, -0.98, 0.23, 0.22, 0.22, "FartCloudLime"),
    (0.20, 0.80, -0.98, 0.23, 0.22, 0.22, "FartCloudLime"),
    (0.00, 0.94, -1.04, 0.25, 0.24, 0.24, "FartCloudNeon"),
    (-0.16, 0.64, -0.92, 0.20, 0.18, 0.20, "FartCloudLime"),
    (0.16, 0.64, -0.92, 0.20, 0.18, 0.20, "FartCloudLime"),
    (0.00, 0.78, -1.18, 0.30, 0.28, 0.28, "FartCloudLime"),
    (-0.24, 0.88, -1.16, 0.22, 0.22, 0.22, "FartCloudNeon"),
    (0.24, 0.86, -1.16, 0.22, 0.22, 0.22, "FartCloudPurple"),
    (-0.14, 0.98, -1.20, 0.21, 0.20, 0.21, "FartCloudLime"),
    (0.14, 0.98, -1.20, 0.21, 0.20, 0.21, "FartCloudLime"),
]
for idx, (fx, fy, fz, rx, ry, rz, mkey) in enumerate(fart_stage2_puffs):
    def fc2_disp(p_w, n_w, s=idx):
        return p_w + n_w * (plush_fleece_displacement(p_w + Vector((s * 1.7, s * 0.9, 0.0))) * 2.6)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=18, v_segs=14, world_deform_fn=fc2_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.2": 1.0})

fart_stage3_puffs = [
    (0.00, 0.92, -1.44, 0.32, 0.30, 0.30, "FartCloudLime"),
    (-0.28, 1.02, -1.40, 0.24, 0.23, 0.24, "FartCloudNeon"),
    (0.28, 1.00, -1.40, 0.24, 0.23, 0.24, "FartCloudLime"),
    (0.00, 1.14, -1.48, 0.26, 0.25, 0.25, "FartCloudPurple"),
    (-0.20, 0.76, -1.38, 0.22, 0.20, 0.22, "FartCloudLime"),
    (0.20, 0.76, -1.38, 0.22, 0.20, 0.22, "FartCloudPurple"),
    (-0.36, 0.88, -1.54, 0.18, 0.18, 0.18, "FartCloudNeon"),
    (0.36, 0.90, -1.54, 0.18, 0.18, 0.18, "FartCloudLime"),
    (0.00, 1.02, -1.68, 0.22, 0.22, 0.22, "FartCloudNeon"),
]
for idx, (fx, fy, fz, rx, ry, rz, mkey) in enumerate(fart_stage3_puffs):
    def fc3_disp(p_w, n_w, s=idx):
        return p_w + n_w * (plush_fleece_displacement(p_w + Vector((0.0, s * 1.4, s * 2.1))) * 2.8)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=16, v_segs=12, world_deform_fn=fc3_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.3": 1.0})

for s_idx, (sx_off, sz_off, mkey) in enumerate([
    (-0.18, -1.16, "FartCloudNeon"),
    (0.02, -1.40, "FartCloudPurple"),
    (0.20, -1.26, "FartCloudNeon"),
]):
    swirl_pts = []
    for k in range(15):
        t = k / 14.0
        wx = sx_off + 0.07 * math.sin(t * 2.5 * math.pi + s_idx)
        wy = 1.08 + 0.48 * t
        wz = sz_off - 0.18 * t + 0.06 * math.cos(t * 2.5 * math.pi + s_idx)
        swirl_pts.append((wx, wy, wz))
    swirl_bm = make_torus_tube_bm(
        swirl_pts,
        lambda t: 0.026 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=8, closed=False
    )
    append_bmesh_part(swirl_bm, mkey, lambda x, y, z: {"FartCloud.3": 1.0})


# ==============================================================================
# 4. CREATE BLENDER MESH OBJECT + SUBSURF MODIFIER
# ==============================================================================
mesh_data = bpy.data.meshes.new("HoppyHopscotch_Plush_MeshData")
for m in MAT_LIST:
    mesh_data.materials.append(m)

master_bm.to_mesh(mesh_data)
master_bm.free()
mesh_data.update()

mesh_obj = bpy.data.objects.new("HoppyHopscotch_Plush_Mesh", mesh_data)
main_col.objects.link(mesh_obj)

for bname in BONE_NAMES:
    mesh_obj.vertex_groups.new(name=bname)


# ==============================================================================
# 5. CREATE SKELETAL ARMATURE RIG (25 BONES) & BIND SKINNING
# ==============================================================================
arm_data = bpy.data.armatures.new("HoppyHopscotch_ArmatureData")
arm_data.display_type = 'OCTAHEDRAL'
arm_obj = bpy.data.objects.new("HoppyHopscotch_Armature", arm_data)
arm_obj.show_in_front = True
main_col.objects.link(arm_obj)

bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='EDIT')
ebones = arm_data.edit_bones


def add_ebone(name, head_3js, tail_3js, parent_name=None, connected=False):
    b = ebones.new(name)
    b.head = to_b_vec(*head_3js)
    b.tail = to_b_vec(*tail_3js)
    if parent_name and parent_name in ebones:
        b.parent = ebones[parent_name]
        b.use_connect = connected
    return b


add_ebone("Root", (0.0, 0.0, 0.0), (0.0, 0.42, 0.0))
add_ebone("Pelvis", (0.0, 0.48, 0.0), (0.0, 0.80, 0.0), "Root", False)
add_ebone("Spine", (0.0, 0.80, 0.0), (0.0, 1.12, 0.0), "Pelvis", True)
add_ebone("Chest", (0.0, 1.12, 0.0), (0.0, 1.46, 0.0), "Spine", True)
add_ebone("Tail", (0.0, 0.68, -0.32), (0.0, 0.72, -0.58), "Pelvis", False)
add_ebone("Head", (0.0, 1.46, 0.0), (0.0, 2.34, 0.0), "Chest", True)

add_ebone("Jaw", (0.0, 1.66, 0.44), (0.0, 1.44, 0.68), "Head", False)
add_ebone("Eyelid.L", (0.220, 1.985, 0.530), (0.220, 2.12, 0.68), "Head", False)
add_ebone("Eyelid.R", (-0.220, 1.985, 0.530), (-0.220, 2.12, 0.68), "Head", False)
add_ebone("Ear.L", (0.23, 2.34, -0.02), (0.52, 3.22, -0.02), "Head", False)
add_ebone("Ear.R", (-0.23, 2.34, -0.02), (-0.29, 3.26, -0.02), "Head", False)

add_ebone("SkullPendant", (0.0, 1.26, 0.45), (0.0, 0.84, 0.49), "Chest", False)

add_ebone("Shoulder.L", (0.26, 1.28, 0.04), (0.42, 1.18, 0.05), "Chest", False)
add_ebone("Arm.L", (0.42, 1.18, 0.05), (0.65, 0.94, 0.09), "Shoulder.L", True)
add_ebone("HandHoof.L", (0.65, 0.94, 0.09), (0.83, 0.76, 0.12), "Arm.L", True)

add_ebone("Shoulder.R", (-0.26, 1.28, 0.04), (-0.42, 1.18, 0.05), "Chest", False)
add_ebone("Arm.R", (-0.42, 1.18, 0.05), (-0.65, 0.94, 0.09), "Shoulder.R", True)
add_ebone("HandHoof.R", (-0.65, 0.94, 0.09), (-0.83, 0.76, 0.12), "Arm.R", True)

add_ebone("Leg.L", (0.23, 0.62, 0.02), (0.29, 0.24, 0.08), "Pelvis", False)
add_ebone("FootHoof.L", (0.29, 0.24, 0.08), (0.31, 0.08, 0.30), "Leg.L", True)

add_ebone("Leg.R", (-0.23, 0.62, 0.02), (-0.29, 0.24, 0.08), "Pelvis", False)
add_ebone("FootHoof.R", (-0.29, 0.24, 0.08), (-0.31, 0.08, 0.30), "Leg.R", True)

# 3 Fart Cloud Bones with heads tucked inside the opaque Pelvis (z_fwd = -0.22)
add_ebone("FartCloud.1", (0.0, 0.68, -0.22), (0.0, 0.68, -0.66), "Root", False)
add_ebone("FartCloud.2", (0.0, 0.74, -0.22), (0.0, 0.78, -0.96), "Root", False)
add_ebone("FartCloud.3", (0.0, 0.80, -0.22), (0.0, 0.92, -1.36), "Root", False)

bpy.ops.object.mode_set(mode='OBJECT')

mesh_obj.parent = arm_obj
arm_mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
arm_mod.object = arm_obj
arm_mod.use_vertex_groups = True

subsurf_mod = mesh_obj.modifiers.new(name="Subdivision", type='SUBSURF')
subsurf_mod.levels = 1
subsurf_mod.render_levels = 2
subsurf_mod.quality = 3


# ==============================================================================
# 6. AUTHOR 6 NLA / ACTION ANIMATION CLIPS ON THE ARMATURE (INCLUDING Hoppy_Fart_Blast)
# ==============================================================================
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')

for pb in arm_obj.pose.bones:
    pb.rotation_mode = 'XYZ'


def reset_pose(hide_fart_cloud=True):
    for pb in arm_obj.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_euler = (0.0, 0.0, 0.0)
        if hide_fart_cloud and pb.name.startswith("FartCloud."):
            pb.scale = (0.0001, 0.0001, 0.0001)
        else:
            pb.scale = (1.0, 1.0, 1.0)


def key_char_bone(action_frame, bone_name, pitch_x=0.0, yaw_y=0.0, roll_z=0.0,
                  dx=0.0, dy_up=0.0, dz_fwd=0.0, scale=None):
    """Pose and keyframe `bone_name` using character-space conjugation."""
    pb = arm_obj.pose.bones[bone_name]
    rest_rot = pb.bone.matrix_local.to_3x3()
    rest_inv = rest_rot.inverted()

    t_arm = Vector((float(dx), float(-dz_fwd), float(dy_up)))
    pb.location = rest_inv @ t_arm
    pb.keyframe_insert(data_path="location", frame=action_frame)

    r_arm = Euler((float(pitch_x), float(roll_z), float(yaw_y)), 'XYZ').to_matrix()
    r_local = rest_inv @ r_arm @ rest_rot
    pb.rotation_euler = r_local.to_euler('XYZ')
    pb.keyframe_insert(data_path="rotation_euler", frame=action_frame)

    if scale is not None:
        if isinstance(scale, (int, float)):
            pb.scale = (float(scale), float(scale), float(scale))
        else:
            pb.scale = Vector(scale)
        pb.keyframe_insert(data_path="scale", frame=action_frame)


def hide_fart_clouds_for_standard_clip(frames):
    for f in frames:
        for fc_name in ("FartCloud.1", "FartCloud.2", "FartCloud.3"):
            key_char_bone(f, fc_name, scale=0.0001)


def bake_action_to_nla(name, frame_end, keyframe_builder):
    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    act = bpy.data.actions.new(name=name)
    act.use_fake_user = True
    arm_obj.animation_data.action = act
    reset_pose(hide_fart_cloud=True)
    keyframe_builder(act)
    track = arm_obj.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name=name, start=1, action=act)
    strip.action_frame_start = 1
    strip.action_frame_end = frame_end
    track.mute = True
    arm_obj.animation_data.action = None
    reset_pose(hide_fart_cloud=True)
    return act, track


def build_hoppy_fart_blast(act):
    """
    36-Frame (1.5s @ 24fps) 4-Act Cartoon Animation: `Hoppy_Fart_Blast`
      - Act 1 (Frames 1..9):   Deep bunny squat, tummy clench, ears pinned back & high-frequency strain!
      - Act 2 (Frames 10..14): High-altitude bunny rocket recoil jump + 3-stage green/lime/purple 3D fart cloud + shockwave ring + stink ribbons!
      - Act 3 (Frames 15..26): Mid-air bunny hop & cushioned landing on big rabbit feet!
      - Act 4 (Frames 27..36): Turn to camera, paw-fanning cloud behind back & energetic bunny giggle!
    """
    body_keys = [
        (1,   0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000,  0.00),
        (4,  -0.11, -0.03,  0.26,  0.16,  0.18, -0.06,  0.00,  0.05,  0.24, -0.25,  0.24,  0.30,  0.24, -0.30, -0.26,  0.20,  0.000, -0.18),
        (6,  -0.15, -0.05,  0.34,  0.22,  0.24, -0.10,  0.05,  0.08,  0.34, -0.34,  0.32,  0.38,  0.32, -0.38, -0.32,  0.28,  0.022, -0.28),
        (8,  -0.16, -0.05,  0.36,  0.24,  0.26, -0.08, -0.05,  0.08,  0.36, -0.38,  0.34,  0.40,  0.34, -0.40, -0.34,  0.30, -0.022, -0.32),
        (9,  -0.17, -0.06,  0.38,  0.26,  0.28, -0.12,  0.05,  0.09,  0.38, -0.40,  0.36,  0.42,  0.36, -0.42, -0.36,  0.32,  0.020, -0.35),
        (11,  0.22,  0.08,  0.30, -0.18, -0.24,  0.18, -0.10, -0.28, -0.14,  0.32, -0.24, -0.52, -0.24,  0.52,  0.32, -0.48,  0.000,  0.38),
        (14,  0.28,  0.10,  0.24, -0.20, -0.26,  0.26, -0.14, -0.32, -0.16,  0.38, -0.28, -0.58, -0.28,  0.58,  0.36, -0.54,  0.000,  0.44),
        (19,  0.16,  0.06,  0.15, -0.12, -0.15,  0.28, -0.12, -0.22, -0.08,  0.24, -0.14, -0.40, -0.16,  0.42,  0.22, -0.34,  0.000,  0.26),
        (25, -0.06,  0.01,  0.10,  0.05,  0.06,  0.30, -0.12, -0.10,  0.06, -0.14,  0.40, -0.18, -0.12,  0.26, -0.12,  0.14,  0.000, -0.12),
        (28,  0.04,  0.00,  0.04, -0.05, -0.10,  0.34, -0.18, -0.28,  0.10,  0.22,  0.65, -0.34, -0.20,  0.34,  0.04, -0.18,  0.000,  0.25),
        (30, -0.02,  0.00,  0.05,  0.03,  0.03,  0.28, -0.10, -0.08,  0.14, -0.10,  0.44,  0.14, -0.10,  0.20,  0.00,  0.12,  0.000, -0.18),
        (33,  0.03,  0.00,  0.02, -0.04, -0.08,  0.22, -0.15, -0.24,  0.08,  0.18,  0.60, -0.30, -0.15,  0.28,  0.02, -0.12,  0.000,  0.20),
        (36,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000,  0.00),
    ]

    for (f, p_dy, p_dz, p_pitch, c_pitch, h_pitch, h_yaw, h_roll,
         j_pitch, l_pitch, e_roll, al_p, al_r, ar_p, ar_r, lg_p, sk_p, p_dx, tail_w) in body_keys:
        key_char_bone(f, "Pelvis", pitch_x=p_pitch, dx=p_dx, dy_up=p_dy, dz_fwd=p_dz)
        key_char_bone(f, "Spine", pitch_x=c_pitch * 0.5)
        key_char_bone(f, "Chest", pitch_x=c_pitch, yaw_y=h_yaw * 0.3)
        key_char_bone(f, "Tail", pitch_x=tail_w, yaw_y=tail_w * 0.7)
        key_char_bone(f, "Head", pitch_x=h_pitch, yaw_y=h_yaw, roll_z=h_roll)
        key_char_bone(f, "Jaw", pitch_x=j_pitch)
        key_char_bone(f, "Eyelid.L", pitch_x=l_pitch)
        key_char_bone(f, "Eyelid.R", pitch_x=l_pitch)
        key_char_bone(f, "Ear.L", pitch_x=-e_roll * 0.6, roll_z=-e_roll * 0.5)
        key_char_bone(f, "Ear.R", pitch_x=-e_roll * 0.6, roll_z=e_roll * 0.5)
        key_char_bone(f, "Arm.L", pitch_x=al_p, roll_z=al_r)
        key_char_bone(f, "HandHoof.L", pitch_x=al_p * 0.6, roll_z=al_r * 0.5)
        key_char_bone(f, "Arm.R", pitch_x=ar_p, roll_z=ar_r)
        key_char_bone(f, "HandHoof.R", pitch_x=ar_p * 0.5, roll_z=ar_r * 0.4)
        key_char_bone(f, "Leg.L", pitch_x=lg_p)
        key_char_bone(f, "Leg.R", pitch_x=lg_p)
        key_char_bone(f, "FootHoof.L", pitch_x=-lg_p * 0.7)
        key_char_bone(f, "FootHoof.R", pitch_x=-lg_p * 0.7)
        key_char_bone(f, "SkullPendant", pitch_x=sk_p, roll_z=p_dx * 3.0)

    fc1_keys = [
        (1,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (9,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (10, 0.45,   0.0, -0.06, -0.02, 0.00),
        (12, 1.15,   0.0, -0.02, -0.06, 0.30),
        (15, 1.35,   0.0,  0.05, -0.16, 0.70),
        (20, 1.12,   0.0,  0.12, -0.26, 1.15),
        (25, 0.65,   0.0,  0.18, -0.36, 1.60),
        (30, 0.22,   0.0,  0.24, -0.44, 2.00),
        (33, 0.0001, 0.0,  0.00,  0.00, 0.00),
        (36, 0.0001, 0.0,  0.00,  0.00, 0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc1_keys:
        key_char_bone(f, "FartCloud.1", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    fc2_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (9,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (11, 0.72,    0.00, -0.02, -0.04,  0.00),
        (14, 1.28,   -0.02,  0.06, -0.14, -0.18),
        (20, 1.50,   -0.04,  0.16, -0.28, -0.38),
        (25, 1.38,   -0.06,  0.28, -0.42, -0.60),
        (30, 0.92,   -0.08,  0.42, -0.56, -0.85),
        (34, 0.32,   -0.10,  0.54, -0.68, -1.05),
        (35, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (36, 0.0001,  0.00,  0.00,  0.00,  0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc2_keys:
        key_char_bone(f, "FartCloud.2", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    fc3_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (11, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (13, 0.68,    0.00,  0.02, -0.05,  0.00),
        (18, 1.24,    0.03,  0.12, -0.18,  0.15),
        (24, 1.48,    0.05,  0.26, -0.34,  0.32),
        (29, 1.32,    0.08,  0.42, -0.50,  0.52),
        (33, 0.75,    0.10,  0.58, -0.64,  0.70),
        (35, 0.20,    0.12,  0.70, -0.74,  0.85),
        (36, 0.0001,  0.00,  0.00,  0.00,  0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc3_keys:
        key_char_bone(f, "FartCloud.3", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)


def build_idle_breathe(act):
    frames = [1, 15, 30, 45, 60]
    hide_fart_clouds_for_standard_clip(frames)
    for f, ph in [(1, 0.0), (15, 0.5 * math.pi), (30, math.pi), (45, 1.5 * math.pi), (60, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        key_char_bone(f, "Pelvis", pitch_x=0.02 * s, dy_up=0.018 * s)
        key_char_bone(f, "Chest", pitch_x=0.03 * s, roll_z=0.015 * c)
        key_char_bone(f, "Tail", pitch_x=0.10 * c, yaw_y=0.12 * s)
        key_char_bone(f, "Head", pitch_x=0.035 * s, yaw_y=0.04 * c, roll_z=0.025 * s)
        key_char_bone(f, "Ear.L", roll_z=0.08 * s, pitch_x=0.04 * c)
        key_char_bone(f, "Ear.R", roll_z=-0.08 * s, pitch_x=-0.04 * c)
        key_char_bone(f, "Arm.L", pitch_x=0.04 * s, roll_z=0.05 * c)
        key_char_bone(f, "Arm.R", pitch_x=-0.04 * s, roll_z=-0.05 * c)
        key_char_bone(f, "SkullPendant", pitch_x=0.06 * c, yaw_y=0.04 * s)
        blink = 0.22 if f == 30 else 0.0
        key_char_bone(f, "Eyelid.L", pitch_x=blink)
        key_char_bone(f, "Eyelid.R", pitch_x=blink)


def build_walk_cycle(act):
    frames = [1, 12, 24, 36, 48]
    hide_fart_clouds_for_standard_clip(frames)
    for f, ph in [(1, 0.0), (12, 0.5 * math.pi), (24, math.pi), (36, 1.5 * math.pi), (48, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        s2 = math.sin(2.0 * ph)
        key_char_bone(f, "Pelvis", pitch_x=0.04 * s2, yaw_y=0.10 * s, roll_z=0.06 * c, dx=0.03 * s, dy_up=0.055 * abs(s))
        key_char_bone(f, "Chest", pitch_x=0.05 * s2, yaw_y=-0.08 * s, roll_z=-0.05 * c)
        key_char_bone(f, "Tail", pitch_x=0.16 * s2, yaw_y=0.18 * c)
        key_char_bone(f, "Head", pitch_x=-0.04 * s2, yaw_y=0.06 * s, roll_z=0.05 * c)
        key_char_bone(f, "Leg.L", pitch_x=0.38 * s)
        key_char_bone(f, "Leg.R", pitch_x=-0.38 * s)
        key_char_bone(f, "FootHoof.L", pitch_x=-0.18 * c)
        key_char_bone(f, "FootHoof.R", pitch_x=0.18 * c)
        key_char_bone(f, "Arm.L", pitch_x=-0.28 * s, roll_z=0.06 * c)
        key_char_bone(f, "Arm.R", pitch_x=0.28 * s, roll_z=-0.06 * c)
        key_char_bone(f, "Ear.L", pitch_x=0.08 * s2, roll_z=0.10 * c)
        key_char_bone(f, "Ear.R", pitch_x=0.08 * s2, roll_z=-0.10 * c)
        key_char_bone(f, "SkullPendant", pitch_x=0.14 * s2, yaw_y=0.12 * s)


def build_happy_bounce(act):
    frames = [1, 10, 20, 30, 40]
    hide_fart_clouds_for_standard_clip(frames)
    for f, ph in [(1, 0.0), (10, 0.5 * math.pi), (20, math.pi), (30, 1.5 * math.pi), (40, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        jump = max(0.0, s) * 0.16
        key_char_bone(f, "Pelvis", pitch_x=-0.08 * s, dy_up=jump)
        key_char_bone(f, "Chest", pitch_x=-0.08 * s)
        key_char_bone(f, "Tail", pitch_x=0.25 * s)
        key_char_bone(f, "Head", pitch_x=-0.10 * s, yaw_y=0.06 * c)
        key_char_bone(f, "Ear.L", roll_z=0.22 * s, pitch_x=-0.14 * c)
        key_char_bone(f, "Ear.R", roll_z=-0.22 * s, pitch_x=-0.14 * c)
        key_char_bone(f, "Arm.L", roll_z=-0.28 * s)
        key_char_bone(f, "Arm.R", roll_z=0.28 * s)
        key_char_bone(f, "SkullPendant", pitch_x=-0.24 * c)
        key_char_bone(f, "Jaw", pitch_x=-0.14 * max(0.0, s))


def build_wave_paw(act):
    frames = [1, 15, 30, 45, 60]
    hide_fart_clouds_for_standard_clip(frames)
    for f, ph in [(1, 0.0), (15, 0.5 * math.pi), (30, math.pi), (45, 1.5 * math.pi), (60, 2.0 * math.pi)]:
        s = math.sin(ph)
        w = math.sin(3.0 * ph)
        lift = math.sin(0.5 * ph)
        key_char_bone(f, "Shoulder.R", roll_z=0.45 * lift)
        key_char_bone(f, "Arm.R", pitch_x=-0.35 * lift, yaw_y=0.20 * w * lift, roll_z=0.55 * lift)
        key_char_bone(f, "HandHoof.R", roll_z=0.30 * w * lift)
        key_char_bone(f, "Head", pitch_x=0.04 * s, yaw_y=-0.12 * lift, roll_z=0.14 * lift)
        key_char_bone(f, "Ear.L", roll_z=0.14 * lift)
        key_char_bone(f, "Ear.R", roll_z=-0.10 * lift)
        key_char_bone(f, "Tail", yaw_y=0.20 * w * lift)
        key_char_bone(f, "SkullPendant", pitch_x=0.08 * s, yaw_y=0.08 * lift)


def build_curious_tilt(act):
    frames = [1, 15, 30, 45, 60]
    hide_fart_clouds_for_standard_clip(frames)
    for f, ph in [(1, 0.0), (15, 0.5 * math.pi), (30, math.pi), (45, 1.5 * math.pi), (60, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        talk = abs(math.sin(2.0 * ph))
        key_char_bone(f, "Head", pitch_x=0.06 * c, yaw_y=0.18 * s, roll_z=-0.16 * s)
        key_char_bone(f, "Jaw", pitch_x=-0.14 * talk)
        key_char_bone(f, "Eyelid.L", pitch_x=0.12 * max(0.0, s))
        key_char_bone(f, "Eyelid.R", pitch_x=0.12 * max(0.0, -s))
        key_char_bone(f, "Ear.L", roll_z=-0.18 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.18 * s)
        key_char_bone(f, "Chest", yaw_y=0.06 * s, roll_z=-0.04 * s)


fart_act, fart_track = bake_action_to_nla("Hoppy_Fart_Blast", 36, build_hoppy_fart_blast)
idle_act, idle_track = bake_action_to_nla("Idle_Breathe", 60, build_idle_breathe)
walk_act, walk_track = bake_action_to_nla("Walk_Cycle", 48, build_walk_cycle)
bounce_act, bounce_track = bake_action_to_nla("Happy_Bounce", 40, build_happy_bounce)
wave_act, wave_track = bake_action_to_nla("Wave_Paw", 60, build_wave_paw)
curious_act, curious_track = bake_action_to_nla("Curious_Head_Tilt", 60, build_curious_tilt)

for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = False

bpy.ops.object.mode_set(mode='OBJECT')
scene.frame_start = 1
scene.frame_end = 36
scene.frame_set(1)


# ==============================================================================
# 7. EXPORT GLTF 2.0 (.GLB) AND WAVEFRONT (.OBJ) BEFORE ADDING STUDIO LIGHTS
# ==============================================================================
bpy.ops.object.select_all(action='DESELECT')
arm_obj.select_set(True)
mesh_obj.select_set(True)
bpy.context.view_layer.objects.active = arm_obj

bpy.ops.export_scene.gltf(
    filepath=GLB_PATH,
    export_format='GLB',
    use_selection=True,
    export_yup=True,
    export_apply=False,
    export_skins=True,
    export_animations=True,
    export_animation_mode='NLA_TRACKS',
    export_lights=False,
    export_cameras=False,
)

# For static .OBJ export, mute tracks, reset pose so FartCloud is collapsed inside torso,
# set subsurf_mod.levels = 1 for viewport and export base cage so .obj stays under 5MB!
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
subsurf_mod.levels = 1
subsurf_mod.show_viewport = False
bpy.context.view_layer.update()

bpy.ops.wm.obj_export(
    filepath=OBJ_PATH,
    export_selected_objects=True,
    export_materials=True,
)
subsurf_mod.show_viewport = True


# ==============================================================================
# 8. BRIGHT STUDIO CYCLORAMA (#F4F4F6) & HIGH-CONTRAST CYCLES LIGHTING
# ==============================================================================
bpy.ops.mesh.primitive_plane_add(size=24.0, location=(0.0, 0.0, 0.0))
ground_obj = bpy.context.active_object
ground_obj.name = "Studio_Cyclorama_Floor"
studio_col.objects.link(ground_obj)
scene.collection.objects.unlink(ground_obj)
ground_mat = create_plush_material(
    "Studio_Cyc_WhiteGrey", 0xF5F6F8, roughness=0.90, spec_ior=0.1,
    sheen=0.0, bump_strength=0.0, emission_strength=0.16
)
ground_obj.data.materials.append(ground_mat)


def add_area_light(name, loc, target, energy, size, color_rgb=(1.0, 1.0, 1.0)):
    ld = bpy.data.lights.new(name=name, type='AREA')
    ld.energy = energy
    ld.size = size
    ld.color = color_rgb
    lo = bpy.data.objects.new(name=name, object_data=ld)
    studio_col.objects.link(lo)
    lo.location = Vector(loc)
    direction = Vector(target) - Vector(loc)
    lo.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    return lo


add_area_light("Key_Softbox", (-2.6, -4.0, 3.6), (0.0, 0.0, 1.65), energy=200.0, size=3.2, color_rgb=(1.0, 0.99, 0.98))
add_area_light("Fill_Softbox", (2.8, -3.5, 2.6), (0.0, 0.0, 1.55), energy=135.0, size=3.6, color_rgb=(0.97, 0.98, 1.0))
add_area_light("Top_Softbox", (0.0, -0.9, 4.6), (0.0, 0.0, 1.95), energy=145.0, size=3.4, color_rgb=(1.0, 1.0, 1.0))
add_area_light("Rim_Backlight", (0.0, 3.2, 3.3), (0.0, 0.0, 1.70), energy=130.0, size=2.8, color_rgb=(0.98, 0.98, 1.0))

world = bpy.data.worlds.new("HoppyStudioWorld")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = hex_to_rgba(0xF5F6F8)
    bg_node.inputs[1].default_value = 1.02

for look_name in ('AgX - High Contrast', 'High Contrast'):
    try:
        scene.view_settings.look = look_name
        break
    except Exception:
        pass

cam_data = bpy.data.cameras.new("Studio_Camera")
cam_data.lens = 54.0
cam_obj = bpy.data.objects.new("Studio_Camera", cam_data)
studio_col.objects.link(cam_obj)
scene.camera = cam_obj


def aim_camera(loc, target=(0.0, 0.0, 1.62), lens=54.0):
    cam_data.lens = lens
    cam_obj.location = Vector(loc)
    direction = Vector(target) - Vector(loc)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


# ==============================================================================
# 9. RENDER STUDIO HERO & TURNAROUND VIEWS (FRONT 1080x1350, 3/4, SIDE)
# ==============================================================================
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.use_denoising = True
if hasattr(scene.cycles, "denoiser"):
    for d_opt in ('OPENIMAGEDENOISE', 'OPTIX'):
        try:
            scene.cycles.denoiser = d_opt
            break
        except Exception:
            pass

scene.render.resolution_percentage = 100
scene.render.fps = 24
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
scene.frame_set(1)

# 1. Hero Front Render (1080x1350)
subsurf_mod.render_levels = 2
scene.cycles.samples = 32
scene.render.resolution_x = 1080
scene.render.resolution_y = 1350
aim_camera((0.0, -6.20, 1.66), target=(0.0, 0.0, 1.62), lens=54.0)
scene.render.filepath = RENDER_FRONT_PATH
bpy.ops.render.render(write_still=True)

# 2. Turnaround 3/4 & Side Renders (800x1000)
scene.cycles.samples = 24
scene.render.resolution_x = 800
scene.render.resolution_y = 1000

aim_camera((-4.35, -4.45, 1.72), target=(0.0, 0.0, 1.62), lens=54.0)
scene.render.filepath = os.path.join(WORK_DIR, "cycles_3q.png")
bpy.ops.render.render(write_still=True)

aim_camera((-6.20, 0.0, 1.66), target=(0.0, -0.06, 1.62), lens=54.0)
scene.render.filepath = os.path.join(WORK_DIR, "cycles_side.png")
bpy.ops.render.render(write_still=True)


# ==============================================================================
# 10. RENDER THE 36-FRAME `Hoppy_Fart_Blast` CYCLES ANIMATION SEQUENCE!
# ==============================================================================
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = (trk.name != "Hoppy_Fart_Blast")

aim_camera((5.55, -4.05, 1.75), target=(-0.05, 0.36, 1.48), lens=50.0)

scene.frame_start = 1
scene.frame_end = 36
scene.frame_set(14)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)

subsurf_mod.render_levels = 1
scene.cycles.samples = 14
scene.render.resolution_x = 640
scene.render.resolution_y = 640

for f in range(1, 37):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(FART_FRAMES_DIR, f"frame_{f:03d}.png")
    bpy.ops.render.render(write_still=True)

print("SUCCESS v2: Built Hoppy Hopscotch .blend, .glb, .obj, studio renders & 36 Cycles frames!")
print(f"  BLEND: {BLEND_PATH} ({os.path.getsize(BLEND_PATH)} bytes)")
print(f"  GLB:   {GLB_PATH} ({os.path.getsize(GLB_PATH)} bytes)")
print(f"  OBJ:   {OBJ_PATH} ({os.path.getsize(OBJ_PATH)} bytes)")
print(f"  FRONT: {RENDER_FRONT_PATH} ({os.path.getsize(RENDER_FRONT_PATH)} bytes)")
