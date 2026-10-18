#!/usr/bin/env python3
"""
Native Blender 4.3 Builder, Rigging, Animation & Cycles Studio Renderer
for KickinChicken (#053 Smiling Critters Plush Base Model & Kickin_Fart_Blast Animation).

Run headless via:
  /tmp/blender/blender -b --factory-startup --threads 8 --python-exit-code 1 -P /tmp/smiling-critters-assets/models/build_kickin_chicken_blender.py
"""

import os
import math
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, noise

OUT_DIR = "/tmp/smiling-critters-assets/models"
ANIM_DIR = "/tmp/smiling-critters-assets/animations"
WORK_DIR = "/tmp/work_kickin"
FART_FRAMES_DIR = os.path.join(WORK_DIR, "frames")
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANIM_DIR, exist_ok=True)
os.makedirs(FART_FRAMES_DIR, exist_ok=True)

BLEND_PATH = os.path.join(OUT_DIR, "kickin_chicken_plush_base_model.blend")
GLB_PATH = os.path.join(OUT_DIR, "kickin_chicken_plush_base_model.glb")
OBJ_PATH = os.path.join(OUT_DIR, "kickin_chicken_plush_base_model.obj")
RENDER_FRONT_PATH = os.path.join(OUT_DIR, "kickin_chicken_blender_cycles_render.png")
RENDER_PREVIEW_PATH = os.path.join(OUT_DIR, "kickin_chicken_3d_preview.png")
RENDER_3Q_PATH = os.path.join(WORK_DIR, "cycles_3q.png")
RENDER_SIDE_PATH = os.path.join(WORK_DIR, "cycles_side.png")


# ==============================================================================
# 1. SCENE RESET & HELPER UTILITIES
# ==============================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

main_col = bpy.data.collections.new("KickinChicken_Plush_Rig")
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


HEAD_RX = 0.68
HEAD_RY = 0.64
HEAD_RZ = 0.66
HEAD_CY = 1.96


def head_front_z(x, y_up):
    nx = x / HEAD_RX
    ny = (y_up - HEAD_CY) / HEAD_RY
    r2 = min(0.92, nx * nx + ny * ny)
    return HEAD_RZ * math.sqrt(max(0.08, 1.0 - r2))


def plush_fleece_displacement(p_world):
    """Multi-octave 3D procedural fleece micro-displacement."""
    q1 = Vector((p_world.x * 7.5, p_world.y * 7.5, p_world.z * 7.5))
    q2 = Vector((p_world.x * 16.0 + 3.1, p_world.y * 16.0 - 1.7, p_world.z * 16.0 + 2.3))
    q3 = Vector((p_world.x * 32.0 - 4.2, p_world.y * 32.0 + 5.1, p_world.z * 32.0 - 1.9))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    n3 = noise.noise(q3)
    return 0.028 * n1 + 0.014 * abs(n2) + 0.007 * n3


# ==============================================================================
# 2. PROCEDURAL CYCLES / GLTF PBR MATERIALS (KICKIN CHICKEN + FART CLOUD)
# ==============================================================================
def create_plush_material(name, hex_color, roughness=0.84, spec_ior=0.14,
                          sheen=0.28, sheen_tint_mult=1.05,
                          bump_scale=65.0, bump_strength=0.12,
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
    # Golden-yellow plush fleece chicken body (#F5B700)
    "YellowPlush": create_plush_material(
        "Kickin_Yellow_Plush", 0xF5B700, roughness=0.86, spec_ior=0.06,
        sheen=0.14, sheen_tint_mult=1.0, bump_scale=68.0, bump_strength=0.14, subsurface=0.0
    ),
    # Bright sunny golden-yellow for rooster head crest feathers, wing-tips & tail (#FACC15)
    "YellowCrest": create_plush_material(
        "Kickin_Crest_Feather_Yellow", 0xFACC15, roughness=0.82, spec_ior=0.08,
        sheen=0.16, sheen_tint_mult=1.0, bump_scale=56.0, bump_strength=0.12, subsurface=0.0
    ),
    # Warm cream-yellow belly patch (#FEF08A)
    "BellyCream": create_plush_material(
        "Kickin_Belly_Cream", 0xFEF9C3, roughness=0.84, spec_ior=0.06,
        sheen=0.12, sheen_tint_mult=1.0, bump_scale=75.0, bump_strength=0.10, subsurface=0.0
    ),
    # Bright tangerine-orange beak dome, wide grin beak lips, lower shins & 3-toed chicken feet (#EA580C)
    "BeakOrange": create_plush_material(
        "Kickin_Beak_Feet_Orange", 0xEA580C, roughness=0.74, spec_ior=0.10,
        sheen=0.12, sheen_tint_mult=1.0, bump_scale=85.0, bump_strength=0.10, subsurface=0.0
    ),
    # Iconic Golden-Amber / Warm Star Pendant (#F59E0B / #EA580C warm metallic gold)
    "StarGold": create_plush_material(
        "Kickin_Star_Pendant_Gold", 0xF59E0B, roughness=0.22, spec_ior=0.45,
        sheen=0.10, sheen_tint_mult=1.0, bump_scale=110.0, bump_strength=0.02,
        metallic=0.78, coat=0.40, coat_rough=0.04, emission_strength=0.16
    ),
    # Coral-pink plush tongue inside the wide black mouth cavity (#F43F5E)
    "TonguePink": create_plush_material(
        "Kickin_Tongue_Pink", 0xF43F5E, roughness=0.78, spec_ior=0.10,
        sheen=0.15, sheen_tint_mult=1.0, bump_scale=90.0, bump_strength=0.08, subsurface=0.0
    ),
    # Deep jet-black glossy acrylic eye sockets
    "EyeGloss": create_plush_material(
        "Kickin_Eye_Acrylic_Black", 0x030305, roughness=0.05, spec_ior=0.14,
        sheen=0.0, bump_strength=0.0, coat=0.30, coat_rough=0.015
    ),
    # Crisp white oval pupil & studio catchlight highlight
    "CatchlightWhite": create_plush_material(
        "Kickin_Pupil_White", 0xFFFFFF, roughness=0.06, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, emission_strength=0.34
    ),
    # Pitch-black recessed mouth cavity
    "MouthVoidBlack": create_plush_material(
        "Kickin_Mouth_Cavity_Black", 0x010102, roughness=0.99, spec_ior=0.01,
        sheen=0.0, bump_strength=0.0
    ),
    # Brushed silver zipper teeth & collar slider
    "ZipperMetal": create_plush_material(
        "Kickin_Zipper_Silver_Metal", 0xD8DDE6, roughness=0.20, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, metallic=0.94, coat=0.30
    ),
    # Dark charcoal/black collar band, zipper tape, star outline & embroidered brows
    "ZipperTrack": create_plush_material(
        "Kickin_Collar_Zipper_Dark", 0x101115, roughness=0.84, spec_ior=0.08,
        sheen=0.12, bump_strength=0.05
    ),
    # 3D Cartoon Fart Cloud Materials (Vibrant Toxic Lime, Neon Blast Core, Nightmare Purple Swirl)
    "FartCloudLime": create_plush_material(
        "Kickin_Fart_Cloud_Lime", 0x4CE629, roughness=0.68, spec_ior=0.18,
        sheen=0.45, sheen_tint_mult=1.15, bump_scale=24.0, bump_strength=0.22,
        subsurface=0.35, emission_strength=0.28
    ),
    "FartCloudNeon": create_plush_material(
        "Kickin_Fart_Cloud_Neon_YellowGreen", 0xC4FF33, roughness=0.45, spec_ior=0.25,
        sheen=0.35, sheen_tint_mult=1.1, bump_scale=30.0, bump_strength=0.14,
        subsurface=0.25, emission_strength=0.55
    ),
    "FartCloudPurple": create_plush_material(
        "Kickin_Fart_Cloud_Nightmare_Purple", 0x9D4EDD, roughness=0.62, spec_ior=0.20,
        sheen=0.40, sheen_tint_mult=1.1, bump_scale=28.0, bump_strength=0.18,
        subsurface=0.25, emission_strength=0.32
    ),
}


