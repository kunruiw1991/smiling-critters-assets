#!/usr/bin/env python3
"""
Native Blender 4.3 Builder, Rigging, Animation & Cycles Studio Renderer (v3 Final Calibrated)
for Baba Chops (#121 Official Plush Base Model - Smiling Critters / Nightmare Critters).

Run headless via:
  /tmp/blender/blender -b --factory-startup --python-exit-code 1 -P /tmp/build_baba_chops_blender.py
"""

import os
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, noise

OUT_DIR = "/tmp/smiling-critters-assets/models"
os.makedirs(OUT_DIR, exist_ok=True)

BLEND_PATH = os.path.join(OUT_DIR, "baba_chops_plush_base_model.blend")
GLB_PATH = os.path.join(OUT_DIR, "baba_chops_plush_base_model.glb")
OBJ_PATH = os.path.join(OUT_DIR, "baba_chops_plush_base_model.obj")
RENDER_FRONT_PATH = os.path.join(OUT_DIR, "baba_chops_blender_cycles_render.png")
RENDER_PREVIEW_PATH = os.path.join(OUT_DIR, "baba_chops_3d_preview.png")
RENDER_SHEET_DIR = "/tmp/baba_blender_renders"
os.makedirs(RENDER_SHEET_DIR, exist_ok=True)


# ==============================================================================
# 1. SCENE RESET & HELPER UTILITIES
# ==============================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

main_col = bpy.data.collections.new("BabaChops_Plush_Rig")
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
    nx = x / 0.80
    ny = (y_up - 1.98) / 0.72
    r2 = min(0.92, nx * nx + ny * ny)
    return 0.75 * math.sqrt(max(0.08, 1.0 - r2))


def sherpa_fur_displacement(p_world):
    """Multi-octave 3D procedural sherpa wool curl displacement."""
    q1 = Vector((p_world.x * 7.5, p_world.y * 7.5, p_world.z * 7.5))
    q2 = Vector((p_world.x * 16.0 + 3.1, p_world.y * 16.0 - 1.7, p_world.z * 16.0 + 2.3))
    q3 = Vector((p_world.x * 32.0 - 4.2, p_world.y * 32.0 + 5.1, p_world.z * 32.0 - 1.9))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    n3 = noise.noise(q3)
    return 0.038 * n1 + 0.020 * abs(n2) + 0.010 * n3


