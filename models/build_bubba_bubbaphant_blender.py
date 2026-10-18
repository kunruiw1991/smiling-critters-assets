#!/usr/bin/env python3
"""
Native Blender 4.3 Builder, Rigging, Animation & Cycles Studio Renderer
for Bubba Bubbaphant (#029 Official Plush Base Model - Smiling Critters).

Run headless via:
  /tmp/blender/blender -b --threads 8 --factory-startup --python-exit-code 1 \
    -P /tmp/smiling-critters-assets/models/build_bubba_bubbaphant_blender.py
"""

import os
import math
import subprocess
import bpy
import bmesh
from mathutils import Vector, Matrix, Euler, noise

OUT_DIR = "/tmp/smiling-critters-assets/models"
ANIM_DIR = "/tmp/smiling-critters-assets/animations"
WORK_DIR = "/tmp/work_bubba"
RENDER_SHEET_DIR = os.path.join(WORK_DIR, "renders")
FART_FRAMES_DIR = os.path.join(WORK_DIR, "frames")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(ANIM_DIR, exist_ok=True)
os.makedirs(RENDER_SHEET_DIR, exist_ok=True)
os.makedirs(FART_FRAMES_DIR, exist_ok=True)

REF_IMG_PATH = "/tmp/smiling-critters-assets/images/029_Bubba_Bubbaphant_Plushie.webp"
BLEND_PATH = os.path.join(OUT_DIR, "bubba_bubbaphant_plush_base_model.blend")
GLB_PATH = os.path.join(OUT_DIR, "bubba_bubbaphant_plush_base_model.glb")
OBJ_PATH = os.path.join(OUT_DIR, "bubba_bubbaphant_plush_base_model.obj")
RENDER_FRONT_PATH = os.path.join(OUT_DIR, "bubba_bubbaphant_blender_cycles_render.png")
RENDER_PREVIEW_PATH = os.path.join(OUT_DIR, "bubba_bubbaphant_3d_preview.png")


# ==============================================================================
# 1. SCENE RESET & HELPER UTILITIES
# ==============================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.unit_settings.system = 'METRIC'
scene.unit_settings.scale_length = 1.0

main_col = bpy.data.collections.new("BubbaBubbaphant_Plush_Rig")
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
    nx = x / 0.74
    ny = (y_up - 1.94) / 0.64
    r2 = min(0.92, nx * nx + ny * ny)
    return 0.66 * math.sqrt(max(0.08, 1.0 - r2))


def cloud_turbulence(p_world):
    """Multi-octave 3D procedural turbulence for billowing cartoon gas clouds."""
    q1 = Vector((p_world.x * 7.0, p_world.y * 7.0, p_world.z * 7.0))
    q2 = Vector((p_world.x * 15.0 + 3.1, p_world.y * 15.0 - 1.7, p_world.z * 15.0 + 2.3))
    n1 = noise.noise(q1)
    n2 = noise.noise(q2)
    return 0.032 * n1 + 0.016 * abs(n2)


# ==============================================================================
# 2. PROCEDURAL CYCLES / GLTF PBR MATERIALS (CERULEAN ELEPHANT + LIGHTBULB + FART)
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
    # Cerulean / Sky-Blue Plush Fleece Body (#2E8BC0 calibrated for rich plush look)
    "BodyCerulean": create_plush_material(
        "Bubba_Plush_Body_Cerulean", 0x2E8BC0, roughness=0.82, spec_ior=0.16,
        sheen=0.36, sheen_tint_mult=1.18, bump_scale=75.0, bump_strength=0.14,
        subsurface=0.08, emission_strength=0.04
    ),
    # Pale Ice-Blue Belly, Inner Ear Rim, Trunk Tip & Elephant Toe-Nail Accents (#9AD9F5)
    "AccentIceBlue": create_plush_material(
        "Bubba_Accent_Ice_Blue", 0x9AD9F5, roughness=0.76, spec_ior=0.18,
        sheen=0.38, sheen_tint_mult=1.08, bump_scale=85.0, bump_strength=0.10,
        subsurface=0.10, emission_strength=0.05
    ),
    # Deep Royal-Azure Plush for Recessed Inner Ear Cups, Cuffs & Tail Tuft (#1A659E)
    "DeepAzure": create_plush_material(
        "Bubba_InnerEar_Deep_Azure", 0x1A659E, roughness=0.84, spec_ior=0.12,
        sheen=0.28, sheen_tint_mult=1.10, bump_scale=80.0, bump_strength=0.13,
        subsurface=0.04
    ),
    # Iconic Bright Yellow Glowing Lightbulb Pendant (#FFD60A)
    "LightbulbYellow": create_plush_material(
        "Bubba_Pendant_Lightbulb_Yellow", 0xFFD60A, roughness=0.22, spec_ior=0.45,
        sheen=0.10, sheen_tint_mult=1.0, bump_scale=120.0, bump_strength=0.02,
        coat=0.40, coat_rough=0.04, emission_strength=0.26
    ),
    # Warm Amber-Gold Filament Heart Detail on Lightbulb (#B45309)
    "FilamentAmber": create_plush_material(
        "Bubba_Lightbulb_Filament_Amber", 0xB45309, roughness=0.30, spec_ior=0.40,
        sheen=0.0, bump_strength=0.0, metallic=0.70, emission_strength=0.12
    ),
    # Cobalt-Blue Metallic Lightbulb Screw Base & Collar Zipper Pull (#1D4ED8)
    "ScrewBaseBlue": create_plush_material(
        "Bubba_ScrewBase_Cobalt_Blue", 0x1D4ED8, roughness=0.26, spec_ior=0.45,
        sheen=0.0, bump_strength=0.0, metallic=0.82, coat=0.30
    ),
    # Soft Rosy-Pink Plush Tongue inside Open Grin (#F472B6)
    "TonguePink": create_plush_material(
        "Bubba_Tongue_Rose_Pink", 0xF472B6, roughness=0.78, spec_ior=0.15,
        sheen=0.30, bump_scale=90.0, bump_strength=0.08, subsurface=0.10
    ),
    # Deep Jet-Black Glossy Acrylic Dome Eyes
    "EyeGloss": create_plush_material(
        "Bubba_Eye_Acrylic_Black", 0x020203, roughness=0.04, spec_ior=0.12,
        sheen=0.0, bump_strength=0.0, coat=0.28, coat_rough=0.015
    ),
    # Studio Catchlight Highlight on Eyes
    "CatchlightWhite": create_plush_material(
        "Bubba_Eye_Catchlight_White", 0xFFFFFF, roughness=0.05, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, emission_strength=0.35
    ),
    # Pitch-Black Recessed Mouth Cavity & Eyebrows
    "MouthVoidBlack": create_plush_material(
        "Bubba_Mouth_Cavity_Black", 0x010102, roughness=0.99, spec_ior=0.01,
        sheen=0.0, bump_strength=0.0
    ),
    # Brushed Silver Zipper Teeth
    "ZipperMetal": create_plush_material(
        "Bubba_Zipper_Silver_Metal", 0xD8DDE6, roughness=0.22, spec_ior=0.5,
        sheen=0.0, bump_strength=0.0, metallic=0.92, coat=0.25
    ),
    # Dark Zipper Tape Track
    "ZipperTrack": create_plush_material(
        "Bubba_Zipper_Track_Dark", 0x0E1015, roughness=0.88, spec_ior=0.06,
        sheen=0.08, bump_strength=0.05
    ),
    # 3D Cartoon Fart Cloud Materials (Vibrant Toxic Lime, Neon Blast Core, Purple Swirl)
    "FartCloudLime": create_plush_material(
        "Bubba_Fart_Cloud_Lime", 0x4CE629, roughness=0.68, spec_ior=0.18,
        sheen=0.45, sheen_tint_mult=1.15, bump_scale=24.0, bump_strength=0.22,
        subsurface=0.35, emission_strength=0.28
    ),
    "FartCloudNeon": create_plush_material(
        "Bubba_Fart_Cloud_Neon_YellowGreen", 0xC4FF33, roughness=0.45, spec_ior=0.25,
        sheen=0.35, sheen_tint_mult=1.1, bump_scale=30.0, bump_strength=0.14,
        subsurface=0.25, emission_strength=0.55
    ),
    "FartCloudPurple": create_plush_material(
        "Bubba_Fart_Cloud_Purple", 0x9D4EDD, roughness=0.62, spec_ior=0.20,
        sheen=0.40, sheen_tint_mult=1.1, bump_scale=28.0, bump_strength=0.18,
        subsurface=0.25, emission_strength=0.32
    ),
}