# ==============================================================================
# 3. KICKIN CHICKEN GEOMETRY BUILDER (BMESH + SKIN WEIGHTS)
# ==============================================================================
master_bm = bmesh.new()
deform_layer = master_bm.verts.layers.deform.verify()

# 25-Bone KickinChicken_Armature (includes Tail, Ear.L/R, SkullPendant, HandHoof.L/R, FootHoof.L/R, FartCloud.1/2/3)
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
    "YellowPlush",
    "YellowCrest",
    "BellyCream",
    "BeakOrange",
    "StarGold",
    "TonguePink",
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
                      u_segs=24, v_segs=18, rot_euler=(0.0, 0.0, 0.0),
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


def make_torus_tube_bm(curve_pts, radius_fn, radial_segs=16, closed=False, z_flatten=1.0):
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
            offset = normal * (math.cos(ang) * r) + binormal * (math.sin(ang) * r * z_flatten)
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


def make_star_5pt_bm(cx, cy, cz, r_outer, r_inner, half_thick, tilt_x=-0.06):
    """Builds a true 3D faceted/beveled 5-pointed star charm."""
    bm = bmesh.new()
    rot_x = Euler((tilt_x, 0.0, 0.0), 'XYZ').to_matrix()
    center = Vector((cx, cy, cz))

    def star_pt(x_l, y_l, z_l):
        return (rot_x @ Vector((x_l, y_l, z_l))) + center

    v_front = bm.verts.new(star_pt(0.0, 0.0, half_thick))
    v_back = bm.verts.new(star_pt(0.0, 0.0, -half_thick))

    ring_front = []
    ring_back = []
    for i in range(10):
        ang = math.pi / 2.0 + i * (math.pi / 5.0)
        rad = r_outer if (i % 2 == 0) else r_inner
        px = rad * math.cos(ang)
        py = rad * math.sin(ang)
        edge_z = half_thick * (0.38 if (i % 2 == 0) else 0.52)
        ring_front.append(bm.verts.new(star_pt(px, py, edge_z)))
        ring_back.append(bm.verts.new(star_pt(px, py, -edge_z)))

    for i in range(10):
        inext = (i + 1) % 10
        bm.faces.new([v_front, ring_front[i], ring_front[inext]])
        bm.faces.new([v_back, ring_back[inext], ring_back[i]])
        bm.faces.new([ring_front[i], ring_back[i], ring_back[inext], ring_front[inext]])

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


# ------------------------------------------------------------------------------
# 3.1 GOLDEN-YELLOW PLUSH HEAD, CHEEK FEATHER TUFTS & 3-TUFT ROOSTER CREST
# ------------------------------------------------------------------------------
def head_plush_displace(p_w, n_w):
    in_face = (p_w.z > 0.35 and 1.38 < p_w.y < 2.35 and abs(p_w.x) < 0.54)
    scale = 0.05 if in_face else 0.22
    return p_w + n_w * (plush_fleece_displacement(p_w) * scale)


head_core_bm = make_uv_sphere_bm(
    HEAD_RX, HEAD_RY, HEAD_RZ,
    cx=0.0, cy=HEAD_CY, cz=0.0,
    u_segs=36, v_segs=28,
    world_deform_fn=head_plush_displace
)
append_bmesh_part(head_core_bm, "YellowPlush", lambda x, y, z: {"Head": 1.0})

# Signature Left & Right Flared Cheek Feather Tufts (2 tufts per cheek, matching 053_KickinChicken.webp)
for side in (-1, 1):
    # Upper cheek feather tuft
    cheek_tuft_1 = []
    for k in range(11):
        t = k / 10.0
        tx = side * (0.55 + 0.25 * t)
        ty = 1.98 + 0.03 * math.sin(math.pi * t) - 0.11 * (t ** 1.6)
        tz = 0.18 - 0.04 * t
        cheek_tuft_1.append((tx, ty, tz))
    ct1_bm = make_torus_tube_bm(
        cheek_tuft_1,
        lambda t: 0.095 * math.sin(math.pi * (0.12 + 0.84 * t)) * (1.0 - 0.35 * t),
        radial_segs=14, closed=False, z_flatten=0.65
    )
    append_bmesh_part(ct1_bm, "YellowCrest", lambda x, y, z: {"Head": 1.0})

    # Lower cheek feather tuft
    cheek_tuft_2 = []
    for k in range(11):
        t = k / 10.0
        tx = side * (0.56 + 0.21 * t)
        ty = 1.88 - 0.14 * (t ** 1.4)
        tz = 0.22 - 0.04 * t
        cheek_tuft_2.append((tx, ty, tz))
    ct2_bm = make_torus_tube_bm(
        cheek_tuft_2,
        lambda t: 0.078 * math.sin(math.pi * (0.12 + 0.84 * t)) * (1.0 - 0.40 * t),
        radial_segs=12, closed=False, z_flatten=0.65
    )
    append_bmesh_part(ct2_bm, "YellowCrest", lambda x, y, z: {"Head": 1.0})

