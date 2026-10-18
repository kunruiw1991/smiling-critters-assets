#!/usr/bin/env python3
"""
Native Blender 4.3 Builder, Rigging, Animation & Cycles Studio Renderer
for DogDay (#008 Official Plush Base Model - Smiling Critters).

Includes:
  - 1:1 High-Precision 3D Recreation of `images/008_DogDay_Plushie.webp`
  - Sunny warm orange plush fleece body (`#E87A24`), golden-yellow muzzle, eye-patch ring,
    belly, lower paws & inner ears (`#F9C851`), warm rust-orange outer floppy spaniel ears,
    left eye patch & paw cuffs (`#C83A18`), wagging orange dog tail (`Tail`), dark brown
    rounded dog nose, wide sunny grin with coral-red tongue, red/gold belt & collar trim,
    and iconic Golden Sun Pendant with Wavy Rays and Orange/Gold Center (`SkullPendant`).
  - 25-bone `DogDay_Armature` including `FartCloud.1`, `FartCloud.2`, `FartCloud.3` with
    bone heads tucked inside the opaque pelvis (`z_fwd = -0.22`) and scaled to `0.0001`
    in rest pose and non-fart NLA clips.
  - 6 NLA animation clips: `Idle_Breathe`, `Walk_Cycle`, `Happy_Bounce`, `Wave_Paw`,
    `Curious_Head_Tilt`, and `DogDay_Fart_Blast` (36 frames @ 24fps).

Run headless via:
  /tmp/blender/blender -b --factory-startup --threads 8 --python-exit-code 1 -P /tmp/smiling-critters-assets/models/build_dogday_blender.py
"""

import os
import math
import subprocess
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, noise

OUT_DIR = "/tmp/smiling-critters-assets/models"
ANIM_DIR = "/tmp/smiling-critters-assets/animations"
WORK_DIR = "/tmp/work_dogday"
FART_FRAMES_DIR = os.path.join(WORK_DIR, "frames")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANIM_DIR, exist_ok=True)
os.makedirs(FART_FRAMES_DIR, exist_ok=True)

REF_IMG_PATH = "/tmp/smiling-critters-assets/images/008_DogDay_Plushie.webp"
BLEND_PATH = os.path.join(OUT_DIR, "dogday_plush_base_model.blend")
GLB_PATH = os.path.join(OUT_DIR, "dogday_plush_base_model.glb")
OBJ_PATH = os.path.join(OUT_DIR, "dogday_plush_base_model.obj")
RENDER_FRONT_PATH = os.path.join(OUT_DIR, "dogday_blender_cycles_render.png")
RENDER_PREVIEW_PATH = os.path.join(OUT_DIR, "dogday_3d_preview.png")
RENDER_3Q_PATH = os.path.join(WORK_DIR, "cycles_3q.png")
RENDER_SIDE_PATH = os.path.join(WORK_DIR, "cycles_side.png")


# ==============================================================================
# 1. SCENE RESET & HELPER UTILITIES
# ==============================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

main_col = bpy.data.collections.new("DogDay_Plush_Rig")
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
    # Matches head_core_bm (rx=0.72, ry=0.67, rz=0.65, cy=1.98) including cheek_swell
    cheek_swell = math.exp(-((y_up - 1.82) / 0.28) ** 2) if y_up < 1.98 else 0.0
    eff_rx = 0.72 * (1.0 + 0.08 * cheek_swell)
    nx = x / eff_rx
    ny = (y_up - 1.98) / 0.67
    r2 = min(0.94, nx * nx + ny * ny)
    return 0.65 * math.sqrt(max(0.06, 1.0 - r2))


def plush_fleece_displacement(p_world, amp=0.005):
    """Subtle soft plush fleece micro-turbulence."""
    q1 = Vector((p_world.x * 10.0, p_world.y * 10.0, p_world.z * 10.0))
    q2 = Vector((p_world.x * 22.0 + 2.1, p_world.y * 22.0 - 1.4, p_world.z * 22.0 + 1.8))
    return amp * (0.65 * noise.noise(q1) + 0.35 * noise.noise(q2))


def cloud_puff_displacement(p_world):
    """Billowing cartoon cloud displacement."""
    q1 = Vector((p_world.x * 7.5, p_world.y * 7.5, p_world.z * 7.5))
    q2 = Vector((p_world.x * 16.0 + 3.1, p_world.y * 16.0 - 1.7, p_world.z * 16.0 + 2.3))
    return 0.032 * noise.noise(q1) + 0.016 * abs(noise.noise(q2))