# ==============================================================================
# 3. BUBBA BUBBAPHANT GEOMETRY BUILDER (BMESH + SKIN WEIGHTS)
# ==============================================================================
master_bm = bmesh.new()
deform_layer = master_bm.verts.layers.deform.verify()

# 25-Bone Skeletal Armature Hierarchy
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
assert len(BONE_NAMES) == 25, f"Expected 25 bones, got {len(BONE_NAMES)}"
BONE_IDX = {name: i for i, name in enumerate(BONE_NAMES)}

MAT_KEYS_ORDER = [
    "BodyCerulean",
    "AccentIceBlue",
    "DeepAzure",
    "LightbulbYellow",
    "FilamentAmber",
    "ScrewBaseBlue",
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
        segments=1,
        profile=0.7,
        affect='EDGES'
    )
    for v in bm.verts:
        v.co += Vector((cx, cy, cz))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def make_torus_tube_bm(curve_pts, radius_fn, radial_segs=18, closed=False):
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
# 3.1 PLUSH ELEPHANT HEAD WITH WIDE SMILING CHEEKS & CROWN SEAM
# ------------------------------------------------------------------------------
def elephant_head_deform(p):
    ny = p.y / 0.62
    # Narrower rounded forehead dome, wider chubby smiling cheeks
    if ny > 0.15:
        u = (ny - 0.15) / 0.85
        p.x *= (1.0 - 0.18 * (u ** 1.3))
        p.z *= (1.0 - 0.10 * (u ** 1.2))
        # Subtle plush center crown seam indentation
        seam = math.exp(-((p.x / 0.08) ** 2)) * max(0.0, u - 0.2)
        p.y -= 0.018 * seam
    else:
        # Wide cheek flare around the huge grin
        cheek_u = math.exp(-(((ny + 0.12) / 0.42) ** 2))
        p.x *= (1.0 + 0.14 * cheek_u)
        if p.z > 0:
            p.z *= (1.0 + 0.06 * cheek_u)
    return p


head_core_bm = make_uv_sphere_bm(
    0.66, 0.61, 0.62, cx=0.0, cy=1.94, cz=0.0,
    u_segs=32, v_segs=24,
    deform_fn=elephant_head_deform
)
append_bmesh_part(head_core_bm, "BodyCerulean", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.2 LARGE WIDE FANNING ELEPHANT EARS (`Ear.L`, `Ear.R`)
# ------------------------------------------------------------------------------
for side in (-1, 1):
    ear_bone = "Ear.L" if side == 1 else "Ear.R"

    def elephant_ear_outer_deform(p, s=side):
        # Kidney / C-shaped wide elephant ear silhouette
        ux = (s * p.x) / 0.40  # -1 at root, +1 at outer rim
        uy = p.y / 0.50        # -1 at bottom lobe, +1 at top lobe
        # Flare taller on the outer-upper fan, rounder at bottom lobe
        height_scale = 0.88 + 0.24 * max(0.0, ux + 0.2) + 0.10 * uy
        p.y *= height_scale
        # Gentle forward cup & plush C-rim thickening
        r2 = min(1.2, (p.x / 0.36) ** 2 + (p.y / 0.46) ** 2)
        if p.z > 0.0 and r2 < 0.72:
            # Recessed inner ear bowl on the front face
            cup_depth = (0.72 - r2) / 0.72
            p.z -= 0.065 * cup_depth
        # Slight curve backward near the outer ear tip
        p.z -= 0.045 * max(0.0, ux) ** 2
        return p

    ear_cx = side * 0.84
    ear_cy = 2.06
    ear_cz = -0.02
    ear_rot = (0.04, -side * 0.18, -side * 0.10)

    ear_out_bm = make_uv_sphere_bm(
        0.41, 0.50, 0.115,
        cx=ear_cx, cy=ear_cy, cz=ear_cz,
        u_segs=26, v_segs=20,
        rot_euler=ear_rot,
        deform_fn=elephant_ear_outer_deform
    )
    append_bmesh_part(
        ear_out_bm, "BodyCerulean",
        lambda x, y, z, b=ear_bone: {b: 0.90, "Head": 0.10}
    )

    # Pale Ice-Blue (#9AD9F5) Inner Ear Seam Highlight Rim
    def elephant_ear_rim_deform(p, s=side):
        ux = (s * p.x) / 0.31
        uy = p.y / 0.39
        p.y *= (0.88 + 0.22 * max(0.0, ux + 0.2) + 0.08 * uy)
        p.z -= 0.035 * max(0.0, ux) ** 2
        return p

    ear_ice_bm = make_uv_sphere_bm(
        0.31, 0.39, 0.052,
        cx=ear_cx + side * 0.015, cy=ear_cy - 0.005, cz=ear_cz + 0.048,
        u_segs=22, v_segs=16,
        rot_euler=ear_rot,
        deform_fn=elephant_ear_rim_deform
    )
    append_bmesh_part(
        ear_ice_bm, "AccentIceBlue",
        lambda x, y, z, b=ear_bone: {b: 0.92, "Head": 0.08}
    )

    # Deep Royal-Azure (#1A659E) Recessed Inner Ear Lining
    ear_in_bm = make_uv_sphere_bm(
        0.285, 0.365, 0.048,
        cx=ear_cx + side * 0.018, cy=ear_cy - 0.008, cz=ear_cz + 0.056,
        u_segs=22, v_segs=16,
        rot_euler=ear_rot,
        deform_fn=elephant_ear_rim_deform
    )
    append_bmesh_part(
        ear_in_bm, "DeepAzure",
        lambda x, y, z, b=ear_bone: {b: 0.92, "Head": 0.08}
    )


# ------------------------------------------------------------------------------
# 3.3 WIDE CHEERFUL OPEN GRIN, PLUSH CHEEK LIPS & ROSY TONGUE
# ------------------------------------------------------------------------------
def upper_lip_curve_pt(t):
    lx = t * 0.51
    ly = 1.815 + 0.115 * (t * t) - 0.020 * (t ** 4)
    lz = head_front_z(lx, ly) + 0.026 * (1.0 - 0.32 * t * t)
    return (lx, ly, lz)


def lower_lip_curve_pt(t):
    lx = t * 0.51
    ly = 1.435 + 0.495 * (t ** 2)
    lz = head_front_z(lx, ly) + 0.022 * (1.0 - 0.30 * t * t)
    return (lx, ly, lz)


def build_conformed_mouth_cavity_bm():
    bm = bmesh.new()
    u_steps = 32
    v_steps = 12
    grid = []
    for iv in range(v_steps + 1):
        v_frac = iv / v_steps
        ring = []
        for iu in range(u_steps + 1):
            t = -0.96 + 1.92 * (iu / u_steps)
            x_low, y_low, _ = lower_lip_curve_pt(t)
            x_up, y_up, _ = upper_lip_curve_pt(t)
            ux = x_low + (x_up - x_low) * v_frac
            uy = y_low + (y_up - y_low) * v_frac
            uz = head_front_z(ux, uy) - 0.006
            ring.append(bm.verts.new((ux, uy, uz)))
        grid.append(ring)

    for iv in range(v_steps):
        r1 = grid[iv]
        r2 = grid[iv + 1]
        for iu in range(u_steps):
            bm.faces.new([r1[iu], r1[iu + 1], r2[iu + 1], r2[iu]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


mouth_bm = build_conformed_mouth_cavity_bm()
append_bmesh_part(
    mouth_bm, "MouthVoidBlack",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.76 - y) * 2.8)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.76 - y) * 2.8))}
)

