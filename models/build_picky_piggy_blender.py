#!/usr/bin/env python3
"""
Native Blender 4.3 Builder, Rigging, Animation & Cycles Studio Renderer
for PickyPiggy (#025 Official Plush Base Model - Smiling Critters).

Run headless via:
  /tmp/blender/blender -b --factory-startup --threads 8 --python-exit-code 1 -P /tmp/smiling-critters-assets/models/build_picky_piggy_blender.py
"""

import os
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, noise

OUT_DIR = "/tmp/smiling-critters-assets/models"
ANIM_DIR = "/tmp/smiling-critters-assets/animations"
WORK_DIR = "/tmp/work_pickypiggy"
FART_FRAMES_DIR = os.path.join(WORK_DIR, "frames")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANIM_DIR, exist_ok=True)
os.makedirs(FART_FRAMES_DIR, exist_ok=True)

BLEND_PATH = os.path.join(OUT_DIR, "picky_piggy_plush_base_model.blend")
GLB_PATH = os.path.join(OUT_DIR, "picky_piggy_plush_base_model.glb")
OBJ_PATH = os.path.join(OUT_DIR, "picky_piggy_plush_base_model.obj")
RENDER_FRONT_PATH = os.path.join(OUT_DIR, "picky_piggy_blender_cycles_render.png")
RENDER_PREVIEW_PATH = os.path.join(OUT_DIR, "picky_piggy_3d_preview.png")


# ==============================================================================
# 1. SCENE RESET & HELPER UTILITIES
# ==============================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

main_col = bpy.data.collections.new("PickyPiggy_Plush_Rig")
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
    ny = (y_up - 1.94) / 0.68
    cheek_flare = math.exp(-((ny + 0.18) / 0.42) ** 2)
    rx_eff = 0.76 * (1.0 + 0.16 * cheek_flare - 0.14 * max(0.0, ny))
    nx = x / max(0.20, rx_eff)
    r2 = min(0.92, nx * nx + ny * ny)
    return 0.668 * math.sqrt(max(0.08, 1.0 - r2))


def fleece_displacement(p_world):
    """Subtle plush fleece surface displacement."""
    q1 = Vector((p_world.x * 8.0, p_world.y * 8.0, p_world.z * 8.0))
    q2 = Vector((p_world.x * 18.0 + 2.1, p_world.y * 18.0 - 1.3, p_world.z * 18.0 + 1.7))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    return 0.005 * n1 + 0.003 * n2


def cloud_displacement(p_world):
    """Multi-octave 3D cartoon cloud billow displacement."""
    q1 = Vector((p_world.x * 7.5, p_world.y * 7.5, p_world.z * 7.5))
    q2 = Vector((p_world.x * 16.0 + 3.1, p_world.y * 16.0 - 1.7, p_world.z * 16.0 + 2.3))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    return 0.032 * n1 + 0.018 * abs(n2)


# ==============================================================================
# 2. PROCEDURAL CYCLES / GLTF PBR MATERIALS (PICKYPIGGY PALETTE + FART CLOUD)
# ==============================================================================
def create_plush_material(name, hex_color, roughness=0.84, spec_ior=0.14,
                          sheen=0.32, sheen_tint_mult=1.05,
                          bump_scale=65.0, bump_strength=0.12,
                          metallic=0.0, coat=0.0, coat_rough=0.05,
                          subsurface=0.02, emission_strength=0.0):
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
    set_bsdf_input(bsdf, 0.75, "Sheen Roughness")
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
        noise_node.inputs["Roughness"].default_value = 0.72

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
    # Bubblegum-pink plush fleece pig body (#EC5B98 calibrated for studio softboxes)
    "BodyPink": create_plush_material(
        "Picky_Bubblegum_Pink_Plush", 0xE0488A, roughness=0.84, spec_ior=0.12,
        sheen=0.32, sheen_tint_mult=1.05, bump_scale=72.0, bump_strength=0.16, subsurface=0.01
    ),
    # Soft pastel-pink belly & inner ear highlight (#FBCFE8 calibrated for studio softboxes)
    "BellyPastelPink": create_plush_material(
        "Picky_Pastel_Pink_Belly", 0xF5B2D4, roughness=0.86, spec_ior=0.10,
        sheen=0.28, sheen_tint_mult=1.04, bump_scale=78.0, bump_strength=0.12, subsurface=0.01
    ),
    # Darker magenta-rose cloven hooves & inner ear cup (#C2185B)
    "HoofMagenta": create_plush_material(
        "Picky_Hoof_Magenta_Rose", 0xA80E4F, roughness=0.78, spec_ior=0.14,
        sheen=0.30, sheen_tint_mult=1.05, bump_scale=82.0, bump_strength=0.14, subsurface=0.01
    ),
    # Rich medium-magenta pig snout velour
    "SnoutRose": create_plush_material(
        "Picky_Snout_Rose_Velour", 0xD41C68, roughness=0.76, spec_ior=0.16,
        sheen=0.32, sheen_tint_mult=1.05, bump_scale=88.0, bump_strength=0.10, subsurface=0.01
    ),
    # Deep crimson-burgundy nostril & cloven seam indent
    "NostrilDark": create_plush_material(
        "Picky_Nostril_Dark_Crimson", 0x3A031A, roughness=0.90, spec_ior=0.06,
        sheen=0.10, bump_scale=90.0, bump_strength=0.10, subsurface=0.0
    ),
    # Shiny Red Apple Pendant (#D5001C deep candy-apple red)
    "AppleRed": create_plush_material(
        "Picky_Apple_Pendant_Red", 0xB80012, roughness=0.20, spec_ior=0.45,
        sheen=0.12, bump_scale=110.0, bump_strength=0.02, metallic=0.10, coat=0.60, coat_rough=0.04,
        subsurface=0.0, emission_strength=0.0
    ),
    # Vibrant Green Apple Leaf (#38E54D)
    "AppleLeafGreen": create_plush_material(
        "Picky_Apple_Leaf_Green", 0x1FB832, roughness=0.26, spec_ior=0.35,
        sheen=0.15, bump_scale=100.0, bump_strength=0.02, coat=0.40,
        subsurface=0.0, emission_strength=0.0
    ),
    # Warm Brown Apple Stem (#6D3B1A)
    "AppleStemBrown": create_plush_material(
        "Picky_Apple_Stem_Brown", 0x5A2D10, roughness=0.58, spec_ior=0.20,
        sheen=0.12, bump_scale=95.0, bump_strength=0.06, subsurface=0.0
    ),
    # Coral-pink plush tongue (#FF6B8B)
    "TongueCoral": create_plush_material(
        "Picky_Tongue_Coral_Pink", 0xF04870, roughness=0.78, spec_ior=0.14,
        sheen=0.25, bump_scale=85.0, bump_strength=0.08, subsurface=0.01
    ),
    # Deep jet-black glossy acrylic dome eyes
    "EyeGloss": create_plush_material(
        "Picky_Eye_Acrylic_Black", 0x020203, roughness=0.04, spec_ior=0.12,
        sheen=0.0, bump_strength=0.0, coat=0.32, coat_rough=0.015
    ),
    # Studio catchlight highlight on eyes
    "CatchlightWhite": create_plush_material(
        "Picky_Eye_Catchlight_White", 0xFFFFFF, roughness=0.05, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, emission_strength=0.35
    ),
    # Pitch-black recessed mouth cavity
    "MouthVoidBlack": create_plush_material(
        "Picky_Mouth_Cavity_Black", 0x020204, roughness=0.98, spec_ior=0.02,
        sheen=0.0, bump_strength=0.0
    ),
    # Brushed silver zipper hardware
    "ZipperMetal": create_plush_material(
        "Picky_Zipper_Silver_Metal", 0xD8DDE6, roughness=0.22, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, metallic=0.92, coat=0.25
    ),
    # Black collar zipper tape & apple border rim
    "ZipperTrack": create_plush_material(
        "Picky_Zipper_Track_Black", 0x101115, roughness=0.84, spec_ior=0.08,
        sheen=0.10, bump_strength=0.05
    ),
    # 3D Cartoon Fart Cloud Materials (Vibrant Toxic Lime, Neon Blast Core, Lavender Swirl)
    "FartCloudLime": create_plush_material(
        "Picky_Fart_Cloud_Lime", 0x4CE629, roughness=0.68, spec_ior=0.18,
        sheen=0.45, sheen_tint_mult=1.15, bump_scale=24.0, bump_strength=0.22,
        subsurface=0.35, emission_strength=0.28
    ),
    "FartCloudNeon": create_plush_material(
        "Picky_Fart_Cloud_Neon_YellowGreen", 0xC4FF33, roughness=0.45, spec_ior=0.25,
        sheen=0.35, sheen_tint_mult=1.1, bump_scale=30.0, bump_strength=0.14,
        subsurface=0.25, emission_strength=0.55
    ),
    "FartCloudPurple": create_plush_material(
        "Picky_Fart_Cloud_Purple", 0x9D4EDD, roughness=0.62, spec_ior=0.20,
        sheen=0.40, sheen_tint_mult=1.1, bump_scale=28.0, bump_strength=0.18,
        subsurface=0.25, emission_strength=0.32
    ),
}


