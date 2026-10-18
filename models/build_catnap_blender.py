#!/usr/bin/env python3
"""
Native Blender 4.3 Builder, Rigging, Animation & Cycles Studio Renderer
for CatNap (#022 / #035 Official Plush Base Model - Smiling Critters).

Builds:
  - 25-bone `CatNap_Armature` (including `Tail`, `Pendant`, `Ear.L/R`, `Eyelid.L/R`, `FartCloud.1/2/3`)
  - 6 Baked NLA Animation Clips (`Idle_Breathe`, `Walk_Cycle`, `Happy_Bounce`, `Wave_Paw`, `Curious_Head_Tilt`, `CatNap_Fart_Blast`)
  - `.blend`, `.glb`, `.obj`/`.mtl` (with `sub.levels = 1` < 5MB)
  - `catnap_blender_cycles_render.png` (1080x1350 Cycles studio render)
  - `catnap_3d_preview.png` (1920x600 4-panel Reference `022_CatNap_Plushie.webp` vs. Cycles Front / 3/4 / Side sheet)
  - 36-frame `CatNap_Fart_Blast` Cycles animation sequence in `/tmp/work_catnap/frames`

Run headless via:
  /tmp/blender/blender --threads 8 -b --factory-startup --python-exit-code 1 -P /tmp/smiling-critters-assets/models/build_catnap_blender.py
"""

import os
import math
import subprocess
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, noise

OUT_DIR = "/tmp/smiling-critters-assets/models"
ANIM_DIR = "/tmp/smiling-critters-assets/animations"
WORK_DIR = "/tmp/work_catnap"
RENDER_SHEET_DIR = os.path.join(WORK_DIR, "renders")
FART_FRAMES_DIR = os.path.join(WORK_DIR, "frames")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANIM_DIR, exist_ok=True)
os.makedirs(RENDER_SHEET_DIR, exist_ok=True)
os.makedirs(FART_FRAMES_DIR, exist_ok=True)

BLEND_PATH = os.path.join(OUT_DIR, "catnap_plush_base_model.blend")
GLB_PATH = os.path.join(OUT_DIR, "catnap_plush_base_model.glb")
OBJ_PATH = os.path.join(OUT_DIR, "catnap_plush_base_model.obj")
RENDER_FRONT_PATH = os.path.join(OUT_DIR, "catnap_blender_cycles_render.png")
RENDER_PREVIEW_PATH = os.path.join(OUT_DIR, "catnap_3d_preview.png")
REF_IMAGE_PATH = "/tmp/smiling-critters-assets/images/022_CatNap_Plushie.webp"


# ==============================================================================
# 1. SCENE RESET & HELPER UTILITIES
# ==============================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

main_col = bpy.data.collections.new("CatNap_Plush_Rig")
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
    cheek_flare = 1.0 + 0.14 * math.exp(-((y_up - 1.86) / 0.24) ** 2)
    rx_eff = 0.76 * cheek_flare
    nx = x / rx_eff
    ny = (y_up - 1.94) / 0.65
    r2 = min(0.94, nx * nx + ny * ny)
    return 0.65 * math.sqrt(max(0.06, 1.0 - r2))


def plush_fleece_displacement(p_world):
    """Subtle multi-octave 3D plush micro-fleece displacement."""
    q1 = Vector((p_world.x * 8.0, p_world.y * 8.0, p_world.z * 8.0))
    q2 = Vector((p_world.x * 18.0 + 2.1, p_world.y * 18.0 - 1.4, p_world.z * 18.0 + 1.9))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    return 0.007 * n1 + 0.003 * abs(n2)


def cloud_puff_displacement(p_world):
    """Billowing cartoon cloud displacement for 3D Fart Cloud."""
    q1 = Vector((p_world.x * 7.5, p_world.y * 7.5, p_world.z * 7.5))
    q2 = Vector((p_world.x * 16.0 + 3.1, p_world.y * 16.0 - 1.7, p_world.z * 16.0 + 2.3))
    q3 = Vector((p_world.x * 32.0 - 4.2, p_world.y * 32.0 + 5.1, p_world.z * 32.0 - 1.9))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    n3 = noise.noise(q3)
    return 0.036 * n1 + 0.018 * abs(n2) + 0.009 * n3


# ==============================================================================
# 2. PROCEDURAL CYCLES / GLTF PBR MATERIALS (CATNAP PURPLE PLUSH + FART CLOUD)
# ==============================================================================
def create_plush_material(name, hex_color, roughness=0.84, spec_ior=0.14,
                          sheen=0.32, sheen_tint_mult=1.08,
                          bump_scale=75.0, bump_strength=0.16,
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
    set_bsdf_input(bsdf, 0.72, "Sheen Roughness")
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
        bump.inputs["Distance"].default_value = 0.018

        links.new(tex_coord.outputs["Object"], noise_node.inputs["Vector"])
        links.new(noise_node.outputs["Fac"], bump.inputs["Height"])
        links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])

    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


MATS = {
    # Royal lavender/purple plush fleece body (#6B3FA0 under studio lighting)
    "PlushPurple": create_plush_material(
        "CatNap_Plush_Royal_Purple", 0x562D8E, roughness=0.85, spec_ior=0.11,
        sheen=0.22, sheen_tint_mult=1.05, bump_scale=82.0, bump_strength=0.18, subsurface=0.02
    ),
    # Lighter pastel lavender belly & inner ears (#B89CE0)
    "PastelLavender": create_plush_material(
        "CatNap_Pastel_Lavender", 0xB497DC, roughness=0.80, spec_ior=0.14,
        sheen=0.28, sheen_tint_mult=1.05, bump_scale=90.0, bump_strength=0.14, subsurface=0.03
    ),
    # Darker royal purple paws (#4A2574)
    "DarkPawPurple": create_plush_material(
        "CatNap_Dark_Paw_Purple", 0x38195C, roughness=0.86, spec_ior=0.10,
        sheen=0.20, sheen_tint_mult=1.05, bump_scale=88.0, bump_strength=0.16, subsurface=0.01
    ),
    # Deep violet seam & inner ear shadow groove (#311652)
    "SeamPurple": create_plush_material(
        "CatNap_Seam_Deep_Violet", 0x311652, roughness=0.88, spec_ior=0.08,
        sheen=0.18, sheen_tint_mult=1.0, bump_scale=95.0, bump_strength=0.12
    ),
    # Iconic Gold Crescent Moon Pendant (#F5C518)
    "GoldPendant": create_plush_material(
        "CatNap_Gold_Moon_Pendant", 0xF5C518, roughness=0.24, spec_ior=0.45,
        sheen=0.10, sheen_tint_mult=1.0, bump_scale=120.0, bump_strength=0.02,
        metallic=0.78, coat=0.32, coat_rough=0.08, emission_strength=0.06
    ),
    # Deep jet-black glossy acrylic dome eyes
    "EyeGloss": create_plush_material(
        "CatNap_Eye_Acrylic_Black", 0x020204, roughness=0.04, spec_ior=0.14,
        sheen=0.0, bump_strength=0.0, coat=0.35, coat_rough=0.015
    ),
    # White crescent eye-shines & studio catchlights
    "CatchlightWhite": create_plush_material(
        "CatNap_Eye_Crescent_Shine_White", 0xFFFFFF, roughness=0.05, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, emission_strength=0.42
    ),
    # Pitch-black recessed grinning mouth interior
    "MouthVoidBlack": create_plush_material(
        "CatNap_Mouth_Cavity_Black", 0x010102, roughness=0.99, spec_ior=0.01,
        sheen=0.0, bump_strength=0.0
    ),
    # Black velvet cat nose & zipper track
    "ZipperTrack": create_plush_material(
        "CatNap_Nose_And_Zipper_Black", 0x0C0C10, roughness=0.72, spec_ior=0.12,
        sheen=0.12, bump_scale=110.0, bump_strength=0.06
    ),
    # Brushed dark gunmetal/silver zipper teeth
    "ZipperMetal": create_plush_material(
        "CatNap_Zipper_Metal", 0xC8CDD6, roughness=0.22, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, metallic=0.92, coat=0.28
    ),
    # 3D Cartoon Fart Cloud Materials (Vibrant Toxic Lime, Neon Blast Core, Nightmare Lavender Swirl)
    "FartCloudLime": create_plush_material(
        "CatNap_Fart_Cloud_Lime", 0x4CE629, roughness=0.68, spec_ior=0.18,
        sheen=0.45, sheen_tint_mult=1.15, bump_scale=24.0, bump_strength=0.22,
        subsurface=0.35, emission_strength=0.28
    ),
    "FartCloudNeon": create_plush_material(
        "CatNap_Fart_Cloud_Neon_YellowGreen", 0xC4FF33, roughness=0.45, spec_ior=0.25,
        sheen=0.35, sheen_tint_mult=1.1, bump_scale=30.0, bump_strength=0.14,
        subsurface=0.25, emission_strength=0.55
    ),
    "FartCloudPurple": create_plush_material(
        "CatNap_Fart_Cloud_RedGas_Purple", 0x9D4EDD, roughness=0.62, spec_ior=0.20,
        sheen=0.40, sheen_tint_mult=1.1, bump_scale=28.0, bump_strength=0.18,
        subsurface=0.25, emission_strength=0.35
    ),
}