# Rosy-Pink Plush Tongue nestled in the lower mouth cavity
for side in (-1, 1):
    tongue_bm = make_uv_sphere_bm(
        0.13, 0.055, 0.065,
        cx=side * 0.075, cy=1.525, cz=head_front_z(side * 0.075, 1.525) + 0.008,
        u_segs=16, v_segs=12,
        rot_euler=(0.18, 0.0, -side * 0.12)
    )
    append_bmesh_part(tongue_bm, "TonguePink", lambda x, y, z: {"Jaw": 0.85, "Head": 0.15})

# Smooth Cerulean Plush Upper & Lower Smile Lip Rims
upper_lip_pts = [upper_lip_curve_pt(-1.0 + 2.0 * k / 32.0) for k in range(33)]
upper_lip_bm = make_torus_tube_bm(
    upper_lip_pts,
    lambda t: 0.042 + 0.012 * math.sin(math.pi * t),
    radial_segs=14, closed=False
)
append_bmesh_part(upper_lip_bm, "BodyCerulean", lambda x, y, z: {"Head": 0.90, "Jaw": 0.10})

lower_lip_pts = [lower_lip_curve_pt(-1.0 + 2.0 * k / 36.0) for k in range(37)]
lower_lip_bm = make_torus_tube_bm(
    lower_lip_pts,
    lambda t: 0.038 + 0.010 * math.sin(math.pi * t),
    radial_segs=14, closed=False
)
append_bmesh_part(
    lower_lip_bm, "BodyCerulean",
    lambda x, y, z: {"Jaw": max(0.0, min(1.0, (1.76 - y) * 2.6)),
                     "Head": 1.0 - max(0.0, min(1.0, (1.76 - y) * 2.6))}
)

# Cheek Smile Corner Pouches
for side in (-1, 1):
    cheek_pts = []
    for k in range(11):
        t = k / 10.0
        cx = side * (0.48 + 0.055 * math.sin(math.pi * t))
        cy = 1.82 + 0.14 * (1.0 - t)
        cz = head_front_z(cx, cy) + 0.024
        cheek_pts.append((cx, cy, cz))
    cheek_bm = make_torus_tube_bm(cheek_pts, 0.038, radial_segs=12, closed=False)
    append_bmesh_part(cheek_bm, "BodyCerulean", lambda x, y, z: {"Head": 0.92, "Jaw": 0.08})


