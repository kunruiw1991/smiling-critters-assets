#!/usr/bin/env python3
"""
Native Blender 4.3 Builder, Rigging, Animation & Cycles Studio Renderer
for CraftyCorn (#011 Official Plush Base Model - Smiling Critters).

Builds:
  1. `/tmp/smiling-critters-assets/models/craftycorn_plush_base_model.blend`
  2. `/tmp/smiling-critters-assets/models/craftycorn_plush_base_model.glb`
  3. `/tmp/smiling-critters-assets/models/craftycorn_plush_base_model.obj` & `.mtl` (< 5MB with sub.levels = 1)
  4. `/tmp/smiling-critters-assets/models/craftycorn_blender_cycles_render.png` (1080x1350 Cycles studio render)
  5. `/tmp/work_craftycorn/renders/cycles_3q.png` & `cycles_side.png` (for 1920x600 4-panel turnaround preview)
  6. `/tmp/work_craftycorn/frames/frame_001.png .. frame_036.png` (36-frame `CraftyCorn_Fart_Blast` @ 24fps)

Run headless via:
  /tmp/blender/blender -b --factory-startup -t 8 --python-exit-code 1 -P /tmp/smiling-critters-assets/models/build_craftycorn_blender.py
"""

import os
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, noise

OUT_DIR = "/tmp/smiling-critters-assets/models"
ANIM_DIR = "/tmp/smiling-critters-assets/animations"
WORK_DIR = "/tmp/work_craftycorn"
RENDER_SHEET_DIR = os.path.join(WORK_DIR, "renders")
FART_FRAMES_DIR = os.path.join(WORK_DIR, "frames")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANIM_DIR, exist_ok=True)
os.makedirs(RENDER_SHEET_DIR, exist_ok=True)
os.makedirs(FART_FRAMES_DIR, exist_ok=True)

BLEND_PATH = os.path.join(OUT_DIR, "craftycorn_plush_base_model.blend")
GLB_PATH = os.path.join(OUT_DIR, "craftycorn_plush_base_model.glb")
OBJ_PATH = os.path.join(OUT_DIR, "craftycorn_plush_base_model.obj")
RENDER_FRONT_PATH = os.path.join(OUT_DIR, "craftycorn_blender_cycles_render.png")
RENDER_PREVIEW_PATH = os.path.join(OUT_DIR, "craftycorn_3d_preview.png")


# ==============================================================================
# 1. SCENE RESET & HELPER UTILITIES
# ==============================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

main_col = bpy.data.collections.new("CraftyCorn_Plush_Rig")
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
    nx = x / 0.78
    ny = (y_up - 1.96) / 0.70
    r2 = min(0.92, nx * nx + ny * ny)
    return 0.72 * math.sqrt(max(0.08, 1.0 - r2))


def plush_fleece_displacement(p_world):
    """Soft multi-octave 3D plush fleece micro-tuft displacement."""
    q1 = Vector((p_world.x * 6.5, p_world.y * 6.5, p_world.z * 6.5))
    q2 = Vector((p_world.x * 14.0 + 2.7, p_world.y * 14.0 - 1.5, p_world.z * 14.0 + 1.9))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    return 0.016 * n1 + 0.008 * abs(n2)


def cloud_puff_displacement(p_world):
    """Billowing cartoon cloud displacement."""
    q1 = Vector((p_world.x * 7.5, p_world.y * 7.5, p_world.z * 7.5))
    q2 = Vector((p_world.x * 16.0 + 3.1, p_world.y * 16.0 - 1.7, p_world.z * 16.0 + 2.3))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    return 0.032 * n1 + 0.018 * abs(n2)