# ==============================================================================
# 2. PROCEDURAL CYCLES / GLTF PBR MATERIALS (HIGH-CONTRAST RICH DOGDAY PLUSH)
# ==============================================================================
def create_plush_material(name, hex_color, roughness=0.86, spec_ior=0.10,
                          sheen=0.06, sheen_tint_mult=1.0,
                          bump_scale=68.0, bump_strength=0.16,
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
    set_bsdf_input(bsdf, 0.80, "Sheen Roughness")
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
        noise_node.inputs["Roughness"].default_value = 0.75

        bump = nodes.new(type="ShaderNodeBump")
        bump.location = (-180, -180)
        bump.inputs["Strength"].default_value = bump_strength
        bump.inputs["Distance"].default_value = 0.020

        links.new(tex_coord.outputs["Object"], noise_node.inputs["Vector"])
        links.new(noise_node.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


MATS = {
    # Sunny warm orange plush fleece body (#E87A24 calibrated for Cycles AgX)
    "SunnyOrange": create_plush_material(
        "DogDay_Sunny_Orange_Fleece", 0xD65A0A, roughness=0.88, spec_ior=0.08,
        sheen=0.06, bump_scale=72.0, bump_strength=0.18
    ),
    # Golden-yellow muzzle, eye-patch ring, belly, lower paws & inner ears (#F9C851 calibrated)
    "GoldenYellow": create_plush_material(
        "DogDay_Golden_Yellow_Plush", 0xF0AD08, roughness=0.84, spec_ior=0.10,
        sheen=0.06, bump_scale=78.0, bump_strength=0.14
    ),
    # Deep warm burnt/rust-orange outer floppy ears, eye patch & upper paw/foot plush
    "RustOrange": create_plush_material(
        "DogDay_Rust_Orange_Plush", 0x9B240B, roughness=0.88, spec_ior=0.08,
        sheen=0.06, bump_scale=68.0, bump_strength=0.18
    ),
    # Deep crimson-red belt, collar & zipper trim
    "CollarRed": create_plush_material(
        "DogDay_Collar_Belt_Red", 0x7A1106, roughness=0.82, spec_ior=0.10,
        sheen=0.05, bump_scale=85.0, bump_strength=0.12
    ),
    # Dark chocolate brown rounded dog nose & eyebrows
    "NoseBrown": create_plush_material(
        "DogDay_Nose_Dark_Brown", 0x160C08, roughness=0.22, spec_ior=0.28,
        sheen=0.02, bump_scale=110.0, bump_strength=0.03, coat=0.25, coat_rough=0.06
    ),
    # Cheerful coral-red plush tongue
    "TongueRed": create_plush_material(
        "DogDay_Tongue_Coral_Red", 0xC81926, roughness=0.78, spec_ior=0.12,
        sheen=0.06, bump_scale=85.0, bump_strength=0.10
    ),
    # Sun Pendant Wavy Rays Orange-Gold
    "SunRayOrange": create_plush_material(
        "DogDay_Sun_Pendant_Rays", 0xDF4800, roughness=0.36, spec_ior=0.32,
        sheen=0.04, bump_strength=0.02, metallic=0.15, coat=0.22
    ),
    # Sun Pendant Golden Center & Gold Zipper Hardware
    "SunCenterGold": create_plush_material(
        "DogDay_Sun_Pendant_Gold", 0xF5B300, roughness=0.30, spec_ior=0.40,
        sheen=0.04, bump_strength=0.01, metallic=0.28, coat=0.28
    ),
    # Deep jet-black glossy acrylic dome eyes
    "EyeGloss": create_plush_material(
        "DogDay_Eye_Acrylic_Black", 0x020203, roughness=0.04, spec_ior=0.12,
        sheen=0.0, bump_strength=0.0, coat=0.30, coat_rough=0.015
    ),
    # Studio catchlight highlight on eyes
    "CatchlightWhite": create_plush_material(
        "DogDay_Eye_Catchlight_White", 0xFFFFFF, roughness=0.05, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, emission_strength=0.35
    ),
    # Pitch-black recessed mouth interior & zipper track
    "MouthVoidBlack": create_plush_material(
        "DogDay_Mouth_Cavity_Black", 0x010102, roughness=0.99, spec_ior=0.01,
        sheen=0.0, bump_strength=0.0
    ),
    # 3D Cartoon Fart Cloud Materials (Vibrant Toxic Lime, Neon Blast Core, Purple Swirl)
    "FartCloudLime": create_plush_material(
        "DogDay_Fart_Cloud_Lime", 0x3BD61B, roughness=0.68, spec_ior=0.18,
        sheen=0.25, sheen_tint_mult=1.1, bump_scale=24.0, bump_strength=0.22,
        subsurface=0.20, emission_strength=0.26
    ),
    "FartCloudNeon": create_plush_material(
        "DogDay_Fart_Cloud_Neon_YellowGreen", 0xB8FF24, roughness=0.45, spec_ior=0.25,
        sheen=0.20, sheen_tint_mult=1.1, bump_scale=30.0, bump_strength=0.14,
        subsurface=0.15, emission_strength=0.48
    ),
    "FartCloudPurple": create_plush_material(
        "DogDay_Fart_Cloud_Purple", 0x8A38CC, roughness=0.62, spec_ior=0.20,
        sheen=0.25, sheen_tint_mult=1.1, bump_scale=28.0, bump_strength=0.18,
        subsurface=0.15, emission_strength=0.28
    ),
}


# ==============================================================================
# 3. DOGDAY GEOMETRY BUILDER (BMESH + SKIN WEIGHTS, OPTIMIZED FOR <5MB .OBJ)
# ==============================================================================
master_bm = bmesh.new()
deform_layer = master_bm.verts.layers.deform.verify()

BONE_NAMES = [
    "Root",
    "Pelvis",
    "Spine",
    "Chest",
    "Head",
    "Jaw",
    "Eyelid.L",
    "Eyelid.R",
    "Ear.L",
    "Ear.R",
    "SkullPendant",
    "Tail",
    "Shoulder.L",
    "Arm.L",
    "HandPaw.L",
    "Shoulder.R",
    "Arm.R",
    "HandPaw.R",
    "Leg.L",
    "FootPaw.L",
    "Leg.R",
    "FootPaw.R",
    "FartCloud.1",
    "FartCloud.2",
    "FartCloud.3",
]
assert len(BONE_NAMES) == 25, f"Expected 25 bones, got {len(BONE_NAMES)}"
BONE_IDX = {name: i for i, name in enumerate(BONE_NAMES)}

MAT_KEYS = [
    "SunnyOrange",
    "GoldenYellow",
    "RustOrange",
    "CollarRed",
    "NoseBrown",
    "TongueRed",
    "SunRayOrange",
    "SunCenterGold",
    "EyeGloss",
    "CatchlightWhite",
    "MouthVoidBlack",
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
                      u_segs=18, v_segs=12, rot_euler=(0.0, 0.0, 0.0),
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
        segments=1,
        profile=0.7,
        affect='EDGES'
    )
    for v in bm.verts:
        v.co += Vector((cx, cy, cz))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def make_torus_tube_bm(curve_pts, radius_fn, radial_segs=10, closed=False):
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
# 3.1 SUNNY ORANGE HEAD CORE & CROWN FUR TUFTS
# ------------------------------------------------------------------------------
def head_deform(p):
    if p.y < 0.0:
        cheek_swell = math.exp(-((p.y + 0.16) / 0.28) ** 2)
        p.x *= (1.0 + 0.08 * cheek_swell)
    return p


head_core_bm = make_uv_sphere_bm(
    0.72, 0.67, 0.65, cx=0.0, cy=1.98, cz=0.0,
    u_segs=26, v_segs=18,
    deform_fn=head_deform,
    world_deform_fn=lambda p_w, n_w: p_w + n_w * plush_fleece_displacement(p_w, 0.004)
)
append_bmesh_part(head_core_bm, "SunnyOrange", lambda x, y, z: {"Head": 1.0})

# Top crown fur tufts (2 cute upward dog hair tufts on top of head as in 003/050)
for side, tx, ty, tz, rx, ry, rz, ang_z in [
    (-1, -0.07, 2.63, 0.05, 0.085, 0.125, 0.06, 0.25),
    ( 1,  0.06, 2.65, 0.05, 0.095, 0.145, 0.06, -0.22),
]:
    tuft_bm = make_uv_sphere_bm(rx, ry, rz, cx=tx, cy=ty, cz=tz, u_segs=12, v_segs=8, rot_euler=(0.1, 0.0, ang_z))
    append_bmesh_part(tuft_bm, "SunnyOrange", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.2 LONG FLOPPY SPANIEL DOG EARS (`Ear.L`, `Ear.R`)
#     High arch at top-sides of head, draping down past cheeks with Golden-Yellow inner lining
# ------------------------------------------------------------------------------
for side in (-1, 1):
    ear_bone = "Ear.L" if side == 1 else "Ear.R"

    ear_outer_pts = []
    ear_inner_pts = []
    n_ear_steps = 15
    for k in range(n_ear_steps):
        t = k / (n_ear_steps - 1)
        if t < 0.25:
            u = t / 0.25
            ex = side * (0.42 + 0.30 * u)
            ey = 2.40 + 0.13 * math.sin(u * math.pi * 0.85)
            ez = 0.02 + 0.04 * u
        else:
            u = (t - 0.25) / 0.75
            ex = side * (0.72 + 0.16 * math.sin(u * math.pi * 0.75))
            ey = 2.47 - 1.06 * (u ** 1.06)
            ez = 0.06 + 0.08 * math.sin(u * math.pi * 0.8)
        ear_outer_pts.append((ex, ey, ez))
        ear_inner_pts.append((ex - side * 0.024, ey - 0.01, ez + 0.045))

    def build_spaniel_ear_paddle_bm(pts, width_scale, thick_scale):
        bm = bmesh.new()
        radial_segs = 12
        rings = []
        n_pts = len(pts)
        for i, pt in enumerate(pts):
            p = Vector(pt)
            if i == 0:
                tangent = (Vector(pts[i + 1]) - p).normalized()
            elif i == n_pts - 1:
                tangent = (p - Vector(pts[i - 1])).normalized()
            else:
                tangent = (Vector(pts[i + 1]) - Vector(pts[i - 1])).normalized()

            fwd_ref = Vector((0, 0, 1))
            lat = tangent.cross(fwd_ref).normalized()
            norm = lat.cross(tangent).normalized()

            t = i / (n_pts - 1)
            envelope = math.sin(math.pi * (0.08 + 0.88 * t)) * (0.72 + 0.52 * math.sin(math.pi * (t ** 0.85)))
            w_rad = width_scale * envelope
            th_rad = thick_scale * envelope

            ring = []
            for j in range(radial_segs):
                ang = 2.0 * math.pi * j / radial_segs
                c_a = math.cos(ang)
                s_a = math.sin(ang)
                offset = (
                    fwd_ref * (c_a * w_rad)
                    + lat * (s_a * th_rad * 0.88 + c_a * side * 0.04)
                    + norm * (s_a * th_rad * 0.55)
                )
                ring.append(bm.verts.new(p + offset))
            rings.append(ring)

        for i in range(len(rings) - 1):
            r1, r2 = rings[i], rings[i + 1]
            for j in range(radial_segs):
                jn = (j + 1) % radial_segs
                bm.faces.new([r1[j], r2[j], r2[jn], r1[jn]])

        c_start = bm.verts.new(Vector(pts[0]))
        for j in range(radial_segs):
            jn = (j + 1) % radial_segs
            bm.faces.new([c_start, rings[0][jn], rings[0][j]])
        c_end = bm.verts.new(Vector(pts[-1]))
        for j in range(radial_segs):
            jn = (j + 1) % radial_segs
            bm.faces.new([c_end, rings[-1][j], rings[-1][jn]])

        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        return bm

    def ear_weights(x, y, z, b=ear_bone):
        w_ear = max(0.15, min(0.95, (2.46 - y) / 0.65 + (abs(x) - 0.45) / 0.35))
        return {b: w_ear, "Head": 1.0 - w_ear}

    ear_out_bm = build_spaniel_ear_paddle_bm(ear_outer_pts, width_scale=0.26, thick_scale=0.125)
    append_bmesh_part(ear_out_bm, "RustOrange", ear_weights)

    ear_in_bm = build_spaniel_ear_paddle_bm(ear_inner_pts, width_scale=0.19, thick_scale=0.068)
    append_bmesh_part(ear_in_bm, "GoldenYellow", ear_weights)


# ------------------------------------------------------------------------------
# 3.3 CHARACTER'S LEFT EYE PATCH + GOLDEN-YELLOW EYE-PATCH RING, GLOSSY EYES & BROWS
# ------------------------------------------------------------------------------
patch_ring_bm = make_uv_sphere_bm(
    0.265, 0.255, 0.088,
    cx=0.245, cy=2.045, cz=0.535,
    u_segs=20, v_segs=14,
    rot_euler=(-0.08, 0.22, -0.12)
)
append_bmesh_part(patch_ring_bm, "GoldenYellow", lambda x, y, z: {"Head": 1.0})

patch_inner_bm = make_uv_sphere_bm(
    0.242, 0.232, 0.095,
    cx=0.245, cy=2.048, cz=0.548,
    u_segs=20, v_segs=14,
    rot_euler=(-0.08, 0.22, -0.12)
)
append_bmesh_part(patch_inner_bm, "RustOrange", lambda x, y, z: {"Head": 1.0})

for side in (-1, 1):
    lid_bone = "Eyelid.L" if side == 1 else "Eyelid.R"
    ex = side * 0.235
    ey = 2.040
    ez = 0.585

    # Golden-yellow socket ring around each eye
    sock_bm = make_uv_sphere_bm(
        0.180, 0.178, 0.105,
        cx=ex, cy=ey, cz=ez - 0.015,
        u_segs=18, v_segs=12,
        rot_euler=(-0.04, side * 0.18, 0.0)
    )
    append_bmesh_part(sock_bm, "GoldenYellow" if side == -1 else "RustOrange", lambda x, y, z: {"Head": 1.0})

    # Large wide-open glossy jet-black dome eye (matches 008_DogDay_Plushie.webp)
    eye_bm = make_uv_sphere_bm(
        0.168, 0.168, 0.128,
        cx=ex, cy=ey, cz=ez,
        u_segs=22, v_segs=16,
        rot_euler=(-0.04, side * 0.18, 0.0)
    )
    append_bmesh_part(eye_bm, "EyeGloss", lambda x, y, z: {"Head": 1.0})

    # Primary studio catchlight
    hi1_bm = make_uv_sphere_bm(
        0.038, 0.048, 0.015,
        cx=ex - side * 0.038, cy=ey + 0.042, cz=ez + 0.120,
        u_segs=10, v_segs=8,
        rot_euler=(-0.10, side * 0.14, 0.0)
    )
    append_bmesh_part(hi1_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Secondary lower catchlight dot
    hi2_bm = make_uv_sphere_bm(
        0.016, 0.018, 0.010,
        cx=ex + side * 0.042, cy=ey - 0.042, cz=ez + 0.118,
        u_segs=8, v_segs=6
    )
    append_bmesh_part(hi2_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Subtle upper eyelid rim tucked high above the pupil in rest pose so eyes are wide open & joyful!
    def lid_deform(p):
        if p.y < 0.125:
            p.y = 0.125 + (p.y - 0.125) * 0.08
        if p.z < -0.02:
            p.z *= 0.35
        return p

    lid_bm = make_uv_sphere_bm(
        0.176, 0.174, 0.132,
        cx=ex, cy=ey + 0.018, cz=ez,
        u_segs=16, v_segs=12,
        rot_euler=(-0.06, side * 0.18, -side * 0.08),
        deform_fn=lid_deform
    )
    append_bmesh_part(
        lid_bm, "RustOrange" if side == 1 else "SunnyOrange",
        lambda x, y, z, b=lid_bone: {b: 0.90, "Head": 0.10}
    )

    # Cheerful arched eyebrow above eye
    brow_pts = []
    for k in range(9):
        t = -1.0 + 2.0 * k / 8.0
        bx = ex + side * t * 0.12
        by = 2.27 + 0.045 * (1.0 - t * t) - 0.015 * t
        bz = head_front_z(bx, by) + 0.018
        brow_pts.append((bx, by, bz))
    brow_bm = make_torus_tube_bm(
        brow_pts,
        lambda t: 0.018 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=8, closed=False
    )
    append_bmesh_part(brow_bm, "NoseBrown", lambda x, y, z, b=lid_bone: {b: 0.65, "Head": 0.35})


# ------------------------------------------------------------------------------
# 3.4 GOLDEN-YELLOW MUZZLE, DARK BROWN DOG NOSE, WIDE SUNNY GRIN & RED TONGUE
# ------------------------------------------------------------------------------
# Golden-yellow upper snout bridge cushion tucked cleanly above the upper lip (no overhang into mouth)
snout_bm = make_uv_sphere_bm(
    0.24, 0.075, 0.115,
    cx=0.0, cy=1.875, cz=0.615,
    u_segs=18, v_segs=12,
    rot_euler=(-0.06, 0.0, 0.0)
)
append_bmesh_part(snout_bm, "GoldenYellow", lambda x, y, z: {"Head": 0.92, "Jaw": 0.08})


# Rounded triangular dark brown dog nose
def dog_nose_deform(p):
    if p.y > 0:
        p.x *= (1.0 + 0.25 * (p.y / 0.065))
    else:
        p.x *= max(0.35, 1.0 + 0.55 * (p.y / 0.065))
    return p


nose_bm = make_uv_sphere_bm(
    0.112, 0.070, 0.070,
    cx=0.0, cy=1.892, cz=0.722,
    u_segs=18, v_segs=12,
    rot_euler=(-0.14, 0.0, 0.0),
    deform_fn=dog_nose_deform
)
append_bmesh_part(nose_bm, "NoseBrown", lambda x, y, z: {"Head": 1.0})


# Conformed pitch-black recessed mouth cavity (projected slightly in front of head_core_bm so orange never pokes through!)
def upper_smile_y(x):
    t = max(-1.0, min(1.0, x / 0.53))
    return 1.805 + 0.105 * (t * t) - 0.020 * (t ** 4)


def lower_smile_y(x):
    t = max(-1.0, min(1.0, x / 0.53))
    return 1.385 + 0.505 * (t ** 2)


def build_dogday_mouth_cavity_bm():
    bm = bmesh.new()
    cols = 20
    rows = 9
    grid = []
    for ir in range(rows + 1):
        v = ir / rows
        ring = []
        for ic in range(cols + 1):
            t = -1.0 + 2.0 * ic / cols
            ux = t * 0.52
            y_low = lower_smile_y(ux)
            y_up = upper_smile_y(ux)
            uy = y_low + (y_up - y_low) * v
            uz = head_front_z(ux, uy) + 0.012
            ring.append(bm.verts.new((ux, uy, uz)))
        grid.append(ring)

    for ir in range(rows):
        for ic in range(cols):
            bm.faces.new([grid[ir][ic], grid[ir][ic + 1], grid[ir + 1][ic + 1], grid[ir + 1][ic]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


mouth_bm = build_dogday_mouth_cavity_bm()
append_bmesh_part(
    mouth_bm, "MouthVoidBlack",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.76 - y) * 2.8)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.76 - y) * 2.8))}
)

# Thick Golden-Yellow Upper Smiling Lip Rim (#F9C851)
upper_lip_pts = []
for k in range(29):
    t = -1.0 + 2.0 * k / 28.0
    lx = t * 0.53
    ly = upper_smile_y(lx)
    lz = head_front_z(lx, ly) + 0.036 * (1.0 - 0.25 * t * t)
    upper_lip_pts.append((lx, ly, lz))

upper_lip_bm = make_torus_tube_bm(
    upper_lip_pts,
    lambda t: 0.044 + 0.018 * math.sin(math.pi * t),
    radial_segs=12, closed=False
)
append_bmesh_part(upper_lip_bm, "GoldenYellow", lambda x, y, z: {"Head": 0.88, "Jaw": 0.12})

# Thick Golden-Yellow Lower Smiling Lip Rim (#F9C851)
lower_lip_pts = []
for k in range(33):
    t = -1.0 + 2.0 * k / 32.0
    lx = t * 0.53
    ly = lower_smile_y(lx)
    lz = head_front_z(lx, ly) + 0.028 * (1.0 - 0.22 * t * t)
    lower_lip_pts.append((lx, ly, lz))

lower_lip_bm = make_torus_tube_bm(
    lower_lip_pts,
    lambda t: 0.038 + 0.012 * math.sin(math.pi * t),
    radial_segs=12, closed=False
)
append_bmesh_part(
    lower_lip_bm, "GoldenYellow",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.76 - y) * 2.8)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.76 - y) * 2.8))}
)