# ==============================================================================
# 2. PROCEDURAL CYCLES / GLTF PBR MATERIALS (HIGH-CONTRAST PLUSH CALIBRATION)
# ==============================================================================
def create_plush_material(name, hex_color, roughness=0.88, spec_ior=0.12,
                          sheen=0.25, sheen_tint_mult=1.0,
                          bump_scale=45.0, bump_strength=0.12,
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
        noise_node.inputs["Detail"].default_value = 12.0
        noise_node.inputs["Roughness"].default_value = 0.76

        bump = nodes.new(type="ShaderNodeBump")
        bump.location = (-180, -180)
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.022

        links.new(tex_coord.outputs["Object"], noise_node.inputs["Vector"])
        links.new(noise_node.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


MATS = {
    # Deep light-absorbing jet-black sherpa wool (low Specular IOR so it stays rich black!)
    "WoolBlack": create_plush_material(
        "Baba_Wool_Black", 0x050507, roughness=0.93, spec_ior=0.05,
        sheen=0.14, sheen_tint_mult=1.2, bump_scale=46.0, bump_strength=0.42
    ),
    # Deep jet-black short-pile plush body fabric
    "BodyBlack": create_plush_material(
        "Baba_Plush_Body_Black", 0x060609, roughness=0.88, spec_ior=0.06,
        sheen=0.14, sheen_tint_mult=1.2, bump_scale=80.0, bump_strength=0.18
    ),
    # Medium dove-grey velour for muzzle, eyelids, ears, buck teeth & hooves (distinctly darker than white skull!)
    "DoveGrey": create_plush_material(
        "Baba_Velour_Dove_Grey", 0x5A5D64, roughness=0.78, spec_ior=0.14,
        sheen=0.28, sheen_tint_mult=1.02, bump_scale=95.0, bump_strength=0.14, subsurface=0.03
    ),
    # Deeper shadowed dove-grey for inner ear cup and stitch grooves
    "InnerEarGrey": create_plush_material(
        "Baba_Inner_Ear_Grey", 0x3A3C42, roughness=0.84, spec_ior=0.10,
        sheen=0.20, sheen_tint_mult=1.0, bump_scale=90.0, bump_strength=0.14
    ),
    # Stark bright white felt/embroidered Skull Pendant (#121 chest focal point)
    "SkullWhite": create_plush_material(
        "Baba_Skull_Bright_White", 0xFFFFFF, roughness=0.45, spec_ior=0.35,
        sheen=0.20, sheen_tint_mult=1.0, bump_scale=120.0, bump_strength=0.02,
        coat=0.15, emission_strength=0.08
    ),
    # Deep jet-black glossy acrylic dome eyes (controlled spec_ior so they don't wash out grey)
    "EyeGloss": create_plush_material(
        "Baba_Eye_Acrylic_Black", 0x020203, roughness=0.04, spec_ior=0.12,
        sheen=0.0, bump_strength=0.0, coat=0.28, coat_rough=0.015
    ),
    # Studio catchlight highlight on eyes
    "CatchlightWhite": create_plush_material(
        "Baba_Eye_Catchlight_White", 0xFFFFFF, roughness=0.05, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, emission_strength=0.35
    ),
    # Pitch-black recessed mouth interior & skull eye/nose cutouts
    "MouthVoidBlack": create_plush_material(
        "Baba_Mouth_Cavity_Black", 0x010102, roughness=0.99, spec_ior=0.01,
        sheen=0.0, bump_strength=0.0
    ),
    # Brushed nickel / silver zipper teeth & collar pull slider
    "ZipperMetal": create_plush_material(
        "Baba_Zipper_Silver_Metal", 0xD8DDE6, roughness=0.20, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, metallic=0.94, coat=0.30
    ),
    # Dark zipper tape backing
    "ZipperTrack": create_plush_material(
        "Baba_Zipper_Track_Dark", 0x101115, roughness=0.86, spec_ior=0.06,
        sheen=0.10, bump_strength=0.06
    ),
}


# ==============================================================================
# 3. BABA CHOPS GEOMETRY BUILDER (BMESH + SHERPA DISPLACEMENT + SKIN WEIGHTS)
# ==============================================================================
master_bm = bmesh.new()
deform_layer = master_bm.verts.layers.deform.verify()

BONE_NAMES = [
    "Root",
    "Pelvis",
    "Spine",
    "Chest",
    "Neck",
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
]
BONE_IDX = {name: i for i, name in enumerate(BONE_NAMES)}

MAT_LIST = [
    MATS["WoolBlack"],
    MATS["BodyBlack"],
    MATS["DoveGrey"],
    MATS["InnerEarGrey"],
    MATS["SkullWhite"],
    MATS["EyeGloss"],
    MATS["CatchlightWhite"],
    MATS["MouthVoidBlack"],
    MATS["ZipperMetal"],
    MATS["ZipperTrack"],
]
MAT_IDX = {
    "WoolBlack": 0,
    "BodyBlack": 1,
    "DoveGrey": 2,
    "InnerEarGrey": 3,
    "SkullWhite": 4,
    "EyeGloss": 5,
    "CatchlightWhite": 6,
    "MouthVoidBlack": 7,
    "ZipperMetal": 8,
    "ZipperTrack": 9,
}


def append_bmesh_part(part_bm, mat_key, weight_fn):
    mat_idx = MAT_IDX[mat_key]
    v_map = {}
    for v in part_bm.verts:
        ox, oy, oz = v.co.x, v.co.y, v.co.z
        nv = master_bm.verts.new(to_b_vec(ox, oy, oz))
        weights = weight_fn(ox, oy, oz)
        dvert = nv[deform_layer]
        for bname, w in weights.items():
            if w > 1e-4:
                dvert[BONE_IDX[bname]] = float(w)
        v_map[v] = nv

    for f in part_bm.faces:
        try:
            nf = master_bm.faces.new([v_map[v] for v in f.verts])
            nf.material_index = mat_idx
            nf.smooth = True
        except ValueError:
            pass
    part_bm.free()


def make_uv_sphere_bm(rx, ry, rz, cx=0.0, cy=0.0, cz=0.0,
                      u_segs=32, v_segs=24, rot_euler=(0.0, 0.0, 0.0),
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
    """Create a beveled box that retains crisp rectangular form under SUBSURF."""
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


def make_torus_tube_bm(curve_pts, radius_fn, radial_segs=20, closed=False):
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


# ------------------------------------------------------------------------------
# 3.1 SHAGGY SHERPA WOOL HEAD CORE & OVERHANGING BROW/CHEEK FLEECE TUFTS
# ------------------------------------------------------------------------------
def wool_world_displace(p_w, n_w):
    in_face_zone = (p_w.z > 0.46 and 1.42 < p_w.y < 2.12 and abs(p_w.x) < 0.46)
    scale = 0.22 if in_face_zone else 1.20
    return p_w + n_w * (sherpa_fur_displacement(p_w) * scale)


head_core_bm = make_uv_sphere_bm(
    0.70, 0.70, 0.72, cx=0.0, cy=1.97, cz=0.0,
    u_segs=56, v_segs=42,
    world_deform_fn=wool_world_displace
)
append_bmesh_part(head_core_bm, "WoolBlack", lambda x, y, z: {"Head": 1.0})

# Dense shaggy wool tufts: compact peaked crown (#121 silhouette, narrower than arm span!)
wool_puffs = [
    # Pointed top crown tuft
    (0.00, 2.56, 0.12, 0.24), (-0.19, 2.51, 0.14, 0.22), (0.19, 2.51, 0.14, 0.22),
    (-0.37, 2.42, 0.10, 0.20), (0.37, 2.42, 0.10, 0.20),
    (-0.50, 2.28, 0.08, 0.19), (0.50, 2.28, 0.08, 0.19),
    # Forehead bangs
    (0.00, 2.34, 0.46, 0.21), (-0.19, 2.35, 0.44, 0.20), (0.19, 2.35, 0.44, 0.20),
    (-0.36, 2.29, 0.40, 0.19), (0.36, 2.29, 0.40, 0.19),
    # Overhanging shaggy brow locks that drape directly over the top edge of the grey eyelids!
    (0.00, 2.13, 0.63, 0.130), (-0.10, 2.17, 0.62, 0.135), (0.10, 2.17, 0.62, 0.135),
    (-0.22, 2.19, 0.60, 0.140), (0.22, 2.19, 0.60, 0.140),
    (-0.34, 2.18, 0.55, 0.145), (0.34, 2.18, 0.55, 0.145),
    (-0.45, 2.12, 0.46, 0.145), (0.45, 2.12, 0.46, 0.145),
    # Crown middle & back
    (0.00, 2.48, -0.14, 0.24), (-0.24, 2.44, -0.16, 0.22), (0.24, 2.44, -0.16, 0.22),
    (-0.44, 2.34, -0.14, 0.20), (0.44, 2.34, -0.14, 0.20),
    # Compact side cheeks & lower jaw tufts framing the wide grey smile
    (-0.56, 2.12, 0.14, 0.18), (0.56, 2.12, 0.14, 0.18),
    (-0.60, 1.94, 0.12, 0.18), (0.60, 1.94, 0.12, 0.18),
    (-0.58, 1.72, 0.16, 0.18), (0.58, 1.72, 0.16, 0.18),
    (-0.51, 1.54, 0.22, 0.17), (0.51, 1.54, 0.22, 0.17),
    (-0.38, 1.43, 0.24, 0.16), (0.38, 1.43, 0.24, 0.16),
    # Back of head fleece puffs
    (0.00, 2.26, -0.50, 0.25), (-0.30, 2.22, -0.46, 0.23), (0.30, 2.22, -0.46, 0.23),
    (-0.50, 2.08, -0.32, 0.21), (0.50, 2.08, -0.32, 0.21),
    (0.00, 1.94, -0.56, 0.25), (-0.32, 1.93, -0.50, 0.23), (0.32, 1.93, -0.50, 0.23),
    (-0.52, 1.80, -0.34, 0.21), (0.52, 1.80, -0.34, 0.21),
    (0.00, 1.66, -0.48, 0.22), (-0.28, 1.66, -0.42, 0.20), (0.28, 1.66, -0.42, 0.20),
    (-0.30, 1.44, 0.08, 0.16), (0.30, 1.44, 0.08, 0.16), (0.00, 1.42, -0.15, 0.18),
]

for idx, (px, py, pz, pr) in enumerate(wool_puffs):
    def puff_world_disp(p_w, n_w, seed=idx):
        d = sherpa_fur_displacement(p_w + Vector((seed * 0.7, seed * 1.3, 0.0)))
        return p_w + n_w * (d * 1.25)

    p_bm = make_uv_sphere_bm(
        pr * 1.05, pr * 0.95, pr,
        cx=px, cy=py, cz=pz,
        u_segs=28, v_segs=22,
        world_deform_fn=puff_world_disp
    )
    append_bmesh_part(p_bm, "WoolBlack", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.2 ALL-DOVE-GREY CUPPED HORIZONTAL LAMB EARS (#121 AUTHENTIC EAR SHAPE)
# ------------------------------------------------------------------------------
for side in (-1, 1):
    ear_bone = "Ear.L" if side == 1 else "Ear.R"

    def ear_outer_deform(p, s=side):
        t_out = (s * p.x) / 0.28
        p.y *= (0.78 + 0.25 * (1.0 - 0.4 * t_out * t_out))
        if p.z > 0.0:
            r_cup = max(0.0, 1.0 - (p.x / 0.22) ** 2 - (p.y / 0.10) ** 2)
            p.z = p.z * (1.0 - 0.75 * r_cup)
        return p

    ear_out_bm = make_uv_sphere_bm(
        0.26, 0.125, 0.095,
        cx=side * 0.79, cy=1.89, cz=0.06,
        u_segs=32, v_segs=24,
        rot_euler=(0.06, -side * 0.12, -side * 0.10),
        deform_fn=ear_outer_deform
    )
    append_bmesh_part(
        ear_out_bm, "DoveGrey",
        lambda x, y, z, b=ear_bone: {b: 0.88, "Head": 0.12}
    )

    ear_in_bm = make_uv_sphere_bm(
        0.18, 0.072, 0.040,
        cx=side * 0.80, cy=1.885, cz=0.108,
        u_segs=24, v_segs=18,
        rot_euler=(0.06, -side * 0.12, -side * 0.10)
    )
    append_bmesh_part(
        ear_in_bm, "InnerEarGrey",
        lambda x, y, z, b=ear_bone: {b: 0.92, "Head": 0.08}
    )


# ------------------------------------------------------------------------------
# 3.3 EYES, DOVE-GREY SOCKET FOLDS, ANGRY-CUTE V-BROW EYELID HOODS & CATCHLIGHTS
# ------------------------------------------------------------------------------
bridge_bm = make_uv_sphere_bm(
    0.090, 0.135, 0.080,
    cx=0.0, cy=1.985, cz=0.635,
    u_segs=20, v_segs=16
)
append_bmesh_part(bridge_bm, "InnerEarGrey", lambda x, y, z: {"Head": 1.0})

for side in (-1, 1):
    lid_bone = "Eyelid.L" if side == 1 else "Eyelid.R"
    ex = side * 0.255
    ey = 1.985
    ez = 0.600

    # Deep jet-black acrylic eye dome
    eye_bm = make_uv_sphere_bm(
        0.180, 0.172, 0.132,
        cx=ex, cy=ey, cz=ez,
        u_segs=36, v_segs=28,
        rot_euler=(-0.04, side * 0.18, 0.0)
    )
    append_bmesh_part(eye_bm, "EyeGloss", lambda x, y, z: {"Head": 1.0})

    # Vertical studio softbox reflection bar on the black eye dome
    hi1_bm = make_uv_sphere_bm(
        0.020, 0.050, 0.012,
        cx=ex - side * 0.032, cy=ey - 0.012, cz=ez + 0.125,
        u_segs=16, v_segs=12,
        rot_euler=(0.05, side * 0.14, 0.0)
    )
    append_bmesh_part(hi1_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Single-piece Spherical-Hood Dove-Grey Upper Eyelid slanted +side * 0.48 rad (V-brow!)
    # Flush with the eye dome in side profile and tucked underneath the overhanging black wool bangs!
    def eyelid_hood_deform(p, s=side):
        if p.y < 0.008:
            p.y = 0.008 + (p.y - 0.008) * 0.14
        if p.y > 0.145:
            p.y = 0.145 + (p.y - 0.145) * 0.35
        if p.z < -0.02:
            p.z *= 0.35
        return p

    lid_hood_bm = make_uv_sphere_bm(
        0.204, 0.192, 0.146,
        cx=ex, cy=ey, cz=ez,
        u_segs=32, v_segs=24,
        rot_euler=(-0.04, side * 0.18, side * 0.48),
        deform_fn=eyelid_hood_deform
    )
    append_bmesh_part(
        lid_hood_bm, "DoveGrey",
        lambda x, y, z, b=lid_bone: {b: 0.92, "Head": 0.08}
    )

    # Flush lower eyelid rim crease along the V-brow diagonal
    lid_rim_pts = []
    rot_lid = Euler((-0.04, side * 0.18, side * 0.48), 'XYZ').to_matrix()
    for k in range(21):
        t = -1.0 + 2.0 * k / 20.0
        lx = t * 0.198
        ly = 0.010
        lz = math.sqrt(max(0.01, 1.0 - t * t)) * 0.147
        v_world = (rot_lid @ Vector((lx, ly, lz))) + Vector((ex, ey, ez))
        lid_rim_pts.append((v_world.x, v_world.y, v_world.z))
    lid_rim_bm = make_torus_tube_bm(
        lid_rim_pts,
        lambda t: 0.025 * math.sin(math.pi * (0.06 + 0.88 * t)),
        radial_segs=14, closed=False
    )
    append_bmesh_part(
        lid_rim_bm, "DoveGrey",
        lambda x, y, z, b=lid_bone: {b: 0.95, "Head": 0.05}
    )


# ------------------------------------------------------------------------------
# 3.4 WIDE SCULPTED DOVE-GREY MUZZLE, NOSTRILS, RECESSED MOUTH & FLUSH BUCK TEETH
# ------------------------------------------------------------------------------
snout_bm = make_uv_sphere_bm(
    0.29, 0.110, 0.145,
    cx=0.0, cy=1.835, cz=0.635,
    u_segs=32, v_segs=22,
    rot_euler=(-0.06, 0.0, 0.0)
)
append_bmesh_part(snout_bm, "DoveGrey", lambda x, y, z: {"Head": 0.88, "Jaw": 0.12})

for side in (-1, 1):
    nos_bm = make_uv_sphere_bm(
        0.022, 0.014, 0.016,
        cx=side * 0.082, cy=1.878, cz=0.752,
        u_segs=14, v_segs=12,
        rot_euler=(-0.22, 0.0, -side * 0.25)
    )
    append_bmesh_part(nos_bm, "MouthVoidBlack", lambda x, y, z: {"Head": 1.0})


def build_conformed_mouth_cavity_bm():
    bm = bmesh.new()
    u_steps = 40
    v_steps = 20
    grid = []
    for iv in range(v_steps + 1):
        v_frac = iv / v_steps
        ring = []
        for iu in range(u_steps):
            ang = 2.0 * math.pi * iu / u_steps
            ux = math.cos(ang) * 0.50 * v_frac
            raw_y = math.sin(ang)
            if raw_y >= 0:
                uy = 1.76 + raw_y * 0.06 * v_frac + 0.08 * (ux / 0.50) ** 2
            else:
                uy = 1.76 + raw_y * 0.33 * v_frac + 0.06 * (ux / 0.50) ** 2
            uz = head_front_z(ux, uy) - 0.014 * (1.0 - 0.35 * v_frac)
            ring.append(bm.verts.new((ux, uy, uz)))
        grid.append(ring)

    for iv in range(v_steps):
        r1 = grid[iv]
        r2 = grid[iv + 1]
        for iu in range(u_steps):
            iun = (iu + 1) % u_steps
            bm.faces.new([r1[iu], r2[iu], r2[iun], r1[iun]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


mouth_bm = build_conformed_mouth_cavity_bm()
append_bmesh_part(
    mouth_bm, "MouthVoidBlack",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.75 - y) * 3.0)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.75 - y) * 3.0))}
)

# Upper Smile Lip Rim
upper_lip_pts = []
for k in range(37):
    t = -1.0 + 2.0 * k / 36.0
    lx = t * 0.51
    ly = 1.775 + 0.095 * (t * t) - 0.025 * (t ** 4)
    lz = head_front_z(lx, ly) + 0.030 * (1.0 - 0.38 * t * t)
    upper_lip_pts.append((lx, ly, lz))

upper_lip_bm = make_torus_tube_bm(
    upper_lip_pts,
    lambda t: 0.042 + 0.015 * math.sin(math.pi * t),
    radial_segs=18, closed=False
)
append_bmesh_part(upper_lip_bm, "DoveGrey", lambda x, y, z: {"Head": 0.88, "Jaw": 0.12})

# Lower Smile Lip Rim (bottom at y=1.425 so collar zipper slider is clearly visible below chin!)
lower_lip_pts = []
for k in range(41):
    t = -1.0 + 2.0 * k / 40.0
    lx = t * 0.51
    ly = 1.425 + 0.425 * (t ** 2)
    lz = head_front_z(lx, ly) + 0.020 * (1.0 - 0.35 * t * t)
    lower_lip_pts.append((lx, ly, lz))

lower_lip_bm = make_torus_tube_bm(
    lower_lip_pts,
    lambda t: 0.032 + 0.011 * math.sin(math.pi * t),
    radial_segs=18, closed=False
)
append_bmesh_part(
    lower_lip_bm, "DoveGrey",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.75 - y) * 2.8)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.75 - y) * 2.8))}
)