# ==============================================================================
# 2. PROCEDURAL CYCLES / GLTF PBR MATERIALS (CRAFTYCORN PLUSH + FART CLOUD)
# ==============================================================================
def create_plush_material(name, hex_color, roughness=0.84, spec_ior=0.14,
                          sheen=0.30, sheen_tint_mult=1.0,
                          bump_scale=55.0, bump_strength=0.14,
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
    set_bsdf_input(bsdf, 0.76, "Sheen Roughness")
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
    # Snow-white plush fleece unicorn body & head (#F2F5F8)
    "FleeceWhite": create_plush_material(
        "CraftyCorn_Fleece_White", 0xF2F5F8, roughness=0.84, spec_ior=0.14,
        sheen=0.36, sheen_tint_mult=1.0, bump_scale=68.0, bump_strength=0.16,
        subsurface=0.05
    ),
    # Bright cyan/aqua plush for mane crest, fluffy tail & hooves (#22B8CF)
    "AquaCyan": create_plush_material(
        "CraftyCorn_Aqua_Cyan_Plush", 0x22B8CF, roughness=0.78, spec_ior=0.16,
        sheen=0.34, sheen_tint_mult=1.05, bump_scale=56.0, bump_strength=0.20,
        subsurface=0.06
    ),
    # Soft sky-aqua plush for inner ears & forehead mane highlights (#38BDF8)
    "AquaLight": create_plush_material(
        "CraftyCorn_Aqua_Light_Plush", 0x38BDF8, roughness=0.76, spec_ior=0.16,
        sheen=0.32, sheen_tint_mult=1.05, bump_scale=62.0, bump_strength=0.16,
        subsurface=0.05
    ),
    # Deep teal stitch grooves for hoof cloven lines & ear recesses (#0E7490)
    "AquaSeam": create_plush_material(
        "CraftyCorn_Aqua_Seam_Dark", 0x0E7490, roughness=0.88, spec_ior=0.08,
        sheen=0.16, bump_scale=80.0, bump_strength=0.10
    ),
    # Spiraled white / pastel-silver pearlescent unicorn horn (#DCEEF5)
    "HornPearl": create_plush_material(
        "CraftyCorn_Horn_Pearl_Spiral", 0xDCEEF5, roughness=0.24, spec_ior=0.45,
        sheen=0.15, bump_scale=90.0, bump_strength=0.03,
        metallic=0.22, coat=0.65, coat_rough=0.06
    ),
    # Horn spiral groove accent (#94B8C8)
    "HornGroove": create_plush_material(
        "CraftyCorn_Horn_Spiral_Groove", 0x88B4C8, roughness=0.32, spec_ior=0.35,
        sheen=0.10, bump_strength=0.0, metallic=0.28, coat=0.45
    ),
    # Deep jet-black glossy acrylic dome eyes
    "EyeGloss": create_plush_material(
        "CraftyCorn_Eye_Acrylic_Black", 0x020203, roughness=0.04, spec_ior=0.14,
        sheen=0.0, bump_strength=0.0, coat=0.32, coat_rough=0.015
    ),
    # Studio catchlight highlight on eyes
    "CatchlightWhite": create_plush_material(
        "CraftyCorn_Eye_Catchlight_White", 0xFFFFFF, roughness=0.05, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, emission_strength=0.38
    ),
    # Pitch-black recessed mouth cavity
    "MouthVoidBlack": create_plush_material(
        "CraftyCorn_Mouth_Cavity_Black", 0x010102, roughness=0.99, spec_ior=0.01,
        sheen=0.0, bump_strength=0.0
    ),
    # Coral-pink plush tongue inside mouth cavity
    "TonguePink": create_plush_material(
        "CraftyCorn_Tongue_Pink", 0xF43F5E, roughness=0.80, spec_ior=0.12,
        sheen=0.28, bump_scale=75.0, bump_strength=0.10, subsurface=0.06
    ),
    # Brushed silver/gunmetal zipper teeth & collar pull slider
    "ZipperMetal": create_plush_material(
        "CraftyCorn_Zipper_Silver_Metal", 0xCBD5E1, roughness=0.22, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, metallic=0.90, coat=0.30
    ),
    # Dark zipper tape backing & flower pendant border
    "ZipperTrack": create_plush_material(
        "CraftyCorn_Zipper_Track_Dark", 0x0F172A, roughness=0.86, spec_ior=0.06,
        sheen=0.10, bump_strength=0.06
    ),
    # Rainbow Flower Pendant Materials (Yellow Center + 5 Rainbow Petals)
    "PetalCenterYellow": create_plush_material(
        "CraftyCorn_Pendant_Center_Yellow", 0xFACC15, roughness=0.25, spec_ior=0.40,
        sheen=0.15, bump_strength=0.02, metallic=0.15, coat=0.55, emission_strength=0.08
    ),
    "PetalOrange": create_plush_material(
        "CraftyCorn_Pendant_Petal_Orange", 0xF97316, roughness=0.28, spec_ior=0.38,
        sheen=0.15, bump_strength=0.02, metallic=0.12, coat=0.50, emission_strength=0.05
    ),
    "PetalGreen": create_plush_material(
        "CraftyCorn_Pendant_Petal_Green", 0x22C55E, roughness=0.28, spec_ior=0.38,
        sheen=0.15, bump_strength=0.02, metallic=0.12, coat=0.50, emission_strength=0.05
    ),
    "PetalBlue": create_plush_material(
        "CraftyCorn_Pendant_Petal_Blue", 0x0EA5E9, roughness=0.28, spec_ior=0.38,
        sheen=0.15, bump_strength=0.02, metallic=0.12, coat=0.50, emission_strength=0.05
    ),
    "PetalPurple": create_plush_material(
        "CraftyCorn_Pendant_Petal_Purple", 0x9333EA, roughness=0.28, spec_ior=0.38,
        sheen=0.15, bump_strength=0.02, metallic=0.12, coat=0.50, emission_strength=0.05
    ),
    "PetalRed": create_plush_material(
        "CraftyCorn_Pendant_Petal_Red", 0xEF4444, roughness=0.28, spec_ior=0.38,
        sheen=0.15, bump_strength=0.02, metallic=0.12, coat=0.50, emission_strength=0.05
    ),
    # 3D Cartoon Fart Cloud Materials (Vibrant Toxic Lime, Neon Blast Core, Unicorn Lavender Swirl)
    "FartCloudLime": create_plush_material(
        "CraftyCorn_Fart_Cloud_Lime", 0x4CE629, roughness=0.68, spec_ior=0.18,
        sheen=0.45, sheen_tint_mult=1.15, bump_scale=24.0, bump_strength=0.22,
        subsurface=0.35, emission_strength=0.28
    ),
    "FartCloudNeon": create_plush_material(
        "CraftyCorn_Fart_Cloud_Neon_YellowGreen", 0xC4FF33, roughness=0.45, spec_ior=0.25,
        sheen=0.35, sheen_tint_mult=1.1, bump_scale=30.0, bump_strength=0.14,
        subsurface=0.25, emission_strength=0.55
    ),
    "FartCloudPurple": create_plush_material(
        "CraftyCorn_Fart_Cloud_Unicorn_Purple", 0x9D4EDD, roughness=0.62, spec_ior=0.20,
        sheen=0.40, sheen_tint_mult=1.1, bump_scale=28.0, bump_strength=0.18,
        subsurface=0.25, emission_strength=0.32
    ),
}


# ==============================================================================
# 3. CRAFTYCORN GEOMETRY BUILDER (BMESH + SKIN WEIGHTS)
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

MAT_KEYS_ORDER = [
    "FleeceWhite",
    "AquaCyan",
    "AquaLight",
    "AquaSeam",
    "HornPearl",
    "HornGroove",
    "EyeGloss",
    "CatchlightWhite",
    "MouthVoidBlack",
    "TonguePink",
    "ZipperMetal",
    "ZipperTrack",
    "PetalCenterYellow",
    "PetalOrange",
    "PetalGreen",
    "PetalBlue",
    "PetalPurple",
    "PetalRed",
    "FartCloudLime",
    "FartCloudNeon",
    "FartCloudPurple",
]
MAT_LIST = [MATS[k] for k in MAT_KEYS_ORDER]
MAT_IDX = {k: i for i, k in enumerate(MAT_KEYS_ORDER)}


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
                      u_segs=24, v_segs=16, rot_euler=(0.0, 0.0, 0.0),
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