# ==============================================================================
# 3. PICKYPIGGY GEOMETRY BUILDER (BMESH + SKIN WEIGHTS)
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
    "FartCloud.1",
    "FartCloud.2",
    "FartCloud.3",
]
BONE_IDX = {name: i for i, name in enumerate(BONE_NAMES)}

MAT_KEYS = [
    "BodyPink",
    "BellyPastelPink",
    "HoofMagenta",
    "SnoutRose",
    "NostrilDark",
    "AppleRed",
    "AppleLeafGreen",
    "AppleStemBrown",
    "TongueCoral",
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


def make_torus_tube_bm(curve_pts, radius_fn, radial_segs=16, closed=False):
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
# 3.1 BUBBLEGUM-PINK PLUSH PIG HEAD (WIDE SMILING CHEEKS + ROUNDED CRANIUM)
# ------------------------------------------------------------------------------
def pig_head_deform(p):
    # p is initially scaled by (0.76, 0.68, 0.65) around (0, 1.94, 0)
    ny = p.y / 0.68
    # Flare out the lower cheeks around the wide Smiling Critters grin (ny in [-0.65, +0.10])
    cheek_flare = math.exp(-((ny + 0.18) / 0.42) ** 2)
    p.x *= (1.0 + 0.16 * cheek_flare - 0.14 * max(0.0, ny))
    # Subtle recess in the front mouth zone so the wide black smiling cavity is never occluded
    if p.z > 0.25 and abs(p.x) < 0.54 and -0.54 < p.y < -0.12:
        p.z -= 0.042
    # Subtle plush center seam indentation on forehead
    if p.z > 0.20 and p.y > 0.05 and abs(p.x) < 0.035:
        p.z -= 0.008 * (1.0 - abs(p.x) / 0.035)
    return p


head_core_bm = make_uv_sphere_bm(
    0.76, 0.68, 0.65, cx=0.0, cy=1.94, cz=0.0,
    u_segs=32, v_segs=24,
    deform_fn=pig_head_deform,
    world_deform_fn=lambda p_w, n_w: p_w + n_w * fleece_displacement(p_w)
)
append_bmesh_part(
    head_core_bm, "BodyPink",
    lambda x, y, z: {"Jaw": max(0.0, min(0.35, (1.62 - y) * 1.2)),
                     "Head": 1.0 - max(0.0, min(0.35, (1.62 - y) * 1.2))}
)


# ------------------------------------------------------------------------------
# 3.2 FLOPPY FORWARD-FOLDED PIG EARS (Ear.L / Ear.R, #EC5B98 + #C2185B INNER)
# ------------------------------------------------------------------------------
for side in (-1, 1):
    ear_bone = "Ear.L" if side == 1 else "Ear.R"

    def pig_ear_outer_deform(p, s=side):
        # Local sphere: rx=0.28, ry=0.22, rz=0.095
        # Taper base and point tip, plus fold tip forward (+Z) and slightly down (-Y)
        u = (s * p.x + 0.28) / 0.56  # 0 at root, 1 at outer tip
        u = max(0.0, min(1.0, u))
        width_profile = math.sin(math.pi * (0.12 + 0.82 * u)) * (1.18 - 0.35 * u)
        p.y *= width_profile
        # Forward flop & upper arch of pig ear
        p.y += 0.08 * math.sin(math.pi * u) - 0.05 * (u ** 2)
        p.z += 0.11 * (u ** 1.6)
        # Cup indentation on front face
        if p.z > 0.0:
            cup = max(0.0, 1.0 - (p.x / 0.22) ** 2 - (p.y / 0.15) ** 2)
            p.z -= 0.035 * cup
        return p

    ear_out_bm = make_uv_sphere_bm(
        0.28, 0.21, 0.090,
        cx=side * 0.58, cy=2.44, cz=0.08,
        u_segs=32, v_segs=24,
        rot_euler=(0.18, -side * 0.16, side * 0.36),
        deform_fn=pig_ear_outer_deform
    )
    append_bmesh_part(
        ear_out_bm, "BodyPink",
        lambda x, y, z, b=ear_bone: {b: 0.90, "Head": 0.10}
    )

    def pig_ear_inner_deform(p, s=side):
        u = (s * p.x + 0.21) / 0.42
        u = max(0.0, min(1.0, u))
        p.y *= math.sin(math.pi * (0.14 + 0.80 * u)) * (1.12 - 0.32 * u)
        p.y += 0.06 * math.sin(math.pi * u) - 0.04 * (u ** 2)
        p.z += 0.09 * (u ** 1.6)
        return p

    ear_in_bm = make_uv_sphere_bm(
        0.21, 0.145, 0.042,
        cx=side * 0.59, cy=2.425, cz=0.125,
        u_segs=26, v_segs=18,
        rot_euler=(0.18, -side * 0.16, side * 0.36),
        deform_fn=pig_ear_inner_deform
    )
    append_bmesh_part(
        ear_in_bm, "HoofMagenta",
        lambda x, y, z, b=ear_bone: {b: 0.92, "Head": 0.08}
    )

    # Subtle pastel-pink inner ear rim accent
    ear_rim_bm = make_uv_sphere_bm(
        0.23, 0.16, 0.035,
        cx=side * 0.585, cy=2.43, cz=0.112,
        u_segs=24, v_segs=16,
        rot_euler=(0.18, -side * 0.16, side * 0.36),
        deform_fn=pig_ear_inner_deform
    )
    append_bmesh_part(
        ear_rim_bm, "BellyPastelPink",
        lambda x, y, z, b=ear_bone: {b: 0.91, "Head": 0.09}
    )


# ------------------------------------------------------------------------------
# 3.3 GLOSSY BLACK DOME EYES, CATCHLIGHTS, EYELID RIMS & ARCHED EYEBROWS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    lid_bone = "Eyelid.L" if side == 1 else "Eyelid.R"
    ex = side * 0.235
    ey = 2.055
    ez = 0.565

    # Plush eye socket ring
    sock_bm = make_uv_sphere_bm(
        0.182, 0.182, 0.115,
        cx=ex, cy=ey, cz=ez - 0.015,
        u_segs=28, v_segs=20,
        rot_euler=(-0.06, side * 0.16, 0.0)
    )
    append_bmesh_part(sock_bm, "BodyPink", lambda x, y, z: {"Head": 1.0})

    # Large glossy black acrylic dome eye (025_PickyPiggy_Plushie.webp)
    eye_bm = make_uv_sphere_bm(
        0.168, 0.168, 0.128,
        cx=ex, cy=ey, cz=ez,
        u_segs=32, v_segs=24,
        rot_euler=(-0.06, side * 0.16, 0.0)
    )
    append_bmesh_part(eye_bm, "EyeGloss", lambda x, y, z: {"Head": 1.0})

    # Primary studio softbox catchlight
    hi1_bm = make_uv_sphere_bm(
        0.036, 0.048, 0.014,
        cx=ex - side * 0.042, cy=ey + 0.042, cz=ez + 0.116,
        u_segs=14, v_segs=12,
        rot_euler=(-0.10, side * 0.14, 0.0)
    )
    append_bmesh_part(hi1_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Secondary lower catchlight dot
    hi2_bm = make_uv_sphere_bm(
        0.018, 0.020, 0.010,
        cx=ex + side * 0.045, cy=ey - 0.045, cz=ez + 0.114,
        u_segs=12, v_segs=10,
        rot_euler=(0.05, side * 0.14, 0.0)
    )
    append_bmesh_part(hi2_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Upper plush eyelid rim (weighted to Eyelid.L/R for blinking & fart-strain squinting)
    lid_rim_pts = []
    rot_lid = Euler((-0.06, side * 0.16, -side * 0.08), 'XYZ').to_matrix()
    for k in range(17):
        t = -1.0 + 2.0 * k / 16.0
        lx = t * 0.172
        ly = 0.125 * math.cos(t * math.pi * 0.48) + 0.035
        lz = math.sqrt(max(0.02, 1.0 - t * t)) * 0.126
        v_world = (rot_lid @ Vector((lx, ly, lz))) + Vector((ex, ey, ez))
        lid_rim_pts.append((v_world.x, v_world.y, v_world.z))
    lid_rim_bm = make_torus_tube_bm(
        lid_rim_pts,
        lambda t: 0.024 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=12, closed=False
    )
    append_bmesh_part(
        lid_rim_bm, "BodyPink",
        lambda x, y, z, b=lid_bone: {b: 0.92, "Head": 0.08}
    )

    # Expressive arched cartoon eyebrow on upper forehead
    brow_pts = []
    for k in range(13):
        t = k / 12.0
        bx = side * (0.10 + 0.24 * t)
        by = 2.31 + 0.065 * math.sin(math.pi * t) - 0.02 * t
        bz = head_front_z(bx, by) + 0.015
        brow_pts.append((bx, by, bz))
    brow_bm = make_torus_tube_bm(
        brow_pts,
        lambda t: 0.016 * math.sin(math.pi * (0.10 + 0.80 * t)),
        radial_segs=10, closed=False
    )
    append_bmesh_part(
        brow_bm, "ZipperTrack",
        lambda x, y, z, b=lid_bone: {b: 0.50, "Head": 0.50}
    )


# ------------------------------------------------------------------------------
# 3.4 PROMINENT OVAL PIG SNOUT (#E02874) WITH TWO DARK OVAL NOSTRILS (#C2185B)
# ------------------------------------------------------------------------------
def pig_snout_deform(p):
    # Flatten front face of snout into a plump pig snout disk with rounded rim
    if p.z > 0.05:
        p.z = 0.05 + (p.z - 0.05) * 0.55
    # Slightly wider bottom than top
    p.x *= (1.0 - 0.08 * (p.y / 0.135))
    return p


snout_bm = make_uv_sphere_bm(
    0.215, 0.138, 0.155,
    cx=0.0, cy=1.875, cz=0.635,
    u_segs=32, v_segs=22,
    rot_euler=(-0.08, 0.0, 0.0),
    deform_fn=pig_snout_deform
)
append_bmesh_part(snout_bm, "SnoutRose", lambda x, y, z: {"Head": 0.92, "Jaw": 0.08})

for side in (-1, 1):
    # Outer nostril rim in deeper magenta (#C2185B)
    nos_rim_bm = make_uv_sphere_bm(
        0.042, 0.058, 0.024,
        cx=side * 0.076, cy=1.872, cz=0.742,
        u_segs=18, v_segs=14,
        rot_euler=(-0.08, side * 0.10, -side * 0.12)
    )
    append_bmesh_part(nos_rim_bm, "HoofMagenta", lambda x, y, z: {"Head": 1.0})

    # Deep recessed oval pig nostril center (#6A0B31)
    nos_hole_bm = make_uv_sphere_bm(
        0.028, 0.044, 0.022,
        cx=side * 0.076, cy=1.872, cz=0.752,
        u_segs=16, v_segs=12,
        rot_euler=(-0.08, side * 0.10, -side * 0.12)
    )
    append_bmesh_part(nos_hole_bm, "NostrilDark", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.5 WIDE CHEERFUL SMILING MOUTH CAVITY, LIPS, CORAL TONGUE & SCENT DISC
# ------------------------------------------------------------------------------
def build_conformed_mouth_cavity_bm():
    bm = bmesh.new()
    u_steps = 40
    v_steps = 18
    grid = []
    for iv in range(v_steps + 1):
        v_frac = iv / v_steps
        ring = []
        for iu in range(u_steps):
            ang = 2.0 * math.pi * iu / u_steps
            ux = math.cos(ang) * 0.56 * v_frac
            raw_y = math.sin(ang)
            if raw_y >= 0:
                uy = 1.77 + raw_y * 0.05 * v_frac + 0.14 * (ux / 0.56) ** 2
            else:
                uy = 1.77 + raw_y * 0.38 * v_frac + 0.10 * (ux / 0.56) ** 2
            uz = head_front_z(ux, uy) + 0.006 * (1.0 - 0.25 * v_frac)
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
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.75 - y) * 2.8)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.75 - y) * 2.8))}
)