# Cheek corner plush folds wrapping the ends of the smile
for side in (-1, 1):
    cheek_pts = []
    for k in range(13):
        t = k / 12.0
        cx = side * (0.47 + 0.05 * math.sin(math.pi * t))
        cy = 1.76 + 0.15 * (1.0 - t)
        cz = head_front_z(cx, cy) + 0.022
        cheek_pts.append((cx, cy, cz))
    cheek_bm = make_torus_tube_bm(cheek_pts, 0.036, radial_segs=14, closed=False)
    append_bmesh_part(cheek_bm, "DoveGrey", lambda x, y, z: {"Head": 0.90, "Jaw": 0.10})

# Twin Contiguous Squared-Off Dove-Grey Buck Teeth (#121 rounded-rectangle plush teeth)
for side in (-1, 1):
    tx = side * 0.072
    ty = 1.685
    tz = head_front_z(tx, ty) + 0.002

    def tooth_deform(p, s=side):
        # Widen the lower corners into a plush rounded-square tooth before clamping the medial edge
        if p.y < 0:
            p.x *= (1.0 + 0.18 * min(1.0, (p.y / -0.105) ** 2))
        if p.y < -0.108:
            p.y = -0.108 + (p.y + 0.108) * 0.25
        # Medial inner edge at x=0: clamp cleanly so left and right teeth kiss at x=0
        if s * p.x < -0.070:
            p.x = -s * (0.070 + (abs(p.x) - 0.070) * 0.08)
        return p

    tooth_bm = make_uv_sphere_bm(
        0.078, 0.138, 0.035,
        cx=tx, cy=ty, cz=tz,
        u_segs=32, v_segs=24,
        rot_euler=(-0.32, 0.0, 0.0),
        deform_fn=tooth_deform
    )
    append_bmesh_part(tooth_bm, "DoveGrey", lambda x, y, z: {"Head": 0.95, "Jaw": 0.05})