def make_beveled_box_bm(sx, sy, sz, cx, cy, cz, bevel_frac=0.14, segments=1):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    if segments > 0:
        bmesh.ops.bevel(
            bm,
            geom=list(bm.verts) + list(bm.edges) + list(bm.faces),
            offset=min(sx, sy, sz) * bevel_frac,
            offset_type='OFFSET',
            segments=segments,
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


# ------------------------------------------------------------------------------
# 3.1 SNOW-WHITE PLUSH HEAD CORE WITH WIDE SMILING UNICORN CHEEKS
# ------------------------------------------------------------------------------
def head_shape_deform(p):
    # Flare out the lower cheeks around y in [-0.35, 0.05] for the wide Smiling Critters grin
    ny = p.y / 0.68
    if -0.55 < ny < 0.15:
        cheek_swell = math.exp(-((ny + 0.18) / 0.28) ** 2) * (min(1.0, abs(p.x) / 0.45) ** 1.2)
        p.x *= (1.0 + 0.16 * cheek_swell)
    # Slightly recess the front mouth cavity bowl so the black mouth mesh never Z-clips with the white head
    if p.z > 0.25 and abs(p.x) < 0.50 and -0.54 < p.y < -0.14:
        mx = p.x / 0.50
        my = (p.y + 0.34) / 0.20
        m_bowl = max(0.0, 1.0 - mx * mx - my * my)
        p.z -= 0.055 * m_bowl
    return p


head_core_bm = make_uv_sphere_bm(
    0.72, 0.68, 0.70, cx=0.0, cy=1.96, cz=0.0,
    u_segs=32, v_segs=22,
    deform_fn=head_shape_deform
)
append_bmesh_part(head_core_bm, "FleeceWhite", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.2 UPRIGHT UNICORN EARS WITH SNOW-WHITE OUTER & CYAN/AQUA INNER RECESS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    ear_bone = "Ear.L" if side == 1 else "Ear.R"

    def ear_outer_deform(p, s=side):
        # Taper slightly toward base and round the upright tip
        ny = p.y / 0.28
        taper = 0.88 + 0.18 * (1.0 - ny * ny)
        p.x *= taper
        if p.z > 0.0:
            # Cup the front face slightly for the cyan inner ear insert
            r_cup = max(0.0, 1.0 - (p.x / 0.14) ** 2 - (p.y / 0.22) ** 2)
            p.z *= (1.0 - 0.55 * r_cup)
        return p

    ear_out_bm = make_uv_sphere_bm(
        0.185, 0.285, 0.110,
        cx=side * 0.52, cy=2.48, cz=0.06,
        u_segs=22, v_segs=16,
        rot_euler=(0.08, -side * 0.16, -side * 0.36),
        deform_fn=ear_outer_deform
    )
    append_bmesh_part(
        ear_out_bm, "FleeceWhite",
        lambda x, y, z, b=ear_bone: {b: 0.88, "Head": 0.12}
    )

    ear_in_bm = make_uv_sphere_bm(
        0.118, 0.205, 0.048,
        cx=side * 0.535, cy=2.47, cz=0.115,
        u_segs=18, v_segs=14,
        rot_euler=(0.08, -side * 0.16, -side * 0.36)
    )
    append_bmesh_part(
        ear_in_bm, "AquaCyan",
        lambda x, y, z, b=ear_bone: {b: 0.92, "Head": 0.08}
    )

    ear_crease_bm = make_uv_sphere_bm(
        0.055, 0.140, 0.028,
        cx=side * 0.54, cy=2.45, cz=0.142,
        u_segs=14, v_segs=10,
        rot_euler=(0.08, -side * 0.16, -side * 0.36)
    )
    append_bmesh_part(
        ear_crease_bm, "AquaSeam",
        lambda x, y, z, b=ear_bone: {b: 0.95, "Head": 0.05}
    )


# ------------------------------------------------------------------------------
# 3.3 SCALLOPED CYAN FOREHEAD MANE CREST & FLOWING BACK/SIDE MANE LOCKS
# ------------------------------------------------------------------------------
# Forehead 3-scallop cyan bangs crest (iconic #011 CraftyCorn plush feature!)
bangs_puffs = [
    # Main top crown cushion behind horn
    (0.00, 2.47, 0.22, 0.34, 0.20, 0.30, 0.0, 0.0, 0.0, "AquaCyan"),
    # Central forehead scallop lobe (dips right between the upper brows)
    (0.00, 2.26, 0.53, 0.19, 0.16, 0.18, 0.15, 0.0, 0.0, "AquaLight"),
    # Left & Right forehead scallop lobes flanking the central lobe
    (-0.21, 2.29, 0.48, 0.18, 0.15, 0.17, 0.12, -0.18, 0.18, "AquaCyan"),
    (0.21, 2.29, 0.48, 0.18, 0.15, 0.17, 0.12, 0.18, -0.18, "AquaCyan"),
    (-0.36, 2.33, 0.36, 0.16, 0.14, 0.16, 0.08, -0.28, 0.25, "AquaLight"),
    (0.36, 2.33, 0.36, 0.16, 0.14, 0.16, 0.08, 0.28, -0.25, "AquaLight"),
    # Flowing back-of-head & neck cyan mane crest + connected lower neck curls
    (0.00, 2.52, -0.10, 0.28, 0.22, 0.28, 0.0, 0.0, 0.0, "AquaCyan"),
    (0.00, 2.40, -0.40, 0.28, 0.24, 0.26, 0.0, 0.0, 0.0, "AquaCyan"),
    (0.00, 2.16, -0.56, 0.28, 0.25, 0.25, 0.0, 0.0, 0.0, "AquaLight"),
    (0.00, 1.90, -0.60, 0.27, 0.24, 0.24, 0.0, 0.0, 0.0, "AquaCyan"),
    (0.00, 1.66, -0.54, 0.25, 0.21, 0.22, 0.0, 0.0, 0.0, "AquaLight"),
    # Connected side-back mane tufts flaring out behind the lower neck (no isolated cheek patch!)
    (-0.26, 2.02, -0.52, 0.22, 0.18, 0.20, 0.0, -0.20, 0.25, "AquaCyan"),
    (0.26, 2.02, -0.52, 0.22, 0.18, 0.20, 0.0, 0.20, -0.25, "AquaCyan"),
    (-0.34, 1.80, -0.46, 0.21, 0.16, 0.18, 0.0, -0.25, 0.35, "AquaLight"),
    (0.34, 1.80, -0.46, 0.21, 0.16, 0.18, 0.0, 0.25, -0.35, "AquaLight"),
    (-0.40, 1.62, -0.38, 0.19, 0.14, 0.16, 0.0, -0.20, 0.40, "AquaCyan"),
    (0.40, 1.62, -0.38, 0.19, 0.14, 0.16, 0.0, 0.20, -0.40, "AquaCyan"),
]

for idx, (px, py, pz, rx, ry, rz, ex, ey, ez, mkey) in enumerate(bangs_puffs):
    def mane_disp(p_w, n_w, s=idx):
        return p_w + n_w * (plush_fleece_displacement(p_w + Vector((s * 0.7, s * 1.1, 0.0))) * 0.9)

    m_bm = make_uv_sphere_bm(
        rx, ry, rz, cx=px, cy=py, cz=pz,
        u_segs=20, v_segs=14,
        rot_euler=(ex, ey, ez),
        world_deform_fn=mane_disp
    )
    append_bmesh_part(m_bm, mkey, lambda x, y, z: {"Head": 1.0})

# Subtle cyan stitch grooves between the 3 forehead bangs scallops
for side in (-1, 1):
    s_pts = [
        (side * 0.11, 2.20 + 0.18 * (k / 8.0), 0.59 - 0.10 * (k / 8.0))
        for k in range(9)
    ]
    s_bm = make_torus_tube_bm(s_pts, 0.008, radial_segs=8, closed=False)
    append_bmesh_part(s_bm, "AquaSeam", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.4 SPIRALED WHITE / PASTEL-SILVER UNICORN HORN CENTERED ON FOREHEAD
# ------------------------------------------------------------------------------
horn_base = Vector((0.0, 2.34, 0.44))
horn_tip = Vector((0.0, 2.86, 0.80))
horn_axis = (horn_tip - horn_base)
horn_len = horn_axis.length
horn_dir = horn_axis.normalized()

# Build tapered spiraled unicorn horn cone
horn_pts = [
    tuple(horn_base.lerp(horn_tip, k / 18.0))
    for k in range(19)
]


def horn_radius_fn(t):
    # Smoothly tapers from 0.115 at base to a rounded 0.018 tip
    return 0.115 * ((1.0 - 0.84 * t) ** 0.88)


horn_bm = make_torus_tube_bm(horn_pts, horn_radius_fn, radial_segs=20, closed=False)
append_bmesh_part(horn_bm, "HornPearl", lambda x, y, z: {"Head": 1.0})

# Helical spiral ridge wrapping 4.5 turns around the unicorn horn
spiral_pts = []
up_tmp = Vector((1.0, 0.0, 0.0))
h_binorm = horn_dir.cross(up_tmp).normalized()
h_norm = h_binorm.cross(horn_dir).normalized()
for k in range(55):
    t = 0.04 + 0.88 * (k / 54.0)
    center_p = horn_base.lerp(horn_tip, t)
    r_cone = horn_radius_fn(t) * 0.96
    ang = t * 4.5 * 2.0 * math.pi
    offset = h_norm * (math.cos(ang) * r_cone) + h_binorm * (math.sin(ang) * r_cone)
    spiral_pts.append(tuple(center_p + offset))

spiral_bm = make_torus_tube_bm(
    spiral_pts,
    lambda t: 0.014 * (1.0 - 0.55 * t) * math.sin(math.pi * min(1.0, max(0.05, t))),
    radial_segs=8, closed=False
)
append_bmesh_part(spiral_bm, "HornGroove", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.5 LARGE GLOSSY BLACK OVAL EYES, CATCHLIGHTS & HAPPY UPPER EYELID BROWS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    lid_bone = "Eyelid.L" if side == 1 else "Eyelid.R"
    ex = side * 0.225
    ey = 1.985
    ez = 0.605

    eye_bm = make_uv_sphere_bm(
        0.158, 0.175, 0.125,
        cx=ex, cy=ey, cz=ez,
        u_segs=26, v_segs=20,
        rot_euler=(-0.05, side * 0.16, -side * 0.06)
    )
    append_bmesh_part(eye_bm, "EyeGloss", lambda x, y, z: {"Head": 1.0})

    # Primary studio softbox catchlight
    hi1_bm = make_uv_sphere_bm(
        0.036, 0.052, 0.014,
        cx=ex - side * 0.038, cy=ey + 0.042, cz=ez + 0.118,
        u_segs=14, v_segs=10,
        rot_euler=(-0.10, side * 0.14, 0.0)
    )
    append_bmesh_part(hi1_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Secondary lower pin catchlight
    hi2_bm = make_uv_sphere_bm(
        0.018, 0.022, 0.010,
        cx=ex + side * 0.042, cy=ey - 0.045, cz=ez + 0.115,
        u_segs=10, v_segs=8,
        rot_euler=(0.05, side * 0.14, 0.0)
    )
    append_bmesh_part(hi2_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Cheerful arched upper eyelid / brow rim weighted to Eyelid.L / Eyelid.R
    lid_rim_pts = []
    for k in range(15):
        t = -1.0 + 2.0 * k / 14.0
        lx = ex + t * 0.165
        ly = ey + 0.145 + 0.035 * (1.0 - t * t)
        lz = ez + 0.085 * math.sqrt(max(0.05, 1.0 - 0.75 * t * t))
        lid_rim_pts.append((lx, ly, lz))

    lid_rim_bm = make_torus_tube_bm(
        lid_rim_pts,
        lambda t: 0.022 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=10, closed=False
    )
    append_bmesh_part(
        lid_rim_bm, "FleeceWhite",
        lambda x, y, z, b=lid_bone: {b: 0.92, "Head": 0.08}
    )


# ------------------------------------------------------------------------------
# 3.6 SCULPTED SNOUT BRIDGE, NOSTRILS, WIDE SMILING MOUTH CAVITY & PINK TONGUE
# ------------------------------------------------------------------------------
snout_bm = make_uv_sphere_bm(
    0.20, 0.095, 0.125,
    cx=0.0, cy=1.845, cz=0.635,
    u_segs=22, v_segs=16,
    rot_euler=(-0.06, 0.0, 0.0)
)
append_bmesh_part(snout_bm, "FleeceWhite", lambda x, y, z: {"Head": 0.90, "Jaw": 0.10})

for side in (-1, 1):
    nos_bm = make_uv_sphere_bm(
        0.018, 0.012, 0.014,
        cx=side * 0.062, cy=1.855, cz=0.748,
        u_segs=12, v_segs=10,
        rot_euler=(-0.20, 0.0, -side * 0.30)
    )
    append_bmesh_part(nos_bm, "MouthVoidBlack", lambda x, y, z: {"Head": 1.0})


def build_conformed_mouth_cavity_bm():
    bm = bmesh.new()
    u_steps = 36
    v_steps = 14
    grid = []
    for iv in range(v_steps + 1):
        v_frac = iv / v_steps
        ring = []
        for iu in range(u_steps):
            ang = 2.0 * math.pi * iu / u_steps
            ux = math.cos(ang) * 0.51 * v_frac
            raw_y = math.sin(ang)
            if raw_y >= 0:
                uy = 1.77 + raw_y * 0.055 * v_frac + 0.095 * (ux / 0.51) ** 2
            else:
                uy = 1.77 + raw_y * 0.345 * v_frac + 0.075 * (ux / 0.51) ** 2
            uz = head_front_z(ux, uy) + 0.008 * (1.0 - 0.25 * v_frac)
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

# Cute plush pink tongue nestled at the bottom of the smiling mouth cavity
tongue_bm = make_uv_sphere_bm(
    0.18, 0.085, 0.045,
    cx=0.0, cy=1.515, cz=head_front_z(0.0, 1.515) + 0.016,
    u_segs=18, v_segs=12,
    rot_euler=(0.38, 0.0, 0.0)
)
append_bmesh_part(tongue_bm, "TonguePink", lambda x, y, z: {"Jaw": 0.85, "Head": 0.15})

# Snow-white plush upper and lower smiling lip rims
upper_lip_pts = []
for k in range(29):
    t = -1.0 + 2.0 * k / 28.0
    lx = t * 0.53
    ly = 1.78 + 0.105 * (t * t) - 0.020 * (t ** 4)
    lz = head_front_z(lx, ly) + 0.026 * (1.0 - 0.35 * t * t)
    upper_lip_pts.append((lx, ly, lz))

upper_lip_bm = make_torus_tube_bm(
    upper_lip_pts,
    lambda t: 0.036 + 0.012 * math.sin(math.pi * t),
    radial_segs=14, closed=False
)
append_bmesh_part(upper_lip_bm, "FleeceWhite", lambda x, y, z: {"Head": 0.88, "Jaw": 0.12})

lower_lip_pts = []
for k in range(33):
    t = -1.0 + 2.0 * k / 32.0
    lx = t * 0.53
    ly = 1.415 + 0.45 * (t ** 2)
    lz = head_front_z(lx, ly) + 0.022 * (1.0 - 0.35 * t * t)
    lower_lip_pts.append((lx, ly, lz))

lower_lip_bm = make_torus_tube_bm(
    lower_lip_pts,
    lambda t: 0.034 + 0.010 * math.sin(math.pi * t),
    radial_segs=14, closed=False
)
append_bmesh_part(
    lower_lip_bm, "FleeceWhite",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.75 - y) * 2.8)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.75 - y) * 2.8))}
)