# ------------------------------------------------------------------------------
# 3.4 LARGE GLOSSY BLACK EYES, CATCHLIGHTS & ARCHED EYEBROWS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    lid_bone = "Eyelid.L" if side == 1 else "Eyelid.R"
    ex = side * 0.205
    ey = 2.055
    ez = head_front_z(ex, ey) - 0.010

    # Eye socket plush rim
    sock_bm = make_uv_sphere_bm(
        0.158, 0.168, 0.095,
        cx=ex, cy=ey, cz=ez - 0.015,
        u_segs=24, v_segs=18,
        rot_euler=(-0.05, side * 0.15, 0.0)
    )
    append_bmesh_part(sock_bm, "BodyCerulean", lambda x, y, z: {"Head": 1.0})

    # Glossy Jet-Black Acrylic Eye Dome
    eye_bm = make_uv_sphere_bm(
        0.142, 0.152, 0.108,
        cx=ex, cy=ey, cz=ez,
        u_segs=30, v_segs=22,
        rot_euler=(-0.05, side * 0.15, 0.0)
    )
    append_bmesh_part(eye_bm, "EyeGloss", lambda x, y, z: {"Head": 1.0})

    # Primary Studio White Catchlight
    hi1_bm = make_uv_sphere_bm(
        0.032, 0.048, 0.014,
        cx=ex - side * 0.030, cy=ey + 0.028, cz=ez + 0.102,
        u_segs=14, v_segs=10,
        rot_euler=(-0.08, side * 0.12, 0.0)
    )
    append_bmesh_part(hi1_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Secondary Lower Pin Catchlight
    hi2_bm = make_uv_sphere_bm(
        0.015, 0.015, 0.010,
        cx=ex + side * 0.035, cy=ey - 0.038, cz=ez + 0.098,
        u_segs=10, v_segs=8
    )
    append_bmesh_part(hi2_bm, "CatchlightWhite", lambda x, y, z: {"Head": 1.0})

    # Upper Plush Eyelid Rim (`Eyelid.L` / `Eyelid.R`)
    lid_pts = []
    for k in range(15):
        t = -1.0 + 2.0 * k / 14.0
        lx = ex + t * 0.145
        ly = ey + 0.115 * math.cos(t * 1.15)
        lz = ez + 0.088 * math.cos(t * 0.95)
        lid_pts.append((lx, ly, lz))
    lid_bm = make_torus_tube_bm(
        lid_pts,
        lambda t: 0.020 * math.sin(math.pi * (0.08 + 0.84 * t)),
        radial_segs=12, closed=False
    )
    append_bmesh_part(lid_bm, "BodyCerulean", lambda x, y, z, b=lid_bone: {b: 0.90, "Head": 0.10})

    # Arched Cheerful Black Eyebrows on Upper Forehead
    brow_pts = []
    for k in range(13):
        t = k / 12.0
        bx = side * (0.09 + 0.22 * t)
        by = 2.27 + 0.065 * math.sin(math.pi * t)
        bz = head_front_z(bx, by) + 0.016
        brow_pts.append((bx, by, bz))
    brow_bm = make_torus_tube_bm(
        brow_pts,
        lambda t: 0.018 * math.sin(math.pi * (0.10 + 0.80 * t)),
        radial_segs=10, closed=False
    )
    append_bmesh_part(brow_bm, "MouthVoidBlack", lambda x, y, z: {"Head": 1.0})


# ------------------------------------------------------------------------------
# 3.5 ICONIC UPWARD-CURLED PLUSH ELEPHANT TRUNK (`Head` / `Jaw`)
# ------------------------------------------------------------------------------
# Smooth J-curve elephant trunk starting between the eyes, sweeping down over the mouth
# and curling forward & upward with a Pale Ice-Blue (#9AD9F5) tip pad!
trunk_pts = []
n_trunk = 28
for k in range(n_trunk):
    u = k / (n_trunk - 1)
    # Slight cute asymmetry (tiny 0.02m tilt at tip just like 029_Bubba_Bubbaphant_Plushie.webp)
    tx = -0.022 * math.sin(u * math.pi * 0.85)
    if u < 0.62:
        # Descending plush bridge & trunk shaft
        v = u / 0.62
        ty = 1.95 - 0.43 * (v ** 1.08)
        tz = 0.60 + 0.23 * math.sin(v * math.pi * 0.62)
    else:
        # Upward & forward J-hook curl at the bottom of the trunk
        v = (u - 0.62) / 0.38
        ang = v * math.pi * 0.78
        ty = 1.52 + 0.13 * (1.0 - math.cos(ang))
        tz = 0.81 + 0.15 * math.sin(ang)
    trunk_pts.append((tx, ty, tz))


def trunk_radius_fn(t):
    # Plump at the brow root, tapering smoothly toward the curled tip, flaring slightly at the rim
    base_r = 0.132 * (1.0 - 0.32 * t) + 0.016 * math.exp(-(((t - 0.96) / 0.08) ** 2))
    return base_r


def trunk_weight_fn(x, y, z):
    # Smoothly blend from Head at the upper root to Jaw at the lower curled tip
    jaw_w = max(0.0, min(0.65, (1.88 - y) * 1.35 + max(0.0, z - 0.75) * 1.2))
    return {"Head": 1.0 - jaw_w, "Jaw": jaw_w}


trunk_bm = make_torus_tube_bm(trunk_pts, trunk_radius_fn, radial_segs=20, closed=False)
append_bmesh_part(trunk_bm, "BodyCerulean", trunk_weight_fn)

# Pale Ice-Blue (#9AD9F5) Circular Trunk-Tip Pad & Deep-Azure Nostril Indentation
tip_pt = Vector(trunk_pts[-1])
tip_euler = (-0.52, 0.0, 0.0)

trunk_tip_pad_bm = make_uv_sphere_bm(
    0.088, 0.088, 0.024,
    cx=tip_pt.x, cy=tip_pt.y + 0.005, cz=tip_pt.z + 0.008,
    u_segs=18, v_segs=12,
    rot_euler=tip_euler
)
append_bmesh_part(trunk_tip_pad_bm, "AccentIceBlue", trunk_weight_fn)

trunk_nostril_bm = make_uv_sphere_bm(
    0.050, 0.042, 0.015,
    cx=tip_pt.x, cy=tip_pt.y + 0.010, cz=tip_pt.z + 0.019,
    u_segs=14, v_segs=10,
    rot_euler=tip_euler
)
append_bmesh_part(trunk_nostril_bm, "DeepAzure", trunk_weight_fn)


# ------------------------------------------------------------------------------
# 3.6 PLUSH TORSO, PALE ICE-BLUE BELLY PATCH, BLACK ZIPPER & YELLOW LIGHTBULB PENDANT
# ------------------------------------------------------------------------------
TORSO_PROFILE = [
    (0.00, 0.50), (0.20, 0.51), (0.37, 0.56), (0.48, 0.65),
    (0.52, 0.78), (0.53, 0.92), (0.50, 1.06), (0.45, 1.20),
    (0.39, 1.33), (0.33, 1.43), (0.26, 1.50), (0.00, 1.52)
]


def build_torso_bm():
    bm = bmesh.new()
    u_segs = 36
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
        t = min(1.0, (y - 1.12) / 0.38)
        return {"Spine": max(0.0, 0.4 * (1.0 - t)), "Chest": 0.85, "Head": 0.15 * t}


torso_bm = build_torso_bm()
append_bmesh_part(torso_bm, "BodyCerulean", torso_weights)


def torso_front_z(y, x=0.0):
    # Piecewise linear interpolation of exact TORSO_PROFILE radius
    r = 0.42
    for i in range(1, len(TORSO_PROFILE) - 2):
        r0, y0 = TORSO_PROFILE[i]
        r1, y1 = TORSO_PROFILE[i + 1]
        if y0 <= y <= y1:
            u = (y - y0) / max(1e-5, y1 - y0)
            r = r0 + u * (r1 - r0)
            break
    z_center = r * 0.88
    x_ratio = min(0.92, abs(x) / max(0.12, r))
    return z_center * math.sqrt(max(0.08, 1.0 - x_ratio * x_ratio))


# Pale Ice-Blue (#9AD9F5) Conformed Oval Belly Patch
def build_belly_patch_bm():
    bm = bmesh.new()
    u_steps = 24
    v_steps = 10
    grid = []
    for iv in range(v_steps + 1):
        vf = iv / v_steps
        ring = []
        for iu in range(u_steps):
            ang = 2.0 * math.pi * iu / u_steps
            bx = math.cos(ang) * 0.28 * vf
            by = 0.88 + math.sin(ang) * 0.29 * vf
            bz = torso_front_z(by, bx) + 0.008 * (1.0 - 0.35 * vf * vf)
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
append_bmesh_part(belly_bm, "AccentIceBlue", torso_weights)

# Black Zipper Track & Silver Zipper Teeth Running Vertically Down the Front
zip_pts = [
    (0.0, 0.56 + (1.42 - 0.56) * k / 22.0, torso_front_z(0.56 + (1.42 - 0.56) * k / 22.0) + 0.008)
    for k in range(23)
]
zip_track_bm = make_torus_tube_bm(zip_pts, 0.025, radial_segs=10, closed=False)
append_bmesh_part(zip_track_bm, "ZipperTrack", torso_weights)

for i in range(28):
    zy = 0.58 + (1.40 - 0.58) * (i / 27.0)
    zz = torso_front_z(zy) + 0.020
    zx = (0.009 if (i % 2 == 0) else -0.009)
    t_bm = make_beveled_box_bm(0.032, 0.012, 0.018, zx, zy, zz)
    append_bmesh_part(t_bm, "ZipperMetal", torso_weights)

# Cobalt-Blue Zipper Collar Slider & Clasp
slider_bm = make_beveled_box_bm(0.064, 0.080, 0.042, 0.0, 1.335, 0.448)
append_bmesh_part(slider_bm, "ScrewBaseBlue", lambda x, y, z: {"Chest": 0.7, "SkullPendant": 0.3})

clasp_bm = make_beveled_box_bm(0.040, 0.060, 0.036, 0.0, 1.275, 0.465)
append_bmesh_part(clasp_bm, "ScrewBaseBlue", lambda x, y, z: {"SkullPendant": 1.0})


# ------------------------------------------------------------------------------
# 3.7 ICONIC BRIGHT YELLOW GLOWING LIGHTBULB PENDANT WITH SCREW BASE (`SkullPendant`)
# ------------------------------------------------------------------------------
def lightbulb_globe_deform(p):
    # Pear-shaped lightbulb: round upper globe tapering into a cylindrical lower neck
    ny = p.y / 0.175
    if ny < -0.15:
        u = min(1.0, (-0.15 - ny) / 0.85)
        neck_factor = 1.0 - 0.42 * (u ** 1.1)
        p.x *= neck_factor
    return p


bulb_bm = make_uv_sphere_bm(
    0.178, 0.175, 0.056,
    cx=0.0, cy=1.125, cz=0.495,
    u_segs=32, v_segs=24,
    rot_euler=(-0.05, 0.0, 0.0),
    deform_fn=lightbulb_globe_deform
)
append_bmesh_part(bulb_bm, "LightbulbYellow", lambda x, y, z: {"SkullPendant": 1.0})

# Glowing Heart-Shaped Filament on Front of Yellow Lightbulb
filament_pts = []
for k in range(29):
    u = k / 28.0
    ang = (u - 0.5) * math.pi * 1.75
    # Classic lightbulb heart-loop filament silhouette
    fx = 0.078 * math.sin(ang) * (1.0 - 0.25 * (u - 0.5) ** 2)
    fy = 1.06 + 0.115 * math.cos(ang * 0.65) - 0.042 * abs(math.sin(ang * 1.1))
    fz = 0.546
    filament_pts.append((fx, fy, fz))

filament_bm = make_torus_tube_bm(filament_pts, 0.0095, radial_segs=10, closed=False)
append_bmesh_part(filament_bm, "FilamentAmber", lambda x, y, z: {"SkullPendant": 1.0})

# Cobalt-Blue Threaded Screw Base at Bottom of Lightbulb (`y = 0.90..0.98`)
screw_base_bm = make_uv_sphere_bm(
    0.088, 0.062, 0.048,
    cx=0.0, cy=0.945, cz=0.495,
    u_segs=22, v_segs=16,
    rot_euler=(-0.05, 0.0, 0.0)
)
append_bmesh_part(screw_base_bm, "ScrewBaseBlue", lambda x, y, z: {"SkullPendant": 1.0})

for thread_y in (0.968, 0.945, 0.922):
    th_pts = []
    for k in range(20):
        ang = 2.0 * math.pi * k / 20.0
        th_pts.append((0.086 * math.cos(ang), thread_y, 0.495 + 0.046 * math.sin(ang)))
    th_bm = make_torus_tube_bm(th_pts, 0.008, radial_segs=8, closed=True)
    append_bmesh_part(th_bm, "ZipperMetal", lambda x, y, z: {"SkullPendant": 1.0})

# Dark contact button at very bottom of lightbulb screw base
contact_bm = make_uv_sphere_bm(
    0.048, 0.022, 0.032,
    cx=0.0, cy=0.892, cz=0.495,
    u_segs=14, v_segs=10
)
append_bmesh_part(contact_bm, "MouthVoidBlack", lambda x, y, z: {"SkullPendant": 1.0})


# ------------------------------------------------------------------------------
# 3.8 SPLAYED PLUSH ARMS & ELEPHANT CUFF PAWS WITH TOE-NAIL PADS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    sh_bone = "Shoulder.L" if side == 1 else "Shoulder.R"
    arm_bone = "Arm.L" if side == 1 else "Arm.R"
    hoof_bone = "HandHoof.L" if side == 1 else "HandHoof.R"

    arm_pts = []
    for k in range(13):
        t = k / 12.0
        ax = side * (0.32 + 0.38 * t)
        ay = 1.33 - 0.32 * t + 0.02 * math.sin(math.pi * t)
        az = 0.02 + 0.04 * t
        arm_pts.append((ax, ay, az))

    arm_bm = make_torus_tube_bm(
        arm_pts,
        lambda t: 0.142 * (1.0 + 0.05 * t),
        radial_segs=20, closed=False
    )

    def arm_weight_fn(x, y, z, sb=sh_bone, ab=arm_bone, hb=hoof_bone):
        dist = max(0.0, min(1.0, (abs(x) - 0.32) / 0.45))
        if dist < 0.35:
            return {"Chest": 0.35 * (1.0 - dist / 0.35), sb: 0.65, ab: 0.35 * (dist / 0.35)}
        elif dist < 0.85:
            return {ab: 0.85, sb: 0.15}
        else:
            return {ab: 0.50, hb: 0.50}

    append_bmesh_part(arm_bm, "BodyCerulean", arm_weight_fn)

    # Deep-Azure Elephant Paw Cuff (`HandHoof.L/R`)
    paw_pts = []
    for k in range(11):
        t = k / 10.0
        mx = side * (0.68 + 0.23 * t)
        my = 1.03 - 0.19 * t
        mz = 0.06 + 0.03 * t
        paw_pts.append((mx, my, mz))

    def paw_radius(t):
        if t < 0.15:
            return 0.148 + 0.014 * (t / 0.15)
        elif t < 0.72:
            return 0.162 + 0.008 * math.sin(math.pi * (t - 0.15) / 0.57)
        else:
            u = (t - 0.72) / 0.28
            return 0.162 * math.sqrt(max(0.04, 1.0 - u * u))

    paw_bm = make_torus_tube_bm(paw_pts, paw_radius, radial_segs=20, closed=False)
    append_bmesh_part(
        paw_bm, "DeepAzure",
        lambda x, y, z, hb=hoof_bone, ab=arm_bone: {hb: 0.90, ab: 0.10}
    )

    # 3 Pale Ice-Blue (#9AD9F5) Elephant Toe-Nail Accents on Each Paw
    for toe_z_off in (-0.055, 0.0, 0.055):
        toe_bm = make_uv_sphere_bm(
            0.032, 0.040, 0.026,
            cx=side * 0.89, cy=0.83, cz=0.11 + toe_z_off,
            u_segs=12, v_segs=10,
            rot_euler=(0.0, 0.0, -side * 0.55)
        )
        append_bmesh_part(toe_bm, "AccentIceBlue", lambda x, y, z, hb=hoof_bone: {hb: 1.0})


# ------------------------------------------------------------------------------
# 3.9 STOUT ELEPHANT LEGS, ROUNDED STUMPY FEET & 3 PALE ICE-BLUE TOE-NAIL PADS
# ------------------------------------------------------------------------------
for side in (-1, 1):
    leg_bone = "Leg.L" if side == 1 else "Leg.R"
    foot_bone = "FootHoof.L" if side == 1 else "FootHoof.R"

    leg_pts = []
    for k in range(13):
        t = k / 12.0
        lx = side * (0.25 + 0.055 * t)
        ly = 0.66 - 0.42 * t
        lz = 0.0 + 0.03 * t
        leg_pts.append((lx, ly, lz))

    leg_bm = make_torus_tube_bm(
        leg_pts,
        lambda t: 0.188 * (1.0 - 0.04 * t),
        radial_segs=20, closed=False
    )

    def leg_weight_fn(x, y, z, lb=leg_bone, fb=foot_bone):
        if y > 0.52:
            return {"Pelvis": 0.45, lb: 0.55}
        elif y > 0.25:
            return {lb: 0.90, fb: 0.10}
        else:
            return {lb: 0.25, fb: 0.75}

    append_bmesh_part(leg_bm, "BodyCerulean", leg_weight_fn)

    fx = side * 0.310
    fy = 0.145
    fz = 0.075

    def foot_deform(p):
        if p.y < -0.02:
            p.y = -0.125 + (p.y + 0.125) * 0.16
        return p

    foot_bm = make_uv_sphere_bm(
        0.205, 0.160, 0.225,
        cx=fx, cy=fy, cz=fz,
        u_segs=26, v_segs=18,
        deform_fn=foot_deform
    )
    append_bmesh_part(
        foot_bm, "DeepAzure",
        lambda x, y, z, fb=foot_bone, lb=leg_bone: {fb: 0.92, lb: 0.08}
    )

    # 3 Sculpted Pale Ice-Blue (#9AD9F5) Elephant Toe-Nail Pads on Front of Each Foot
    for t_ang in (-0.42, 0.0, 0.42):
        tx = fx + math.sin(t_ang) * 0.125
        ty = 0.085
        tz = fz + math.cos(t_ang) * 0.212
        ftoe_bm = make_uv_sphere_bm(
            0.044, 0.056, 0.026,
            cx=tx, cy=ty, cz=tz,
            u_segs=14, v_segs=10,
            rot_euler=(-0.18, t_ang, 0.0)
        )
        append_bmesh_part(ftoe_bm, "AccentIceBlue", lambda x, y, z, fb=foot_bone: {fb: 1.0})


# ------------------------------------------------------------------------------
# 3.10 SMALL TUFTED BLUE ELEPHANT TAIL (`Tail` BONE)
# ------------------------------------------------------------------------------
tail_pts = []
for k in range(13):
    t = k / 12.0
    tx = 0.0
    ty = 0.68 - 0.04 * math.sin(t * math.pi) + 0.14 * (t ** 1.6)
    tz = -0.40 - 0.36 * t
    tail_pts.append((tx, ty, tz))

tail_shaft_bm = make_torus_tube_bm(
    tail_pts,
    lambda t: 0.042 * (1.0 - 0.30 * t),
    radial_segs=12, closed=False
)
append_bmesh_part(
    tail_shaft_bm, "BodyCerulean",
    lambda x, y, z: {"Tail": 0.88, "Pelvis": 0.12}
)

# Tufted Paintbrush Tip on Elephant Tail
def tail_tuft_deform(p):
    # Teardrop tuft point at outer end
    if p.z < 0:
        p.x *= (1.0 + 0.4 * (p.z / 0.11))
        p.y *= (1.0 + 0.4 * (p.z / 0.11))
    return p


tail_tuft_bm = make_uv_sphere_bm(
    0.068, 0.082, 0.110,
    cx=0.0, cy=0.81, cz=-0.81,
    u_segs=18, v_segs=14,
    rot_euler=(0.45, 0.0, 0.0),
    deform_fn=tail_tuft_deform
)
append_bmesh_part(tail_tuft_bm, "DeepAzure", lambda x, y, z: {"Tail": 0.95, "Pelvis": 0.05})


# ------------------------------------------------------------------------------
# 3.11 3D SCULPTED CARTOON FART CLOUD CLUSTER (`FartCloud.1`, `FartCloud.2`, `FartCloud.3`)
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
        return p_w + n_w * (cloud_turbulence(p_w + Vector((s * 1.1, 0.0, s * 0.7))) * 0.85)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=14, v_segs=10, world_deform_fn=fc1_disp)
    append_bmesh_part(bm_p, mkey, lambda x, y, z: {"FartCloud.1": 1.0})