# ------------------------------------------------------------------------------
# 3.5 PEAR-SHAPED BLACK PLUSH TORSO, COLLAR ZIPPER SLIDER & SKULL PENDANT CHARM
# ------------------------------------------------------------------------------
def build_torso_bm():
    bm = bmesh.new()
    u_segs = 44
    profile = [
        (0.00, 0.52), (0.18, 0.53), (0.35, 0.57), (0.46, 0.66),
        (0.51, 0.78), (0.52, 0.92), (0.49, 1.06), (0.45, 1.20),
        (0.39, 1.33), (0.33, 1.43), (0.26, 1.50), (0.00, 1.52)
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
    if y < 0.78:
        t = max(0.0, min(1.0, (y - 0.52) / 0.26))
        return {"Pelvis": 1.0 - 0.5 * t, "Spine": 0.5 * t}
    elif y < 1.12:
        t = (y - 0.78) / 0.34
        return {"Pelvis": max(0.0, 0.5 - t), "Spine": 1.0 - abs(t - 0.5), "Chest": max(0.0, t - 0.3)}
    elif y < 1.40:
        t = (y - 1.12) / 0.28
        return {"Spine": max(0.0, 0.5 * (1.0 - t)), "Chest": 1.0 - 0.3 * t, "Neck": 0.3 * t}
    else:
        return {"Chest": 0.4, "Neck": 0.6}


torso_bm = build_torso_bm()
append_bmesh_part(torso_bm, "BodyBlack", torso_weights)


def torso_front_z(y):
    t = max(0.0, min(1.0, (y - 0.56) / (1.44 - 0.56)))
    r = 0.35 + 0.17 * math.sin(math.pi * (t ** 0.72)) - 0.08 * t
    return r * 0.88


# Zipper fabric track + interlocking silver metal zipper teeth along the vertical center seam
zip_pts = [(0.0, 0.58 + (1.42 - 0.58) * k / 24.0, torso_front_z(0.58 + (1.42 - 0.58) * k / 24.0) + 0.005)
           for k in range(25)]
zip_track_bm = make_torus_tube_bm(zip_pts, 0.024, radial_segs=10, closed=False)
append_bmesh_part(zip_track_bm, "ZipperTrack", torso_weights)

for i in range(36):
    zy = 0.60 + (1.40 - 0.60) * (i / 35.0)
    zz = torso_front_z(zy) + 0.018
    zx = (0.010 if (i % 2 == 0) else -0.010)
    t_bm = make_beveled_box_bm(0.036, 0.014, 0.020, zx, zy, zz)
    append_bmesh_part(t_bm, "ZipperMetal", torso_weights)

# Collar silver zipper slider + metallic pull clasp visible right under the chin (y=1.26..1.38)
slider_bm = make_beveled_box_bm(0.068, 0.082, 0.044, 0.0, 1.338, 0.448)
append_bmesh_part(slider_bm, "ZipperMetal", lambda x, y, z: {"Chest": 0.7, "SkullPendant": 0.3})

clasp_bm = make_beveled_box_bm(0.038, 0.065, 0.038, 0.0, 1.282, 0.464)
append_bmesh_part(clasp_bm, "ZipperMetal", lambda x, y, z: {"SkullPendant": 1.0})

# White rectangular top tab connecting the Skull Pendant to the silver zipper pull (#121 detail)
bail_bm = make_beveled_box_bm(0.068, 0.058, 0.036, 0.0, 1.236, 0.470)
append_bmesh_part(bail_bm, "SkullWhite", lambda x, y, z: {"SkullPendant": 1.0})

# Stark Bright-White 3D Skull Pendant Charm centered on chest (y=0.88..1.22)
skull_cranium_bm = make_uv_sphere_bm(
    0.205, 0.162, 0.048,
    cx=0.0, cy=1.095, cz=0.482,
    u_segs=32, v_segs=24,
    rot_euler=(-0.05, 0.0, 0.0)
)
append_bmesh_part(skull_cranium_bm, "SkullWhite", lambda x, y, z: {"SkullPendant": 1.0})

for side in (-1, 1):
    cheek_bm = make_uv_sphere_bm(
        0.078, 0.065, 0.044,
        cx=side * 0.130, cy=1.035, cz=0.485,
        u_segs=18, v_segs=14,
        rot_euler=(-0.05, 0.0, 0.0)
    )
    append_bmesh_part(cheek_bm, "SkullWhite", lambda x, y, z: {"SkullPendant": 1.0})

skull_jaw_bm = make_uv_sphere_bm(
    0.125, 0.095, 0.045,
    cx=0.0, cy=0.955, cz=0.488,
    u_segs=24, v_segs=18,
    rot_euler=(-0.05, 0.0, 0.0)
)
append_bmesh_part(skull_jaw_bm, "SkullWhite", lambda x, y, z: {"SkullPendant": 1.0})

# Skull large angled dark oval eye sockets, central nasal triangle & 3 stitched tooth bars
for side in (-1, 1):
    s_eye_bm = make_uv_sphere_bm(
        0.062, 0.056, 0.022,
        cx=side * 0.078, cy=1.095, cz=0.522,
        u_segs=18, v_segs=14,
        rot_euler=(-0.05, 0.0, side * 0.22)
    )
    append_bmesh_part(s_eye_bm, "MouthVoidBlack", lambda x, y, z: {"SkullPendant": 1.0})

s_nose_bm = make_uv_sphere_bm(
    0.026, 0.036, 0.020,
    cx=0.0, cy=1.028, cz=0.526,
    u_segs=14, v_segs=12,
    rot_euler=(-0.05, 0.0, 0.0)
)
append_bmesh_part(s_nose_bm, "MouthVoidBlack", lambda x, y, z: {"SkullPendant": 1.0})

for sx in (-0.052, 0.0, 0.052):
    st_bm = bmesh.new()
    bmesh.ops.create_cube(st_bm, size=1.0)
    for v in st_bm.verts:
        v.co = Vector((v.co.x * 0.012 + sx, v.co.y * 0.062 + 0.935, v.co.z * 0.018 + 0.528))
    append_bmesh_part(st_bm, "MouthVoidBlack", lambda x, y, z: {"SkullPendant": 1.0})


# ------------------------------------------------------------------------------
# 3.6 SPLAYED PLUSH ARMS & ELONGATED DOVE-GREY HOOF MITTEN CUFFS (#121 MATCH)
# ------------------------------------------------------------------------------
for side in (-1, 1):
    sh_bone = "Shoulder.L" if side == 1 else "Shoulder.R"
    arm_bone = "Arm.L" if side == 1 else "Arm.R"
    hoof_bone = "HandHoof.L" if side == 1 else "HandHoof.R"

    arm_pts = []
    for k in range(15):
        t = k / 14.0
        ax = side * (0.32 + 0.40 * t)
        ay = 1.33 - 0.32 * t + 0.02 * math.sin(math.pi * t)
        az = 0.02 + 0.04 * t
        arm_pts.append((ax, ay, az))

    arm_bm = make_torus_tube_bm(
        arm_pts,
        lambda t: 0.142 * (1.0 + 0.04 * t),
        radial_segs=22, closed=False
    )

    def arm_weight_fn(x, y, z, sb=sh_bone, ab=arm_bone, hb=hoof_bone):
        dist = max(0.0, min(1.0, (abs(x) - 0.32) / 0.45))
        if dist < 0.35:
            return {"Chest": 0.35 * (1.0 - dist / 0.35), sb: 0.65, ab: 0.35 * (dist / 0.35)}
        elif dist < 0.85:
            return {ab: 0.85, sb: 0.15}
        else:
            return {ab: 0.50, hb: 0.50}

    append_bmesh_part(arm_bm, "BodyBlack", arm_weight_fn)

    mitten_pts = []
    for k in range(15):
        t = k / 14.0
        mx = side * (0.69 + 0.24 * t)
        my = 1.03 - 0.20 * t
        mz = 0.06 + 0.03 * t
        mitten_pts.append((mx, my, mz))

    def mitten_radius(t):
        if t < 0.12:
            return 0.145 + 0.015 * (t / 0.12)
        elif t < 0.72:
            return 0.160 + 0.008 * math.sin(math.pi * (t - 0.12) / 0.60)
        else:
            u = (t - 0.72) / 0.28
            return 0.160 * math.sqrt(max(0.02, 1.0 - u * u))

    mitten_bm = make_torus_tube_bm(mitten_pts, mitten_radius, radial_segs=24, closed=False)
    append_bmesh_part(
        mitten_bm, "DoveGrey",
        lambda x, y, z, hb=hoof_bone, ab=arm_bone: {hb: 0.90, ab: 0.10}
    )

    cleft_pts = []
    for k in range(9):
        t = k / 8.0
        cx = side * (0.83 + 0.09 * t)
        cy = 0.91 - 0.08 * t
        cz = 0.085 + 0.135 * math.sin(math.pi * (0.15 + 0.70 * t))
        cleft_pts.append((cx, cy, cz))
    cleft_bm = make_torus_tube_bm(cleft_pts, 0.007, radial_segs=10, closed=False)
    append_bmesh_part(cleft_bm, "InnerEarGrey", lambda x, y, z, hb=hoof_bone: {hb: 1.0})


# ------------------------------------------------------------------------------
# 3.7 STOUT A-STANCE PLUSH LEGS & SYMMETRIC CLOVEN FOOT HOOVES
# ------------------------------------------------------------------------------
for side in (-1, 1):
    leg_bone = "Leg.L" if side == 1 else "Leg.R"
    foot_bone = "FootHoof.L" if side == 1 else "FootHoof.R"

    leg_pts = []
    for k in range(15):
        t = k / 14.0
        lx = side * (0.24 + 0.055 * t)
        ly = 0.66 - 0.43 * t
        lz = 0.0 + 0.02 * t
        leg_pts.append((lx, ly, lz))

    leg_bm = make_torus_tube_bm(
        leg_pts,
        lambda t: 0.182 * (1.0 - 0.06 * t),
        radial_segs=24, closed=False
    )

    def leg_weight_fn(x, y, z, lb=leg_bone, fb=foot_bone):
        if y > 0.52:
            return {"Pelvis": 0.45, lb: 0.55}
        elif y > 0.25:
            return {lb: 0.90, fb: 0.10}
        else:
            return {lb: 0.25, fb: 0.75}

    append_bmesh_part(leg_bm, "BodyBlack", leg_weight_fn)

    fx = side * 0.305
    fy = 0.135
    fz = 0.055

    def foot_deform(p):
        if p.y < -0.02:
            p.y = -0.115 + (p.y + 0.115) * 0.15
        return p

    foot_bm = make_uv_sphere_bm(
        0.190, 0.148, 0.215,
        cx=fx, cy=fy, cz=fz,
        u_segs=28, v_segs=20,
        rot_euler=(0.0, 0.0, 0.0),
        deform_fn=foot_deform
    )
    append_bmesh_part(
        foot_bm, "DoveGrey",
        lambda x, y, z, fb=foot_bone, lb=leg_bone: {fb: 0.92, lb: 0.08}
    )

    fcleft_pts = []
    for k in range(9):
        t = k / 8.0
        cy = 0.03 + 0.14 * t
        cz = fz + 0.210 - 0.025 * (t - 0.4) ** 2
        fcleft_pts.append((fx, cy, cz))
    fcleft_bm = make_torus_tube_bm(fcleft_pts, 0.007, radial_segs=10, closed=False)
    append_bmesh_part(fcleft_bm, "InnerEarGrey", lambda x, y, z, fb=foot_bone: {fb: 1.0})


# ==============================================================================
# 4. CREATE BLENDER MESH OBJECT + SUBSURF MODIFIER
# ==============================================================================
mesh_data = bpy.data.meshes.new("BabaChops_Plush_MeshData")
for m in MAT_LIST:
    mesh_data.materials.append(m)

master_bm.to_mesh(mesh_data)
master_bm.free()
mesh_data.update()

mesh_obj = bpy.data.objects.new("BabaChops_Plush_Mesh", mesh_data)
main_col.objects.link(mesh_obj)

for bname in BONE_NAMES:
    mesh_obj.vertex_groups.new(name=bname)


# ==============================================================================
# 5. CREATE SKELETAL ARMATURE RIG (22 BONES) & BIND SKINNING
# ==============================================================================
arm_data = bpy.data.armatures.new("BabaChops_ArmatureData")
arm_data.display_type = 'OCTAHEDRAL'
arm_obj = bpy.data.objects.new("BabaChops_Armature", arm_data)
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


add_ebone("Root", (0.0, 0.0, 0.0), (0.0, 0.45, 0.0))
add_ebone("Pelvis", (0.0, 0.52, 0.0), (0.0, 0.82, 0.0), "Root", False)
add_ebone("Spine", (0.0, 0.82, 0.0), (0.0, 1.14, 0.0), "Pelvis", True)
add_ebone("Chest", (0.0, 1.14, 0.0), (0.0, 1.44, 0.0), "Spine", True)
add_ebone("Neck", (0.0, 1.44, 0.0), (0.0, 1.62, 0.0), "Chest", True)
add_ebone("Head", (0.0, 1.62, 0.0), (0.0, 2.45, 0.0), "Neck", True)

add_ebone("Jaw", (0.0, 1.68, 0.45), (0.0, 1.48, 0.72), "Head", False)
add_ebone("Eyelid.L", (0.255, 1.985, 0.600), (0.255, 2.12, 0.76), "Head", False)
add_ebone("Eyelid.R", (-0.255, 1.985, 0.600), (-0.255, 2.12, 0.76), "Head", False)
add_ebone("Ear.L", (0.65, 1.90, 0.04), (1.16, 1.88, 0.04), "Head", False)
add_ebone("Ear.R", (-0.65, 1.90, 0.04), (-1.16, 1.88, 0.04), "Head", False)

add_ebone("SkullPendant", (0.0, 1.28, 0.46), (0.0, 0.92, 0.50), "Chest", False)

add_ebone("Shoulder.L", (0.28, 1.34, 0.02), (0.44, 1.24, 0.03), "Chest", False)
add_ebone("Arm.L", (0.44, 1.24, 0.03), (0.72, 1.01, 0.06), "Shoulder.L", True)
add_ebone("HandHoof.L", (0.72, 1.01, 0.06), (0.93, 0.83, 0.09), "Arm.L", True)

add_ebone("Shoulder.R", (-0.28, 1.34, 0.02), (-0.44, 1.24, 0.03), "Chest", False)
add_ebone("Arm.R", (-0.44, 1.24, 0.03), (-0.72, 1.01, 0.06), "Shoulder.R", True)
add_ebone("HandHoof.R", (-0.72, 1.01, 0.06), (-0.93, 0.83, 0.09), "Arm.R", True)

add_ebone("Leg.L", (0.24, 0.66, 0.0), (0.30, 0.24, 0.02), "Pelvis", False)
add_ebone("FootHoof.L", (0.30, 0.24, 0.02), (0.31, 0.06, 0.22), "Leg.L", True)

add_ebone("Leg.R", (-0.24, 0.66, 0.0), (-0.30, 0.24, 0.02), "Pelvis", False)
add_ebone("FootHoof.R", (-0.30, 0.24, 0.02), (-0.31, 0.06, 0.22), "Leg.R", True)

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
# 6. AUTHOR 5 NLA / ACTION ANIMATION CLIPS ON THE ARMATURE
# ==============================================================================
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')

for pb in arm_obj.pose.bones:
    pb.rotation_mode = 'XYZ'


def reset_pose():
    for pb in arm_obj.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_euler = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)