# Coral-pink plush tongue at the bottom of the cheerful grin
tongue_bm = make_uv_sphere_bm(
    0.19, 0.058, 0.075,
    cx=0.0, cy=1.455, cz=head_front_z(0.0, 1.455) + 0.012,
    u_segs=24, v_segs=16,
    rot_euler=(0.18, 0.0, 0.0)
)
append_bmesh_part(tongue_bm, "TongueCoral", lambda x, y, z: {"Jaw": 0.90, "Head": 0.10})

# Subtle plush speaker/scent button disc inside mouth cavity (from 025_PickyPiggy_Plushie.webp)
disc_bm = make_uv_sphere_bm(
    0.110, 0.110, 0.022,
    cx=0.0, cy=1.635, cz=head_front_z(0.0, 1.635) + 0.010,
    u_segs=22, v_segs=14
)
append_bmesh_part(disc_bm, "ZipperTrack", lambda x, y, z: {"Head": 0.70, "Jaw": 0.30})

upper_lip_pts = []
for k in range(37):
    t = -1.0 + 2.0 * k / 36.0
    lx = t * 0.57
    ly = 1.775 + 0.155 * (t * t) - 0.020 * (t ** 4)
    lz = head_front_z(lx, ly) + 0.028 * (1.0 - 0.35 * t * t)
    upper_lip_pts.append((lx, ly, lz))

upper_lip_bm = make_torus_tube_bm(
    upper_lip_pts,
    lambda t: 0.044 + 0.014 * math.sin(math.pi * t),
    radial_segs=16, closed=False
)
append_bmesh_part(upper_lip_bm, "BodyPink", lambda x, y, z: {"Head": 0.88, "Jaw": 0.12})