# 3D Shockwave Torus Ring around the nozzle blast (`FartCloud.1`)
ring_pts = []
for k in range(20):
    ang = 2.0 * math.pi * k / 20.0
    ring_pts.append((0.24 * math.cos(ang), 0.69 + 0.24 * math.sin(ang), -0.62))
shock_ring_bm = make_torus_tube_bm(ring_pts, 0.036, radial_segs=10, closed=True)
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
        return p_w + n_w * (cloud_turbulence(p_w + Vector((s * 1.7, s * 0.9, 0.0))) * 1.15)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=14, v_segs=10, world_deform_fn=fc2_disp)
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
        return p_w + n_w * (cloud_turbulence(p_w + Vector((0.0, s * 1.4, s * 2.1))) * 1.20)
    bm_p = make_uv_sphere_bm(rx, ry, rz, cx=fx, cy=fy, cz=fz, u_segs=14, v_segs=10, world_deform_fn=fc3_disp)
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
mesh_data = bpy.data.meshes.new("BubbaBubbaphant_Plush_MeshData")
for m in MAT_LIST:
    mesh_data.materials.append(m)

master_bm.to_mesh(mesh_data)
master_bm.free()
mesh_data.update()

mesh_obj = bpy.data.objects.new("BubbaBubbaphant_Plush_Mesh", mesh_data)
main_col.objects.link(mesh_obj)