for side in (-1, 1):
    cheek_pts = []
    for k in range(11):
        t = k / 10.0
        cx = side * (0.49 + 0.055 * math.sin(math.pi * t))
        cy = 1.76 + 0.14 * (1.0 - t)
        cz = head_front_z(cx, cy) + 0.020
        cheek_pts.append((cx, cy, cz))
    cheek_bm = make_torus_tube_bm(cheek_pts, 0.036, radial_segs=12, closed=False)
    append_bmesh_part(cheek_bm, "FleeceWhite", lambda x, y, z: {"Head": 0.90, "Jaw": 0.10})


# ------------------------------------------------------------------------------
# 3.7 PEAR-SHAPED SNOW-WHITE PLUSH TORSO, BLACK ZIPPER & RAINBOW FLOWER PENDANT
# ------------------------------------------------------------------------------
def build_torso_bm():
    bm = bmesh.new()
    u_segs = 36
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
append_bmesh_part(torso_bm, "FleeceWhite", torso_weights)


def torso_front_z(y):
    t = max(0.0, min(1.0, (y - 0.56) / (1.44 - 0.56)))
    r = 0.35 + 0.17 * math.sin(math.pi * (t ** 0.72)) - 0.08 * t
    return r * 0.88


# Black collar & vertical center zipper track (matching 011_CraftyCorn_Plushie.webp)
zip_pts = [(0.0, 0.56 + (1.42 - 0.56) * k / 20.0, torso_front_z(0.56 + (1.42 - 0.56) * k / 20.0) + 0.006)
           for k in range(21)]