# Iconic 3-Tuft Yellow Rooster Head Feathers (Crest Plumes weighted to Ear.L / Ear.R)
# Plume 1 (Viewer's Left / -X long sweeping rooster crest plume, weighted to Ear.R)
crest_left_pts = []
for k in range(17):
    t = k / 16.0
    cx = -0.04 - 0.66 * (t ** 0.92)
    cy = 2.46 + 0.28 * math.sin(math.pi * (t ** 0.75)) - 0.14 * (t ** 1.8)
    cz = 0.08 - 0.03 * t
    crest_left_pts.append((cx, cy, cz))

crest_left_bm = make_torus_tube_bm(
    crest_left_pts,
    lambda t: 0.165 * math.sin(math.pi * (0.10 + 0.85 * t)) * (1.0 - 0.18 * t),
    radial_segs=18, closed=False, z_flatten=0.62
)
append_bmesh_part(
    crest_left_bm, "YellowCrest",
    lambda x, y, z: {"Ear.R": 0.88, "Head": 0.12}
)

# Plume 2 (Central-top big overarching rooster crest plume, weighted 0.5 Ear.L + 0.5 Ear.R)
crest_mid_pts = []
for k in range(17):
    t = k / 16.0
    cx = -0.22 + 0.54 * t
    cy = 2.48 + 0.38 * math.sin(math.pi * (t ** 0.82)) - 0.04 * t
    cz = 0.02 - 0.02 * t
    crest_mid_pts.append((cx, cy, cz))

crest_mid_bm = make_torus_tube_bm(
    crest_mid_pts,
    lambda t: 0.185 * math.sin(math.pi * (0.12 + 0.82 * t)),
    radial_segs=18, closed=False, z_flatten=0.64
)
append_bmesh_part(
    crest_mid_bm, "YellowCrest",
    lambda x, y, z: {"Ear.L": 0.45, "Ear.R": 0.45, "Head": 0.10}
)

# Plume 3 (Viewer's Right / +X curved side crest plume, weighted to Ear.L)
crest_right_pts = []
for k in range(15):
    t = k / 14.0
    cx = 0.16 + 0.40 * math.sin(0.85 * math.pi * t)
    cy = 2.44 + 0.24 * math.sin(math.pi * (t ** 0.75)) - 0.16 * (t ** 1.6)
    cz = -0.02 - 0.02 * t
    crest_right_pts.append((cx, cy, cz))

crest_right_bm = make_torus_tube_bm(
    crest_right_pts,
    lambda t: 0.145 * math.sin(math.pi * (0.12 + 0.84 * t)) * (1.0 - 0.15 * t),
    radial_segs=16, closed=False, z_flatten=0.62
)
append_bmesh_part(
    crest_right_bm, "YellowCrest",
    lambda x, y, z: {"Ear.L": 0.88, "Head": 0.12}
)


# ------------------------------------------------------------------------------
# 3.2 EYES, LARGE WHITE OVAL PUPILS, EYELIDS & CONFIDENT ARCHED BROWS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    lid_bone = "Eyelid.L" if side == 1 else "Eyelid.R"
    ex = side * 0.215
    ey = 2.045
    ez = 0.560

    # Deep black oval eye socket dome
    eye_bm = make_uv_sphere_bm(
        0.165, 0.195, 0.115,
        cx=ex, cy=ey, cz=ez,
        u_segs=26, v_segs=20,
        rot_euler=(-0.05, side * 0.18, side * 0.10)
    )
    append_bmesh_part(eye_bm, "EyeGloss", lambda x, y, z: {"Head": 1.0})

    # Iconic Smiling Critters White Oval Pupil inside the black eye socket
    pupil_bm = make_uv_sphere_bm(
        0.068, 0.098, 0.032,
        cx=ex - side * 0.012, cy=ey - 0.010, cz=ez + 0.095,
        u_segs=20, v_segs=16,
        rot_euler=(-0.05, side * 0.18, side * 0.06)
    )
    append_bmesh_part(pupil_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Upper eyelid yellow plush rim
    lid_rim_pts = []
    for k in range(15):
        t = -1.0 + 2.0 * k / 14.0
        lx = ex + t * 0.175
        # Viewer's left (side=-1) has a high cool arch; viewer's right (side=+1) has a confident angled smirk brow
        if side == -1:
            ly = ey + 0.155 + 0.045 * (1.0 - t * t)
        else:
            ly = ey + 0.135 + 0.035 * (1.0 - t * t) + 0.045 * t
        lz = head_front_z(lx, ly) + 0.025
        lid_rim_pts.append((lx, ly, lz))

    lid_rim_bm = make_torus_tube_bm(
        lid_rim_pts,
        lambda t: 0.022 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=12, closed=False
    )
    append_bmesh_part(
        lid_rim_bm, "YellowPlush",
        lambda x, y, z, b=lid_bone: {b: 0.90, "Head": 0.10}
    )

    # Embroidered dark arched eyebrow above each eye
    brow_pts = []
    for k in range(15):
        t = -1.0 + 2.0 * k / 14.0
        bx = ex + t * 0.165
        if side == -1:
            by = ey + 0.215 + 0.055 * (1.0 - t * t) - 0.020 * t
        else:
            by = ey + 0.185 + 0.040 * (1.0 - t * t) + 0.050 * t
        bz = head_front_z(bx, by) + 0.018
        brow_pts.append((bx, by, bz))

    brow_bm = make_torus_tube_bm(
        brow_pts,
        lambda t: 0.015 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=10, closed=False
    )
    append_bmesh_part(
        brow_bm, "ZipperTrack",
        lambda x, y, z, b=lid_bone: {b: 0.85, "Head": 0.15}
    )


# ------------------------------------------------------------------------------
# 3.3 TANGERINE-ORANGE BEAK DOME, WIDE BLACK GRIN, PINK TONGUE & BEAK LIPS
# ------------------------------------------------------------------------------
# Rounded Orange Upper Beak Mound right between/below the eyes (053_KickinChicken.webp)
beak_dome_bm = make_uv_sphere_bm(
    0.175, 0.102, 0.135,
    cx=0.0, cy=1.855, cz=0.625,
    u_segs=26, v_segs=18,
    rot_euler=(0.06, 0.0, 0.0)
)
append_bmesh_part(beak_dome_bm, "BeakOrange", lambda x, y, z: {"Head": 0.92, "Jaw": 0.08})


def build_conformed_mouth_cavity_bm():
    bm = bmesh.new()
    u_steps = 36
    v_steps = 16
    grid = []
    for iv in range(v_steps + 1):
        v_frac = iv / v_steps
        ring = []
        for iu in range(u_steps):
            ang = 2.0 * math.pi * iu / u_steps
            ux = math.cos(ang) * 0.49 * v_frac
            raw_y = math.sin(ang)
            if raw_y >= 0:
                uy = 1.77 + raw_y * 0.055 * v_frac + 0.095 * (ux / 0.49) ** 2
            else:
                uy = 1.77 + raw_y * 0.35 * v_frac + 0.075 * (ux / 0.49) ** 2
            # Sit +0.016m outside head_front_z so the pitch-black mouth cavity is 100% visible!
            uz = head_front_z(ux, uy) + 0.016
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

# Coral-Pink Bilobed Plush Tongue nestled at the bottom of the black mouth cavity
for side in (-1, 1):
    tx = side * 0.070
    ty = 1.485
    tz = head_front_z(tx, ty) + 0.026
    t_lobe_bm = make_uv_sphere_bm(
        0.105, 0.055, 0.024,
        cx=tx, cy=ty, cz=tz,
        u_segs=18, v_segs=14,
        rot_euler=(0.32, side * 0.12, -side * 0.15)
    )
    append_bmesh_part(
        t_lobe_bm, "TonguePink",
        lambda x, y, z: {"Jaw": 0.85, "Head": 0.15}
    )

# Sculpted Tangerine-Orange Upper & Lower Beak Lips framing the wide open grin (#EA580C)
upper_lip_pts = []
for k in range(33):
    t = -1.0 + 2.0 * k / 32.0
    lx = t * 0.50
    ly = 1.785 + 0.105 * (t * t) - 0.020 * (t ** 4)
    lz = head_front_z(lx, ly) + 0.036 * (1.0 - 0.30 * t * t)
    upper_lip_pts.append((lx, ly, lz))

upper_lip_bm = make_torus_tube_bm(
    upper_lip_pts,
    lambda t: 0.036 + 0.012 * math.sin(math.pi * t),
    radial_segs=16, closed=False
)
append_bmesh_part(upper_lip_bm, "BeakOrange", lambda x, y, z: {"Head": 0.88, "Jaw": 0.12})

lower_lip_pts = []
for k in range(37):
    t = -1.0 + 2.0 * k / 36.0
    lx = t * 0.50
    ly = 1.415 + 0.455 * (t ** 2)
    lz = head_front_z(lx, ly) + 0.030 * (1.0 - 0.28 * t * t)
    lower_lip_pts.append((lx, ly, lz))

lower_lip_bm = make_torus_tube_bm(
    lower_lip_pts,
    lambda t: 0.030 + 0.010 * math.sin(math.pi * t),
    radial_segs=16, closed=False
)
append_bmesh_part(
    lower_lip_bm, "BeakOrange",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.75 - y) * 2.8)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.75 - y) * 2.8))}
)