lower_lip_pts = []
for k in range(41):
    t = -1.0 + 2.0 * k / 40.0
    lx = t * 0.57
    ly = 1.390 + 0.520 * (t ** 2)
    lz = head_front_z(lx, ly) + 0.022 * (1.0 - 0.35 * t * t)
    lower_lip_pts.append((lx, ly, lz))

lower_lip_bm = make_torus_tube_bm(
    lower_lip_pts,
    lambda t: 0.038 + 0.012 * math.sin(math.pi * t),
    radial_segs=16, closed=False
)
append_bmesh_part(
    lower_lip_bm, "BodyPink",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.75 - y) * 2.6)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.75 - y) * 2.6))}
)

for side in (-1, 1):
    cheek_pts = []
    for k in range(11):
        t = k / 10.0
        cx = side * (0.53 + 0.05 * math.sin(math.pi * t))
        cy = 1.82 + 0.16 * (1.0 - t)
        cz = head_front_z(cx, cy) + 0.022
        cheek_pts.append((cx, cy, cz))
    cheek_bm = make_torus_tube_bm(cheek_pts, 0.038, radial_segs=12, closed=False)
    append_bmesh_part(cheek_bm, "BodyPink", lambda x, y, z: {"Head": 0.90, "Jaw": 0.10})