def key_bone(action_frame, bone_name, rot=None, loc=None):
    pb = arm_obj.pose.bones[bone_name]
    if rot is not None:
        pb.rotation_euler = Euler(rot, 'XYZ')
        pb.keyframe_insert(data_path="rotation_euler", frame=action_frame)
    if loc is not None:
        pb.location = Vector(loc)
        pb.keyframe_insert(data_path="location", frame=action_frame)


def bake_action_to_nla(name, frame_end, keyframe_builder):
    if not arm_obj.animation_data:
        arm_obj.animation_data_create()
    act = bpy.data.actions.new(name=name)
    act.use_fake_user = True
    arm_obj.animation_data.action = act
    reset_pose()
    keyframe_builder(act)
    track = arm_obj.animation_data.nla_tracks.new()
    track.name = name
    strip = track.strips.new(name=name, start=1, action=act)
    strip.action_frame_start = 1
    strip.action_frame_end = frame_end
    track.mute = False
    arm_obj.animation_data.action = None
    reset_pose()


def build_idle_breathe(act):
    for f, ph in [(1, 0.0), (15, 0.5 * math.pi), (30, math.pi), (45, 1.5 * math.pi), (60, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        key_bone(f, "Pelvis", loc=(0.0, 0.0, 0.015 * s), rot=(0.02 * s, 0.0, 0.0))
        key_bone(f, "Chest", rot=(0.03 * s, 0.0, 0.015 * c))
        key_bone(f, "Head", rot=(0.035 * s, 0.04 * c, 0.025 * s))
        key_bone(f, "Ear.L", rot=(0.0, 0.0, 0.06 * s))
        key_bone(f, "Ear.R", rot=(0.0, 0.0, -0.06 * s))
        key_bone(f, "Arm.L", rot=(0.04 * s, 0.0, 0.05 * c))
        key_bone(f, "Arm.R", rot=(-0.04 * s, 0.0, -0.05 * c))
        key_bone(f, "SkullPendant", rot=(0.06 * c, 0.04 * s, 0.0))
        blink = 0.22 if f == 30 else 0.0
        key_bone(f, "Eyelid.L", rot=(blink, 0.0, 0.0))
        key_bone(f, "Eyelid.R", rot=(blink, 0.0, 0.0))


def build_walk_cycle(act):
    for f, ph in [(1, 0.0), (12, 0.5 * math.pi), (24, math.pi), (36, 1.5 * math.pi), (48, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        s2 = math.sin(2.0 * ph)
        key_bone(f, "Pelvis", loc=(0.03 * s, 0.045 * abs(s), 0.0), rot=(0.04 * s2, 0.10 * s, 0.06 * c))
        key_bone(f, "Chest", rot=(0.05 * s2, -0.08 * s, -0.05 * c))
        key_bone(f, "Head", rot=(-0.04 * s2, 0.06 * s, 0.05 * c))
        key_bone(f, "Leg.L", rot=(0.38 * s, 0.0, 0.0))
        key_bone(f, "Leg.R", rot=(-0.38 * s, 0.0, 0.0))
        key_bone(f, "FootHoof.L", rot=(-0.18 * c, 0.0, 0.0))
        key_bone(f, "FootHoof.R", rot=(0.18 * c, 0.0, 0.0))
        key_bone(f, "Arm.L", rot=(-0.28 * s, 0.0, 0.06 * c))
        key_bone(f, "Arm.R", rot=(0.28 * s, 0.0, -0.06 * c))
        key_bone(f, "Ear.L", rot=(0.05 * s2, 0.0, 0.10 * c))
        key_bone(f, "Ear.R", rot=(0.05 * s2, 0.0, -0.10 * c))
        key_bone(f, "SkullPendant", rot=(0.14 * s2, 0.12 * s, 0.0))


def build_happy_bounce(act):
    for f, ph in [(1, 0.0), (10, 0.5 * math.pi), (20, math.pi), (30, 1.5 * math.pi), (40, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        jump = max(0.0, s) * 0.12
        key_bone(f, "Pelvis", loc=(0.0, jump, 0.0), rot=(-0.06 * s, 0.0, 0.0))
        key_bone(f, "Chest", rot=(-0.08 * s, 0.0, 0.0))
        key_bone(f, "Head", rot=(-0.10 * s, 0.06 * c, 0.0))
        key_bone(f, "Ear.L", rot=(0.0, 0.0, 0.22 * s))
        key_bone(f, "Ear.R", rot=(0.0, 0.0, -0.22 * s))
        key_bone(f, "Arm.L", rot=(0.0, 0.0, 0.25 * s))
        key_bone(f, "Arm.R", rot=(0.0, 0.0, -0.25 * s))
        key_bone(f, "SkullPendant", rot=(0.22 * c, 0.0, 0.0))
        key_bone(f, "Jaw", rot=(0.10 * max(0.0, s), 0.0, 0.0))


def build_wave_hoof(act):
    for f, ph in [(1, 0.0), (15, 0.5 * math.pi), (30, math.pi), (45, 1.5 * math.pi), (60, 2.0 * math.pi)]:
        s = math.sin(ph)
        w = math.sin(3.0 * ph)
        lift = math.sin(0.5 * ph)
        key_bone(f, "Shoulder.R", rot=(0.0, 0.0, -0.45 * lift))
        key_bone(f, "Arm.R", rot=(-0.35 * lift, 0.20 * w * lift, -0.55 * lift))
        key_bone(f, "HandHoof.R", rot=(0.0, 0.0, 0.30 * w * lift))
        key_bone(f, "Head", rot=(0.04 * s, -0.12 * lift, 0.14 * lift))
        key_bone(f, "Ear.L", rot=(0.0, 0.0, 0.12 * lift))
        key_bone(f, "Ear.R", rot=(0.0, 0.0, -0.08 * lift))
        key_bone(f, "SkullPendant", rot=(0.08 * s, 0.08 * lift, 0.0))


def build_curious_tilt(act):
    for f, ph in [(1, 0.0), (15, 0.5 * math.pi), (30, math.pi), (45, 1.5 * math.pi), (60, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        talk = abs(math.sin(2.0 * ph))
        key_bone(f, "Head", rot=(0.06 * c, 0.18 * s, -0.16 * s))
        key_bone(f, "Jaw", rot=(0.14 * talk, 0.0, 0.0))
        key_bone(f, "Eyelid.L", rot=(0.12 * max(0.0, s), 0.0, 0.0))
        key_bone(f, "Eyelid.R", rot=(0.12 * max(0.0, -s), 0.0, 0.0))
        key_bone(f, "Ear.L", rot=(0.0, 0.0, -0.14 * s))
        key_bone(f, "Ear.R", rot=(0.0, 0.0, -0.14 * s))
        key_bone(f, "Chest", rot=(0.0, 0.06 * s, -0.04 * s))


bake_action_to_nla("Idle_Breathe", 60, build_idle_breathe)
bake_action_to_nla("Walk_Cycle", 48, build_walk_cycle)
bake_action_to_nla("Happy_Bounce", 40, build_happy_bounce)
bake_action_to_nla("Wave_Hoof", 60, build_wave_hoof)
bake_action_to_nla("Curious_Head_Tilt", 60, build_curious_tilt)

bpy.ops.object.mode_set(mode='OBJECT')
scene.frame_start = 1
scene.frame_end = 60
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

bpy.ops.wm.obj_export(
    filepath=OBJ_PATH,
    export_selected_objects=True,
    export_materials=True,
)


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
    sheen=0.0, bump_strength=0.0, emission_strength=0.18
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


add_area_light("Key_Softbox", (-2.4, -3.6, 3.2), (0.0, 0.0, 1.45), energy=220.0, size=3.0, color_rgb=(1.0, 0.99, 0.98))
add_area_light("Fill_Softbox", (2.6, -3.2, 2.4), (0.0, 0.0, 1.35), energy=150.0, size=3.4, color_rgb=(0.97, 0.98, 1.0))
add_area_light("Top_Softbox", (0.0, -0.8, 4.2), (0.0, 0.0, 1.65), energy=160.0, size=3.2, color_rgb=(1.0, 1.0, 1.0))
add_area_light("Rim_Backlight", (0.0, 3.0, 3.0), (0.0, 0.0, 1.50), energy=140.0, size=2.6, color_rgb=(0.98, 0.98, 1.0))

world = bpy.data.worlds.new("BabaStudioWorld")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = hex_to_rgba(0xF5F6F8)
    bg_node.inputs[1].default_value = 1.05

# Color management: High Contrast for deep plush blacks + crisp studio whites
for look_name in ('AgX - High Contrast', 'High Contrast'):
    try:
        scene.view_settings.look = look_name
        break
    except Exception:
        pass

cam_data = bpy.data.cameras.new("Studio_Camera")
cam_data.lens = 62.0
cam_obj = bpy.data.objects.new("Studio_Camera", cam_data)
studio_col.objects.link(cam_obj)
scene.camera = cam_obj


def aim_camera(loc, target=(0.0, 0.0, 1.34), lens=62.0):
    cam_data.lens = lens
    cam_obj.location = Vector(loc)
    direction = Vector(target) - Vector(loc)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


aim_camera((0.0, -5.85, 1.38), target=(0.0, 0.0, 1.32), lens=62.0)

# Save native .blend master file
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)

scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 64
scene.cycles.use_denoising = True
if hasattr(scene.cycles, "denoiser"):
    for d_opt in ('OPENIMAGEDENOISE', 'OPTIX'):
        try:
            scene.cycles.denoiser = d_opt
            break
        except Exception:
            pass

scene.render.resolution_x = 1080
scene.render.resolution_y = 1350
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

scene.render.filepath = RENDER_FRONT_PATH
bpy.ops.render.render(write_still=True)

scene.render.resolution_x = 800
scene.render.resolution_y = 1000
scene.cycles.samples = 40

aim_camera((-4.10, -4.20, 1.48), target=(0.0, 0.0, 1.32), lens=62.0)
scene.render.filepath = os.path.join(RENDER_SHEET_DIR, "cycles_3q.png")
bpy.ops.render.render(write_still=True)

aim_camera((-5.85, 0.0, 1.38), target=(0.0, 0.0, 1.32), lens=62.0)
scene.render.filepath = os.path.join(RENDER_SHEET_DIR, "cycles_side.png")
bpy.ops.render.render(write_still=True)

print("SUCCESS v3: Built .blend, .glb, .obj, and rendered high-contrast Cycles studio images!")
print(f"  BLEND: {BLEND_PATH} ({os.path.getsize(BLEND_PATH)} bytes)")
print(f"  GLB:   {GLB_PATH} ({os.path.getsize(GLB_PATH)} bytes)")
print(f"  FRONT: {RENDER_FRONT_PATH} ({os.path.getsize(RENDER_FRONT_PATH)} bytes)")