# Smile corner cheek caps
for side in (-1, 1):
    cheek_pts = []
    for k in range(9):
        t = k / 8.0
        cx = side * (0.48 + 0.04 * math.sin(math.pi * t))
        cy = 1.79 + 0.12 * (1.0 - t)
        cz = head_front_z(cx, cy) + 0.025
        cheek_pts.append((cx, cy, cz))
    cheek_bm = make_torus_tube_bm(cheek_pts, 0.032, radial_segs=12, closed=False)
    append_bmesh_part(cheek_bm, "YellowPlush", lambda x, y, z: {"Head": 0.90, "Jaw": 0.10})


# ------------------------------------------------------------------------------
# 3.4 TORSO, CREAM BELLY PATCH, BLACK COLLAR, ZIPPER & GOLDEN 5-POINTED STAR PENDANT
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
    else:
        t = max(0.0, min(1.0, (y - 1.12) / 0.38))
        return {"Spine": max(0.0, 0.4 * (1.0 - t)), "Chest": 1.0 - 0.4 * (1.0 - t)}


torso_bm = build_torso_bm()
append_bmesh_part(torso_bm, "YellowPlush", torso_weights)


TORSO_PROFILE = [
    (0.00, 0.52), (0.18, 0.53), (0.35, 0.57), (0.46, 0.66),
    (0.51, 0.78), (0.52, 0.92), (0.49, 1.06), (0.45, 1.20),
    (0.39, 1.33), (0.33, 1.43), (0.26, 1.50), (0.00, 1.52)
]


def torso_front_z(y, x=0.0):
    r = 0.30
    for i in range(len(TORSO_PROFILE) - 1):
        r0, y0 = TORSO_PROFILE[i]
        r1, y1 = TORSO_PROFILE[i + 1]
        if y0 <= y <= y1:
            alpha = (y - y0) / max(1e-6, y1 - y0)
            r = r0 + alpha * (r1 - r0)
            break
    x_ratio = min(0.95, abs(x) / max(0.10, r))
    return r * 0.88 * math.sqrt(max(0.06, 1.0 - x_ratio * x_ratio))


# Warm Cream-Yellow Belly Patch (#FEF08A) conformed to the front of the torso
def build_belly_patch_bm():
    bm = bmesh.new()
    u_steps = 28
    v_steps = 12
    grid = []
    for iv in range(v_steps + 1):
        v_frac = iv / v_steps
        ring = []
        for iu in range(u_steps):
            ang = 2.0 * math.pi * iu / u_steps
            bx = math.cos(ang) * 0.30 * v_frac
            by = 0.92 + math.sin(ang) * 0.31 * v_frac
            bz = torso_front_z(by, bx) + 0.015 * (1.0 - 0.30 * (v_frac ** 2))
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
append_bmesh_part(belly_bm, "BellyCream", torso_weights)

# Black Collar Band around the neck (053_KickinChicken.webp)
collar_pts = []
for k in range(28):
    ang = 2.0 * math.pi * k / 28.0
    collar_pts.append((0.31 * math.cos(ang), 1.40 - 0.03 * math.sin(ang), 0.28 * math.sin(ang)))
collar_bm = make_torus_tube_bm(collar_pts, 0.026, radial_segs=12, closed=True)
append_bmesh_part(collar_bm, "ZipperTrack", lambda x, y, z: {"Chest": 0.8, "Head": 0.2})

# Vertical Center Zipper Track & Silver Zipper Teeth
zip_pts = [(0.0, 0.58 + (1.39 - 0.58) * k / 20.0, torso_front_z(0.58 + (1.39 - 0.58) * k / 20.0) + 0.025)
           for k in range(21)]
zip_track_bm = make_torus_tube_bm(zip_pts, 0.022, radial_segs=10, closed=False)
append_bmesh_part(zip_track_bm, "ZipperTrack", torso_weights)