# ------------------------------------------------------------------------------
# 3.6 PLUMP PIG TORSO, PASTEL BELLY, BLACK ZIPPER & SHINY RED APPLE PENDANT
# ------------------------------------------------------------------------------
def build_torso_bm():
    bm = bmesh.new()
    u_segs = 32
    profile = [
        (0.00, 0.50), (0.20, 0.51), (0.38, 0.56), (0.49, 0.65),
        (0.54, 0.78), (0.55, 0.92), (0.51, 1.06), (0.46, 1.20),
        (0.40, 1.32), (0.33, 1.42), (0.26, 1.48), (0.00, 1.50)
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
                vz = math.sin(ang) * r_rad * 0.90
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
        t = max(0.0, min(1.0, (y - 0.50) / 0.28))
        return {"Pelvis": 1.0 - 0.5 * t, "Spine": 0.5 * t}
    elif y < 1.12:
        t = (y - 0.78) / 0.34
        return {"Pelvis": max(0.0, 0.5 - t), "Spine": 1.0 - abs(t - 0.5), "Chest": max(0.0, t - 0.3)}
    elif y < 1.38:
        t = (y - 1.12) / 0.26
        return {"Spine": max(0.0, 0.5 * (1.0 - t)), "Chest": 1.0 - 0.3 * t, "Neck": 0.3 * t}
    else:
        return {"Chest": 0.4, "Neck": 0.6}


torso_bm = build_torso_bm()
append_bmesh_part(torso_bm, "BodyPink", torso_weights)


def torso_front_z(y):
    t = max(0.0, min(1.0, (y - 0.54) / (1.42 - 0.54)))
    r = 0.38 + 0.17 * math.sin(math.pi * (t ** 0.72)) - 0.08 * t
    return r * 0.90


# Soft pastel-pink belly patch (#FBCFE8) conformed to front lower torso behind zipper track
belly_bm = make_uv_sphere_bm(
    0.31, 0.30, 0.08,
    cx=0.0, cy=0.88, cz=torso_front_z(0.88) - 0.072,
    u_segs=28, v_segs=20
)
append_bmesh_part(belly_bm, "BellyPastelPink", torso_weights)

# Black Collar-to-Belly Zipper Track & Teeth
zip_pts = [(0.0, 0.55 + (1.40 - 0.55) * k / 24.0, torso_front_z(0.55 + (1.40 - 0.55) * k / 24.0) + 0.016)
           for k in range(25)]
zip_track_bm = make_torus_tube_bm(zip_pts, 0.028, radial_segs=10, closed=False)
append_bmesh_part(zip_track_bm, "ZipperTrack", torso_weights)

for i in range(32):
    zy = 0.57 + (1.38 - 0.57) * (i / 31.0)
    zz = torso_front_z(zy) + 0.028
    zx = (0.009 if (i % 2 == 0) else -0.009)
    t_bm = make_beveled_box_bm(0.032, 0.012, 0.018, zx, zy, zz)
    append_bmesh_part(t_bm, "ZipperMetal", torso_weights)

slider_bm = make_beveled_box_bm(0.062, 0.075, 0.042, 0.0, 1.32, 0.455)
append_bmesh_part(slider_bm, "ZipperMetal", lambda x, y, z: {"Chest": 0.7, "SkullPendant": 0.3})

# Iconic Shiny Red Apple with Green Leaf & Brown Stem Pendant (weighted to SkullPendant)
def apple_body_deform(p, is_border=False):
    # Classic bilobed heart-apple silhouette (wider top lobes, indented top & bottom clefts)
    ny = p.y / 0.185
    nx = p.x / 0.215
    cleft_env = math.exp(-((nx / 0.36) ** 2))
    if ny > 0.25:
        p.y -= 0.052 * cleft_env * ((ny - 0.25) / 0.75) ** 1.4
    elif ny < -0.35:
        p.y += 0.032 * cleft_env * ((-ny - 0.35) / 0.65) ** 1.4
    # Taper lower half slightly and flare upper lobes
    p.x *= (1.0 + 0.14 * ny - 0.08 * (ny * ny))
    return p

# Black embroidered border backing around the apple charm (matches 025_PickyPiggy_Plushie.webp)
apple_border_bm = make_uv_sphere_bm(
    0.228, 0.198, 0.042,
    cx=0.0, cy=1.065, cz=0.488,
    u_segs=32, v_segs=24,
    rot_euler=(-0.05, 0.0, 0.0),
    deform_fn=apple_body_deform
)
append_bmesh_part(apple_border_bm, "ZipperTrack", lambda x, y, z: {"SkullPendant": 1.0})

# Glossy crimson-red apple body
apple_red_bm = make_uv_sphere_bm(
    0.206, 0.178, 0.052,
    cx=0.0, cy=1.065, cz=0.500,
    u_segs=32, v_segs=24,
    rot_euler=(-0.05, 0.0, 0.0),
    deform_fn=apple_body_deform
)
append_bmesh_part(apple_red_bm, "AppleRed", lambda x, y, z: {"SkullPendant": 1.0})

# Curved Brown Apple Stem rising from top cleft
stem_pts = [
    (0.00, 1.205, 0.502),
    (-0.008, 1.255, 0.504),
    (-0.022, 1.305, 0.506),
    (-0.038, 1.345, 0.508),
]
stem_bm = make_torus_tube_bm(
    stem_pts,
    lambda t: 0.018 + 0.008 * t,
    radial_segs=12, closed=False
)
append_bmesh_part(stem_bm, "AppleStemBrown", lambda x, y, z: {"SkullPendant": 1.0})

# Vibrant Green Apple Leaf sprouting to the upper-right of the stem
leaf_bm = make_uv_sphere_bm(
    0.072, 0.034, 0.022,
    cx=0.068, cy=1.268, cz=0.508,
    u_segs=20, v_segs=14,
    rot_euler=(-0.05, 0.0, 0.42),
    deform_fn=lambda p: Vector((p.x, p.y * (1.0 - 0.5 * (p.x / 0.072) ** 2), p.z))
)
append_bmesh_part(leaf_bm, "AppleLeafGreen", lambda x, y, z: {"SkullPendant": 1.0})


# ------------------------------------------------------------------------------
# 3.7 CURLY PINK PIG TAIL (2.5-TURN SPRINGY HELIX ON REAR PELVIS)
# ------------------------------------------------------------------------------
tail_pts = []
for k in range(45):
    t = k / 44.0
    ang = t * 2.4 * 2.0 * math.pi
    loop_r = 0.095 * math.sin(math.pi * (0.12 + 0.78 * t))
    tx = loop_r * math.cos(ang)
    ty = 0.68 + 0.34 * t + loop_r * math.sin(ang) * 0.65
    tz = -0.42 - 0.36 * (t ** 0.85) + 0.04 * math.sin(ang)
    tail_pts.append((tx, ty, tz))

tail_bm = make_torus_tube_bm(
    tail_pts,
    lambda t: 0.036 * (1.0 - 0.55 * (t ** 1.4)),
    radial_segs=12, closed=False
)
append_bmesh_part(tail_bm, "BodyPink", lambda x, y, z: {"Pelvis": 0.85, "Spine": 0.15})


# ------------------------------------------------------------------------------
# 3.8 SPLAYED BUBBLEGUM-PINK ARMS & MAGENTA-ROSE CLOVEN HAND HOOVES
# ------------------------------------------------------------------------------
for side in (-1, 1):
    sh_bone = "Shoulder.L" if side == 1 else "Shoulder.R"
    arm_bone = "Arm.L" if side == 1 else "Arm.R"
    hoof_bone = "HandHoof.L" if side == 1 else "HandHoof.R"

    arm_pts = []
    for k in range(13):
        t = k / 12.0
        ax = side * (0.31 + 0.38 * t)
        ay = 1.32 - 0.34 * t + 0.02 * math.sin(math.pi * t)
        az = 0.02 + 0.04 * t
        arm_pts.append((ax, ay, az))

    arm_bm = make_torus_tube_bm(
        arm_pts,
        lambda t: 0.138 * (1.0 + 0.06 * t),
        radial_segs=20, closed=False
    )

    def arm_weight_fn(x, y, z, sb=sh_bone, ab=arm_bone, hb=hoof_bone):
        dist = max(0.0, min(1.0, (abs(x) - 0.31) / 0.44))
        if dist < 0.35:
            return {"Chest": 0.35 * (1.0 - dist / 0.35), sb: 0.65, ab: 0.35 * (dist / 0.35)}
        elif dist < 0.85:
            return {ab: 0.85, sb: 0.15}
        else:
            return {ab: 0.50, hb: 0.50}

    append_bmesh_part(arm_bm, "BodyPink", arm_weight_fn)

    mitten_pts = []
    for k in range(13):
        t = k / 12.0
        mx = side * (0.66 + 0.24 * t)
        my = 1.00 - 0.22 * t
        mz = 0.06 + 0.03 * t
        mitten_pts.append((mx, my, mz))

    def mitten_radius(t):
        if t < 0.15:
            return 0.145 + 0.015 * (t / 0.15)
        elif t < 0.72:
            return 0.160 + 0.008 * math.sin(math.pi * (t - 0.15) / 0.57)
        else:
            u = (t - 0.72) / 0.28
            return 0.160 * math.sqrt(max(0.02, 1.0 - u * u))

    mitten_bm = make_torus_tube_bm(mitten_pts, mitten_radius, radial_segs=20, closed=False)
    append_bmesh_part(
        mitten_bm, "HoofMagenta",
        lambda x, y, z, hb=hoof_bone, ab=arm_bone: {hb: 0.90, ab: 0.10}
    )

    # Cloven pig hoof cleft seam line
    cleft_pts = []
    for k in range(9):
        t = k / 8.0
        cx = side * (0.78 + 0.11 * t)
        cy = 0.89 - 0.10 * t
        cz = 0.085 + 0.140 * math.sin(math.pi * (0.12 + 0.72 * t))
        cleft_pts.append((cx, cy, cz))
    cleft_bm = make_torus_tube_bm(cleft_pts, 0.009, radial_segs=8, closed=False)
    append_bmesh_part(cleft_bm, "NostrilDark", lambda x, y, z, hb=hoof_bone: {hb: 1.0})


# ------------------------------------------------------------------------------
# 3.9 STOUT PIG LEGS & ROUNDED MAGENTA-ROSE CLOVEN FOOT HOOVES
# ------------------------------------------------------------------------------
for side in (-1, 1):
    leg_bone = "Leg.L" if side == 1 else "Leg.R"
    foot_bone = "FootHoof.L" if side == 1 else "FootHoof.R"

    leg_pts = []
    for k in range(13):
        t = k / 12.0
        lx = side * (0.24 + 0.06 * t)
        ly = 0.65 - 0.42 * t
        lz = 0.0 + 0.03 * t
        leg_pts.append((lx, ly, lz))

    leg_bm = make_torus_tube_bm(
        leg_pts,
        lambda t: 0.185 * (1.0 - 0.04 * t),
        radial_segs=20, closed=False
    )

    def leg_weight_fn(x, y, z, lb=leg_bone, fb=foot_bone):
        if y > 0.50:
            return {"Pelvis": 0.45, lb: 0.55}
        elif y > 0.25:
            return {lb: 0.90, fb: 0.10}
        else:
            return {lb: 0.25, fb: 0.75}

    append_bmesh_part(leg_bm, "BodyPink", leg_weight_fn)

    fx = side * 0.310
    fy = 0.145
    fz = 0.075

    def foot_deform(p):
        if p.y < -0.02:
            p.y = -0.120 + (p.y + 0.120) * 0.18
        return p

    foot_bm = make_uv_sphere_bm(
        0.205, 0.158, 0.225,
        cx=fx, cy=fy, cz=fz,
        u_segs=26, v_segs=18,
        rot_euler=(0.0, 0.0, 0.0),
        deform_fn=foot_deform
    )
    append_bmesh_part(
        foot_bm, "HoofMagenta",
        lambda x, y, z, fb=foot_bone, lb=leg_bone: {fb: 0.92, lb: 0.08}
    )

    # Cloven vertical cleft groove on front of pig foot hoof
    fcleft_pts = []
    for k in range(9):
        t = k / 8.0
        cy = 0.03 + 0.16 * t
        cz = fz + 0.220 - 0.028 * (t - 0.4) ** 2
        fcleft_pts.append((fx, cy, cz))
    fcleft_bm = make_torus_tube_bm(fcleft_pts, 0.009, radial_segs=8, closed=False)
    append_bmesh_part(fcleft_bm, "NostrilDark", lambda x, y, z, fb=foot_bone: {fb: 1.0})

    # Horizontal plush seam groove around lower foot pad (matches 025_PickyPiggy_Plushie.webp)
    sole_seam_pts = []
    for k in range(20):
        ang = 2.0 * math.pi * k / 20.0
        sole_seam_pts.append((
            fx + 0.202 * math.cos(ang),
            0.095,
            fz + 0.222 * math.sin(ang)
        ))
    sole_seam_bm = make_torus_tube_bm(sole_seam_pts, 0.007, radial_segs=8, closed=True)
    append_bmesh_part(sole_seam_bm, "NostrilDark", lambda x, y, z, fb=foot_bone: {fb: 1.0})


# ------------------------------------------------------------------------------
# 3.10 3D SCULPTED CARTOON FART CLOUD CLUSTER (WEIGHTED TO FartCloud.1 / .2 / .3)
# ------------------------------------------------------------------------------
# Stage 1 (`FartCloud.1`): Nozzle Blast Jet + 3D Shockwave Ring right behind Pelvis
fart_stage1_puffs = [
    (0.00, 0.68, -0.50, 0.12, 0.11, 0.14, "FartCloudNeon"),
    (0.00, 0.69, -0.64, 0.18, 0.16, 0.18, "FartCloudLime"),
    (-0.10, 0.72, -0.68, 0.14, 0.13, 0.14, "FartCloudLime"),
    (0.10, 0.66, -0.68, 0.14, 0.13, 0.14, "FartCloudLime"),
]
for idx, (fx, fy, fz, rx, ry, rz, mkey) in enumerate(fart_stage1_puffs):
    def fc1_disp(p_w, n_w, s=idx):
        return p_w + n_w * (cloud_displacement(p_w + Vector((s * 1.1, 0.0, s * 0.7))) * 0.85)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=20, v_segs=14, world_deform_fn=fc1_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.1": 1.0})

# 3D Shockwave Torus Ring around the nozzle blast (`FartCloud.1`)
ring_pts = []
for k in range(24):
    ang = 2.0 * math.pi * k / 24.0
    ring_pts.append((0.24 * math.cos(ang), 0.69 + 0.24 * math.sin(ang), -0.62))
shock_ring_bm = make_torus_tube_bm(ring_pts, 0.036, radial_segs=12, closed=True)
append_bmesh_part(shock_ring_bm, "FartCloudNeon", lambda x, y, z: {"FartCloud.1": 1.0})

# Stage 2 (`FartCloud.2`): Giant Billowing Cauliflower Cartoon Green Cloud
fart_stage2_puffs = [
    (0.00, 0.76, -0.92, 0.28, 0.26, 0.28, "FartCloudLime"),
    (-0.20, 0.82, -0.96, 0.23, 0.22, 0.22, "FartCloudLime"),
    (0.20, 0.80, -0.96, 0.23, 0.22, 0.22, "FartCloudLime"),
    (0.00, 0.94, -1.02, 0.25, 0.24, 0.24, "FartCloudNeon"),
    (-0.16, 0.64, -0.90, 0.20, 0.18, 0.20, "FartCloudLime"),
    (0.16, 0.64, -0.90, 0.20, 0.18, 0.20, "FartCloudLime"),
    (0.00, 0.78, -1.16, 0.30, 0.28, 0.28, "FartCloudLime"),
    (-0.24, 0.88, -1.14, 0.22, 0.22, 0.22, "FartCloudNeon"),
    (0.24, 0.86, -1.14, 0.22, 0.22, 0.22, "FartCloudPurple"),
    (-0.14, 0.98, -1.18, 0.21, 0.20, 0.21, "FartCloudLime"),
    (0.14, 0.98, -1.18, 0.21, 0.20, 0.21, "FartCloudLime"),
]
for idx, (fx, fy, fz, rx, ry, rz, mkey) in enumerate(fart_stage2_puffs):
    def fc2_disp(p_w, n_w, s=idx):
        return p_w + n_w * (cloud_displacement(p_w + Vector((s * 1.7, s * 0.9, 0.0))) * 1.15)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=20, v_segs=14, world_deform_fn=fc2_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.2": 1.0})

# Stage 3 (`FartCloud.3`): Outer Expanding Puff Balls & Curly Comic Waft Ribbons
fart_stage3_puffs = [
    (0.00, 0.92, -1.42, 0.32, 0.30, 0.30, "FartCloudLime"),
    (-0.28, 1.02, -1.38, 0.24, 0.23, 0.24, "FartCloudNeon"),
    (0.28, 1.00, -1.38, 0.24, 0.23, 0.24, "FartCloudLime"),
    (0.00, 1.14, -1.46, 0.26, 0.25, 0.25, "FartCloudPurple"),
    (-0.20, 0.76, -1.36, 0.22, 0.20, 0.22, "FartCloudLime"),
    (0.20, 0.76, -1.36, 0.22, 0.20, 0.22, "FartCloudPurple"),
    (-0.36, 0.88, -1.52, 0.18, 0.18, 0.18, "FartCloudNeon"),
    (0.36, 0.90, -1.52, 0.18, 0.18, 0.18, "FartCloudLime"),
    (0.00, 1.02, -1.66, 0.22, 0.22, 0.22, "FartCloudNeon"),
]
for idx, (fx, fy, fz, rx, ry, rz, mkey) in enumerate(fart_stage3_puffs):
    def fc3_disp(p_w, n_w, s=idx):
        return p_w + n_w * (cloud_displacement(p_w + Vector((0.0, s * 1.4, s * 2.1))) * 1.20)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=18, v_segs=14, world_deform_fn=fc3_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.3": 1.0})

# 3 Wavy Cartoon Stink Swirl Ribbons rising above the cloud (`FartCloud.3`)
for s_idx, (sx_off, sz_off, mkey) in enumerate([
    (-0.18, -1.15, "FartCloudNeon"),
    (0.02, -1.38, "FartCloudPurple"),
    (0.20, -1.24, "FartCloudNeon"),
]):
    swirl_pts = []
    for k in range(17):
        t = k / 16.0
        wx = sx_off + 0.07 * math.sin(t * 2.5 * math.pi + s_idx)
        wy = 1.08 + 0.48 * t
        wz = sz_off - 0.18 * t + 0.06 * math.cos(t * 2.5 * math.pi + s_idx)
        swirl_pts.append((wx, wy, wz))
    swirl_bm = make_torus_tube_bm(
        swirl_pts,
        lambda t: 0.026 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=10, closed=False
    )
    append_bmesh_part(swirl_bm, mkey, lambda x, y, z: {"FartCloud.3": 1.0})


# ==============================================================================
# 4. CREATE BLENDER MESH OBJECT + SUBSURF MODIFIER
# ==============================================================================
mesh_data = bpy.data.meshes.new("PickyPiggy_Plush_MeshData")
for m in MAT_LIST:
    mesh_data.materials.append(m)

master_bm.to_mesh(mesh_data)
master_bm.free()
mesh_data.update()

mesh_obj = bpy.data.objects.new("PickyPiggy_Plush_Mesh", mesh_data)
main_col.objects.link(mesh_obj)

for bname in BONE_NAMES:
    mesh_obj.vertex_groups.new(name=bname)


# ==============================================================================
# 5. CREATE SKELETAL ARMATURE RIG (25 BONES) & BIND SKINNING
# ==============================================================================
arm_data = bpy.data.armatures.new("PickyPiggy_ArmatureData")
arm_data.display_type = 'OCTAHEDRAL'
arm_obj = bpy.data.objects.new("PickyPiggy_Armature", arm_data)
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
add_ebone("Pelvis", (0.0, 0.50, 0.0), (0.0, 0.82, 0.0), "Root", False)
add_ebone("Spine", (0.0, 0.82, 0.0), (0.0, 1.14, 0.0), "Pelvis", True)
add_ebone("Chest", (0.0, 1.14, 0.0), (0.0, 1.42, 0.0), "Spine", True)
add_ebone("Neck", (0.0, 1.42, 0.0), (0.0, 1.60, 0.0), "Chest", True)
add_ebone("Head", (0.0, 1.60, 0.0), (0.0, 2.45, 0.0), "Neck", True)

add_ebone("Jaw", (0.0, 1.68, 0.45), (0.0, 1.44, 0.72), "Head", False)
add_ebone("Eyelid.L", (0.235, 2.055, 0.565), (0.235, 2.18, 0.72), "Head", False)
add_ebone("Eyelid.R", (-0.235, 2.055, 0.565), (-0.235, 2.18, 0.72), "Head", False)
add_ebone("Ear.L", (0.38, 2.34, 0.06), (0.82, 2.52, 0.14), "Head", False)
add_ebone("Ear.R", (-0.38, 2.34, 0.06), (-0.82, 2.52, 0.14), "Head", False)

add_ebone("SkullPendant", (0.0, 1.28, 0.48), (0.0, 0.90, 0.51), "Chest", False)

add_ebone("Shoulder.L", (0.28, 1.32, 0.02), (0.44, 1.22, 0.03), "Chest", False)
add_ebone("Arm.L", (0.44, 1.22, 0.03), (0.70, 0.99, 0.06), "Shoulder.L", True)
add_ebone("HandHoof.L", (0.70, 0.99, 0.06), (0.91, 0.80, 0.09), "Arm.L", True)

add_ebone("Shoulder.R", (-0.28, 1.32, 0.02), (-0.44, 1.22, 0.03), "Chest", False)
add_ebone("Arm.R", (-0.44, 1.22, 0.03), (-0.70, 0.99, 0.06), "Shoulder.R", True)
add_ebone("HandHoof.R", (-0.70, 0.99, 0.06), (-0.91, 0.80, 0.09), "Arm.R", True)

add_ebone("Leg.L", (0.24, 0.65, 0.0), (0.31, 0.24, 0.03), "Pelvis", False)
add_ebone("FootHoof.L", (0.31, 0.24, 0.03), (0.31, 0.06, 0.24), "Leg.L", True)

add_ebone("Leg.R", (-0.24, 0.65, 0.0), (-0.31, 0.24, 0.03), "Pelvis", False)
add_ebone("FootHoof.R", (-0.31, 0.24, 0.03), (-0.31, 0.06, 0.24), "Leg.R", True)

# 3 Fart Cloud Bones with heads tucked inside the opaque Pelvis (z_fwd = -0.22)
add_ebone("FartCloud.1", (0.0, 0.68, -0.22), (0.0, 0.68, -0.65), "Root", False)
add_ebone("FartCloud.2", (0.0, 0.74, -0.22), (0.0, 0.78, -0.95), "Root", False)
add_ebone("FartCloud.3", (0.0, 0.80, -0.22), (0.0, 0.92, -1.35), "Root", False)

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
# 6. AUTHOR 6 NLA / ACTION ANIMATION CLIPS ON THE ARMATURE (PickyPiggy_Fart_Blast)
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


def build_picky_piggy_fart_blast(act):
    """
    36-Frame (1.5s @ 24fps) High-Energy Cartoon Animation: `PickyPiggy_Fart_Blast`
      - Act 1 (Frames 1..9):   Deep squat, tummy clench, trembling strain & tight eye squint
      - Act 2 (Frames 10..14): Explosive rocket recoil jump + 3-stage green/lime/purple 3D fart cloud + shockwave torus ring
      - Act 3 (Frames 15..26): Mid-air hop & landing bounce
      - Act 4 (Frames 27..36): Turn to camera, hoof-fanning cloud behind back & piggy oink-giggle!
    """
    body_keys = [
        # Frame 1: Neutral start
        (1,   0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000),
        # Frame 4: Squatting down & clenching hooves in
        (4,  -0.09, -0.02,  0.22,  0.14,  0.16, -0.06,  0.00,  0.04,  0.22, -0.18,  0.22,  0.28,  0.22, -0.28, -0.22,  0.18,  0.000),
        # Frames 6, 8, 9: High-tension strain tremble before the blast!
        (6,  -0.13, -0.04,  0.30,  0.18,  0.22, -0.10,  0.05,  0.06,  0.30, -0.25,  0.30,  0.35,  0.30, -0.35, -0.28,  0.24,  0.020),
        (8,  -0.14, -0.04,  0.32,  0.20,  0.24, -0.08, -0.05,  0.06,  0.32, -0.28,  0.32,  0.38,  0.32, -0.38, -0.30,  0.26, -0.020),
        (9,  -0.15, -0.05,  0.35,  0.22,  0.26, -0.12,  0.05,  0.08,  0.34, -0.30,  0.34,  0.40,  0.34, -0.40, -0.32,  0.28,  0.018),
        # Frame 12: KABOOM-TOOT! Big upward/forward rocket jump + wide-eyed oink gasp!
        (12,  0.14,  0.06,  0.28, -0.16, -0.22,  0.16, -0.08, -0.26, -0.12,  0.35, -0.20, -0.48, -0.20,  0.48,  0.24, -0.42,  0.000),
        # Frame 14: Peak of the toot blast — legs dangling, mouth wide open, Apple Pendant flying!
        (14,  0.17,  0.08,  0.22, -0.18, -0.24,  0.24, -0.12, -0.30, -0.14,  0.40, -0.25, -0.54, -0.25,  0.54,  0.28, -0.48,  0.000),
        # Frame 19: Mid-air hop & secondary toot ripple
        (19,  0.10,  0.05,  0.14, -0.10, -0.14,  0.26, -0.10, -0.22, -0.08,  0.25, -0.12, -0.38, -0.15,  0.40,  0.16, -0.30,  0.000),
        # Frame 24: Landing cushion bounce on hooves
        (24, -0.04,  0.01,  0.08,  0.04,  0.04,  0.28, -0.12, -0.12,  0.04, -0.10,  0.38, -0.15, -0.10,  0.25, -0.08,  0.12,  0.000),
        # Frames 27, 30, 33: Turn to camera, hoof-fanning cloud behind back + piggy oink-giggle!
        (27,  0.02,  0.00,  0.04, -0.04, -0.08,  0.30, -0.16, -0.26,  0.08,  0.18,  0.62, -0.32, -0.18,  0.32,  0.00, -0.15,  0.000),
        (30, -0.01,  0.00,  0.05,  0.02,  0.02,  0.26, -0.10, -0.06,  0.12, -0.08,  0.42,  0.12, -0.08,  0.18,  0.00,  0.10,  0.000),
        (33,  0.02,  0.00,  0.02, -0.03, -0.06,  0.20, -0.14, -0.22,  0.06,  0.14,  0.58, -0.28, -0.14,  0.26,  0.00, -0.10,  0.000),
        # Frame 36: Seamless return to neutral start pose
        (36,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000),
    ]

    for (f, p_dy, p_dz, p_pitch, c_pitch, h_pitch, h_yaw, h_roll,
         j_pitch, l_pitch, e_roll, al_p, al_r, ar_p, ar_r, lg_p, sk_p, p_dx) in body_keys:
        key_char_bone(f, "Pelvis", pitch_x=p_pitch, dx=p_dx, dy_up=p_dy, dz_fwd=p_dz)
        key_char_bone(f, "Spine", pitch_x=c_pitch * 0.5)
        key_char_bone(f, "Chest", pitch_x=c_pitch, yaw_y=h_yaw * 0.3)
        key_char_bone(f, "Head", pitch_x=h_pitch, yaw_y=h_yaw, roll_z=h_roll)
        key_char_bone(f, "Jaw", pitch_x=j_pitch)
        key_char_bone(f, "Eyelid.L", pitch_x=l_pitch)
        key_char_bone(f, "Eyelid.R", pitch_x=l_pitch)
        key_char_bone(f, "Ear.L", roll_z=-e_roll)
        key_char_bone(f, "Ear.R", roll_z=e_roll)
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
        (10, 0.35,   0.0, -0.08, -0.02, 0.00),
        (12, 1.08,   0.0, -0.04, -0.06, 0.25),
        (14, 1.35,   0.0,  0.04, -0.16, 0.65),
        (19, 1.12,   0.0,  0.10, -0.26, 1.10),
        (24, 0.65,   0.0,  0.18, -0.36, 1.55),
        (28, 0.22,   0.0,  0.24, -0.44, 1.95),
        (32, 0.0001, 0.0,  0.00,  0.00, 0.00),
        (36, 0.0001, 0.0,  0.00,  0.00, 0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc1_keys:
        key_char_bone(f, "FartCloud.1", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    fc2_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (10, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (12, 0.72,    0.00, -0.02, -0.04,  0.00),
        (14, 1.25,   -0.02,  0.06, -0.14, -0.18),
        (19, 1.48,   -0.04,  0.16, -0.28, -0.38),
        (24, 1.38,   -0.06,  0.28, -0.42, -0.60),
        (28, 0.94,   -0.08,  0.42, -0.56, -0.85),
        (33, 0.35,   -0.10,  0.54, -0.68, -1.05),
        (35, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (36, 0.0001,  0.00,  0.00,  0.00,  0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc2_keys:
        key_char_bone(f, "FartCloud.2", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    fc3_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (12, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (14, 0.65,    0.00,  0.02, -0.05,  0.00),
        (19, 1.22,    0.03,  0.12, -0.18,  0.15),
        (24, 1.45,    0.05,  0.26, -0.34,  0.32),
        (28, 1.32,    0.08,  0.42, -0.50,  0.52),
        (32, 0.78,    0.10,  0.58, -0.64,  0.70),
        (35, 0.22,    0.12,  0.70, -0.74,  0.85),
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
        key_char_bone(f, "Pelvis", pitch_x=0.02 * s, dy_up=0.015 * s)
        key_char_bone(f, "Chest", pitch_x=0.03 * s, roll_z=0.015 * c)
        key_char_bone(f, "Head", pitch_x=0.035 * s, yaw_y=0.04 * c, roll_z=0.025 * s)
        key_char_bone(f, "Ear.L", roll_z=0.06 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.06 * s)
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
        key_char_bone(f, "Pelvis", pitch_x=0.04 * s2, yaw_y=0.10 * s, roll_z=0.06 * c, dx=0.03 * s, dy_up=0.045 * abs(s))
        key_char_bone(f, "Chest", pitch_x=0.05 * s2, yaw_y=-0.08 * s, roll_z=-0.05 * c)
        key_char_bone(f, "Head", pitch_x=-0.04 * s2, yaw_y=0.06 * s, roll_z=0.05 * c)
        key_char_bone(f, "Leg.L", pitch_x=0.38 * s)
        key_char_bone(f, "Leg.R", pitch_x=-0.38 * s)
        key_char_bone(f, "FootHoof.L", pitch_x=-0.18 * c)
        key_char_bone(f, "FootHoof.R", pitch_x=0.18 * c)
        key_char_bone(f, "Arm.L", pitch_x=-0.28 * s, roll_z=0.06 * c)
        key_char_bone(f, "Arm.R", pitch_x=0.28 * s, roll_z=-0.06 * c)
        key_char_bone(f, "Ear.L", pitch_x=0.05 * s2, roll_z=0.10 * c)
        key_char_bone(f, "Ear.R", pitch_x=0.05 * s2, roll_z=-0.10 * c)
        key_char_bone(f, "SkullPendant", pitch_x=0.14 * s2, yaw_y=0.12 * s)


def build_happy_bounce(act):
    frames = [1, 10, 20, 30, 40]
    hide_fart_clouds_for_standard_clip(frames)
    for f, ph in [(1, 0.0), (10, 0.5 * math.pi), (20, math.pi), (30, 1.5 * math.pi), (40, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        jump = max(0.0, s) * 0.12
        key_char_bone(f, "Pelvis", pitch_x=-0.06 * s, dy_up=jump)
        key_char_bone(f, "Chest", pitch_x=-0.08 * s)
        key_char_bone(f, "Head", pitch_x=-0.10 * s, yaw_y=0.06 * c)
        key_char_bone(f, "Ear.L", roll_z=0.22 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.22 * s)
        key_char_bone(f, "Arm.L", roll_z=-0.25 * s)
        key_char_bone(f, "Arm.R", roll_z=0.25 * s)
        key_char_bone(f, "SkullPendant", pitch_x=-0.22 * c)
        key_char_bone(f, "Jaw", pitch_x=-0.12 * max(0.0, s))


def build_wave_hoof(act):
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
        key_char_bone(f, "Ear.L", roll_z=0.12 * lift)
        key_char_bone(f, "Ear.R", roll_z=-0.08 * lift)
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
        key_char_bone(f, "Ear.L", roll_z=-0.14 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.14 * s)
        key_char_bone(f, "Chest", yaw_y=0.06 * s, roll_z=-0.04 * s)


fart_act, fart_track = bake_action_to_nla("PickyPiggy_Fart_Blast", 36, build_picky_piggy_fart_blast)
idle_act, idle_track = bake_action_to_nla("Idle_Breathe", 60, build_idle_breathe)
walk_act, walk_track = bake_action_to_nla("Walk_Cycle", 48, build_walk_cycle)
bounce_act, bounce_track = bake_action_to_nla("Happy_Bounce", 40, build_happy_bounce)
wave_act, wave_track = bake_action_to_nla("Wave_Hoof", 60, build_wave_hoof)
curious_act, curious_track = bake_action_to_nla("Curious_Head_Tilt", 60, build_curious_tilt)

# Unmute all tracks transiently during GLB export so glTF exporter writes all 6 NLA tracks
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
# and set subsurf_mod.levels = 1 so the .obj stays well under 5MB
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
subsurf_mod.levels = 1
bpy.context.view_layer.update()

bpy.ops.wm.obj_export(
    filepath=OBJ_PATH,
    export_selected_objects=True,
    export_materials=True,
)
if os.path.getsize(OBJ_PATH) > 5 * 1024 * 1024:
    subsurf_mod.levels = 0
    bpy.context.view_layer.update()
    bpy.ops.wm.obj_export(
        filepath=OBJ_PATH,
        export_selected_objects=True,
        export_materials=True,
    )
    subsurf_mod.levels = 1


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

world = bpy.data.worlds.new("PickyStudioWorld")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = hex_to_rgba(0xF5F6F8)
    bg_node.inputs[1].default_value = 1.05

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


# ==============================================================================
# 9. RENDER STUDIO TURNAROUND VIEWS (REST POSE) & 36-FRAME FART BLAST SEQUENCE
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

scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'
scene.render.resolution_percentage = 100
scene.render.fps = 24

# 9.1 Rest-pose turnaround renders (Front 1080x1350, 3/4 800x1000, Side 800x1000)
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
scene.frame_set(1)

scene.cycles.samples = 48
scene.render.resolution_x = 1080
scene.render.resolution_y = 1350
aim_camera((0.0, -5.85, 1.38), target=(0.0, 0.0, 1.34), lens=62.0)
scene.render.filepath = RENDER_FRONT_PATH
bpy.ops.render.render(write_still=True)

scene.cycles.samples = 36
scene.render.resolution_x = 800
scene.render.resolution_y = 1000
aim_camera((-4.10, -4.20, 1.48), target=(0.0, 0.0, 1.34), lens=62.0)
scene.render.filepath = os.path.join(WORK_DIR, "cycles_3q.png")
bpy.ops.render.render(write_still=True)

aim_camera((-5.85, 0.0, 1.38), target=(0.0, 0.0, 1.34), lens=62.0)
scene.render.filepath = os.path.join(WORK_DIR, "cycles_side.png")
bpy.ops.render.render(write_still=True)

# 9.2 Activate ONLY `PickyPiggy_Fart_Blast` NLA track & render 36 frames (640x640)
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = (trk.name != "PickyPiggy_Fart_Blast")

aim_camera((4.85, -3.55, 1.48), target=(-0.05, 0.36, 1.18), lens=54.0)

scene.frame_start = 1
scene.frame_end = 36
scene.frame_set(14)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)

scene.cycles.samples = 24
scene.render.resolution_x = 640
scene.render.resolution_y = 640

for f in range(1, 37):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(FART_FRAMES_DIR, f"frame_{f:03d}.png")
    bpy.ops.render.render(write_still=True)

print("SUCCESS: Rendered PickyPiggy turnaround views + all 36 Cycles frames of PickyPiggy_Fart_Blast!")
print(f"  BLEND: {BLEND_PATH} ({os.path.getsize(BLEND_PATH)} bytes)")
print(f"  GLB:   {GLB_PATH} ({os.path.getsize(GLB_PATH)} bytes)")
print(f"  OBJ:   {OBJ_PATH} ({os.path.getsize(OBJ_PATH)} bytes)")