# Smooth Golden-Yellow Rounded Smile Cheek Corners (matches 008_DogDay_Plushie.webp)
for side in (-1, 1):
    cx = side * 0.525
    cy = 1.885
    cz = head_front_z(cx, cy) + 0.026
    corner_bm = make_uv_sphere_bm(0.048, 0.052, 0.044, cx=cx, cy=cy, cz=cz, u_segs=12, v_segs=10)
    append_bmesh_part(corner_bm, "GoldenYellow", lambda x, y, z: {"Head": 0.90, "Jaw": 0.10})


# Cheerful Coral-Red Plush Tongue inside the lower mouth cavity
def tongue_deform(p):
    groove = math.exp(-((p.x / 0.035) ** 2)) * 0.014
    if p.z > 0:
        p.z -= groove
    return p


tongue_bm = make_uv_sphere_bm(
    0.165, 0.135, 0.042,
    cx=0.0, cy=1.535, cz=head_front_z(0.0, 1.535) + 0.016,
    u_segs=18, v_segs=12,
    rot_euler=(-0.36, 0.0, 0.0),
    deform_fn=tongue_deform
)
append_bmesh_part(tongue_bm, "TongueRed", lambda x, y, z: {"Jaw": 0.85, "Head": 0.15})


# ------------------------------------------------------------------------------
# 3.5 SUNNY ORANGE TORSO, GOLDEN-YELLOW BELLY, RED/GOLD TRIM & GOLDEN SUN PENDANT
# ------------------------------------------------------------------------------
TORSO_PROFILE = [
    (0.00, 0.50), (0.18, 0.51), (0.36, 0.56), (0.47, 0.65),
    (0.52, 0.78), (0.53, 0.92), (0.50, 1.06), (0.45, 1.20),
    (0.39, 1.33), (0.33, 1.42), (0.26, 1.49), (0.00, 1.51)
]