for i in range(30):
    zy = 0.60 + (1.36 - 0.60) * (i / 29.0)
    zz = torso_front_z(zy) + 0.036
    zx = (0.010 if (i % 2 == 0) else -0.010)
    t_bm = make_beveled_box_bm(0.034, 0.013, 0.018, zx, zy, zz)
    append_bmesh_part(t_bm, "ZipperMetal", torso_weights)

slider_bm = make_beveled_box_bm(0.064, 0.076, 0.042, 0.0, 1.335, 0.456)
append_bmesh_part(slider_bm, "ZipperMetal", lambda x, y, z: {"Chest": 0.7, "SkullPendant": 0.3})

bail_bm = make_beveled_box_bm(0.056, 0.060, 0.034, 0.0, 1.265, 0.476)
append_bmesh_part(bail_bm, "ZipperMetal", lambda x, y, z: {"SkullPendant": 1.0})

# Iconic Golden 5-Pointed Star Pendant (with crisp dark border rim + faceted 3D gold star)
star_rim_bm = make_star_5pt_bm(
    cx=0.0, cy=1.085, cz=0.490,
    r_outer=0.215, r_inner=0.098, half_thick=0.024, tilt_x=-0.06
)
append_bmesh_part(star_rim_bm, "ZipperTrack", lambda x, y, z: {"SkullPendant": 1.0})

star_gold_bm = make_star_5pt_bm(
    cx=0.0, cy=1.085, cz=0.504,
    r_outer=0.192, r_inner=0.086, half_thick=0.028, tilt_x=-0.06
)
append_bmesh_part(star_gold_bm, "StarGold", lambda x, y, z: {"SkullPendant": 1.0})


# ------------------------------------------------------------------------------
# 3.5 FEATHERED WING-ARMS (`Shoulder.L/R`, `Arm.L/R`, `HandHoof.L/R`)
# ------------------------------------------------------------------------------
for side in (-1, 1):
    sh_bone = "Shoulder.L" if side == 1 else "Shoulder.R"
    arm_bone = "Arm.L" if side == 1 else "Arm.R"
    hoof_bone = "HandHoof.L" if side == 1 else "HandHoof.R"

    arm_pts = []
    for k in range(13):
        t = k / 12.0
        ax = side * (0.32 + 0.42 * t)
        ay = 1.32 - 0.34 * t + 0.02 * math.sin(math.pi * t)
        az = 0.02 + 0.05 * t
        arm_pts.append((ax, ay, az))

    arm_bm = make_torus_tube_bm(
        arm_pts,
        lambda t: 0.138 * (1.0 + 0.06 * math.sin(math.pi * t)),
        radial_segs=18, closed=False
    )

    def arm_weight_fn(x, y, z, sb=sh_bone, ab=arm_bone, hb=hoof_bone):
        dist = max(0.0, min(1.0, (abs(x) - 0.32) / 0.45))
        if dist < 0.35:
            return {"Chest": 0.35 * (1.0 - dist / 0.35), sb: 0.65, ab: 0.35 * (dist / 0.35)}
        elif dist < 0.85:
            return {ab: 0.85, sb: 0.15}
        else:
            return {ab: 0.50, hb: 0.50}

    append_bmesh_part(arm_bm, "YellowPlush", arm_weight_fn)

    # Rounded Wing-Hand Palm (`HandHoof.L/R`)
    palm_bm = make_uv_sphere_bm(
        0.155, 0.145, 0.115,
        cx=side * 0.77, cy=0.94, cz=0.075,
        u_segs=20, v_segs=16,
        rot_euler=(0.0, 0.0, -side * 0.55)
    )
    append_bmesh_part(
        palm_bm, "YellowPlush",
        lambda x, y, z, hb=hoof_bone, ab=arm_bone: {hb: 0.90, ab: 0.10}
    )

    # 3 Sculpted Wing-Tip Feather Fingers at the end of each hand (028_KickinChicken pose)
    for f_idx, (ang_off, f_len, f_rad) in enumerate([
        (-0.34, 0.16, 0.058),
        (0.00,  0.19, 0.064),
        (0.34,  0.15, 0.054),
    ]):
        base_ang = -0.68 + ang_off
        f_pts = []
        for k in range(9):
            u = k / 8.0
            fx = side * (0.79 + math.cos(base_ang) * f_len * u)
            fy = 0.91 + math.sin(base_ang) * f_len * u
            fz = 0.075 + (f_idx - 1) * 0.028 * (0.4 + 0.6 * u)
            f_pts.append((fx, fy, fz))
        finger_bm = make_torus_tube_bm(
            f_pts,
            lambda u, r0=f_rad: r0 * math.sin(math.pi * (0.15 + 0.80 * u)),
            radial_segs=12, closed=False
        )
        append_bmesh_part(
            finger_bm, "YellowCrest",
            lambda x, y, z, hb=hoof_bone: {hb: 1.0}
        )


# ------------------------------------------------------------------------------
# 3.6 YELLOW UPPER LEGS, ORANGE LOWER SHINS & 3-TOED CHICKEN FEET
# ------------------------------------------------------------------------------
for side in (-1, 1):
    leg_bone = "Leg.L" if side == 1 else "Leg.R"
    foot_bone = "FootHoof.L" if side == 1 else "FootHoof.R"

    # Upper Yellow Plush Thigh (y = 0.33 .. 0.66)
    thigh_pts = []
    for k in range(11):
        t = k / 10.0
        lx = side * (0.23 + 0.035 * t)
        ly = 0.66 - 0.33 * t
        lz = 0.0 + 0.01 * t
        thigh_pts.append((lx, ly, lz))

    thigh_bm = make_torus_tube_bm(
        thigh_pts,
        lambda t: 0.178 * (1.0 - 0.10 * t),
        radial_segs=20, closed=False
    )
    append_bmesh_part(
        thigh_bm, "YellowPlush",
        lambda x, y, z, lb=leg_bone: {"Pelvis": 0.40 if y > 0.54 else 0.0, lb: 0.60 if y > 0.54 else 1.0}
    )

    # Lower Tangerine-Orange Shin (y = 0.12 .. 0.35)
    shin_pts = []
    for k in range(9):
        t = k / 8.0
        lx = side * (0.265 + 0.025 * t)
        ly = 0.35 - 0.23 * t
        lz = 0.01 + 0.02 * t
        shin_pts.append((lx, ly, lz))

    shin_bm = make_torus_tube_bm(
        shin_pts,
        lambda t: 0.152 * (1.0 - 0.06 * t),
        radial_segs=18, closed=False
    )
    append_bmesh_part(
        shin_bm, "BeakOrange",
        lambda x, y, z, lb=leg_bone, fb=foot_bone: {lb: 0.65 if y > 0.22 else 0.25, fb: 0.35 if y > 0.22 else 0.75}
    )

    # Orange Chicken Foot Heel/Pad (`FootHoof.L/R`)
    fx = side * 0.295
    fy = 0.095
    fz = 0.045

    def foot_pad_deform(p):
        if p.y < -0.015:
            p.y = -0.085 + (p.y + 0.085) * 0.15
        return p

    pad_bm = make_uv_sphere_bm(
        0.165, 0.115, 0.165,
        cx=fx, cy=fy, cz=fz,
        u_segs=20, v_segs=16,
        deform_fn=foot_pad_deform
    )
    append_bmesh_part(
        pad_bm, "BeakOrange",
        lambda x, y, z, fb=foot_bone, lb=leg_bone: {fb: 0.92, lb: 0.08}
    )

    # 3 Sculpted Forward Chicken Toes on each foot (053_KickinChicken.webp)
    for t_ang, t_len, t_rad in [
        (-0.38, 0.22, 0.068),
        (0.00,  0.26, 0.074),
        (0.38,  0.22, 0.068),
    ]:
        yaw = side * 0.08 + t_ang
        toe_pts = []
        for k in range(9):
            u = k / 8.0
            tx = fx + math.sin(yaw) * t_len * u
            ty = 0.065 - 0.012 * u + 0.015 * math.sin(math.pi * u)
            tz = fz + 0.06 + math.cos(yaw) * t_len * u
            toe_pts.append((tx, ty, tz))
        toe_bm = make_torus_tube_bm(
            toe_pts,
            lambda u, r0=t_rad: r0 * math.sin(math.pi * (0.18 + 0.76 * u)),
            radial_segs=14, closed=False, z_flatten=0.72
        )
        append_bmesh_part(
            toe_bm, "BeakOrange",
            lambda x, y, z, fb=foot_bone: {fb: 1.0}
        )