# ==============================================================================
# 3. CATNAP GEOMETRY BUILDER (BMESH + SKIN WEIGHTS FOR 25-BONE ARMATURE)
# ==============================================================================
master_bm = bmesh.new()
deform_layer = master_bm.verts.layers.deform.verify()

# 25-Bone CatNap_Armature
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
    "Pendant",
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

MAT_KEYS_ORDER = [
    "PlushPurple",
    "PastelLavender",
    "DarkPawPurple",
    "SeamPurple",
    "GoldPendant",
    "EyeGloss",
    "CatchlightWhite",
    "MouthVoidBlack",
    "ZipperTrack",
    "ZipperMetal",
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


def make_torus_tube_bm(curve_pts, radius_fn, radial_segs=18, closed=False):
    """Builds a smooth tube along `curve_pts` using parallel-transport frames (zero twist/pinch)."""
    bm = bmesh.new()
    n_pts = len(curve_pts)
    rings = []
    prev_normal = None

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

        if prev_normal is None:
            up_ref = Vector((0, 1, 0)) if abs(tangent.y) < 0.85 else Vector((0, 0, 1))
            normal = tangent.cross(up_ref).normalized()
        else:
            proj = prev_normal - tangent * prev_normal.dot(tangent)
            if proj.length > 1e-5:
                normal = proj.normalized()
            else:
                up_ref = Vector((0, 1, 0)) if abs(tangent.y) < 0.85 else Vector((0, 0, 1))
                normal = tangent.cross(up_ref).normalized()
        prev_normal = normal
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
# 3.1 ROYAL PURPLE PLUSH CAT HEAD (WIDE CHEEK FLARE MATCHING #022 / #035)
# ------------------------------------------------------------------------------
def cat_head_deform(p):
    cheek_flare = 1.0 + 0.14 * math.exp(-((p.y + 0.08) / 0.24) ** 2)
    p.x *= cheek_flare
    if p.y > 0.35:
        p.y = 0.35 + (p.y - 0.35) * 0.86
    return p


def cat_head_world_displace(p_w, n_w):
    in_face_zone = (p_w.z > 0.44 and 1.40 < p_w.y < 2.22 and abs(p_w.x) < 0.56)
    scale = 0.25 if in_face_zone else 1.0
    return p_w + n_w * (plush_fleece_displacement(p_w) * scale)


head_core_bm = make_uv_sphere_bm(
    0.76, 0.65, 0.65, cx=0.0, cy=1.94, cz=0.0,
    u_segs=48, v_segs=36,
    deform_fn=cat_head_deform,
    world_deform_fn=cat_head_world_displace
)
append_bmesh_part(
    head_core_bm, "PlushPurple",
    lambda x, y, z: {
        "Jaw": max(0.0, min(0.55, (1.62 - y) * 1.6)) if (z > 0.15 and y < 1.62) else 0.0,
        "Head": 1.0 - (max(0.0, min(0.55, (1.62 - y) * 1.6)) if (z > 0.15 and y < 1.62) else 0.0),
    }
)


# ------------------------------------------------------------------------------
# 3.2 POINTED UPRIGHT TRIANGULAR CAT EARS (`Ear.L`, `Ear.R`) WITH PASTEL INNER EARS
# ------------------------------------------------------------------------------
def make_triangular_cat_ear_bm(side, is_inner=False):
    """Builds a plump upright triangular plush cat ear with smooth base blend & rounded tip."""
    bm = bmesh.new()
    v_rings = 18
    u_segs = 28
    height = 0.42 if is_inner else 0.56
    base_w = 0.165 if is_inner else 0.255
    base_d = 0.038 if is_inner else 0.125

    rot_m = Euler((0.06, -side * 0.06, -side * 0.18), 'XYZ').to_matrix()
    # Tuck outer ear base inside the head sphere so the join is 100% seamless
    origin = Vector((side * 0.36, 2.40 if is_inner else 2.30, 0.065 if is_inner else 0.015))

    rings = []
    for iv in range(v_rings):
        t = iv / (v_rings - 1)
        # Plump triangular cat ear taper with softly rounded tip
        profile = ((1.0 - t * 0.90) ** 0.62) * math.sqrt(max(0.015, 1.0 - (t * 0.97) ** 2))
        w = base_w * profile
        d = base_d * (0.38 + 0.62 * (1.0 - t * 0.85))
        ly = t * height
        ring = []
        for iu in range(u_segs):
            ang = 2.0 * math.pi * iu / u_segs
            lx = math.cos(ang) * w
            lz = math.sin(ang) * d
            if not is_inner and lz > 0:
                scoop = math.exp(-(lx / max(0.04, w * 0.68)) ** 2) * math.sin(math.pi * min(1.0, t * 1.10))
                lz *= (1.0 - 0.38 * scoop)
            lx += side * 0.025 * (t ** 1.3)
            p_world = (rot_m @ Vector((lx, ly, lz))) + origin
            ring.append(bm.verts.new(p_world))
        rings.append(ring)

    c_base = bm.verts.new(origin)
    for iu in range(u_segs):
        iun = (iu + 1) % u_segs
        bm.faces.new([c_base, rings[0][iun], rings[0][iu]])

    for iv in range(v_rings - 1):
        r1 = rings[iv]
        r2 = rings[iv + 1]
        for iu in range(u_segs):
            iun = (iu + 1) % u_segs
            bm.faces.new([r1[iu], r2[iu], r2[iun], r1[iun]])

    tip_pos = (rot_m @ Vector((side * 0.025, height + 0.010, 0.0))) + origin
    c_tip = bm.verts.new(tip_pos)
    for iu in range(u_segs):
        iun = (iu + 1) % u_segs
        bm.faces.new([c_tip, rings[-1][iu], rings[-1][iun]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


for side in (-1, 1):
    ear_bone = "Ear.L" if side == 1 else "Ear.R"
    ear_out_bm = make_triangular_cat_ear_bm(side, is_inner=False)
    append_bmesh_part(
        ear_out_bm, "PlushPurple",
        lambda x, y, z, b=ear_bone: {b: 0.88, "Head": 0.12}
    )
    ear_in_bm = make_triangular_cat_ear_bm(side, is_inner=True)
    append_bmesh_part(
        ear_in_bm, "PastelLavender",
        lambda x, y, z, b=ear_bone: {b: 0.92, "Head": 0.08}
    )


# ------------------------------------------------------------------------------
# 3.3 GLOSSY BLACK EYES, WHITE CRESCENT EYE-SHINES & PLUSH SOCKET BROWS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    lid_bone = "Eyelid.L" if side == 1 else "Eyelid.R"
    ex = side * 0.245
    ey = 2.045
    ez = 0.575

    socket_bm = make_uv_sphere_bm(
        0.195, 0.192, 0.115,
        cx=ex, cy=ey, cz=ez - 0.015,
        u_segs=30, v_segs=22,
        rot_euler=(-0.05, side * 0.18, 0.0)
    )
    append_bmesh_part(socket_bm, "SeamPurple", lambda x, y, z: {"Head": 1.0})

    eye_bm = make_uv_sphere_bm(
        0.182, 0.180, 0.135,
        cx=ex, cy=ey, cz=ez,
        u_segs=36, v_segs=28,
        rot_euler=(-0.05, side * 0.18, 0.0)
    )
    append_bmesh_part(eye_bm, "EyeGloss", lambda x, y, z: {"Head": 1.0})

    # Iconic White Crescent Eye-Shine inside the upper-inner eye dome
    cres_pts = []
    rot_eye = Euler((-0.05, side * 0.18, 0.0), 'XYZ').to_matrix()
    for k in range(15):
        t = k / 14.0
        ang = 0.35 * math.pi + t * 0.85 * math.pi
        lx = -side * 0.025 + math.cos(ang) * 0.068
        ly = 0.015 + math.sin(ang) * 0.068
        lz = math.sqrt(max(0.02, 1.0 - (lx / 0.182) ** 2 - (ly / 0.180) ** 2)) * 0.137
        pw = (rot_eye @ Vector((lx, ly, lz))) + Vector((ex, ey, ez))
        cres_pts.append((pw.x, pw.y, pw.z))

    cres_bm = make_torus_tube_bm(
        cres_pts,
        lambda t: 0.020 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=12, closed=False
    )
    append_bmesh_part(cres_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    pin_bm = make_uv_sphere_bm(
        0.018, 0.018, 0.010,
        cx=ex + side * 0.055, cy=ey - 0.048, cz=ez + 0.125,
        u_segs=12, v_segs=10
    )
    append_bmesh_part(pin_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    brow_pts = []
    for k in range(19):
        t = -1.0 + 2.0 * k / 18.0
        lx = t * 0.195
        ly = 0.135 - 0.055 * (t * t)
        lz = math.sqrt(max(0.02, 1.0 - min(0.95, (lx / 0.20) ** 2 + (ly / 0.20) ** 2))) * 0.142
        pw = (rot_eye @ Vector((lx, ly, lz))) + Vector((ex, ey, ez))
        brow_pts.append((pw.x, pw.y, pw.z))

    brow_bm = make_torus_tube_bm(
        brow_pts,
        lambda t: 0.028 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=14, closed=False
    )
    append_bmesh_part(
        brow_bm, "PlushPurple",
        lambda x, y, z, b=lid_bone: {b: 0.90, "Head": 0.10}
    )


# ------------------------------------------------------------------------------
# 3.4 SCULPTED BLACK TRIANGULAR CAT NOSE & WIDE CAVERNOUS GRINNING MOUTH
# ------------------------------------------------------------------------------
muzzle_bm = make_uv_sphere_bm(
    0.22, 0.105, 0.125,
    cx=0.0, cy=1.875, cz=0.615,
    u_segs=28, v_segs=20,
    rot_euler=(-0.05, 0.0, 0.0)
)
append_bmesh_part(muzzle_bm, "PlushPurple", lambda x, y, z: {"Head": 1.0})


def cat_nose_deform(p):
    t_vert = (p.y / 0.058 + 1.0) * 0.5
    p.x *= (0.35 + 0.85 * t_vert)
    if p.y > 0.02:
        p.y = 0.02 + (p.y - 0.02) * 0.55
    return p


nose_bm = make_uv_sphere_bm(
    0.082, 0.058, 0.048,
    cx=0.0, cy=1.905, cz=0.720,
    u_segs=24, v_segs=18,
    rot_euler=(-0.12, 0.0, 0.0),
    deform_fn=cat_nose_deform
)
append_bmesh_part(nose_bm, "ZipperTrack", lambda x, y, z: {"Head": 1.0})


def upper_lip_curve_pt(t):
    """Exact 3D point on the upper cat-smile lip for t in [-1, 1]."""
    lx = t * 0.56
    ly = 1.805 + 0.145 * (t * t) - 0.015 * (t ** 4)
    lz = head_front_z(lx, ly) + 0.028 * (1.0 - 0.32 * t * t)
    return Vector((lx, ly, lz))


def lower_lip_curve_pt(t):
    """Exact 3D point on the deep lower grin lip for t in [-1, 1]."""
    lx = t * 0.56
    ly = 1.400 + 0.535 * (t * t)
    lz = head_front_z(lx, ly) + 0.024 * (1.0 - 0.30 * t * t)
    return Vector((lx, ly, lz))


def build_catnap_mouth_cavity_bm():
    """
    Conforms the pitch-black mouth cavity strictly INSIDE `upper_lip_curve_pt(t)`
    and `lower_lip_curve_pt(t)` while sitting cleanly in front of `head_core_bm`
    so the entire wide grinning mouth is solid pitch black with zero edge bleed.
    """
    bm = bmesh.new()
    cols = 44
    rows = 18
    grid = []
    for r in range(rows + 1):
        v = r / rows  # 0 = lower lip centerline, 1 = upper lip centerline
        ring = []
        for c in range(cols + 1):
            t = -0.985 + 1.970 * (c / cols)
            p_low = lower_lip_curve_pt(t)
            p_up = upper_lip_curve_pt(t)
            ux = p_low.x * (1.0 - v) + p_up.x * v
            uy = p_low.y * (1.0 - v) + p_up.y * v
            # Sit +0.014m..+0.020m in front of the purple head surface, while staying
            # tucked inside the 0.040m-radius upper/lower lip tubes at v=0 and v=1
            uz = head_front_z(ux, uy) + 0.014 + 0.006 * math.sin(math.pi * v)
            ring.append(bm.verts.new((ux, uy, uz)))
        grid.append(ring)

    for r in range(rows):
        for c in range(cols):
            bm.faces.new([grid[r][c], grid[r][c + 1], grid[r + 1][c + 1], grid[r + 1][c]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


mouth_bm = build_catnap_mouth_cavity_bm()
append_bmesh_part(
    mouth_bm, "MouthVoidBlack",
    lambda x, y, z: {
        "Jaw": max(0.0, min(1.0, (1.76 - y) * 2.6)),
        "Head": 1.0 - max(0.0, min(1.0, (1.76 - y) * 2.6)),
    }
)

# Subtle dark embossed circular voicebox disc inside the mouth cavity (from #022 reference!)
voicebox_bm = make_uv_sphere_bm(
    0.095, 0.095, 0.010,
    cx=0.0, cy=1.64, cz=head_front_z(0.0, 1.64) + 0.020,
    u_segs=24, v_segs=16,
    rot_euler=(-0.10, 0.0, 0.0)
)
append_bmesh_part(voicebox_bm, "ZipperTrack", lambda x, y, z: {"Head": 0.6, "Jaw": 0.4})

upper_lip_pts = [tuple(upper_lip_curve_pt(-1.0 + 2.0 * k / 40.0)) for k in range(41)]
upper_lip_bm = make_torus_tube_bm(
    upper_lip_pts,
    lambda t: 0.040 + 0.014 * math.sin(math.pi * t),
    radial_segs=18, closed=False
)
append_bmesh_part(upper_lip_bm, "PlushPurple", lambda x, y, z: {"Head": 0.90, "Jaw": 0.10})

lower_lip_pts = [tuple(lower_lip_curve_pt(-1.0 + 2.0 * k / 44.0)) for k in range(45)]
lower_lip_bm = make_torus_tube_bm(
    lower_lip_pts,
    lambda t: 0.038 + 0.010 * math.sin(math.pi * t),
    radial_segs=18, closed=False
)
append_bmesh_part(
    lower_lip_bm, "PlushPurple",
    lambda x, y, z: {
        "Jaw": max(0.0, min(1.0, (1.76 - y) * 2.5)),
        "Head": 1.0 - max(0.0, min(1.0, (1.76 - y) * 2.5)),
    }
)

for side in (-1, 1):
    p_c = upper_lip_curve_pt(side)
    corner_bm = make_uv_sphere_bm(
        0.045, 0.045, 0.042,
        cx=p_c.x, cy=p_c.y, cz=p_c.z,
        u_segs=16, v_segs=12
    )
    append_bmesh_part(corner_bm, "PlushPurple", lambda x, y, z: {"Head": 0.92, "Jaw": 0.08})


# ------------------------------------------------------------------------------
# 3.5 ROYAL PURPLE PLUSH TORSO, PASTEL LAVENDER BELLY, ZIPPER & GOLD MOON PENDANT
# ------------------------------------------------------------------------------
TORSO_PROFILE = [
    (0.00, 0.50), (0.18, 0.52), (0.35, 0.56), (0.46, 0.65),
    (0.51, 0.78), (0.52, 0.92), (0.49, 1.06), (0.45, 1.20),
    (0.39, 1.33), (0.33, 1.43), (0.26, 1.50), (0.00, 1.52)
]


def exact_torso_radius(y):
    for i in range(len(TORSO_PROFILE) - 1):
        r0, y0 = TORSO_PROFILE[i]
        r1, y1 = TORSO_PROFILE[i + 1]
        if y0 <= y <= y1:
            t = (y - y0) / max(1e-5, y1 - y0)
            return r0 + (r1 - r0) * t
    return 0.35


def torso_front_z(y, x=0.0):
    r = exact_torso_radius(y)
    nx = min(0.92, abs(x) / max(0.10, r))
    return r * 0.88 * math.sqrt(max(0.08, 1.0 - nx * nx))


def build_torso_bm():
    bm = bmesh.new()
    u_segs = 44
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
        t = min(1.0, (y - 1.12) / 0.36)
        return {"Spine": max(0.0, 0.4 * (1.0 - t)), "Chest": 1.0 - 0.4 * (1.0 - t)}


torso_bm = build_torso_bm()
append_bmesh_part(torso_bm, "PlushPurple", torso_weights)


# Pastel Lavender Belly Patch smoothly contoured over exact_torso_radius(y)
def build_belly_patch_bm():
    bm = bmesh.new()
    u_steps = 32
    v_steps = 14
    grid = []
    for iv in range(v_steps + 1):
        vf = iv / v_steps
        ring = []
        for iu in range(u_steps):
            ang = 2.0 * math.pi * iu / u_steps
            bx = math.cos(ang) * 0.25 * vf
            by = 0.94 + math.sin(ang) * 0.29 * vf
            bx *= (1.0 - 0.14 * ((by - 0.94) / 0.29))
            # Sit cleanly +0.012m outside the exact torso surface in the interior, tucking in at the rim (vf=1)
            bz = torso_front_z(by, bx) + 0.012 * math.cos(vf * math.pi * 0.52)
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
append_bmesh_part(belly_bm, "PastelLavender", torso_weights)

# Black Zipper Track & Collar Line
zip_pts = [
    (0.0, 0.56 + (1.42 - 0.56) * k / 24.0, torso_front_z(0.56 + (1.42 - 0.56) * k / 24.0) + 0.018)
    for k in range(25)
]
zip_track_bm = make_torus_tube_bm(zip_pts, 0.024, radial_segs=12, closed=False)
append_bmesh_part(zip_track_bm, "ZipperTrack", torso_weights)

for i in range(34):
    zy = 0.58 + (1.38 - 0.58) * (i / 33.0)
    zz = torso_front_z(zy) + 0.028
    zx = (0.010 if (i % 2 == 0) else -0.010)
    t_bm = make_beveled_box_bm(0.032, 0.013, 0.018, zx, zy, zz)
    append_bmesh_part(t_bm, "ZipperMetal", torso_weights)

# Gold Collar Zipper Slider & Bail Loop for Crescent Moon Pendant
slider_bm = make_beveled_box_bm(0.064, 0.078, 0.044, 0.0, 1.345, 0.455)
append_bmesh_part(slider_bm, "GoldPendant", lambda x, y, z: {"Chest": 0.6, "Pendant": 0.4})

bail_bm = make_beveled_box_bm(0.052, 0.065, 0.036, 0.0, 1.275, 0.478)
append_bmesh_part(bail_bm, "GoldPendant", lambda x, y, z: {"Pendant": 1.0})


def build_gold_crescent_moon_bm():
    """
    Builds a crisp, thick, smooth 3D C-shaped Gold Crescent Moon Pendant
    matching 022_CatNap_Plushie.webp and 035_Catnapplush.webp.
    """
    n_spine = 45
    radial_segs = 24
    bm = bmesh.new()
    rings = []

    cx_moon = 0.02
    cy_moon = 1.075
    cz_moon = 0.502
    r_arc = 0.148

    for i in range(n_spine):
        t = i / (n_spine - 1)
        ang = (0.28 + 1.44 * t) * math.pi
        px = cx_moon + math.cos(ang) * r_arc
        py = cy_moon + math.sin(ang) * r_arc
        pz = cz_moon + 0.008 * math.sin(math.pi * t)

        s_prof = math.sin(math.pi * t) ** 0.82
        rad_xy = 0.006 + 0.068 * s_prof
        rad_z = 0.005 + 0.026 * s_prof

        radial_dir = Vector((math.cos(ang), math.sin(ang), 0.0)).normalized()
        z_dir = Vector((0.0, 0.0, 1.0))

        center_pt = Vector((px, py, pz)) - radial_dir * (rad_xy * 0.35)
        ring = []
        for j in range(radial_segs):
            phi = 2.0 * math.pi * j / radial_segs
            offset = radial_dir * (math.cos(phi) * rad_xy) + z_dir * (math.sin(phi) * rad_z)
            ring.append(bm.verts.new(center_pt + offset))
        rings.append(ring)

    for i in range(n_spine - 1):
        r1 = rings[i]
        r2 = rings[i + 1]
        for j in range(radial_segs):
            jn = (j + 1) % radial_segs
            bm.faces.new([r1[j], r2[j], r2[jn], r1[jn]])

    ang0 = 0.28 * math.pi
    tip0 = bm.verts.new((cx_moon + math.cos(ang0) * r_arc, cy_moon + math.sin(ang0) * r_arc, cz_moon))
    for j in range(radial_segs):
        jn = (j + 1) % radial_segs
        bm.faces.new([tip0, rings[0][jn], rings[0][j]])

    ang1 = 1.72 * math.pi
    tip1 = bm.verts.new((cx_moon + math.cos(ang1) * r_arc, cy_moon + math.sin(ang1) * r_arc, cz_moon))
    for j in range(radial_segs):
        jn = (j + 1) % radial_segs
        bm.faces.new([tip1, rings[-1][j], rings[-1][jn]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


moon_bm = build_gold_crescent_moon_bm()
append_bmesh_part(moon_bm, "GoldPendant", lambda x, y, z: {"Pendant": 1.0})


# ------------------------------------------------------------------------------
# 3.6 SPLAYED PURPLE PLUSH ARMS & DARKER PURPLE CAT PAWS (`HandPaw.L/R`)
# ------------------------------------------------------------------------------
for side in (-1, 1):
    sh_bone = "Shoulder.L" if side == 1 else "Shoulder.R"
    arm_bone = "Arm.L" if side == 1 else "Arm.R"
    paw_bone = "HandPaw.L" if side == 1 else "HandPaw.R"

    arm_pts = []
    for k in range(15):
        t = k / 14.0
        ax = side * (0.31 + 0.40 * t)
        ay = 1.33 - 0.32 * t + 0.02 * math.sin(math.pi * t)
        az = 0.02 + 0.04 * t
        arm_pts.append((ax, ay, az))

    arm_bm = make_torus_tube_bm(
        arm_pts,
        lambda t: 0.135 * (1.0 + 0.04 * t),
        radial_segs=22, closed=False
    )

    def arm_weight_fn(x, y, z, sb=sh_bone, ab=arm_bone, pb=paw_bone):
        dist = max(0.0, min(1.0, (abs(x) - 0.31) / 0.45))
        if dist < 0.35:
            return {"Chest": 0.35 * (1.0 - dist / 0.35), sb: 0.65, ab: 0.35 * (dist / 0.35)}
        elif dist < 0.85:
            return {ab: 0.85, sb: 0.15}
        else:
            return {ab: 0.50, pb: 0.50}

    append_bmesh_part(arm_bm, "PlushPurple", arm_weight_fn)

    paw_pts = []
    for k in range(15):
        t = k / 14.0
        mx = side * (0.68 + 0.23 * t)
        my = 1.03 - 0.19 * t
        mz = 0.06 + 0.03 * t
        paw_pts.append((mx, my, mz))

    def paw_radius(t):
        if t < 0.14:
            return 0.138 + 0.016 * (t / 0.14)
        elif t < 0.72:
            return 0.154 + 0.010 * math.sin(math.pi * (t - 0.14) / 0.58)
        else:
            u = (t - 0.72) / 0.28
            return 0.154 * math.sqrt(max(0.02, 1.0 - u * u))

    paw_bm = make_torus_tube_bm(paw_pts, paw_radius, radial_segs=24, closed=False)
    append_bmesh_part(
        paw_bm, "DarkPawPurple",
        lambda x, y, z, pb=paw_bone, ab=arm_bone: {pb: 0.90, ab: 0.10}
    )


# ------------------------------------------------------------------------------
# 3.7 STOUT STANDING PLUSH LEGS & DARKER PURPLE FOOT PAWS (`FootPaw.L/R`)
# ------------------------------------------------------------------------------
for side in (-1, 1):
    leg_bone = "Leg.L" if side == 1 else "Leg.R"
    foot_bone = "FootPaw.L" if side == 1 else "FootPaw.R"

    leg_pts = []
    for k in range(15):
        t = k / 14.0
        lx = side * (0.235 + 0.045 * t)
        ly = 0.66 - 0.43 * t
        lz = 0.0 + 0.02 * t
        leg_pts.append((lx, ly, lz))

    leg_bm = make_torus_tube_bm(
        leg_pts,
        lambda t: 0.178 * (1.0 - 0.05 * t),
        radial_segs=24, closed=False
    )

    def leg_weight_fn(x, y, z, lb=leg_bone, fb=foot_bone):
        if y > 0.52:
            return {"Pelvis": 0.45, lb: 0.55}
        elif y > 0.25:
            return {lb: 0.90, fb: 0.10}
        else:
            return {lb: 0.25, fb: 0.75}

    append_bmesh_part(leg_bm, "PlushPurple", leg_weight_fn)

    fx = side * 0.290
    fy = 0.135
    fz = 0.055

    def foot_deform(p):
        if p.y < -0.02:
            p.y = -0.115 + (p.y + 0.115) * 0.15
        return p

    foot_bm = make_uv_sphere_bm(
        0.192, 0.148, 0.220,
        cx=fx, cy=fy, cz=fz,
        u_segs=28, v_segs=20,
        rot_euler=(0.0, 0.0, 0.0),
        deform_fn=foot_deform
    )
    append_bmesh_part(
        foot_bm, "DarkPawPurple",
        lambda x, y, z, fb=foot_bone, lb=leg_bone: {fb: 0.92, lb: 0.08}
    )

    for toe_x in (-0.052, 0.052):
        fseam_pts = []
        for k in range(9):
            t = k / 8.0
            cy = 0.03 + 0.13 * t
            cz = fz + 0.208 - 0.028 * (t - 0.4) ** 2 - 0.012 * abs(toe_x)
            fseam_pts.append((fx + toe_x, cy, cz))
        fseam_bm = make_torus_tube_bm(fseam_pts, 0.006, radial_segs=8, closed=False)
        append_bmesh_part(fseam_bm, "SeamPurple", lambda x, y, z, fb=foot_bone: {fb: 1.0})


# ------------------------------------------------------------------------------
# 3.8 LONG CURLED PURPLE CAT TAIL (`Tail` BONE — TWIST-FREE PARALLEL TRANSPORT)
# ------------------------------------------------------------------------------
tail_control_pts = [
    (0.00, 0.58, -0.32),
    (-0.16, 0.50, -0.38),
    (-0.38, 0.40, -0.34),
    (-0.62, 0.29, -0.22),
    (-0.82, 0.20, -0.02),
    (-0.92, 0.14,  0.22),
    (-0.88, 0.11,  0.46),
    (-0.70, 0.10,  0.64),
    (-0.42, 0.10,  0.74),
    (-0.12, 0.11,  0.76),
    ( 0.16, 0.13,  0.70),
]


def eval_catmull_rom_chain(pts, samples_per_seg=6):
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0 = Vector(pts[max(0, i - 1)])
        p1 = Vector(pts[i])
        p2 = Vector(pts[i + 1])
        p3 = Vector(pts[min(n - 1, i + 2)])
        steps = samples_per_seg if i < n - 2 else samples_per_seg + 1
        for s in range(steps):
            if i < n - 2 and s == steps:
                continue
            t = s / samples_per_seg
            t2 = t * t
            t3 = t2 * t
            pos = 0.5 * (
                (2.0 * p1)
                + (-p0 + p2) * t
                + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2
                + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3
            )
            out.append((pos.x, pos.y, pos.z))
    return out


tail_smooth_pts = eval_catmull_rom_chain(tail_control_pts, samples_per_seg=5)


def tail_radius_fn(t):
    if t < 0.08:
        return 0.078 + 0.012 * (t / 0.08)
    elif t < 0.88:
        return 0.090 + 0.008 * math.sin(math.pi * (t - 0.08) / 0.80)
    else:
        u = (t - 0.88) / 0.12
        return 0.092 * math.sqrt(max(0.04, 1.0 - u * u))


tail_bm = make_torus_tube_bm(tail_smooth_pts, tail_radius_fn, radial_segs=20, closed=False)


def tail_weight_fn(x, y, z):
    if y > 0.48 and z < -0.25 and abs(x) < 0.25:
        return {"Pelvis": 0.45, "Tail": 0.55}
    return {"Tail": 1.0}


append_bmesh_part(tail_bm, "PlushPurple", tail_weight_fn)


# ------------------------------------------------------------------------------
# 3.9 3D SCULPTED CARTOON FART CLOUD CLUSTER (WEIGHTED TO FartCloud.1 / .2 / .3)
# ------------------------------------------------------------------------------
fart_stage1_puffs = [
    (0.00, 0.68, -0.50, 0.12, 0.11, 0.14, "FartCloudNeon"),
    (0.00, 0.69, -0.64, 0.18, 0.16, 0.18, "FartCloudLime"),
    (-0.10, 0.72, -0.68, 0.14, 0.13, 0.14, "FartCloudLime"),
    (0.10, 0.66, -0.68, 0.14, 0.13, 0.14, "FartCloudPurple"),
]
for idx, (fx, fy, fz, rx, ry, rz, mkey) in enumerate(fart_stage1_puffs):
    def fc1_disp(p_w, n_w, s=idx):
        return p_w + n_w * (cloud_puff_displacement(p_w + Vector((s * 1.1, 0.0, s * 0.7))) * 0.85)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=20, v_segs=16, world_deform_fn=fc1_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.1": 1.0})

ring_pts = []
for k in range(28):
    ang = 2.0 * math.pi * k / 28.0
    ring_pts.append((0.24 * math.cos(ang), 0.69 + 0.24 * math.sin(ang), -0.62))
shock_ring_bm = make_torus_tube_bm(ring_pts, 0.036, radial_segs=14, closed=True)
append_bmesh_part(shock_ring_bm, "FartCloudNeon", lambda x, y, z: {"FartCloud.1": 1.0})

fart_stage2_puffs = [
    (0.00, 0.76, -0.92, 0.28, 0.26, 0.28, "FartCloudLime"),
    (-0.20, 0.82, -0.96, 0.23, 0.22, 0.22, "FartCloudLime"),
    (0.20, 0.80, -0.96, 0.23, 0.22, 0.22, "FartCloudPurple"),
    (0.00, 0.94, -1.02, 0.25, 0.24, 0.24, "FartCloudNeon"),
    (-0.16, 0.64, -0.90, 0.20, 0.18, 0.20, "FartCloudLime"),
    (0.16, 0.64, -0.90, 0.20, 0.18, 0.20, "FartCloudLime"),
    (0.00, 0.78, -1.16, 0.30, 0.28, 0.28, "FartCloudLime"),
    (-0.24, 0.88, -1.14, 0.22, 0.22, 0.22, "FartCloudNeon"),
    (0.24, 0.86, -1.14, 0.22, 0.22, 0.22, "FartCloudPurple"),
    (-0.14, 0.98, -1.18, 0.21, 0.20, 0.21, "FartCloudLime"),
    (0.14, 0.98, -1.18, 0.21, 0.20, 0.21, "FartCloudPurple"),
]
for idx, (fx, fy, fz, rx, ry, rz, mkey) in enumerate(fart_stage2_puffs):
    def fc2_disp(p_w, n_w, s=idx):
        return p_w + n_w * (cloud_puff_displacement(p_w + Vector((s * 1.7, s * 0.9, 0.0))) * 1.15)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=22, v_segs=16, world_deform_fn=fc2_disp)
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
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=20, v_segs=16, world_deform_fn=fc3_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.3": 1.0})

for s_idx, (sx_off, sz_off, mkey) in enumerate([
    (-0.18, -1.15, "FartCloudNeon"),
    (0.02, -1.38, "FartCloudPurple"),
    (0.20, -1.24, "FartCloudNeon"),
]):
    swirl_pts = []
    for k in range(19):
        t = k / 18.0
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
mesh_data = bpy.data.meshes.new("CatNap_Plush_MeshData")
for m in MAT_LIST:
    mesh_data.materials.append(m)

master_bm.to_mesh(mesh_data)
master_bm.free()
mesh_data.update()

mesh_obj = bpy.data.objects.new("CatNap_Plush_Mesh", mesh_data)
main_col.objects.link(mesh_obj)

for bname in BONE_NAMES:
    mesh_obj.vertex_groups.new(name=bname)


# ==============================================================================
# 5. CREATE SKELETAL ARMATURE RIG (25 BONES) & BIND SKINNING
# ==============================================================================
arm_data = bpy.data.armatures.new("CatNap_ArmatureData")
arm_data.display_type = 'OCTAHEDRAL'
arm_obj = bpy.data.objects.new("CatNap_Armature", arm_data)
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
add_ebone("Chest", (0.0, 1.14, 0.0), (0.0, 1.52, 0.0), "Spine", True)
add_ebone("Head", (0.0, 1.52, 0.0), (0.0, 2.45, 0.0), "Chest", True)

add_ebone("Jaw", (0.0, 1.68, 0.45), (0.0, 1.44, 0.72), "Head", False)
add_ebone("Eyelid.L", (0.245, 2.045, 0.575), (0.245, 2.18, 0.74), "Head", False)
add_ebone("Eyelid.R", (-0.245, 2.045, 0.575), (-0.245, 2.18, 0.74), "Head", False)
add_ebone("Ear.L", (0.36, 2.30, 0.02), (0.50, 2.86, 0.02), "Head", False)
add_ebone("Ear.R", (-0.36, 2.30, 0.02), (-0.50, 2.86, 0.02), "Head", False)

add_ebone("Pendant", (0.0, 1.28, 0.46), (0.0, 0.92, 0.50), "Chest", False)
add_ebone("Tail", (0.0, 0.58, -0.32), (-0.65, 0.22, 0.15), "Pelvis", False)

add_ebone("Shoulder.L", (0.28, 1.34, 0.02), (0.44, 1.24, 0.03), "Chest", False)
add_ebone("Arm.L", (0.44, 1.24, 0.03), (0.71, 1.01, 0.06), "Shoulder.L", True)
add_ebone("HandPaw.L", (0.71, 1.01, 0.06), (0.91, 0.84, 0.09), "Arm.L", True)

add_ebone("Shoulder.R", (-0.28, 1.34, 0.02), (-0.44, 1.24, 0.03), "Chest", False)
add_ebone("Arm.R", (-0.44, 1.24, 0.03), (-0.71, 1.01, 0.06), "Shoulder.R", True)
add_ebone("HandPaw.R", (-0.71, 1.01, 0.06), (-0.91, 0.84, 0.09), "Arm.R", True)

add_ebone("Leg.L", (0.235, 0.66, 0.0), (0.28, 0.24, 0.02), "Pelvis", False)
add_ebone("FootPaw.L", (0.28, 0.24, 0.02), (0.29, 0.06, 0.22), "Leg.L", True)

add_ebone("Leg.R", (-0.235, 0.66, 0.0), (-0.28, 0.24, 0.02), "Pelvis", False)
add_ebone("FootPaw.R", (-0.28, 0.24, 0.02), (-0.29, 0.06, 0.22), "Leg.R", True)

# 3 Fart Cloud Bones with heads tucked inside the opaque purple Pelvis (z_fwd = -0.22)
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
# 6. AUTHOR 6 NLA / ACTION ANIMATION CLIPS ON THE ARMATURE (INCLUDING CatNap_Fart_Blast)
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
    """
    Pose and keyframe `bone_name` using intuitive character-space axes via rest-pose conjugation.
    """
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


def build_catnap_fart_blast(act):
    """
    36-Frame (1.5s @ 24fps) 4-Act Cartoon Animation: `CatNap_Fart_Blast`
      - Act 1 (Frames 1..9):   Deep squat, tummy clench, high-frequency strain tremble & tight eye squint
      - Act 2 (Frames 10..14): Explosive rocket recoil jump + 3-stage green/lime/purple 3D fart cloud + shockwave ring + stink ribbons!
      - Act 3 (Frames 15..26): Mid-air hop & cushioned cat-paw landing!
      - Act 4 (Frames 27..36): Turn to camera, paw-fanning cloud behind back & cheeky cat giggle!
    """
    body_keys = [
        (1,   0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000,  0.00),
        (4,  -0.09, -0.02,  0.22,  0.14,  0.16, -0.06,  0.00,  0.04,  0.22, -0.18,  0.22,  0.28,  0.22, -0.28, -0.22,  0.18,  0.000, -0.12),
        (6,  -0.13, -0.04,  0.30,  0.18,  0.22, -0.10,  0.05,  0.06,  0.30, -0.25,  0.30,  0.35,  0.30, -0.35, -0.28,  0.24,  0.020, -0.18),
        (8,  -0.15, -0.05,  0.34,  0.21,  0.25, -0.08, -0.05,  0.08,  0.33, -0.28,  0.33,  0.38,  0.33, -0.38, -0.31,  0.27, -0.020, -0.22),
        (9,  -0.16, -0.05,  0.36,  0.22,  0.26, -0.12,  0.05,  0.08,  0.35, -0.30,  0.35,  0.40,  0.35, -0.40, -0.32,  0.29,  0.018, -0.24),
        (11,  0.13,  0.05,  0.28, -0.15, -0.20,  0.14, -0.08, -0.24, -0.12,  0.32, -0.20, -0.46, -0.20,  0.46,  0.22, -0.40,  0.000,  0.25),
        (14,  0.18,  0.08,  0.22, -0.18, -0.24,  0.22, -0.12, -0.30, -0.14,  0.38, -0.25, -0.54, -0.25,  0.54,  0.28, -0.48,  0.000,  0.36),
        (19,  0.11,  0.05,  0.14, -0.10, -0.14,  0.26, -0.10, -0.22, -0.08,  0.25, -0.12, -0.38, -0.15,  0.40,  0.16, -0.30,  0.000,  0.22),
        (24, -0.04,  0.01,  0.08,  0.04,  0.04,  0.28, -0.12, -0.12,  0.04, -0.10,  0.38, -0.15, -0.10,  0.25, -0.08,  0.12,  0.000, -0.08),
        (27,  0.02,  0.00,  0.04, -0.04, -0.08,  0.30, -0.16, -0.26,  0.08,  0.18,  0.64, -0.32, -0.18,  0.32,  0.00, -0.15,  0.000,  0.16),
        (30, -0.01,  0.00,  0.05,  0.02,  0.02,  0.26, -0.10, -0.06,  0.12, -0.08,  0.42,  0.12, -0.08,  0.18,  0.00,  0.10,  0.000, -0.12),
        (33,  0.02,  0.00,  0.02, -0.03, -0.06,  0.20, -0.14, -0.22,  0.06,  0.14,  0.58, -0.28, -0.14,  0.26,  0.00, -0.10,  0.000,  0.14),
        (36,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000,  0.00),
    ]

    for (f, p_dy, p_dz, p_pitch, c_pitch, h_pitch, h_yaw, h_roll,
         j_pitch, l_pitch, e_roll, al_p, al_r, ar_p, ar_r, lg_p, pd_p, p_dx, tl_yaw) in body_keys:
        key_char_bone(f, "Pelvis", pitch_x=p_pitch, dx=p_dx, dy_up=p_dy, dz_fwd=p_dz)
        key_char_bone(f, "Spine", pitch_x=c_pitch * 0.5)
        key_char_bone(f, "Chest", pitch_x=c_pitch, yaw_y=h_yaw * 0.3)
        key_char_bone(f, "Head", pitch_x=h_pitch, yaw_y=h_yaw, roll_z=h_roll)
        key_char_bone(f, "Jaw", pitch_x=j_pitch)
        key_char_bone(f, "Eyelid.L", pitch_x=l_pitch)
        key_char_bone(f, "Eyelid.R", pitch_x=l_pitch)
        key_char_bone(f, "Ear.L", roll_z=-e_roll * 0.5)
        key_char_bone(f, "Ear.R", roll_z=e_roll * 0.5)
        key_char_bone(f, "Arm.L", pitch_x=al_p, roll_z=al_r)
        key_char_bone(f, "HandPaw.L", pitch_x=al_p * 0.6, roll_z=al_r * 0.5)
        key_char_bone(f, "Arm.R", pitch_x=ar_p, roll_z=ar_r)
        key_char_bone(f, "HandPaw.R", pitch_x=ar_p * 0.5, roll_z=ar_r * 0.4)
        key_char_bone(f, "Leg.L", pitch_x=lg_p)
        key_char_bone(f, "Leg.R", pitch_x=lg_p)
        key_char_bone(f, "FootPaw.L", pitch_x=-lg_p * 0.7)
        key_char_bone(f, "FootPaw.R", pitch_x=-lg_p * 0.7)
        key_char_bone(f, "Pendant", pitch_x=pd_p, roll_z=p_dx * 3.0)
        key_char_bone(f, "Tail", pitch_x=tl_yaw * 0.4, yaw_y=tl_yaw)

    fc1_keys = [
        (1,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (9,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (10, 0.42,   0.0, -0.06, -0.02, 0.00),
        (12, 1.12,   0.0, -0.02, -0.06, 0.25),
        (14, 1.35,   0.0,  0.04, -0.14, 0.60),
        (19, 1.10,   0.0,  0.10, -0.26, 1.10),
        (24, 0.65,   0.0,  0.18, -0.36, 1.55),
        (28, 0.25,   0.0,  0.24, -0.44, 1.95),
        (32, 0.0001, 0.0,  0.00,  0.00, 0.00),
        (36, 0.0001, 0.0,  0.00,  0.00, 0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc1_keys:
        key_char_bone(f, "FartCloud.1", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    fc2_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (9,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (11, 0.68,    0.00, -0.02, -0.04,  0.00),
        (14, 1.26,   -0.02,  0.06, -0.14, -0.18),
        (19, 1.48,   -0.04,  0.16, -0.28, -0.38),
        (24, 1.38,   -0.06,  0.28, -0.42, -0.60),
        (28, 1.02,   -0.08,  0.40, -0.54, -0.82),
        (33, 0.35,   -0.10,  0.54, -0.68, -1.05),
        (35, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (36, 0.0001,  0.00,  0.00,  0.00,  0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc2_keys:
        key_char_bone(f, "FartCloud.2", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    fc3_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (11, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (14, 0.72,    0.00,  0.02, -0.05,  0.00),
        (19, 1.28,    0.03,  0.14, -0.20,  0.18),
        (24, 1.46,    0.05,  0.26, -0.34,  0.34),
        (28, 1.34,    0.08,  0.42, -0.50,  0.52),
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
        key_char_bone(f, "Ear.L", roll_z=0.05 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.05 * s)
        key_char_bone(f, "Arm.L", pitch_x=0.04 * s, roll_z=0.05 * c)
        key_char_bone(f, "Arm.R", pitch_x=-0.04 * s, roll_z=-0.05 * c)
        key_char_bone(f, "Pendant", pitch_x=0.06 * c, yaw_y=0.04 * s)
        key_char_bone(f, "Tail", yaw_y=0.08 * s, pitch_x=0.04 * c)
        blink = 0.20 if f == 30 else 0.0
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
        key_char_bone(f, "Ear.L", pitch_x=0.04 * s2, roll_z=0.08 * c)
        key_char_bone(f, "Ear.R", pitch_x=0.04 * s2, roll_z=-0.08 * c)
        key_char_bone(f, "Pendant", pitch_x=0.14 * s2, yaw_y=0.12 * s)
        key_char_bone(f, "Tail", yaw_y=0.16 * c, pitch_x=0.08 * s2)


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
        key_char_bone(f, "Ear.L", roll_z=0.16 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.16 * s)
        key_char_bone(f, "Arm.L", roll_z=-0.25 * s)
        key_char_bone(f, "Arm.R", roll_z=0.25 * s)
        key_char_bone(f, "Pendant", pitch_x=-0.22 * c)
        key_char_bone(f, "Jaw", pitch_x=-0.12 * max(0.0, s))
        key_char_bone(f, "Tail", pitch_x=0.18 * s, yaw_y=0.14 * c)


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
        key_char_bone(f, "Ear.L", roll_z=0.10 * lift)
        key_char_bone(f, "Ear.R", roll_z=-0.06 * lift)
        key_char_bone(f, "Pendant", pitch_x=0.08 * s, yaw_y=0.08 * lift)
        key_char_bone(f, "Tail", yaw_y=0.18 * s)


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
        key_char_bone(f, "Ear.L", roll_z=-0.12 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.12 * s)
        key_char_bone(f, "Chest", yaw_y=0.06 * s, roll_z=-0.04 * s)
        key_char_bone(f, "Tail", yaw_y=-0.14 * s)


fart_act, fart_track = bake_action_to_nla("CatNap_Fart_Blast", 36, build_catnap_fart_blast)
idle_act, idle_track = bake_action_to_nla("Idle_Breathe", 60, build_idle_breathe)
walk_act, walk_track = bake_action_to_nla("Walk_Cycle", 48, build_walk_cycle)
bounce_act, bounce_track = bake_action_to_nla("Happy_Bounce", 40, build_happy_bounce)
wave_act, wave_track = bake_action_to_nla("Wave_Paw", 60, build_wave_paw)
curious_act, curious_track = bake_action_to_nla("Curious_Head_Tilt", 60, build_curious_tilt)

# Unmute all tracks transiently during GLB export so glTF exporter writes all 6 NLA tracks
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = False

bpy.ops.object.mode_set(mode='OBJECT')
scene.frame_start = 1
scene.frame_end = 36
scene.frame_set(1)


# ==============================================================================
# 7. EXPORT GLTF 2.0 (.GLB) AND WAVEFRONT (.OBJ < 5MB WITH sub.levels = 1)
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
# and set `sub.levels = 1` before `.obj` export so the `.obj` stays under 5MB!
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')

sub.levels = 1
sub.show_viewport = False
bpy.context.view_layer.update()

bpy.ops.wm.obj_export(
    filepath=OBJ_PATH,
    export_selected_objects=True,
    export_materials=True,
    export_eval_mode='DAG_EVAL_VIEWPORT',
)

sub.show_viewport = True
sub.levels = 1
sub.render_levels = 2
bpy.context.view_layer.update()


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
add_area_light("Fill_Softbox", (2.6, -3.2, 2.4), (0.0, 0.0, 1.35), energy=155.0, size=3.4, color_rgb=(0.97, 0.98, 1.0))
add_area_light("Top_Softbox", (0.0, -0.8, 4.2), (0.0, 0.0, 1.65), energy=165.0, size=3.2, color_rgb=(1.0, 1.0, 1.0))
add_area_light("Rim_Backlight", (0.0, 3.0, 3.0), (0.0, 0.0, 1.50), energy=145.0, size=2.6, color_rgb=(0.98, 0.98, 1.0))

world = bpy.data.worlds.new("CatNapStudioWorld")
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
cam_data.lens = 60.0
cam_obj = bpy.data.objects.new("Studio_Camera", cam_data)
studio_col.objects.link(cam_obj)
scene.camera = cam_obj


def aim_camera(loc, target=(0.0, 0.0, 1.42), lens=60.0):
    cam_data.lens = lens
    cam_obj.location = Vector(loc)
    direction = Vector(target) - Vector(loc)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 24
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


# ==============================================================================
# 9. RENDER STUDIO HERO (`1080x1350`) & 4-PANEL TURNAROUND SHEET (`1920x600`)
# ==============================================================================
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
scene.frame_set(1)

# 9.1 Hero Studio Render (1080x1350)
scene.render.resolution_x = 1080
scene.render.resolution_y = 1350
aim_camera((0.0, -5.65, 1.50), target=(0.0, 0.0, 1.42), lens=60.0)
scene.render.filepath = RENDER_FRONT_PATH
bpy.ops.render.render(write_still=True)

# 9.2 Front, 3/4 & Side Turnaround Renders (480x600)
scene.render.resolution_x = 480
scene.render.resolution_y = 600
c_front_p = os.path.join(RENDER_SHEET_DIR, "cycles_front.png")
c_3q_p = os.path.join(RENDER_SHEET_DIR, "cycles_3q.png")
c_side_p = os.path.join(RENDER_SHEET_DIR, "cycles_side.png")

aim_camera((0.0, -5.65, 1.50), target=(0.0, 0.0, 1.42), lens=60.0)
scene.render.filepath = c_front_p
bpy.ops.render.render(write_still=True)

aim_camera((3.10, -4.75, 1.54), target=(0.0, 0.0, 1.42), lens=60.0)
scene.render.filepath = c_3q_p
bpy.ops.render.render(write_still=True)

aim_camera((5.65, 0.0, 1.50), target=(0.0, 0.0, 1.42), lens=60.0)
scene.render.filepath = c_side_p
bpy.ops.render.render(write_still=True)

# Composite 1920x600 4-panel preview sheet (Ref `022_CatNap_Plushie.webp` alpha-blended onto studio grey + Front + 3/4 + Side)
ref_pad_p = os.path.join(RENDER_SHEET_DIR, "ref_panel.png")
subprocess.run([
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=#e2e3e6:s=480x600",
    "-i", REF_IMAGE_PATH,
    "-filter_complex", "[1:v]scale=420:540:force_original_aspect_ratio=decrease:flags=lanczos[fg];[0:v][fg]overlay=(W-w)/2:(H-h)/2:shortest=1[v]",
    "-map", "[v]", "-frames:v", "1",
    ref_pad_p
], check=True)
subprocess.run([
    "ffmpeg", "-y",
    "-i", ref_pad_p,
    "-i", c_front_p,
    "-i", c_3q_p,
    "-i", c_side_p,
    "-filter_complex", "[0:v][1:v][2:v][3:v]hstack=inputs=4[v]",
    "-map", "[v]",
    RENDER_PREVIEW_PATH
], check=True)


# ==============================================================================
# 10. RENDER THE 36-FRAME `CatNap_Fart_Blast` CYCLES ANIMATION SEQUENCE!
# ==============================================================================
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = (trk.name != "CatNap_Fart_Blast")

aim_camera((4.95, -3.65, 1.52), target=(-0.06, 0.36, 1.22), lens=54.0)

scene.frame_start = 1
scene.frame_end = 36
scene.frame_set(15)
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)

scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.cycles.samples = 20

for f in range(1, 37):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(FART_FRAMES_DIR, f"frame_{f:03d}.png")
    bpy.ops.render.render(write_still=True)

print("SUCCESS: Rendered CatNap Studio Hero, 4-Panel Preview, and all 36 Cycles frames of CatNap_Fart_Blast!")
print(f"  BLEND: {BLEND_PATH} ({os.path.getsize(BLEND_PATH)} bytes)")
print(f"  GLB:   {GLB_PATH} ({os.path.getsize(GLB_PATH)} bytes)")
print(f"  OBJ:   {OBJ_PATH} ({os.path.getsize(OBJ_PATH)} bytes)")