def torso_radius_at_y(y):
    if y <= TORSO_PROFILE[1][1]:
        return TORSO_PROFILE[1][0]
    if y >= TORSO_PROFILE[-2][1]:
        return TORSO_PROFILE[-2][0]
    for i in range(1, len(TORSO_PROFILE) - 2):
        r1, y1 = TORSO_PROFILE[i]
        r2, y2 = TORSO_PROFILE[i + 1]
        if y1 <= y <= y2:
            u = (y - y1) / max(1e-5, y2 - y1)
            return r1 + u * (r2 - r1)
    return 0.45


def torso_front_z(y, x=0.0):
    r = torso_radius_at_y(y)
    nx = min(0.92, abs(x) / max(0.10, r))
    return r * 0.88 * math.sqrt(max(0.08, 1.0 - nx * nx))


def build_torso_bm():
    bm = bmesh.new()
    u_segs = 22
    rings = []
    for r_rad, ry in TORSO_PROFILE:
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
        t = max(0.0, min(1.0, (y - 0.50) / 0.28))
        return {"Pelvis": 1.0 - 0.5 * t, "Spine": 0.5 * t}
    elif y < 1.12:
        t = (y - 0.78) / 0.34
        return {"Pelvis": max(0.0, 0.5 - t), "Spine": 1.0 - abs(t - 0.5), "Chest": max(0.0, t - 0.3)}
    else:
        t = max(0.0, min(1.0, (y - 1.12) / 0.36))
        return {"Spine": max(0.0, 0.4 * (1.0 - t)), "Chest": 1.0 - 0.25 * t, "Head": 0.25 * t}


torso_bm = build_torso_bm()
append_bmesh_part(torso_bm, "SunnyOrange", torso_weights)