zip_track_bm = make_torus_tube_bm(zip_pts, 0.028, radial_segs=8, closed=False)
append_bmesh_part(zip_track_bm, "ZipperTrack", torso_weights)

# Cyan trim piping along the zipper edges (as seen on #011 plush zipper tape!)
for side in (-1, 1):
    pipe_pts = [
        (side * 0.026, 0.57 + (1.41 - 0.57) * k / 18.0, torso_front_z(0.57 + (1.41 - 0.57) * k / 18.0) + 0.004)
        for k in range(19)
    ]
    pipe_bm = make_torus_tube_bm(pipe_pts, 0.009, radial_segs=8, closed=False)
    append_bmesh_part(pipe_bm, "AquaCyan", torso_weights)

for i in range(24):
    zy = 0.58 + (1.38 - 0.58) * (i / 23.0)
    zz = torso_front_z(zy) + 0.018
    zx = (0.009 if (i % 2 == 0) else -0.009)
    t_bm = make_beveled_box_bm(0.032, 0.014, 0.018, zx, zy, zz, segments=0)
    append_bmesh_part(t_bm, "ZipperMetal", torso_weights)

slider_bm = make_beveled_box_bm(0.064, 0.078, 0.042, 0.0, 1.32, 0.448, segments=1)
append_bmesh_part(slider_bm, "ZipperMetal", lambda x, y, z: {"Chest": 0.7, "SkullPendant": 0.3})

clasp_bm = make_beveled_box_bm(0.052, 0.068, 0.036, 0.0, 1.255, 0.468, segments=1)
append_bmesh_part(clasp_bm, "PetalOrange", lambda x, y, z: {"SkullPendant": 1.0})

# Iconic Rainbow-Petaled Flower Pendant with Yellow Center (`SkullPendant` bone)
pendant_cy = 1.085
pendant_cz = 0.488

# Dark outline backing disc behind flower
backing_center_bm = make_uv_sphere_bm(
    0.135, 0.135, 0.024,
    cx=0.0, cy=pendant_cy, cz=pendant_cz - 0.010,
    u_segs=20, v_segs=12,
    rot_euler=(-0.05, 0.0, 0.0)
)
append_bmesh_part(backing_center_bm, "ZipperTrack", lambda x, y, z: {"SkullPendant": 1.0})

# 5 Rainbow Petals in exact clockwise order from top (matching 011_CraftyCorn_Plushie & 038_CraftyCorn):
#   Top (90 deg): Orange
#   Upper-Right (18 deg, +X): Green
#   Lower-Right (-54 deg, +X): Blue
#   Lower-Left (-126 deg, -X): Purple
#   Upper-Left (162 deg, -X): Red
petal_specs = [
    (90.0,   "PetalOrange"),
    (18.0,   "PetalGreen"),
    (-54.0,  "PetalBlue"),
    (-126.0, "PetalPurple"),
    (162.0,  "PetalRed"),
]
petal_orbit_r = 0.118

for ang_deg, p_mat in petal_specs:
    ang_rad = math.radians(ang_deg)
    px = math.cos(ang_rad) * petal_orbit_r
    py = pendant_cy + math.sin(ang_rad) * petal_orbit_r
    pz = pendant_cz + 0.008 - 0.008 * math.sin(ang_rad)

    # Dark border rim around each petal
    pet_back_bm = make_uv_sphere_bm(
        0.092, 0.084, 0.026,
        cx=px, cy=py, cz=pz - 0.008,
        u_segs=18, v_segs=12,
        rot_euler=(-0.05, 0.0, ang_rad)
    )
    append_bmesh_part(pet_back_bm, "ZipperTrack", lambda x, y, z: {"SkullPendant": 1.0})

    # Vibrant satin-gloss rainbow petal cushion
    pet_bm = make_uv_sphere_bm(
        0.082, 0.074, 0.032,
        cx=px, cy=py, cz=pz + 0.004,
        u_segs=20, v_segs=14,
        rot_euler=(-0.05, 0.0, ang_rad)
    )
    append_bmesh_part(pet_bm, p_mat, lambda x, y, z: {"SkullPendant": 1.0})

# Central Yellow Flower Core Disc (with dark outline ring)
center_ring_bm = make_uv_sphere_bm(
    0.098, 0.098, 0.034,
    cx=0.0, cy=pendant_cy, cz=pendant_cz + 0.016,
    u_segs=22, v_segs=14,
    rot_euler=(-0.05, 0.0, 0.0)
)
append_bmesh_part(center_ring_bm, "ZipperTrack", lambda x, y, z: {"SkullPendant": 1.0})

center_yellow_bm = make_uv_sphere_bm(
    0.088, 0.088, 0.038,
    cx=0.0, cy=pendant_cy, cz=pendant_cz + 0.024,
    u_segs=22, v_segs=14,
    rot_euler=(-0.05, 0.0, 0.0)
)
append_bmesh_part(center_yellow_bm, "PetalCenterYellow", lambda x, y, z: {"SkullPendant": 1.0})