for bname in BONE_NAMES:
    mesh_obj.vertex_groups.new(name=bname)


# ==============================================================================
# 5. CREATE SKELETAL ARMATURE RIG (25 BONES) & BIND SKINNING
# ==============================================================================
arm_data = bpy.data.armatures.new("BubbaBubbaphant_ArmatureData")
arm_data.display_type = 'OCTAHEDRAL'
arm_obj = bpy.data.objects.new("BubbaBubbaphant_Armature", arm_data)
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
add_ebone("Head", (0.0, 1.50, 0.0), (0.0, 2.45, 0.0), "Chest", True)

add_ebone("Jaw", (0.0, 1.72, 0.45), (0.0, 1.52, 0.88), "Head", False)
add_ebone("Eyelid.L", (0.205, 2.055, 0.58), (0.205, 2.18, 0.72), "Head", False)
add_ebone("Eyelid.R", (-0.205, 2.055, 0.58), (-0.205, 2.18, 0.72), "Head", False)
add_ebone("Ear.L", (0.58, 2.06, -0.02), (1.22, 2.08, -0.04), "Head", False)
add_ebone("Ear.R", (-0.58, 2.06, -0.02), (-1.22, 2.08, -0.04), "Head", False)

add_ebone("SkullPendant", (0.0, 1.28, 0.46), (0.0, 0.90, 0.50), "Chest", False)
add_ebone("Tail", (0.0, 0.68, -0.40), (0.0, 0.81, -0.82), "Pelvis", False)

add_ebone("Shoulder.L", (0.28, 1.34, 0.02), (0.44, 1.24, 0.03), "Chest", False)
add_ebone("Arm.L", (0.44, 1.24, 0.03), (0.70, 1.02, 0.06), "Shoulder.L", True)
add_ebone("HandHoof.L", (0.70, 1.02, 0.06), (0.91, 0.84, 0.09), "Arm.L", True)

add_ebone("Shoulder.R", (-0.28, 1.34, 0.02), (-0.44, 1.24, 0.03), "Chest", False)
add_ebone("Arm.R", (-0.44, 1.24, 0.03), (-0.70, 1.02, 0.06), "Shoulder.R", True)
add_ebone("HandHoof.R", (-0.70, 1.02, 0.06), (-0.91, 0.84, 0.09), "Arm.R", True)

add_ebone("Leg.L", (0.25, 0.66, 0.0), (0.31, 0.24, 0.03), "Pelvis", False)
add_ebone("FootHoof.L", (0.31, 0.24, 0.03), (0.31, 0.06, 0.24), "Leg.L", True)

add_ebone("Leg.R", (-0.25, 0.66, 0.0), (-0.31, 0.24, 0.03), "Pelvis", False)
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