# Full Golden-Yellow Plush Oval Belly Patch (#F9C851) sitting proudly on front torso (y = 0.56..1.28)
def build_belly_patch_bm():
    bm = bmesh.new()
    u_steps = 24
    v_steps = 12
    grid = []
    for iv in range(v_steps + 1):
        v_frac = iv / v_steps
        ring = []
        for iu in range(u_steps):
            ang = 2.0 * math.pi * iu / u_steps
            bx = math.cos(ang) * 0.31 * v_frac
            by = 0.91 + math.sin(ang) * 0.35 * v_frac
            bz = torso_front_z(by, bx) + 0.016 * (1.0 - 0.35 * (v_frac ** 3))
            ring.append(bm.verts.new((bx, by, bz)))
        grid.append(ring)

    for iv in range(v_steps):
        r1 = grid[iv]
        r2 = grid[iv + 1]
        for iu in range(u_steps):
            iun = (iu + 1) % u_steps
            bm.faces.new([r1[iu], r2[iu], r2[iun], r1[iun]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


belly_bm = build_belly_patch_bm()
append_bmesh_part(belly_bm, "GoldenYellow", torso_weights)

# Red & Gold Collar Ring & Belt/Zipper Trim (matches 008_DogDay_Plushie.webp)
collar_pts = []
for k in range(24):
    ang = 2.0 * math.pi * k / 24.0
    collar_pts.append((0.33 * math.cos(ang), 1.40, 0.30 * math.sin(ang)))
collar_bm = make_torus_tube_bm(collar_pts, 0.026, radial_segs=8, closed=True)
append_bmesh_part(collar_bm, "CollarRed", torso_weights)

# Red-orange vertical zipper border piping + black zipper track down center of belly
for side in (-1, 1):
    pipe_pts = [
        (side * 0.028, 0.56 + (1.38 - 0.56) * k / 18.0,
         torso_front_z(0.56 + (1.38 - 0.56) * k / 18.0, side * 0.028) + 0.020)
        for k in range(19)
    ]
    pipe_bm = make_torus_tube_bm(pipe_pts, 0.013, radial_segs=8, closed=False)
    append_bmesh_part(pipe_bm, "CollarRed", torso_weights)

zip_pts = [
    (0.0, 0.56 + (1.38 - 0.56) * k / 18.0,
     torso_front_z(0.56 + (1.38 - 0.56) * k / 18.0, 0.0) + 0.022)
    for k in range(19)
]
zip_track_bm = make_torus_tube_bm(zip_pts, 0.019, radial_segs=8, closed=False)
append_bmesh_part(zip_track_bm, "MouthVoidBlack", torso_weights)

# Gold zipper slider & bail at upper chest
slider_bm = make_beveled_box_bm(0.064, 0.072, 0.042, 0.0, 1.335, torso_front_z(1.335, 0.0) + 0.032)
append_bmesh_part(slider_bm, "SunRayOrange", lambda x, y, z: {"Chest": 0.7, "SkullPendant": 0.3})

bail_bm = make_beveled_box_bm(0.052, 0.056, 0.034, 0.0, 1.285, torso_front_z(1.285, 0.0) + 0.038)
append_bmesh_part(bail_bm, "SunCenterGold", lambda x, y, z: {"SkullPendant": 1.0})

# ICONIC GOLDEN SUN PENDANT WITH WAVY RAYS AND ORANGE/GOLD CENTER (`SkullPendant` bone)
sun_cy = 1.115
sun_cz = torso_front_z(sun_cy, 0.0) + 0.048


def build_sun_rays_bm():
    bm = bmesh.new()
    n_rays = 10
    n_steps = n_rays * 6  # 60 steps for crisp wavy star rays
    r_inner_ring = 0.142
    r_outer_peak = 0.228
    half_thick = 0.022

    top_ring = []
    bot_ring = []
    mid_ring = []
    for i in range(n_steps):
        ang = 2.0 * math.pi * i / n_steps
        wave = 0.5 * (1.0 + math.cos(n_rays * ang))
        sharp_wave = wave ** 0.75
        r = r_inner_ring + (r_outer_peak - r_inner_ring) * sharp_wave
        px = math.cos(ang) * r
        py = sun_cy + math.sin(ang) * r
        pz_f = sun_cz + half_thick
        pz_b = sun_cz - half_thick
        top_ring.append(bm.verts.new((px, py, pz_f)))
        bot_ring.append(bm.verts.new((px, py, pz_b)))
        mid_ring.append(bm.verts.new((math.cos(ang) * (r + 0.008), sun_cy + math.sin(ang) * (r + 0.008), sun_cz)))

    c_front = bm.verts.new((0.0, sun_cy, sun_cz + half_thick + 0.004))
    c_back = bm.verts.new((0.0, sun_cy, sun_cz - half_thick - 0.004))

    for i in range(n_steps):
        inext = (i + 1) % n_steps
        bm.faces.new([c_front, top_ring[i], top_ring[inext]])
        bm.faces.new([c_back, bot_ring[inext], bot_ring[i]])
        bm.faces.new([top_ring[i], mid_ring[i], mid_ring[inext], top_ring[inext]])
        bm.faces.new([mid_ring[i], bot_ring[i], bot_ring[inext], mid_ring[inext]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


sun_rays_bm = build_sun_rays_bm()
append_bmesh_part(sun_rays_bm, "SunRayOrange", lambda x, y, z: {"SkullPendant": 1.0})

# Dark rim outline ring around the central sun disc
sun_rim_pts = [
    (0.128 * math.cos(2.0 * math.pi * k / 24.0),
     sun_cy + 0.128 * math.sin(2.0 * math.pi * k / 24.0),
     sun_cz + 0.024)
    for k in range(24)
]
sun_rim_bm = make_torus_tube_bm(sun_rim_pts, 0.010, radial_segs=8, closed=True)
append_bmesh_part(sun_rim_bm, "NoseBrown", lambda x, y, z: {"SkullPendant": 1.0})

# Raised Golden-Yellow Sun Disc Center
sun_disc_bm = make_uv_sphere_bm(
    0.122, 0.122, 0.032,
    cx=0.0, cy=sun_cy, cz=sun_cz + 0.018,
    u_segs=18, v_segs=12
)
append_bmesh_part(sun_disc_bm, "SunCenterGold", lambda x, y, z: {"SkullPendant": 1.0})


# ------------------------------------------------------------------------------
# 3.6 SPLAYED SUNNY-ORANGE ARMS & RUST-ORANGE / GOLDEN-YELLOW PAWS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    sh_bone = "Shoulder.L" if side == 1 else "Shoulder.R"
    arm_bone = "Arm.L" if side == 1 else "Arm.R"
    paw_bone = "HandPaw.L" if side == 1 else "HandPaw.R"

    arm_pts = []
    for k in range(11):
        t = k / 10.0
        ax = side * (0.31 + 0.38 * t)
        ay = 1.33 - 0.34 * t + 0.02 * math.sin(math.pi * t)
        az = 0.02 + 0.04 * t
        arm_pts.append((ax, ay, az))

    arm_bm = make_torus_tube_bm(
        arm_pts,
        lambda t: 0.135 * (1.0 + 0.05 * t),
        radial_segs=14, closed=False
    )

    def arm_weight_fn(x, y, z, sb=sh_bone, ab=arm_bone, pb=paw_bone):
        dist = max(0.0, min(1.0, (abs(x) - 0.31) / 0.42))
        if dist < 0.35:
            return {"Chest": 0.35 * (1.0 - dist / 0.35), sb: 0.65, ab: 0.35 * (dist / 0.35)}
        elif dist < 0.85:
            return {ab: 0.85, sb: 0.15}
        else:
            return {ab: 0.50, pb: 0.50}

    append_bmesh_part(arm_bm, "SunnyOrange", arm_weight_fn)

    paw_pts = []
    for k in range(9):
        t = k / 8.0
        px = side * (0.66 + 0.22 * t)
        py = 1.01 - 0.20 * t
        pz = 0.06 + 0.03 * t
        paw_pts.append((px, py, pz))

    def paw_radius(t):
        if t < 0.15:
            return 0.140 + 0.018 * (t / 0.15)
        elif t < 0.72:
            return 0.158 + 0.008 * math.sin(math.pi * (t - 0.15) / 0.57)
        else:
            u = (t - 0.72) / 0.28
            return 0.158 * math.sqrt(max(0.02, 1.0 - u * u))

    paw_bm = make_torus_tube_bm(paw_pts, paw_radius, radial_segs=14, closed=False)
    append_bmesh_part(
        paw_bm, "RustOrange",
        lambda x, y, z, pb=paw_bone, ab=arm_bone: {pb: 0.90, ab: 0.10}
    )

    # Golden-yellow inner paw pad (#F9C851)
    pad_bm = make_uv_sphere_bm(
        0.072, 0.082, 0.032,
        cx=side * 0.78, cy=0.89, cz=0.195,
        u_segs=12, v_segs=8,
        rot_euler=(0.15, side * 0.25, side * 0.65)
    )
    append_bmesh_part(pad_bm, "GoldenYellow", lambda x, y, z, pb=paw_bone: {pb: 1.0})


# ------------------------------------------------------------------------------
# 3.7 STOUT SUNNY-ORANGE LEGS & ROUNDED RUST-ORANGE / GOLDEN-YELLOW FEET PAWS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    leg_bone = "Leg.L" if side == 1 else "Leg.R"
    foot_bone = "FootPaw.L" if side == 1 else "FootPaw.R"

    leg_pts = []
    for k in range(11):
        t = k / 10.0
        lx = side * (0.24 + 0.06 * t)
        ly = 0.65 - 0.42 * t
        lz = 0.0 + 0.03 * t
        leg_pts.append((lx, ly, lz))

    leg_bm = make_torus_tube_bm(
        leg_pts,
        lambda t: 0.175 * (1.0 - 0.05 * t),
        radial_segs=14, closed=False
    )

    def leg_weight_fn(x, y, z, lb=leg_bone, fb=foot_bone):
        if y > 0.50:
            return {"Pelvis": 0.45, lb: 0.55}
        elif y > 0.25:
            return {lb: 0.90, fb: 0.10}
        else:
            return {lb: 0.25, fb: 0.75}

    append_bmesh_part(leg_bm, "SunnyOrange", leg_weight_fn)

    fx = side * 0.31
    fy = 0.155
    fz = 0.11

    def foot_deform(p):
        if p.y < -0.04:
            p.y = -0.135 + (p.y + 0.135) * 0.18
        return p

    foot_bm = make_uv_sphere_bm(
        0.205, 0.165, 0.235,
        cx=fx, cy=fy, cz=fz,
        u_segs=18, v_segs=12,
        rot_euler=(0.0, -side * 0.08, 0.0),
        deform_fn=foot_deform
    )
    append_bmesh_part(
        foot_bm, "RustOrange",
        lambda x, y, z, fb=foot_bone, lb=leg_bone: {fb: 0.92, lb: 0.08}
    )

    # Golden-yellow lower foot sole / toe accent (#F9C851)
    sole_bm = make_uv_sphere_bm(
        0.188, 0.055, 0.215,
        cx=fx, cy=0.052, cz=fz + 0.012,
        u_segs=16, v_segs=10,
        rot_euler=(0.0, -side * 0.08, 0.0)
    )
    append_bmesh_part(sole_bm, "GoldenYellow", lambda x, y, z, fb=foot_bone: {fb: 1.0})

    # Plush seam line across front of foot
    seam_pts = []
    for k in range(11):
        t = -1.0 + 2.0 * k / 10.0
        sx = fx + t * 0.185
        sy = fy - 0.015 * (t * t)
        sz = fz + 0.232 * math.sqrt(max(0.05, 1.0 - 0.75 * t * t))
        seam_pts.append((sx, sy, sz))
    seam_bm = make_torus_tube_bm(seam_pts, 0.009, radial_segs=6, closed=False)
    append_bmesh_part(seam_bm, "CollarRed", lambda x, y, z, fb=foot_bone: {fb: 1.0})


# ------------------------------------------------------------------------------
# 3.8 WAGGING SUNNY-ORANGE DOG TAIL (`Tail` bone)
# ------------------------------------------------------------------------------
tail_pts = []
for k in range(11):
    t = k / 10.0
    tx = 0.18 * (t ** 1.3)
    ty = 0.68 + 0.42 * (t ** 1.15)
    tz = -0.36 - 0.36 * math.sin(t * math.pi * 0.72)
    tail_pts.append((tx, ty, tz))

tail_bm = make_torus_tube_bm(
    tail_pts,
    lambda t: 0.095 * math.sin(math.pi * (0.15 + 0.80 * t)) * (1.0 + 0.25 * t),
    radial_segs=10, closed=False
)
append_bmesh_part(
    tail_bm, "SunnyOrange",
    lambda x, y, z: {"Tail": 0.90, "Pelvis": 0.10}
)

tail_tip_bm = make_uv_sphere_bm(
    0.075, 0.095, 0.075,
    cx=tail_pts[-1][0], cy=tail_pts[-1][1] + 0.02, cz=tail_pts[-1][2],
    u_segs=12, v_segs=8,
    rot_euler=(0.3, 0.0, -0.25)
)
append_bmesh_part(tail_tip_bm, "GoldenYellow", lambda x, y, z: {"Tail": 1.0})


# ------------------------------------------------------------------------------
# 3.9 3D SCULPTED CARTOON FART CLOUD CLUSTER (WEIGHTED TO FartCloud.1 / .2 / .3)
# ------------------------------------------------------------------------------
fart_stage1_puffs = [
    (0.00, 0.68, -0.50, 0.12, 0.11, 0.14, "FartCloudNeon"),
    (0.00, 0.69, -0.64, 0.18, 0.16, 0.18, "FartCloudLime"),
    (-0.10, 0.72, -0.68, 0.14, 0.13, 0.14, "FartCloudLime"),
    (0.10, 0.66, -0.68, 0.14, 0.13, 0.14, "FartCloudLime"),
]
for idx, (fx, fy, fz, rx, ry, rz, mkey) in enumerate(fart_stage1_puffs):
    def fc1_disp(p_w, n_w, s=idx):
        return p_w + n_w * (cloud_puff_displacement(p_w + Vector((s * 1.1, 0.0, s * 0.7))) * 0.85)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=10, v_segs=8, world_deform_fn=fc1_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.1": 1.0})

ring_pts = []
for k in range(16):
    ang = 2.0 * math.pi * k / 16.0
    ring_pts.append((0.24 * math.cos(ang), 0.69 + 0.24 * math.sin(ang), -0.62))
shock_ring_bm = make_torus_tube_bm(ring_pts, 0.036, radial_segs=8, closed=True)
append_bmesh_part(shock_ring_bm, "FartCloudNeon", lambda x, y, z: {"FartCloud.1": 1.0})

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
        return p_w + n_w * (cloud_puff_displacement(p_w + Vector((s * 1.7, s * 0.9, 0.0))) * 1.15)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=10, v_segs=8, world_deform_fn=fc2_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.2": 1.0})

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
        return p_w + n_w * (cloud_puff_displacement(p_w + Vector((0.0, s * 1.4, s * 2.1))) * 1.20)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=10, v_segs=8, world_deform_fn=fc3_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.3": 1.0})

for s_idx, (sx_off, sz_off, mkey) in enumerate([
    (-0.18, -1.15, "FartCloudNeon"),
    (0.02, -1.38, "FartCloudPurple"),
    (0.20, -1.24, "FartCloudNeon"),
]):
    swirl_pts = []
    for k in range(13):
        t = k / 12.0
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
mesh_data = bpy.data.meshes.new("DogDay_Plush_MeshData")
for m in MAT_LIST:
    mesh_data.materials.append(m)

master_bm.to_mesh(mesh_data)
master_bm.free()
mesh_data.update()

mesh_obj = bpy.data.objects.new("DogDay_Plush_Mesh", mesh_data)
main_col.objects.link(mesh_obj)

for bname in BONE_NAMES:
    mesh_obj.vertex_groups.new(name=bname)


# ==============================================================================
# 5. CREATE SKELETAL ARMATURE RIG (25 BONES) & BIND SKINNING
# ==============================================================================
arm_data = bpy.data.armatures.new("DogDay_ArmatureData")
arm_data.display_type = 'OCTAHEDRAL'
arm_obj = bpy.data.objects.new("DogDay_Armature", arm_data)
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
add_ebone("Chest", (0.0, 1.14, 0.0), (0.0, 1.52, 0.0), "Spine", True)
add_ebone("Head", (0.0, 1.52, 0.0), (0.0, 2.50, 0.0), "Chest", True)

add_ebone("Jaw", (0.0, 1.68, 0.42), (0.0, 1.42, 0.68), "Head", False)
add_ebone("Eyelid.L", (0.235, 2.040, 0.585), (0.235, 2.18, 0.72), "Head", False)
add_ebone("Eyelid.R", (-0.235, 2.040, 0.585), (-0.235, 2.18, 0.72), "Head", False)
add_ebone("Ear.L", (0.52, 2.38, 0.04), (0.82, 1.46, 0.08), "Head", False)
add_ebone("Ear.R", (-0.52, 2.38, 0.04), (-0.82, 1.46, 0.08), "Head", False)

add_ebone("SkullPendant", (0.0, 1.28, 0.46), (0.0, 0.96, 0.50), "Chest", False)
add_ebone("Tail", (0.0, 0.68, -0.34), (0.18, 1.10, -0.72), "Pelvis", False)

add_ebone("Shoulder.L", (0.28, 1.33, 0.02), (0.44, 1.22, 0.03), "Chest", False)
add_ebone("Arm.L", (0.44, 1.22, 0.03), (0.69, 0.99, 0.06), "Shoulder.L", True)
add_ebone("HandPaw.L", (0.69, 0.99, 0.06), (0.88, 0.81, 0.09), "Arm.L", True)

add_ebone("Shoulder.R", (-0.28, 1.33, 0.02), (-0.44, 1.22, 0.03), "Chest", False)
add_ebone("Arm.R", (-0.44, 1.22, 0.03), (-0.69, 0.99, 0.06), "Shoulder.R", True)
add_ebone("HandPaw.R", (-0.69, 0.99, 0.06), (-0.88, 0.81, 0.09), "Arm.R", True)

add_ebone("Leg.L", (0.24, 0.65, 0.0), (0.30, 0.23, 0.03), "Pelvis", False)
add_ebone("FootPaw.L", (0.30, 0.23, 0.03), (0.31, 0.06, 0.24), "Leg.L", True)

add_ebone("Leg.R", (-0.24, 0.65, 0.0), (-0.30, 0.23, 0.03), "Pelvis", False)
add_ebone("FootPaw.R", (-0.30, 0.23, 0.03), (-0.31, 0.06, 0.24), "Leg.R", True)

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
# 6. AUTHOR 6 NLA / ACTION ANIMATION CLIPS ON THE ARMATURE (INCLUDING DogDay_Fart_Blast)
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


def build_dogday_fart_blast(act):
    body_keys = [
        (1,   0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000,  0.00),
        (4,  -0.09, -0.02,  0.22,  0.14,  0.16, -0.06,  0.00,  0.04,  0.24, -0.18,  0.22,  0.28,  0.22, -0.28, -0.22,  0.18,  0.000, -0.25),
        (6,  -0.13, -0.04,  0.30,  0.18,  0.22, -0.10,  0.05,  0.06,  0.34, -0.25,  0.30,  0.35,  0.30, -0.35, -0.28,  0.24,  0.020, -0.35),
        (8,  -0.14, -0.04,  0.32,  0.20,  0.24, -0.08, -0.05,  0.06,  0.36, -0.28,  0.32,  0.38,  0.32, -0.38, -0.30,  0.26, -0.020, -0.38),
        (9,  -0.15, -0.05,  0.35,  0.22,  0.26, -0.12,  0.05,  0.08,  0.38, -0.30,  0.34,  0.40,  0.34, -0.40, -0.32,  0.28,  0.018, -0.40),
        (12,  0.14,  0.06,  0.28, -0.16, -0.22,  0.16, -0.08, -0.22, -0.06,  0.42, -0.20, -0.48, -0.20,  0.48,  0.24, -0.42,  0.000,  0.45),
        (14,  0.18,  0.08,  0.24, -0.18, -0.24,  0.22, -0.12, -0.26, -0.08,  0.48, -0.25, -0.54, -0.25,  0.54,  0.28, -0.48,  0.000,  0.52),
        (19,  0.11,  0.05,  0.14, -0.10, -0.14,  0.26, -0.10, -0.18, -0.04,  0.30, -0.12, -0.38, -0.15,  0.40,  0.16, -0.30,  0.000,  0.38),
        (24, -0.04,  0.01,  0.08,  0.04,  0.04,  0.28, -0.12, -0.12,  0.02, -0.12,  0.38, -0.15, -0.10,  0.25, -0.08,  0.12,  0.000,  0.15),
        (27,  0.02,  0.00,  0.04, -0.04, -0.08,  0.30, -0.16, -0.22,  0.04,  0.20,  0.62, -0.32, -0.18,  0.32,  0.00, -0.15,  0.000,  0.30),
        (30, -0.01,  0.00,  0.05,  0.02,  0.02,  0.26, -0.10, -0.06,  0.06, -0.08,  0.42,  0.12, -0.08,  0.18,  0.00,  0.10,  0.000, -0.25),
        (33,  0.02,  0.00,  0.02, -0.03, -0.06,  0.20, -0.14, -0.18,  0.04,  0.14,  0.58, -0.28, -0.14,  0.26,  0.00, -0.10,  0.000,  0.28),
        (36,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000,  0.00),
    ]

    for (f, p_dy, p_dz, p_pitch, c_pitch, h_pitch, h_yaw, h_roll,
         j_pitch, l_pitch, e_roll, al_p, al_r, ar_p, ar_r, lg_p, sk_p, p_dx, t_yaw) in body_keys:
        key_char_bone(f, "Pelvis", pitch_x=p_pitch, dx=p_dx, dy_up=p_dy, dz_fwd=p_dz)
        key_char_bone(f, "Spine", pitch_x=c_pitch * 0.5)
        key_char_bone(f, "Chest", pitch_x=c_pitch, yaw_y=h_yaw * 0.3)
        key_char_bone(f, "Head", pitch_x=h_pitch, yaw_y=h_yaw, roll_z=h_roll)
        key_char_bone(f, "Jaw", pitch_x=j_pitch)
        key_char_bone(f, "Eyelid.L", pitch_x=l_pitch)
        key_char_bone(f, "Eyelid.R", pitch_x=l_pitch)
        key_char_bone(f, "Ear.L", roll_z=-e_roll, pitch_x=h_pitch * 0.4)
        key_char_bone(f, "Ear.R", roll_z=e_roll, pitch_x=h_pitch * 0.4)
        key_char_bone(f, "Arm.L", pitch_x=al_p, roll_z=al_r)
        key_char_bone(f, "HandPaw.L", pitch_x=al_p * 0.6, roll_z=al_r * 0.5)
        key_char_bone(f, "Arm.R", pitch_x=ar_p, roll_z=ar_r)
        key_char_bone(f, "HandPaw.R", pitch_x=ar_p * 0.5, roll_z=ar_r * 0.4)
        key_char_bone(f, "Leg.L", pitch_x=lg_p)
        key_char_bone(f, "Leg.R", pitch_x=lg_p)
        key_char_bone(f, "FootPaw.L", pitch_x=-lg_p * 0.7)
        key_char_bone(f, "FootPaw.R", pitch_x=-lg_p * 0.7)
        key_char_bone(f, "SkullPendant", pitch_x=sk_p, roll_z=p_dx * 3.0)
        key_char_bone(f, "Tail", pitch_x=0.35 if (10 <= f <= 22) else 0.0, yaw_y=t_yaw)

    fc1_keys = [
        (1,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (9,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (10, 0.35,   0.0, -0.08, -0.02, 0.00),
        (12, 1.08,   0.0, -0.04, -0.06, 0.25),
        (14, 1.34,   0.0,  0.04, -0.16, 0.65),
        (19, 1.12,   0.0,  0.10, -0.26, 1.10),
        (24, 0.65,   0.0,  0.18, -0.36, 1.55),
        (29, 0.22,   0.0,  0.24, -0.44, 1.95),
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
        (28, 0.96,   -0.08,  0.42, -0.56, -0.85),
        (33, 0.35,   -0.10,  0.54, -0.68, -1.05),
        (35, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (36, 0.0001,  0.00,  0.00,  0.00,  0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc2_keys:
        key_char_bone(f, "FartCloud.2", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    fc3_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (11, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (14, 0.68,    0.00,  0.02, -0.05,  0.00),
        (18, 1.20,    0.03,  0.12, -0.18,  0.15),
        (23, 1.45,    0.05,  0.26, -0.34,  0.32),
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
        key_char_bone(f, "Tail", yaw_y=0.22 * s, roll_z=0.10 * c)
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
        key_char_bone(f, "FootPaw.L", pitch_x=-0.18 * c)
        key_char_bone(f, "FootPaw.R", pitch_x=0.18 * c)
        key_char_bone(f, "Arm.L", pitch_x=-0.28 * s, roll_z=0.06 * c)
        key_char_bone(f, "Arm.R", pitch_x=0.28 * s, roll_z=-0.06 * c)
        key_char_bone(f, "Ear.L", pitch_x=0.06 * s2, roll_z=0.12 * c)
        key_char_bone(f, "Ear.R", pitch_x=0.06 * s2, roll_z=-0.12 * c)
        key_char_bone(f, "SkullPendant", pitch_x=0.14 * s2, yaw_y=0.12 * s)
        key_char_bone(f, "Tail", yaw_y=0.32 * c, pitch_x=0.10 * s2)


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
        key_char_bone(f, "Ear.L", roll_z=0.26 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.26 * s)
        key_char_bone(f, "Arm.L", roll_z=-0.25 * s)
        key_char_bone(f, "Arm.R", roll_z=0.25 * s)
        key_char_bone(f, "SkullPendant", pitch_x=-0.22 * c)
        key_char_bone(f, "Jaw", pitch_x=-0.12 * max(0.0, s))
        key_char_bone(f, "Tail", yaw_y=0.35 * c, pitch_x=0.15 * s)


def build_wave_paw(act):
    frames = [1, 15, 30, 45, 60]
    hide_fart_clouds_for_standard_clip(frames)
    for f, ph in [(1, 0.0), (15, 0.5 * math.pi), (30, math.pi), (45, 1.5 * math.pi), (60, 2.0 * math.pi)]:
        s = math.sin(ph)
        w = math.sin(3.0 * ph)
        lift = math.sin(0.5 * ph)
        key_char_bone(f, "Shoulder.R", roll_z=0.45 * lift)
        key_char_bone(f, "Arm.R", pitch_x=-0.35 * lift, yaw_y=0.20 * w * lift, roll_z=0.55 * lift)
        key_char_bone(f, "HandPaw.R", roll_z=0.30 * w * lift)
        key_char_bone(f, "Head", pitch_x=0.04 * s, yaw_y=-0.12 * lift, roll_z=0.14 * lift)
        key_char_bone(f, "Ear.L", roll_z=0.12 * lift)
        key_char_bone(f, "Ear.R", roll_z=-0.08 * lift)
        key_char_bone(f, "SkullPendant", pitch_x=0.08 * s, yaw_y=0.08 * lift)
        key_char_bone(f, "Tail", yaw_y=0.28 * w * lift)


def build_curious_tilt(act):
    frames = [1, 15, 30, 45, 60]
    hide_fart_clouds_for_standard_clip(frames)
    for f, ph in [(1, 0.0), (15, 0.5 * math.pi), (30, math.pi), (45, 1.5 * math.pi), (60, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        talk = abs(math.sin(2.0 * ph))
        key_char_bone(f, "Head", pitch_x=0.06 * c, yaw_y=0.18 * s, roll_z=-0.18 * s)
        key_char_bone(f, "Jaw", pitch_x=-0.14 * talk)
        key_char_bone(f, "Eyelid.L", pitch_x=0.12 * max(0.0, s))
        key_char_bone(f, "Eyelid.R", pitch_x=0.12 * max(0.0, -s))
        key_char_bone(f, "Ear.L", roll_z=-0.16 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.16 * s)
        key_char_bone(f, "Chest", yaw_y=0.06 * s, roll_z=-0.04 * s)
        key_char_bone(f, "Tail", yaw_y=0.20 * s)


fart_act, fart_track = bake_action_to_nla("DogDay_Fart_Blast", 36, build_dogday_fart_blast)
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

# Set sub.levels = 1 before .obj export so the .obj stays under 5MB
subsurf_mod.levels = 1
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
bpy.context.view_layer.update()

bpy.ops.wm.obj_export(
    filepath=OBJ_PATH,
    export_selected_objects=True,
    export_materials=True,
    export_uv=False,
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


add_area_light("Key_Softbox", (-2.4, -3.6, 3.2), (0.0, 0.0, 1.45), energy=125.0, size=3.0, color_rgb=(1.0, 0.99, 0.98))
add_area_light("Fill_Softbox", (2.6, -3.2, 2.4), (0.0, 0.0, 1.35), energy=80.0, size=3.4, color_rgb=(0.98, 0.99, 1.0))
add_area_light("Top_Softbox", (0.0, -0.8, 4.2), (0.0, 0.0, 1.65), energy=85.0, size=3.2, color_rgb=(1.0, 1.0, 1.0))
add_area_light("Rim_Backlight", (0.0, 3.0, 3.0), (0.0, 0.0, 1.50), energy=75.0, size=2.6, color_rgb=(0.98, 0.98, 1.0))

world = bpy.data.worlds.new("DogDayStudioWorld")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = hex_to_rgba(0xF5F6F8)
    bg_node.inputs[1].default_value = 0.72

for look_name in ('AgX - High Contrast', 'High Contrast'):
    try:
        scene.view_settings.look = look_name
        break
    except Exception:
        pass

cam_data = bpy.data.cameras.new("Studio_Camera")
cam_data.lens = 60.0
cam_obj = bpy.data.objects.new("Studio_Camera", cam_data)
studio_col.objects.link(cam_obj)
scene.camera = cam_obj


def aim_camera(loc, target=(0.0, 0.0, 1.34), lens=60.0):
    cam_data.lens = lens
    cam_obj.location = Vector(loc)
    direction = Vector(target) - Vector(loc)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


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


# ==============================================================================
# 9. RENDER STATIC STUDIO RENDERS (1080x1350 FRONT + 1920x600 4-PANEL TURNAROUND)
# ==============================================================================
SKIP_RENDERS = (os.environ.get("DOGDAY_SKIP_RENDERS") == "1")

if not SKIP_RENDERS:
    for trk in arm_obj.animation_data.nla_tracks:
        trk.mute = True
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')
    reset_pose(hide_fart_cloud=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    scene.frame_set(1)

    # 1. Front Studio Render (1080x1350)
    aim_camera((0.0, -5.05, 1.40), target=(0.0, 0.0, 1.33), lens=60.0)
    scene.cycles.samples = 28
    scene.render.resolution_x = 1080
    scene.render.resolution_y = 1350
    scene.render.resolution_percentage = 100
    scene.render.filepath = RENDER_FRONT_PATH
    bpy.ops.render.render(write_still=True)

    # 2. 3/4 & Side Turnaround Views (480x600)
    scene.cycles.samples = 22
    scene.render.resolution_x = 480
    scene.render.resolution_y = 600

    aim_camera((3.10, -3.95, 1.44), target=(0.0, 0.0, 1.33), lens=60.0)
    scene.render.filepath = RENDER_3Q_PATH
    bpy.ops.render.render(write_still=True)

    aim_camera((5.05, -0.15, 1.40), target=(0.0, 0.0, 1.33), lens=60.0)
    scene.render.filepath = RENDER_SIDE_PATH
    bpy.ops.render.render(write_still=True)

    # 3. Composite 1920x600 4-Panel Preview Sheet (`008_DogDay_Plushie.webp` vs Front / 3/4 / Side)
    subprocess.run([
        "ffmpeg", "-y",
        "-i", REF_IMG_PATH,
        "-i", RENDER_FRONT_PATH,
        "-i", RENDER_3Q_PATH,
        "-i", RENDER_SIDE_PATH,
        "-filter_complex",
        "[0:v]scale=440:540:force_original_aspect_ratio=decrease:flags=lanczos,"
        "pad=480:600:(ow-iw)/2:(oh-ih)/2:color=#f2f3f5[p0];"
        "[1:v]scale=480:600:flags=lanczos[p1];"
        "[2:v]scale=480:600:flags=lanczos[p2];"
        "[3:v]scale=480:600:flags=lanczos[p3];"
        "[p0][p1][p2][p3]hstack=inputs=4[v]",
        "-map", "[v]",
        RENDER_PREVIEW_PATH
    ], check=True)


# ==============================================================================
# 10. RENDER THE 36-FRAME `DogDay_Fart_Blast` CYCLES ANIMATION SEQUENCE!
# ==============================================================================
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = (trk.name != "DogDay_Fart_Blast")

aim_camera((4.85, -3.55, 1.48), target=(-0.05, 0.36, 1.18), lens=54.0)

scene.frame_start = 1
scene.frame_end = 36
scene.frame_set(15)
if os.path.exists(BLEND_PATH):
    os.remove(BLEND_PATH)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)
if os.path.exists(BLEND_PATH + "1"):
    os.remove(BLEND_PATH + "1")

if not SKIP_RENDERS:
    scene.cycles.samples = 20
    scene.render.resolution_x = 640
    scene.render.resolution_y = 640
    scene.render.resolution_percentage = 100
    scene.render.fps = 24

    for f in range(1, 37):
        scene.frame_set(f)
        scene.render.filepath = os.path.join(FART_FRAMES_DIR, f"frame_{f:03d}.png")
        bpy.ops.render.render(write_still=True)

print("SUCCESS: Built DogDay 3D exports + studio sheets + DogDay_Fart_Blast!")
print(f"  BLEND: {BLEND_PATH} ({os.path.getsize(BLEND_PATH)} bytes)")
print(f"  GLB:   {GLB_PATH} ({os.path.getsize(GLB_PATH)} bytes)")
print(f"  OBJ:   {OBJ_PATH} ({os.path.getsize(OBJ_PATH)} bytes)")