# ------------------------------------------------------------------------------
# 3.8 SPLAYED SNOW-WHITE PLUSH ARMS & BRIGHT CYAN/AQUA HOOF MITTENS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    sh_bone = "Shoulder.L" if side == 1 else "Shoulder.R"
    arm_bone = "Arm.L" if side == 1 else "Arm.R"
    hoof_bone = "HandHoof.L" if side == 1 else "HandHoof.R"

    arm_pts = []
    for k in range(11):
        t = k / 10.0
        ax = side * (0.32 + 0.40 * t)
        ay = 1.33 - 0.32 * t + 0.02 * math.sin(math.pi * t)
        az = 0.02 + 0.04 * t
        arm_pts.append((ax, ay, az))

    arm_bm = make_torus_tube_bm(
        arm_pts,
        lambda t: 0.140 * (1.0 + 0.04 * t),
        radial_segs=16, closed=False
    )

    def arm_weight_fn(x, y, z, sb=sh_bone, ab=arm_bone, hb=hoof_bone):
        dist = max(0.0, min(1.0, (abs(x) - 0.32) / 0.45))
        if dist < 0.35:
            return {"Chest": 0.35 * (1.0 - dist / 0.35), sb: 0.65, ab: 0.35 * (dist / 0.35)}
        elif dist < 0.85:
            return {ab: 0.85, sb: 0.15}
        else:
            return {ab: 0.50, hb: 0.50}

    append_bmesh_part(arm_bm, "FleeceWhite", arm_weight_fn)

    mitten_pts = []
    for k in range(11):
        t = k / 10.0
        mx = side * (0.69 + 0.24 * t)
        my = 1.03 - 0.20 * t
        mz = 0.06 + 0.03 * t
        mitten_pts.append((mx, my, mz))

    def mitten_radius(t):
        if t < 0.12:
            return 0.144 + 0.014 * (t / 0.12)
        elif t < 0.72:
            return 0.158 + 0.008 * math.sin(math.pi * (t - 0.12) / 0.60)
        else:
            u = (t - 0.72) / 0.28
            return 0.158 * math.sqrt(max(0.02, 1.0 - u * u))

    mitten_bm = make_torus_tube_bm(mitten_pts, mitten_radius, radial_segs=18, closed=False)
    append_bmesh_part(
        mitten_bm, "AquaCyan",
        lambda x, y, z, hb=hoof_bone, ab=arm_bone: {hb: 0.90, ab: 0.10}
    )

    cleft_pts = []
    for k in range(7):
        t = k / 6.0
        cx = side * (0.82 + 0.10 * t)
        cy = 0.92 - 0.09 * t
        cz = 0.085 + 0.132 * math.sin(math.pi * (0.15 + 0.70 * t))
        cleft_pts.append((cx, cy, cz))
    cleft_bm = make_torus_tube_bm(cleft_pts, 0.008, radial_segs=8, closed=False)
    append_bmesh_part(cleft_bm, "AquaSeam", lambda x, y, z, hb=hoof_bone: {hb: 1.0})


# ------------------------------------------------------------------------------
# 3.9 STOUT A-STANCE SNOW-WHITE PLUSH LEGS & CYAN/AQUA FOOT HOOVES
# ------------------------------------------------------------------------------
for side in (-1, 1):
    leg_bone = "Leg.L" if side == 1 else "Leg.R"
    foot_bone = "FootHoof.L" if side == 1 else "FootHoof.R"

    leg_pts = []
    for k in range(11):
        t = k / 10.0
        lx = side * (0.24 + 0.055 * t)
        ly = 0.66 - 0.43 * t
        lz = 0.0 + 0.02 * t
        leg_pts.append((lx, ly, lz))

    leg_bm = make_torus_tube_bm(
        leg_pts,
        lambda t: 0.180 * (1.0 - 0.06 * t),
        radial_segs=18, closed=False
    )

    def leg_weight_fn(x, y, z, lb=leg_bone, fb=foot_bone):
        if y > 0.52:
            return {"Pelvis": 0.45, lb: 0.55}
        elif y > 0.25:
            return {lb: 0.90, fb: 0.10}
        else:
            return {lb: 0.25, fb: 0.75}

    append_bmesh_part(leg_bm, "FleeceWhite", leg_weight_fn)

    fx = side * 0.305
    fy = 0.135
    fz = 0.055

    def foot_deform(p):
        if p.y < -0.02:
            p.y = -0.115 + (p.y + 0.115) * 0.15
        return p

    foot_bm = make_uv_sphere_bm(
        0.192, 0.148, 0.218,
        cx=fx, cy=fy, cz=fz,
        u_segs=22, v_segs=16,
        rot_euler=(0.0, 0.0, 0.0),
        deform_fn=foot_deform
    )
    append_bmesh_part(
        foot_bm, "AquaCyan",
        lambda x, y, z, fb=foot_bone, lb=leg_bone: {fb: 0.92, lb: 0.08}
    )

    fcleft_pts = []
    for k in range(7):
        t = k / 6.0
        cy = 0.03 + 0.14 * t
        cz = fz + 0.212 - 0.025 * (t - 0.4) ** 2
        fcleft_pts.append((fx, cy, cz))
    fcleft_bm = make_torus_tube_bm(fcleft_pts, 0.008, radial_segs=8, closed=False)
    append_bmesh_part(fcleft_bm, "AquaSeam", lambda x, y, z, fb=foot_bone: {fb: 1.0})


# ------------------------------------------------------------------------------
# 3.10 FLUFFY CURLED CYAN/AQUA UNICORN TAIL (WEIGHTED TO Pelvis)
# ------------------------------------------------------------------------------
# Sweeps from lower back outward to the side so it frames the silhouette in front/3/4
# views (matching 038_CraftyCorn.webp) and leaves the rear fart blast zone clear!
tail_pts = []
for k in range(17):
    t = k / 16.0
    tx = 0.10 * t + 0.44 * (t ** 1.4) - 0.08 * math.sin(math.pi * t * 1.5)
    ty = 0.64 - 0.10 * math.sin(math.pi * t) + 0.34 * (t ** 1.8)
    tz = -0.40 - 0.18 * math.sin(math.pi * t * 0.8)
    tail_pts.append((tx, ty, tz))


def tail_radius_fn(t):
    return 0.075 + 0.115 * math.sin(math.pi * (t ** 0.75))


tail_bm = make_torus_tube_bm(tail_pts, tail_radius_fn, radial_segs=14, closed=False)
append_bmesh_part(tail_bm, "AquaCyan", lambda x, y, z: {"Pelvis": 1.0})

# Fluffy curled tip puffs on the unicorn tail
for idx, (tpx, tpy, tpz, tpr, mkey) in enumerate([
    (0.46, 0.88, -0.48, 0.15, "AquaLight"),
    (0.54, 0.76, -0.45, 0.14, "AquaCyan"),
    (0.38, 0.72, -0.50, 0.13, "AquaLight"),
]):
    tp_bm = make_uv_sphere_bm(tpr * 1.1, tpr, tpr * 0.9, cx=tpx, cy=tpy, cz=tpz, u_segs=16, v_segs=12)
    append_bmesh_part(tp_bm, mkey, lambda x, y, z: {"Pelvis": 1.0})