# ------------------------------------------------------------------------------
# 3.7 FEATHERED YELLOW ROOSTER TAIL (`Tail` BONE)
# ------------------------------------------------------------------------------
# Central upward-curving rooster tail plume + 2 side tail feather tufts (053_KickinChicken.webp)
for t_side, t_height, t_rad in [
    (0.00,  0.46, 0.155),
    (-0.14, 0.34, 0.115),
    (0.14,  0.34, 0.115),
]:
    tail_pts = []
    for k in range(13):
        u = k / 12.0
        tx = t_side * (0.4 + 0.9 * u)
        ty = 0.72 + t_height * (u ** 1.25)
        tz = -0.36 - 0.38 * math.sin(0.65 * math.pi * u)
        tail_pts.append((tx, ty, tz))
    tail_bm = make_torus_tube_bm(
        tail_pts,
        lambda u, r0=t_rad: r0 * math.sin(math.pi * (0.14 + 0.82 * u)),
        radial_segs=14, closed=False, z_flatten=0.68
    )
    append_bmesh_part(
        tail_bm, "YellowCrest",
        lambda x, y, z: {"Tail": 0.90, "Pelvis": 0.10}
    )


# ------------------------------------------------------------------------------
# 3.8 3D SCULPTED CARTOON FART CLOUD CLUSTER (WEIGHTED TO FartCloud.1 / .2 / .3)
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
        return p_w + n_w * (plush_fleece_displacement(p_w + Vector((s * 1.1, 0.0, s * 0.7))) * 0.85)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=18, v_segs=14, world_deform_fn=fc1_disp)
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
        return p_w + n_w * (plush_fleece_displacement(p_w + Vector((s * 1.7, s * 0.9, 0.0))) * 1.15)
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
        return p_w + n_w * (plush_fleece_displacement(p_w + Vector((0.0, s * 1.4, s * 2.1))) * 1.20)
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
mesh_data = bpy.data.meshes.new("KickinChicken_Plush_MeshData")
for m in MAT_LIST:
    mesh_data.materials.append(m)

master_bm.to_mesh(mesh_data)
master_bm.free()
mesh_data.update()

mesh_obj = bpy.data.objects.new("KickinChicken_Plush_Mesh", mesh_data)
main_col.objects.link(mesh_obj)

for bname in BONE_NAMES:
    mesh_obj.vertex_groups.new(name=bname)


# ==============================================================================
# 5. CREATE SKELETAL ARMATURE RIG (25 BONES) & BIND SKINNING
# ==============================================================================
arm_data = bpy.data.armatures.new("KickinChicken_ArmatureData")
arm_data.display_type = 'OCTAHEDRAL'
arm_obj = bpy.data.objects.new("KickinChicken_Armature", arm_data)
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
add_ebone("Chest", (0.0, 1.14, 0.0), (0.0, 1.50, 0.0), "Spine", True)
add_ebone("Tail", (0.0, 0.72, -0.34), (0.0, 1.16, -0.76), "Pelvis", False)
add_ebone("Head", (0.0, 1.50, 0.0), (0.0, 2.46, 0.0), "Chest", True)

add_ebone("Jaw", (0.0, 1.68, 0.44), (0.0, 1.44, 0.68), "Head", False)
add_ebone("Eyelid.L", (0.215, 2.045, 0.560), (0.215, 2.22, 0.70), "Head", False)
add_ebone("Eyelid.R", (-0.215, 2.045, 0.560), (-0.215, 2.22, 0.70), "Head", False)
add_ebone("Ear.L", (0.14, 2.44, 0.00), (0.54, 2.66, 0.00), "Head", False)
add_ebone("Ear.R", (-0.14, 2.46, 0.04), (-0.64, 2.68, 0.04), "Head", False)

add_ebone("SkullPendant", (0.0, 1.26, 0.46), (0.0, 0.90, 0.50), "Chest", False)

add_ebone("Shoulder.L", (0.28, 1.32, 0.02), (0.44, 1.22, 0.03), "Chest", False)
add_ebone("Arm.L", (0.44, 1.22, 0.03), (0.72, 0.98, 0.06), "Shoulder.L", True)
add_ebone("HandHoof.L", (0.72, 0.98, 0.06), (0.94, 0.80, 0.09), "Arm.L", True)

add_ebone("Shoulder.R", (-0.28, 1.32, 0.02), (-0.44, 1.22, 0.03), "Chest", False)
add_ebone("Arm.R", (-0.44, 1.22, 0.03), (-0.72, 0.98, 0.06), "Shoulder.R", True)
add_ebone("HandHoof.R", (-0.72, 0.98, 0.06), (-0.94, 0.80, 0.09), "Arm.R", True)

add_ebone("Leg.L", (0.24, 0.66, 0.0), (0.29, 0.22, 0.02), "Pelvis", False)
add_ebone("FootHoof.L", (0.29, 0.22, 0.02), (0.30, 0.05, 0.26), "Leg.L", True)