sub = mesh_obj.modifiers.new(name="Subdivision", type='SUBSURF')
sub.levels = 1
sub.render_levels = 2
sub.quality = 3


# ==============================================================================
# 6. AUTHOR 6 NLA / ACTION ANIMATION CLIPS ON THE ARMATURE (INCLUDING Bubba_Fart_Blast)
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


def build_bubba_fart_blast(act):
    """
    36-Frame (1.5s @ 24fps) Cartoon Animation: `Bubba_Fart_Blast`
      - Act 1 (Frames 1..9):   Deep squat, tummy clench, tail lift & strain tremble
      - Act 2 (Frames 10..14): Explosive rocket recoil jump + 3-stage green/lime/purple 3D fart cloud!
      - Act 3 (Frames 15..26): Mid-air hop, trunk trumpet & soft landing on elephant feet
      - Act 4 (Frames 27..36): Turn to camera, paw-fanning cloud behind back & elephant chuckle!
    """
    body_keys = [
        # (frame, p_dy, p_dz, p_pitch, c_pitch, h_pitch, h_yaw, h_roll,
        #  j_pitch, l_pitch, e_roll, al_p, al_r, ar_p, ar_r, lg_p, sk_p, p_dx, tail_p)
        (1,   0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000,  0.00),
        (4,  -0.09, -0.02,  0.22,  0.14,  0.16, -0.06,  0.00,  0.06,  0.20, -0.18,  0.22,  0.28,  0.22, -0.28, -0.22,  0.18,  0.000, -0.30),
        (6,  -0.13, -0.04,  0.30,  0.18,  0.22, -0.10,  0.05,  0.10,  0.28, -0.25,  0.30,  0.35,  0.30, -0.35, -0.28,  0.24,  0.020, -0.45),
        (8,  -0.14, -0.04,  0.32,  0.20,  0.24, -0.08, -0.05,  0.12,  0.30, -0.28,  0.32,  0.38,  0.32, -0.38, -0.30,  0.26, -0.020, -0.52),
        (9,  -0.15, -0.05,  0.35,  0.22,  0.26, -0.12,  0.05,  0.14,  0.32, -0.30,  0.34,  0.40,  0.34, -0.40, -0.32,  0.28,  0.018, -0.58),
        # Act 2 (Frames 10..14): Explosive Rocket Recoil Jump & Trunk Trumpet!
        (11,  0.14,  0.06,  0.28, -0.16, -0.22,  0.16, -0.08, -0.28, -0.12,  0.36, -0.20, -0.48, -0.20,  0.48,  0.24, -0.42,  0.000, -0.65),
        (14,  0.18,  0.08,  0.22, -0.18, -0.25,  0.24, -0.12, -0.34, -0.14,  0.42, -0.25, -0.54, -0.25,  0.54,  0.28, -0.48,  0.000, -0.60),
        # Act 3 (Frames 15..26): Mid-Air Hop & Cushioned Landing
        (19,  0.11,  0.05,  0.14, -0.10, -0.14,  0.26, -0.10, -0.24, -0.08,  0.28, -0.12, -0.38, -0.15,  0.40,  0.16, -0.30,  0.000, -0.40),
        (23, -0.05,  0.01,  0.08,  0.04,  0.04,  0.28, -0.12, -0.12,  0.04, -0.10,  0.38, -0.15, -0.10,  0.25, -0.08,  0.12,  0.000, -0.20),
        (26,  0.02,  0.00,  0.04, -0.04, -0.08,  0.30, -0.16, -0.26,  0.08,  0.18,  0.62, -0.32, -0.18,  0.32,  0.00, -0.15,  0.000, -0.15),
        # Act 4 (Frames 27..36): Turn to Camera, Paw-Fanning Cloud & Elephant Chuckle!
        (29, -0.01,  0.00,  0.05,  0.02,  0.02,  0.26, -0.10, -0.06,  0.12, -0.08,  0.42,  0.12, -0.08,  0.18,  0.00,  0.10,  0.000,  0.10),
        (32,  0.02,  0.00,  0.02, -0.03, -0.06,  0.20, -0.14, -0.22,  0.06,  0.14,  0.58, -0.28, -0.14,  0.26,  0.00, -0.10,  0.000, -0.08),
        (36,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.00,  0.000,  0.00),
    ]

    for (f, p_dy, p_dz, p_pitch, c_pitch, h_pitch, h_yaw, h_roll,
         j_pitch, l_pitch, e_roll, al_p, al_r, ar_p, ar_r, lg_p, sk_p, p_dx, tl_p) in body_keys:
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
        key_char_bone(f, "Tail", pitch_x=tl_p, yaw_y=p_dx * 4.0)

    # Stage 1: Nozzle Jet & Shockwave Ring (`FartCloud.1`)
    fc1_keys = [
        (1,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (9,  0.0001, 0.0,  0.00,  0.00, 0.00),
        (10, 0.45,   0.0, -0.06, -0.02, 0.00),
        (12, 1.12,   0.0, -0.03, -0.06, 0.25),
        (14, 1.35,   0.0,  0.03, -0.14, 0.55),
        (19, 1.12,   0.0,  0.10, -0.26, 1.10),
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
        (9,  0.0001,  0.00,  0.00,  0.00,  0.00),
        (11, 0.72,    0.00, -0.02, -0.04,  0.00),
        (14, 1.25,   -0.02,  0.06, -0.14, -0.18),
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
        (11, 0.0001,  0.00,  0.00,  0.00,  0.00),
        (14, 0.78,    0.00,  0.02, -0.05,  0.00),
        (19, 1.28,    0.03,  0.14, -0.20,  0.18),
        (24, 1.45,    0.05,  0.28, -0.36,  0.34),
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
        key_char_bone(f, "Jaw", pitch_x=-0.04 * s)
        key_char_bone(f, "Ear.L", roll_z=0.08 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.08 * s)
        key_char_bone(f, "Arm.L", pitch_x=0.04 * s, roll_z=0.05 * c)
        key_char_bone(f, "Arm.R", pitch_x=-0.04 * s, roll_z=-0.05 * c)
        key_char_bone(f, "SkullPendant", pitch_x=0.06 * c, yaw_y=0.04 * s)
        key_char_bone(f, "Tail", yaw_y=0.14 * s)
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
        key_char_bone(f, "Jaw", pitch_x=-0.06 * s2)
        key_char_bone(f, "Leg.L", pitch_x=0.38 * s)
        key_char_bone(f, "Leg.R", pitch_x=-0.38 * s)
        key_char_bone(f, "FootHoof.L", pitch_x=-0.18 * c)
        key_char_bone(f, "FootHoof.R", pitch_x=0.18 * c)
        key_char_bone(f, "Arm.L", pitch_x=-0.28 * s, roll_z=0.06 * c)
        key_char_bone(f, "Arm.R", pitch_x=0.28 * s, roll_z=-0.06 * c)
        key_char_bone(f, "Ear.L", pitch_x=0.05 * s2, roll_z=0.12 * c)
        key_char_bone(f, "Ear.R", pitch_x=0.05 * s2, roll_z=-0.12 * c)
        key_char_bone(f, "SkullPendant", pitch_x=0.14 * s2, yaw_y=0.12 * s)
        key_char_bone(f, "Tail", yaw_y=0.22 * c)


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
        key_char_bone(f, "Ear.L", roll_z=0.25 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.25 * s)
        key_char_bone(f, "Arm.L", roll_z=-0.25 * s)
        key_char_bone(f, "Arm.R", roll_z=0.25 * s)
        key_char_bone(f, "SkullPendant", pitch_x=-0.22 * c)
        key_char_bone(f, "Jaw", pitch_x=-0.14 * max(0.0, s))
        key_char_bone(f, "Tail", pitch_x=-0.20 * s)


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
        key_char_bone(f, "SkullPendant", pitch_x=0.08 * s, yaw_y=0.08 * lift)
        key_char_bone(f, "Tail", yaw_y=0.18 * w * lift)


def build_curious_tilt(act):
    frames = [1, 15, 30, 45, 60]
    hide_fart_clouds_for_standard_clip(frames)
    for f, ph in [(1, 0.0), (15, 0.5 * math.pi), (30, math.pi), (45, 1.5 * math.pi), (60, 2.0 * math.pi)]:
        s = math.sin(ph)
        c = math.cos(ph)
        talk = abs(math.sin(2.0 * ph))
        key_char_bone(f, "Head", pitch_x=0.06 * c, yaw_y=0.18 * s, roll_z=-0.16 * s)
        key_char_bone(f, "Jaw", pitch_x=-0.15 * talk)
        key_char_bone(f, "Eyelid.L", pitch_x=0.12 * max(0.0, s))
        key_char_bone(f, "Eyelid.R", pitch_x=0.12 * max(0.0, -s))
        key_char_bone(f, "Ear.L", roll_z=-0.16 * s)
        key_char_bone(f, "Ear.R", roll_z=-0.16 * s)
        key_char_bone(f, "Chest", yaw_y=0.06 * s, roll_z=-0.04 * s)


fart_act, fart_track = bake_action_to_nla("Bubba_Fart_Blast", 36, build_bubba_fart_blast)
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
# and set sub.levels = 1 before .obj export so the .obj stays under 5MB.
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
    export_uv=False,
    export_normals=False,
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


add_area_light("Key_Softbox", (-2.4, -3.6, 3.2), (0.0, 0.0, 1.45), energy=210.0, size=3.0, color_rgb=(1.0, 0.99, 0.98))
add_area_light("Fill_Softbox", (2.6, -3.2, 2.4), (0.0, 0.0, 1.35), energy=145.0, size=3.4, color_rgb=(0.97, 0.98, 1.0))
add_area_light("Top_Softbox", (0.0, -0.8, 4.2), (0.0, 0.0, 1.65), energy=150.0, size=3.2, color_rgb=(1.0, 1.0, 1.0))
add_area_light("Rim_Backlight", (0.0, 3.0, 3.0), (0.0, 0.0, 1.50), energy=135.0, size=2.6, color_rgb=(0.98, 0.98, 1.0))

world = bpy.data.worlds.new("BubbaStudioWorld")
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


def aim_camera(loc, target=(0.0, 0.0, 1.34), lens=60.0):
    cam_data.lens = lens
    cam_obj.location = Vector(loc)
    direction = Vector(target) - Vector(loc)
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()


# ==============================================================================
# 9. RENDER STUDIO FRONT (1080x1350) & TURNAROUND SHEET (1920x600)
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
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'

# 9.1 Studio Front Render (1080x1350) in Rest Pose
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = True
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
reset_pose(hide_fart_cloud=True)
bpy.ops.object.mode_set(mode='OBJECT')

scene.cycles.samples = 48
scene.render.resolution_x = 1080
scene.render.resolution_y = 1350
aim_camera((0.0, -5.65, 1.44), target=(0.0, 0.0, 1.32), lens=54.0)
scene.render.filepath = RENDER_FRONT_PATH
bpy.ops.render.render(write_still=True)

# 9.2 Render 3/4 and Side Views (480x600) for 4-Panel Turnaround Preview
scene.cycles.samples = 36
scene.render.resolution_x = 480
scene.render.resolution_y = 600

c_3q_path = os.path.join(RENDER_SHEET_DIR, "cycles_3q.png")
aim_camera((2.85, -4.75, 1.48), target=(0.0, 0.0, 1.32), lens=54.0)
scene.render.filepath = c_3q_path
bpy.ops.render.render(write_still=True)

c_side_path = os.path.join(RENDER_SHEET_DIR, "cycles_side.png")
aim_camera((5.45, -0.35, 1.44), target=(0.0, -0.05, 1.32), lens=54.0)
scene.render.filepath = c_side_path
bpy.ops.render.render(write_still=True)

# Composite 1920x600 4-Panel Turnaround Preview via ffmpeg
subprocess.run([
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "color=c=#f4f4f6:s=480x600",
    "-i", REF_IMG_PATH,
    "-i", RENDER_FRONT_PATH,
    "-i", c_3q_path,
    "-i", c_side_path,
    "-filter_complex",
    "[1:v]scale=430:540:force_original_aspect_ratio=decrease:flags=lanczos[ref_s];"
    "[0:v][ref_s]overlay=(W-w)/2:(H-h)/2[p0];"
    "[2:v]scale=480:600:flags=lanczos[p1];"
    "[p0][p1][3:v][4:v]hstack=inputs=4[v]",
    "-map", "[v]",
    "-frames:v", "1",
    RENDER_PREVIEW_PATH
], check=True)


# ==============================================================================
# 10. RENDER THE 36-FRAME `Bubba_Fart_Blast` CYCLES ANIMATION SEQUENCE!
# ==============================================================================
for trk in arm_obj.animation_data.nla_tracks:
    trk.mute = (trk.name != "Bubba_Fart_Blast")

aim_camera((4.95, -3.65, 1.52), target=(-0.05, 0.36, 1.20), lens=53.0)

scene.frame_start = 1
scene.frame_end = 36
scene.frame_set(14)  # Save .blend thumbnail right at the peak of the green fart blast!
bpy.ops.wm.save_as_mainfile(filepath=BLEND_PATH, compress=True)

scene.cycles.samples = 24
scene.render.resolution_x = 640
scene.render.resolution_y = 640
scene.render.fps = 24

force_all = os.environ.get("FORCE_ALL_FRAMES", "0") == "1"
key_storyboard_frames = {1, 8, 14, 19, 28, 36}
for f in range(1, 37):
    fpath = os.path.join(FART_FRAMES_DIR, f"frame_{f:03d}.png")
    if not force_all and os.path.exists(fpath) and f not in key_storyboard_frames:
        continue
    scene.frame_set(f)
    scene.render.filepath = fpath
    bpy.ops.render.render(write_still=True)

print("SUCCESS: Built Bubba Bubbaphant 3D model, renders, and 36-frame Bubba_Fart_Blast sequence!")
print(f"  BLEND:   {BLEND_PATH} ({os.path.getsize(BLEND_PATH)} bytes)")
print(f"  GLB:     {GLB_PATH} ({os.path.getsize(GLB_PATH)} bytes)")
print(f"  OBJ:     {OBJ_PATH} ({os.path.getsize(OBJ_PATH)} bytes)")
print(f"  FRONT:   {RENDER_FRONT_PATH} ({os.path.getsize(RENDER_FRONT_PATH)} bytes)")
print(f"  PREVIEW: {RENDER_PREVIEW_PATH} ({os.path.getsize(RENDER_PREVIEW_PATH)} bytes)")