# ------------------------------------------------------------------------------
# 3.11 3D SCULPTED CARTOON FART CLOUD CLUSTER (WEIGHTED TO FartCloud.1 / .2 / .3)
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
        return p_w + n_w * (cloud_puff_displacement(p_w + Vector((s * 1.1, 0.0, s * 0.7))) * 0.85)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=16, v_segs=12, world_deform_fn=fc1_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.1": 1.0})

# 3D Shockwave Torus Ring around the nozzle blast (`FartCloud.1`)
ring_pts = []
for k in range(24):
    ang = 2.0 * math.pi * k / 24.0
    ring_pts.append((0.24 * math.cos(ang), 0.69 + 0.24 * math.sin(ang), -0.62))
shock_ring_bm = make_torus_tube_bm(ring_pts, 0.036, radial_segs=10, closed=True)
append_bmesh_part(shock_ring_bm, "FartCloudNeon", lambda x, y, z: {"FartCloud.1": 1.0})

# Stage 2 (`FartCloud.2`): Giant Billowing Cauliflower Cartoon Green/Purple Cloud
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
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=18, v_segs=14, world_deform_fn=fc2_disp)
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
        return p_w + n_w * (cloud_puff_displacement(p_w + Vector((0.0, s * 1.4, s * 2.1))) * 1.20)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=16, v_segs=12, world_deform_fn=fc3_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.3": 1.0})