add_ebone("Leg.R", (-0.24, 0.66, 0.0), (-0.29, 0.22, 0.02), "Pelvis", False)
add_ebone("FootHoof.R", (-0.29, 0.22, 0.02), (-0.30, 0.05, 0.26), "Leg.R", True)

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
# 6. AUTHOR 6 NLA / ACTION ANIMATION CLIPS ON THE ARMATURE (INCLUDING Kickin_Fart_Blast)
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


def build_kickin_fart_blast(act):
    """
    36-Frame (1.5s @ 24fps) High-Energy Cartoon Animation: `Kickin_Fart_Blast`
      - Act 1 (Frames 1-9):   Deep squat & tummy strain, rooster crest droops, tail lifts
      - Act 2 (Frames 10-14): Explosive rocket recoil jump + 3-stage green/lime/purple 3D fart cloud + shockwave ring
      - Act 3 (Frames 15-26): Mid-air hop & 3-toed chicken foot landing
      - Act 4 (Frames 27-36): Turn to camera, wing-fanning cloud behind back & cool rooster chuckle
    """
    body_keys = [
        # Frame 1: Neutral start
        (1,   0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000),
        # Frame 4: Squatting down & clenching wings in
        (4,  -0.09, -0.02,  0.22,  0.14,  0.16, -0.06,  0.00,  0.04,  0.22, -0.18,  0.22,  0.28,  0.22, -0.28, -0.22,  0.18,  0.000),
        # Frames 6, 8, 9: High-tension strain tremble before the blast!
        (6,  -0.13, -0.04,  0.30,  0.18,  0.22, -0.10,  0.05,  0.06,  0.30, -0.25,  0.30,  0.35,  0.30, -0.35, -0.28,  0.24,  0.020),
        (8,  -0.14, -0.04,  0.32,  0.20,  0.24, -0.08, -0.05,  0.06,  0.32, -0.28,  0.32,  0.38,  0.32, -0.38, -0.30,  0.26, -0.020),
        (9,  -0.15, -0.05,  0.35,  0.22,  0.26, -0.12,  0.05,  0.08,  0.34, -0.30,  0.34,  0.40,  0.34, -0.40, -0.32,  0.28,  0.018),
        # Frame 12: KABOOM-TOOT! Big upward/forward rocket jump + wide-eyed rooster squawk!
        (12,  0.15,  0.06,  0.28, -0.16, -0.22,  0.16, -0.08, -0.26, -0.12,  0.35, -0.20, -0.50, -0.20,  0.50,  0.24, -0.42,  0.000),
        # Frame 14: Peak of the toot blast — orange chicken feet dangling, star charm flying!
        (14,  0.18,  0.08,  0.22, -0.18, -0.24,  0.24, -0.12, -0.30, -0.14,  0.42, -0.25, -0.56, -0.25,  0.56,  0.28, -0.48,  0.000),
        # Frame 19: Mid-air hop & secondary toot ripple
        (19,  0.10,  0.05,  0.14, -0.10, -0.14,  0.26, -0.10, -0.22, -0.08,  0.25, -0.12, -0.38, -0.15,  0.40,  0.16, -0.30,  0.000),
        # Frame 24: Cushioned landing on 3-toed chicken feet
        (24, -0.04,  0.01,  0.08,  0.04,  0.04,  0.28, -0.12, -0.12,  0.04, -0.10,  0.38, -0.15, -0.10,  0.25, -0.08,  0.12,  0.000),
        # Frames 27, 30, 33: Wing-fanning cloud behind back (Arm.L fans the green cloud!) + cool rooster chuckle!
        (27,  0.02,  0.00,  0.04, -0.04, -0.08,  0.30, -0.16, -0.26,  0.08,  0.18,  0.64, -0.34, -0.18,  0.32,  0.00, -0.15,  0.000),
        (30, -0.01,  0.00,  0.05,  0.02,  0.02,  0.26, -0.10, -0.06,  0.12, -0.08,  0.42,  0.14, -0.08,  0.18,  0.00,  0.10,  0.000),
        (33,  0.02,  0.00,  0.02, -0.03, -0.06,  0.20, -0.14, -0.22,  0.06,  0.14,  0.60, -0.30, -0.14,  0.26,  0.00, -0.10,  0.000),
        # Frame 36: Seamless return to neutral start pose
        (36,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000),
    ]

    for (f, p_dy, p_dz, p_pitch, c_pitch, h_pitch, h_yaw, h_roll,
         j_pitch, l_pitch, e_roll, al_p, al_r, ar_p, ar_r, lg_p, sk_p, p_dx) in body_keys:
        key_char_bone(f, "Pelvis", pitch_x=p_pitch, dx=p_dx, dy_up=p_dy, dz_fwd=p_dz)
        key_char_bone(f, "Spine", pitch_x=c_pitch * 0.5)
        key_char_bone(f, "Chest", pitch_x=c_pitch, yaw_y=h_yaw * 0.3)
        key_char_bone(f, "Tail", pitch_x=0.35 * p_pitch - 0.25 * lg_p, yaw_y=-h_yaw * 0.6)
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
        (10, 0.35,   0.0, -0.08, -0.02, 0.00),
        (12, 1.08,   0.0, -0.04, -0.06, 0.25),
        (14, 1.35,   0.0,  0.04, -0.16, 0.65),
        (19, 1.10,   0.0,  0.10, -0.26, 1.10),
        (24, 0.65,   0.0,  0.18, -0.36, 1.55),
        (28, 0.22,   0.0,  0.24, -0.44, 1.95),
        (32, 0.0001, 0.0,  0.00,  0.00, 0.00),
        (36, 0.0001, 0.0,  0.00,  0.00, 0.00),
    ]
    for f, sc, dx, dy, dz, r_z in fc1_keys:
        key_char_bone(f, "FartCloud.1", roll_z=r_z, dx=dx, dy_up=dy, dz_fwd=dz, scale=sc)

    # Stage 2: Giant Billowing Cauliflower Lime Cloud (`FartCloud.2`)
    fc2_keys = [
        (1,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (10, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (12, 0.72,    0.00, -0.02, -0.04,  0.00),
        (14, 1.24,   -0.02,  0.06, -0.14, -0.18),
        (19, 1.48,   -0.04,  0.16, -0.28, -0.38),
        (24, 1.38,   -0.06,  0.28, -0.42, -0.60),
        (28, 0.96,   -0.08,  0.42, -0.56, -0.85),
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
        (14, 0.66,    0.00,  0.02, -0.05,  0.00),
        (19, 1.22,    0.03,  0.12, -0.18,  0.15),
        (24, 1.45,    0.05,  0.26, -0.34,  0.32),
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
        key_char_bone(f, "Tail", pitch_x=0.05 * c, yaw_y=0.08 * s)
        key_char_bone(f, "Head", pitch_x=0.035 * s, yaw_y=0.04 * c, roll_z=0.025 * s)
        key_char_bone(f, "Ear.L", roll_z=0.06 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.06 * s)
        key_char_bone(f, "Arm.L", pitch_x=0.04 * s, roll_z=0.05 * c)
        key_char_bone(f, "Arm.R", pitch_x=-0.04 * s, roll_z=-0.05 * c)
        key_char_bone(f, "SkullPendant", pitch_x=0.06 * c, yaw_y=0.04 * s)
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
        key_char_bone(f, "Tail", pitch_x=0.08 * s2, yaw_y=0.18 * c)
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
        key_char_bone(f, "Tail", pitch_x=0.16 * s)
        key_char_bone(f, "Head", pitch_x=-0.10 * s, yaw_y=0.06 * c)
        key_char_bone(f, "Ear.L", roll_z=0.22 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.22 * s)
        key_char_bone(f, "Arm.L", roll_z=-0.28 * s)
        key_char_bone(f, "Arm.R", roll_z=0.28 * s)
        key_char_bone(f, "SkullPendant", pitch_x=-0.22 * c)
        key_char_bone(f, "Jaw", pitch_x=-0.12 * max(0.0, s))


def build_wave_wing(act):
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
        key_char_bone(f, "Tail", yaw_y=0.14 * s)
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
        key_char_bone(f, "Tail", yaw_y=-0.10 * s)


fart_act, fart_track = bake_action_to_nla("Kickin_Fart_Blast", 36, build_kickin_fart_blast)
idle_act, idle_track = bake_action_to_nla("Idle_Breathe", 60, build_idle_breathe)
walk_act, walk_track = bake_action_to_nla("Walk_Cycle", 48, build_walk_cycle)
bounce_act, bounce_track = bake_action_to_nla("Happy_Bounce", 40, build_happy_bounce)
wave_act, wave_track = bake_action_to_nla("Wave_Wing", 60, build_wave_wing)
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

# For static .OBJ export, mute tracks, reset pose so FartCloud is collapsed inside torso, and set sub.levels = 1
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
subsurf_mod.levels = 0
bpy.context.view_layer.update()

bpy.ops.wm.obj_export(
    filepath=OBJ_PATH,
    export_selected_objects=True,
    export_materials=True,
)

subsurf_mod.levels = 2
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


add_area_light("Key_Softbox", (-2.4, -3.6, 3.2), (0.0, 0.0, 1.45), energy=125.0, size=3.0, color_rgb=(1.0, 0.99, 0.98))
add_area_light("Fill_Softbox", (2.6, -3.2, 2.4), (0.0, 0.0, 1.35), energy=75.0, size=3.4, color_rgb=(0.97, 0.98, 1.0))
add_area_light("Top_Softbox", (0.0, -0.8, 4.2), (0.0, 0.0, 1.65), energy=80.0, size=3.2, color_rgb=(1.0, 1.0, 1.0))
add_area_light("Rim_Backlight", (0.0, 3.0, 3.0), (0.0, 0.0, 1.50), energy=85.0, size=2.6, color_rgb=(0.98, 0.98, 1.0))

world = bpy.data.worlds.new("KickinStudioWorld")
scene.world = world
world.use_nodes = True
bg_node = world.node_tree.nodes.get("Background")
if bg_node:
    bg_node.inputs[0].default_value = hex_to_rgba(0xF5F6F8)
    bg_node.inputs[1].default_value = 0.55

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


def aim_camera(loc, target=(0.0, 0.0, 1.40), lens=60.0):
    cam_data.lens = lens
    cam_obj.location = Vector(loc)
    direction = Vector(target) - Vector(loc)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


# ==============================================================================
# 9. RENDER STUDIO HERO FRONT (`1080x1350`) AND TURNAROUND VIEWS (`3/4`, `Side`)
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

# Ensure rest pose with hidden fart cloud for turnaround renders
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')
scene.frame_set(1)

# 9.1 Hero Front Render (1080x1350)
scene.cycles.samples = 36
scene.render.resolution_x = 1080
scene.render.resolution_y = 1350
aim_camera((0.0, -6.10, 1.45), target=(0.0, 0.0, 1.42), lens=60.0)
scene.render.filepath = RENDER_FRONT_PATH
bpy.ops.render.render(write_still=True)

# 9.2 3/4 & Side Turnaround Renders (800x1000)
scene.cycles.samples = 28
scene.render.resolution_x = 800
scene.render.resolution_y = 1000

aim_camera((-4.25, -4.35, 1.54), target=(0.0, 0.0, 1.42), lens=60.0)
scene.render.filepath = RENDER_3Q_PATH
bpy.ops.render.render(write_still=True)

aim_camera((-6.10, 0.0, 1.45), target=(0.0, 0.0, 1.42), lens=60.0)
scene.render.filepath = RENDER_SIDE_PATH
bpy.ops.render.render(write_still=True)


# ==============================================================================
# 10. RENDER THE 36-FRAME `Kickin_Fart_Blast` CYCLES ANIMATION SEQUENCE!
# ==============================================================================
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = (trk.name != "Kickin_Fart_Blast")

aim_camera((4.95, -3.65, 1.54), target=(-0.05, 0.36, 1.24), lens=54.0)

scene.frame_start = 1
scene.frame_end = 36
scene.frame_set(14)  # Save .blend thumbnail right at the peak of the green fart blast!
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)

scene.cycles.samples = 16
scene.render.resolution_x = 640
scene.render.resolution_y = 640

for f in range(1, 37):
    scene.frame_set(f)
    scene.render.filepath = os.path.join(FART_FRAMES_DIR, f"frame_{f:03d}.png")
    bpy.ops.render.render(write_still=True)

print("SUCCESS: Built KickinChicken .blend, .glb, .obj, studio renders, and all 36 frames of Kickin_Fart_Blast!")
print(f"  BLEND: {BLEND_PATH} ({os.path.getsize(BLEND_PATH)} bytes)")
print(f"  GLB:   {GLB_PATH} ({os.path.getsize(GLB_PATH)} bytes)")
print(f"  OBJ:   {OBJ_PATH} ({os.path.getsize(OBJ_PATH)} bytes)")
print(f"  FRONT: {RENDER_FRONT_PATH} ({os.path.getsize(RENDER_FRONT_PATH)} bytes)")