# 3 Wavy Cartoon Stink Swirl Ribbons rising above the cloud (`FartCloud.3`)
for s_idx, (sx_off, sz_off, mkey) in enumerate([
    (-0.18, -1.15, "FartCloudNeon"),
    (0.02, -1.38, "FartCloudPurple"),
    (0.20, -1.24, "FartCloudNeon"),
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
mesh_data = bpy.data.meshes.new("CraftyCorn_Plush_MeshData")
for m in MAT_LIST:
    mesh_data.materials.append(m)

master_bm.to_mesh(mesh_data)
master_bm.free()
mesh_data.update()

mesh_obj = bpy.data.objects.new("CraftyCorn_Plush_Mesh", mesh_data)
main_col.objects.link(mesh_obj)

for bname in BONE_NAMES:
    mesh_obj.vertex_groups.new(name=bname)


# ==============================================================================
# 5. CREATE SKELETAL ARMATURE RIG (25 BONES) & BIND SKINNING
# ==============================================================================
arm_data = bpy.data.armatures.new("CraftyCorn_ArmatureData")
arm_data.display_type = 'OCTAHEDRAL'
arm_obj = bpy.data.objects.new("CraftyCorn_Armature", arm_data)
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
add_ebone("Eyelid.L", (0.225, 1.985, 0.605), (0.225, 2.12, 0.76), "Head", False)
add_ebone("Eyelid.R", (-0.225, 1.985, 0.605), (-0.225, 2.12, 0.76), "Head", False)
add_ebone("Ear.L", (0.48, 2.34, 0.06), (0.62, 2.74, 0.06), "Head", False)
add_ebone("Ear.R", (-0.48, 2.34, 0.06), (-0.62, 2.74, 0.06), "Head", False)

add_ebone("SkullPendant", (0.0, 1.25, 0.46), (0.0, 0.92, 0.50), "Chest", False)

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

# 3 Fart Cloud Bones with heads tucked inside the opaque Pelvis (z_fwd = -0.22)
add_ebone("FartCloud.1", (0.0, 0.68, -0.22), (0.0, 0.68, -0.65), "Root", False)
add_ebone("FartCloud.2", (0.0, 0.74, -0.22), (0.0, 0.78, -0.95), "Root", False)
add_ebone("FartCloud.3", (0.0, 0.80, -0.22), (0.0, 0.92, -1.35), "Root", False)

bpy.ops.object.mode_set(mode='OBJECT')

mesh_obj.parent = arm_obj
arm_mod = mesh_obj.modifiers.new(name="Armature", type='ARMATURE')
arm_mod.object = arm_obj
arm_mod.use_vertex_groups = True

sub = mesh_obj.modifiers.new(name="Subdivision", type='SUBSURF')
sub.levels = 1
sub.render_levels = 2
sub.quality = 3


# ==============================================================================
# 6. AUTHOR 6 NLA / ACTION ANIMATION CLIPS ON THE ARMATURE (INCLUDING CraftyCorn_Fart_Blast)
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
    """Pose and keyframe `bone_name` using intuitive character-space conjugation."""
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


def build_craftycorn_fart_blast(act):
    """
    36-Frame (1.5s @ 24fps) High-Energy Cartoon Animation: `CraftyCorn_Fart_Blast`
      - Act 1 (Frames 1..9):   Deep squat, tummy clench, trembling strain & tight brow squint
      - Act 2 (Frames 10..14): Explosive rocket recoil jump + 3-stage green/lime/purple 3D cartoon fart cloud + shockwave ring
      - Act 3 (Frames 15..26): Mid-air hop & cushion landing on cyan hooves
      - Act 4 (Frames 27..36): Turn to camera, hoof-fanning cloud behind back & unicorn giggle!
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
        # Frame 12: KABOOM-TOOT! Big upward/forward rocket jump + wide-eyed unicorn gasp!
        (12,  0.14,  0.06,  0.28, -0.16, -0.22,  0.16, -0.08, -0.26, -0.12,  0.35, -0.20, -0.48, -0.20,  0.48,  0.24, -0.42,  0.000),
        # Frame 14: Peak of the toot blast — legs dangling, mouth wide open, flower pendant flying!
        (14,  0.17,  0.08,  0.22, -0.18, -0.24,  0.24, -0.12, -0.30, -0.14,  0.40, -0.25, -0.54, -0.25,  0.54,  0.28, -0.48,  0.000),
        # Frame 19: Mid-air hop & secondary toot ripple
        (19,  0.10,  0.05,  0.14, -0.10, -0.14,  0.26, -0.10, -0.22, -0.08,  0.25, -0.12, -0.38, -0.15,  0.40,  0.16, -0.30,  0.000),
        # Frame 23: Landing cushion bounce on cyan hooves
        (23, -0.04,  0.01,  0.08,  0.04,  0.04,  0.28, -0.12, -0.12,  0.04, -0.10,  0.38, -0.15, -0.10,  0.25, -0.08,  0.12,  0.000),
        # Frames 26, 29, 32: Cheeky hoof-wafting behind back (Arm.L fans the green cloud!) + unicorn giggle!
        (26,  0.02,  0.00,  0.04, -0.04, -0.08,  0.30, -0.16, -0.26,  0.08,  0.18,  0.62, -0.32, -0.18,  0.32,  0.00, -0.15,  0.000),
        (29, -0.01,  0.00,  0.05,  0.02,  0.02,  0.26, -0.10, -0.06,  0.12, -0.08,  0.42,  0.12, -0.08,  0.18,  0.00,  0.10,  0.000),
        (32,  0.02,  0.00,  0.02, -0.03, -0.06,  0.20, -0.14, -0.22,  0.06,  0.14,  0.58, -0.28, -0.14,  0.26,  0.00, -0.10,  0.000),
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

    # Stage 1: Nozzle Jet & Shockwave Ring (`FartCloud.1`)
    fc1_keys = [
        (1,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (9,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (10, 0.30,   0.0, -0.08, -0.02, 0.00),
        (12, 1.05,   0.0, -0.04, -0.06, 0.25),
        (15, 1.32,   0.0,  0.04, -0.16, 0.65),
        (19, 1.10,   0.0,  0.10, -0.26, 1.10),
        (24, 0.65,   0.0,  0.18, -0.36, 1.55),
        (29, 0.22,   0.0,  0.24, -0.44, 1.95),
        (32, 0.0001, 0.0,  0.00,  0.00, 0.00),
        (36, 0.0001, 0.0,  0.00,  0.00, 0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc1_keys:
        key_char_bone(f, "FartCloud.1", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    # Stage 2: Giant Billowing Cauliflower Lime Cloud (`FartCloud.2`)
    fc2_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (10, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (12, 0.68,    0.00, -0.02, -0.04,  0.00),
        (15, 1.22,   -0.02,  0.06, -0.14, -0.18),
        (19, 1.48,   -0.04,  0.16, -0.28, -0.38),
        (24, 1.38,   -0.06,  0.28, -0.42, -0.60),
        (29, 0.92,   -0.08,  0.42, -0.56, -0.85),
        (33, 0.35,   -0.10,  0.54, -0.68, -1.05),
        (35, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (36, 0.0001,  0.00,  0.00,  0.00,  0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc2_keys:
        key_char_bone(f, "FartCloud.2", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    # Stage 3: Outer Expanding Puff Balls & Curly Stink Ribbons (`FartCloud.3`)
    fc3_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (12, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (14, 0.62,    0.00,  0.02, -0.05,  0.00),
        (18, 1.18,    0.03,  0.12, -0.18,  0.15),
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


fart_act, fart_track = bake_action_to_nla("CraftyCorn_Fart_Blast", 36, build_craftycorn_fart_blast)
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
# and set `sub.levels = 1` so `.obj` stays under 5MB!
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
sub.levels = 1
bpy.context.view_layer.update()

bpy.ops.wm.obj_export(
    filepath=OBJ_PATH,
    export_selected_objects=True,
    export_materials=True,
    apply_modifiers=False,
    export_uv=False,
    export_normals=False,
)


# ==============================================================================
# 8. STUDIO CYCLORAMA & HIGH-CONTRAST CYCLES LIGHTING
# ==============================================================================
bpy.ops.mesh.primitive_plane_add(size=24.0, location=(0.0, 0.0, 0.0))
ground_obj = bpy.context.active_object
ground_obj.name = "Studio_Cyclorama_Floor"
studio_col.objects.link(ground_obj)
scene.collection.objects.unlink(ground_obj)
ground_mat = create_plush_material(
    "Studio_Cyc_Neutral", 0xDDE2EB, roughness=0.90, spec_ior=0.1,
    sheen=0.0, bump_strength=0.0, emission_strength=0.12
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


add_area_light("Key_Softbox", (-2.4, -3.6, 3.2), (0.0, 0.0, 1.45), energy=190.0, size=3.0, color_rgb=(1.0, 0.99, 0.98))
add_area_light("Fill_Softbox", (2.6, -3.2, 2.4), (0.0, 0.0, 1.35), energy=120.0, size=3.4, color_rgb=(0.95, 0.98, 1.0))
add_area_light("Top_Softbox", (0.0, -0.8, 4.2), (0.0, 0.0, 1.65), energy=130.0, size=3.2, color_rgb=(1.0, 1.0, 1.0))
add_area_light("Rim_Backlight", (0.0, 3.0, 3.0), (0.0, 0.0, 1.50), energy=150.0, size=2.6, color_rgb=(0.92, 0.98, 1.0))

world = bpy.data.worlds.new("CraftyCornStudioWorld")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = hex_to_rgba(0xDCE1EA)
    bg_node.inputs[1].default_value = 0.95

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


def aim_camera(loc, target=(0.0, 0.0, 1.42), lens=60.0):
    cam_data.lens = lens
    cam_obj.location = Vector(loc)
    direction = Vector(target) - Vector(loc)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


# ==============================================================================
# 9. RENDER REST-POSE STUDIO TURNAROUND VIEWS (FRONT 1080x1350, 3/4 & SIDE)
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

# Ensure rest pose with hidden fart clouds for studio turnaround renders
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
scene.frame_set(1)

# 1. Hero Front Cycles Studio Render (1080x1350)
scene.cycles.samples = 48
scene.render.resolution_x = 1080
scene.render.resolution_y = 1350
aim_camera((0.0, -6.10, 1.48), target=(0.0, 0.0, 1.40), lens=60.0)
scene.render.filepath = RENDER_FRONT_PATH
bpy.ops.render.render(write_still=True)

# 2. 3/4 & Side Turnaround Views for 4-panel preview sheet (800x1000)
scene.cycles.samples = 32
scene.render.resolution_x = 800
scene.render.resolution_y = 1000

aim_camera((-4.25, -4.35, 1.54), target=(0.0, 0.0, 1.40), lens=60.0)
scene.render.filepath = os.path.join(RENDER_SHEET_DIR, "cycles_3q.png")
bpy.ops.render.render(write_still=True)

aim_camera((-6.10, 0.0, 1.48), target=(0.0, 0.0, 1.40), lens=60.0)
scene.render.filepath = os.path.join(RENDER_SHEET_DIR, "cycles_side.png")
bpy.ops.render.render(write_still=True)


# ==============================================================================
# 10. RENDER THE 36-FRAME `CraftyCorn_Fart_Blast` CYCLES ANIMATION SEQUENCE!
# ==============================================================================
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = (trk.name != "CraftyCorn_Fart_Blast")

aim_camera((4.95, -3.65, 1.54), target=(-0.05, 0.36, 1.24), lens=54.0)

scene.frame_start = 1
scene.frame_end = 36
scene.frame_set(14)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)

scene.cycles.samples = 24
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.fps = 24

for f in range(1, 37):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(FART_FRAMES_DIR, f"frame_{f:03d}.png")
    bpy.ops.render.render(write_still=True)

print("SUCCESS: Rendered CraftyCorn studio views and 36-frame CraftyCorn_Fart_Blast animation!")
print(f"  BLEND: {BLEND_PATH} ({os.path.getsize(BLEND_PATH)} bytes)")
print(f"  GLB:   {GLB_PATH} ({os.path.getsize(GLB_PATH)} bytes)")
print(f"  OBJ:   {OBJ_PATH} ({os.path.getsize(OBJ_PATH)} bytes)")
print(f"  FRONT: {RENDER_FRONT_PATH} ({os.path.getsize(RENDER_FRONT_PATH)} bytes)")
