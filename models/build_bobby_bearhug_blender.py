#!/usr/bin/env python3
"""
critter-3d (CatNap-Final-v11) Multi-Character Builder for Smiling Critters & Baba Chops.
Strictly implements the exact multi-stage architecture from https://github.com/kunruiw1991/critter-3d:
  1. Continuous Catmull-Rom plush lofting (`plush_loft`) for head, torso, arms, legs.
  2. Sculpted ear shells (`ear_shell` / floppy ears / crest) voxel-unioned into head (`REMESH` VOXEL + `SMOOTH`) with BVHTree material restoration.
  3. Boolean-carved hollow grin (`BOOLEAN` `DIFFERENCE` `EXACT` + `REMESH` VOXEL + `Mouth cloth rollover` vertex-group `SMOOTH`), recessed black mouth bowl, and Boolean-perforated circular speaker grille (`Mouth • perforated speaker grille` + `Mouth • speaker rim`).
  4. Skin-fitted solid dark domed button eyes (`fitted_eye`) ray-cast onto `fronty(x, z)` (zero cartoon white anime eye-shine dots).
  5. Voxel-unioned continuous plush body (`REMESH` VOXEL + `Shoulder transition` & `Tail root transition` Gaussian smooth) with BVHTree cuff & belly-patch material restoration.
  6. Surface-fitted zipper (`Zipper • surface fitted dark tape` + 27 beveled teeth) and character-specific beveled 3D pendant (`Pendant • ...` + bail + seat).
  7. Object-coordinate isotropic textile micro-bump (`Scale=235, Strength=0.32, Distance=0.0035`) and ~700-950 surface-projected 7-point 3D cotton stitch arcs (`boundaries()` + `seam()`).
"""

import bpy
import bmesh
import math
import os
import sys
import json
import shutil
import subprocess
from math import sin, cos, pi, sqrt
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from mathutils.geometry import tessellate_polygon

# Parse CLI args after `--`
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CHAR_SLUG = argv[0] if len(argv) >= 1 else "bobby_bearhug"
MODE = argv[1] if len(argv) >= 2 else "full"  # "preview" or "full"

OUT_MODELS_DIR = "/tmp/smiling-critters-assets/models"
OUT_ANIMS_DIR = "/tmp/smiling-critters-assets/animations"
IMAGES_DIR = "/tmp/smiling-critters-assets/images"
WORK_DIR = f"/tmp/work_v11_{CHAR_SLUG}"
os.makedirs(OUT_MODELS_DIR, exist_ok=True)
os.makedirs(OUT_ANIMS_DIR, exist_ok=True)
os.makedirs(WORK_DIR, exist_ok=True)

REF_MAP = {
    "catnap": os.path.join(IMAGES_DIR, "319_OfficialToyCatNapRender.png"),
    "bobby_bearhug": os.path.join(IMAGES_DIR, "320_OfficialBobbyRender.png"),
    "bubba_bubbaphant": os.path.join(IMAGES_DIR, "321_OfficialBubbaRender.png"),
    "craftycorn": os.path.join(IMAGES_DIR, "322_OfficialCraftyCornRender.png"),
    "dogday": os.path.join(IMAGES_DIR, "323_OfficialToyDogDayRender.png"),
    "hoppy_hopscotch": os.path.join(IMAGES_DIR, "324_OfficialHoppyRender.png"),
    "kickin_chicken": os.path.join(IMAGES_DIR, "325_OfficialKickinChickenRender.png"),
    "picky_piggy": os.path.join(IMAGES_DIR, "326_OfficialPickyPiggyRender.png"),
    "baba_chops": "/tmp/baba_toy_ref.png",
}

CHAR_SPECS = {
    "catnap": {
        "title": "CatNap",
        "main_color": (.235, .045, .46),
        "cuff_color": (.115, .023, .23),
        "ear_inner_color": (.038, .006, .09),
        "thread_color": (.52, .48, .57),
        "groove_color": (.058, .021, .095),
        "mouth_thread_color": (.17, .15, .20),
        "pendant_color": (.93, .58, .07),
    },
    "dogday": {
        "title": "DogDay",
        "main_color": (.52, .135, .012),      # Saturated golden-orange plush (calibrated for 700W/500W/800W AgX)
        "cuff_color": (.20, .024, .005),      # Deep rust-brown ears, cuffs, left eye patch
        "belly_color": (.72, .46, .012),      # Rich golden-yellow muzzle band & oval belly patch
        "ear_inner_color": (.14, .016, .003),
        "thread_color": (.74, .60, .46),      # Warm cream-tan stitch thread
        "groove_color": (.16, .03, .005),
        "mouth_thread_color": (.20, .16, .12),
        "pendant_color": (.85, .55, .02),     # Gold sun center
        "pendant_alt_color": (.65, .16, .01), # Orange sun rays
    },
    "bobby_bearhug": {
        "title": "Bobby BearHug",
        "main_color": (.40, .012, .016),      # Rich crimson-red plush
        "cuff_color": (.62, .16, .21),        # Warm rose-pink cuffs, inner ears, muzzle & belly
        "belly_color": (.62, .16, .21),
        "ear_inner_color": (.52, .12, .16),
        "thread_color": (.86, .62, .66),      # Soft pink-white cotton thread
        "groove_color": (.18, .008, .012),
        "mouth_thread_color": (.20, .12, .14),
        "pendant_color": (.32, .008, .015),   # Deep ruby-red heart pendant
    },
    "bubba_bubbaphant": {
        "title": "Bubba Bubbaphant",
        "main_color": (.075, .34, .60),       # Rich cyan-cerulean plush
        "cuff_color": (.015, .075, .28),      # Deep royal-navy inner ears, cuffs, trunk tip, tail tuft
        "ear_inner_color": (.012, .060, .24),
        "thread_color": (.55, .76, .90),      # Sky-blue cotton thread
        "groove_color": (.010, .06, .18),
        "mouth_thread_color": (.12, .16, .20),
        "pendant_color": (.78, .55, .015),    # Golden-yellow lightbulb
        "pendant_alt_color": (.018, .09, .32),# Royal-blue screw base
    },
    "craftycorn": {
        "title": "CraftyCorn",
        "main_color": (.74, .76, .79),        # Crisp porcelain cream-white plush
        "cuff_color": (.022, .42, .48),       # Vibrant turquoise-aqua hooves, mane & tail
        "ear_inner_color": (.010, .18, .22),  # Deep teal inner equine ears
        "thread_color": (.54, .58, .62),      # Subtle silver-grey cotton stitch thread
        "groove_color": (.26, .29, .32),
        "mouth_thread_color": (.18, .20, .22),
        "pendant_color": (.82, .58, .015),    # Rich yellow flower center
    },
    "hoppy_hopscotch": {
        "title": "Hoppy Hopscotch",
        "main_color": (.11, .46, .022),       # Vivid lime-green plush
        "cuff_color": (.018, .18, .012),      # Rich forest-green cuffs, inner ears & ear tips
        "ear_inner_color": (.014, .14, .008),
        "thread_color": (.58, .82, .48),      # Pale mint-green cotton thread
        "groove_color": (.012, .10, .006),
        "mouth_thread_color": (.14, .18, .12),
        "pendant_color": (.82, .58, .015),    # Golden-yellow lightning bolt
    },
    "kickin_chicken": {
        "title": "KickinChicken",
        "main_color": (.62, .38, .008),       # Vivid sunflower golden-yellow plush
        "cuff_color": (.56, .11, .008),       # Rich tangerine-orange cuffs & beak
        "ear_inner_color": (.48, .28, .006),
        "thread_color": (.85, .72, .32),      # Warm yellow cotton thread
        "groove_color": (.26, .14, .005),
        "mouth_thread_color": (.20, .18, .12),
        "pendant_color": (.42, .012, .012),   # Deep crimson-red star pendant
    },
    "picky_piggy": {
        "title": "PickyPiggy",
        "main_color": (.54, .15, .28),        # Rich rose-pink plush
        "cuff_color": (.28, .022, .12),       # Deep magenta-pink cuffs & inner ears
        "ear_inner_color": (.22, .015, .09),
        "thread_color": (.86, .58, .70),      # Soft pink cotton thread
        "groove_color": (.18, .012, .08),
        "mouth_thread_color": (.20, .12, .16),
        "pendant_color": (.42, .010, .015),   # Deep glossy crimson apple pendant
    },
    "baba_chops": {
        "title": "Baba Chops",
        "main_color": (.022, .022, .025),     # Deep charcoal-black body & wool hood
        "cuff_color": (.64, .65, .67),        # Crisp off-white lamb face, ears, mittens, hooves & buck teeth
        "ear_inner_color": (.12, .12, .14),   # Recessed dark grey inner sheep ear
        "thread_color": (.44, .45, .48),      # Light grey cotton stitch thread
        "groove_color": (.008, .008, .010),
        "mouth_thread_color": (.18, .18, .20),
        "pendant_color": (.10, .075, .058),   # Weathered dark bronze/gunmetal skull pendant
    },
}

spec = CHAR_SPECS[CHAR_SLUG]

# ==============================================================================
# Helper Functions (Exact critter-3d v07..v11 implementation)
# ==============================================================================
def build_character_scene():
    if CHAR_SLUG == "catnap":
        bpy.ops.wm.open_mainfile(filepath="/tmp/critter-3d/unzipped/CatNap-Final-v11.blend")
        col = bpy.data.collections['CATNAP • shape review v11']
        studio = bpy.data.collections['STUDIO • cameras and lighting']
        root = bpy.data.objects['CATNAP_ROOT • unrigged shape draft']
        if 'Stitch-detail' not in bpy.data.objects:
            cd = bpy.data.cameras.new('Stitch-detail')
            cd.type = 'ORTHO'
            cd.ortho_scale = 2.65
            co = bpy.data.objects.new('Stitch-detail', cd)
            co.location = (0, -9, 1.55)
            co.rotation_euler = (Vector((0, -.25, 1.55)) - co.location).to_track_quat('-Z', 'Y').to_euler()
            studio.objects.link(co)
        return col, studio, root, {"total_stitches": 761}

    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)

    col = bpy.data.collections.new(f'{CHAR_SLUG.upper()} • shape review v11')
    bpy.context.scene.collection.children.link(col)
    studio = bpy.data.collections.new('STUDIO • cameras and lighting')
    bpy.context.scene.collection.children.link(studio)

    def move(obj, target_col=col):
        for c in list(obj.users_collection):
            c.objects.unlink(obj)
        target_col.objects.link(obj)
        return obj

    def mat(name, color, rough=.84, metal=0.0, bump=False, sheen=.28):
        m = bpy.data.materials.new(name)
        m.diffuse_color = (*color, 1)
        m.use_nodes = True
        nt = m.node_tree
        n = nt.nodes
        p = n.get('Principled BSDF')
        p.inputs['Base Color'].default_value = (*color, 1)
        p.inputs['Roughness'].default_value = rough
        p.inputs['Metallic'].default_value = metal
        if bump:
            p.inputs['Sheen Weight'].default_value = sheen
            tex = n.new('ShaderNodeTexNoise')
            tex.inputs['Scale'].default_value = 235
            tex.inputs['Detail'].default_value = 2
            coord = n.new('ShaderNodeTexCoord')
            nt.links.new(coord.outputs['Object'], tex.inputs['Vector'])
            b = n.new('ShaderNodeBump')
            b.inputs['Strength'].default_value = .32
            b.inputs['Distance'].default_value = .0035
            nt.links.new(tex.outputs['Fac'], b.inputs['Height'])
            nt.links.new(b.outputs['Normal'], p.inputs['Normal'])
        return m

    main_mat = mat(f'01 • {spec["title"]} primary plush', spec['main_color'], .84, bump=True)
    cuff_mat = mat(f'02 • {spec["title"]} secondary plush', spec['cuff_color'], .84, bump=True)
    belly_mat = mat(f'02b • {spec["title"]} tertiary plush', spec.get('belly_color', spec['cuff_color']), .84, bump=True)
    ear_dark = mat(f'11 • {spec["title"]} recessed inner ear', spec['ear_inner_color'], .88, bump=True)
    black = mat('03 • dark eye buttons', (.006, .004, .011), .38)
    inside = mat('04 • mouth cavity • matte', (.003, .002, .004), .85)
    inside.node_tree.nodes.get('Principled BSDF').inputs['Specular IOR Level'].default_value = .18
    pendant_mat = mat('06 • character pendant', spec['pendant_color'], .27, .65 if CHAR_SLUG in ('catnap', 'dogday', 'bubba_bubbaphant', 'hoppy_hopscotch', 'baba_chops') else .22)
    pendant_alt = mat('06b • pendant secondary', spec.get('pendant_alt_color', (.95, .75, .05)), .30, .35)
    zipmat = mat('07 • zipper fabric', (.035, .025, .045), .82)
    teeth = mat('08 • zipper teeth', (.16, .14, .18), .48, .30)
    thread = mat('Stitch • primary cotton thread', spec['thread_color'], .87, sheen=.30)
    groove = mat('Stitch • recessed seam join', spec['groove_color'], .87, sheen=.30)
    mouththread = mat('Stitch • mouth muted thread', spec['mouth_thread_color'], .87, sheen=.30)
    nose_black = mat('Nose • soft matte black', (.006, .004, .011), .52)
    speaker = mat('12 • recessed speaker', (.012, .010, .017), .70)

    def finish(o, m):
        if m:
            o.data.materials.append(m)
        if o.type == 'MESH':
            for p in o.data.polygons:
                p.use_smooth = True
        move(o)
        return o

    def ell(name, loc, scale, m, seg=48, rings=32):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, location=loc)
        o = bpy.context.object
        o.name = name
        o.scale = scale
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        return finish(o, m)

    def bezier_curve(name, pts, r, m, radii=None, cyclic=False):
        cu = bpy.data.curves.new(name, 'CURVE')
        cu.dimensions = '3D'
        cu.resolution_u = 16
        cu.bevel_depth = r
        cu.bevel_resolution = 5
        cu.use_fill_caps = True
        s = cu.splines.new('BEZIER')
        s.bezier_points.add(len(pts) - 1)
        for i, (p, co) in enumerate(zip(s.bezier_points, pts)):
            p.co = co
            p.handle_left_type = 'AUTO'
            p.handle_right_type = 'AUTO'
            p.radius = (radii[i] if radii else 1)
        s.use_cyclic_u = cyclic
        o = bpy.data.objects.new(name, cu)
        col.objects.link(o)
        cu.materials.append(m)
        return o

    def polyextrude(name, xz, yfront, yback, m, bevel=0):
        n = len(xz)
        v = [(x, yfront, z) for x, z in xz] + [(x, yback, z) for x, z in xz]
        faces = []
        vectors = [Vector((x, z, 0)) for x, z in xz]
        tris = tessellate_polygon([vectors])
        lookup = {tuple(v): i for i, v in enumerate(vectors)}
        for t in tris:
            ids = [p if isinstance(p, int) else lookup[tuple(p)] for p in t]
            faces.append(tuple(reversed(ids)))
            faces.append(tuple(i + n for i in ids))
        faces += [(i, (i + 1) % n, (i + 1) % n + n, i + n) for i in range(n)]
        me = bpy.data.meshes.new(name)
        me.from_pydata(v, [], faces)
        me.update()
        o = bpy.data.objects.new(name, me)
        col.objects.link(o)
        if m:
            me.materials.append(m)
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bmesh.ops.dissolve_limit(bm, angle_limit=.001, verts=list(bm.verts), edges=list(bm.edges))
        bm.to_mesh(me)
        bm.free()
        if bevel:
            bpy.ops.object.select_all(action='DESELECT')
            o.select_set(True)
            bpy.context.view_layer.objects.active = o
            b = o.modifiers.new('Rounded cast edges', 'BEVEL')
            b.width = bevel
            b.use_clamp_overlap = True
            b.segments = 4
            b.limit_method = 'ANGLE'
            b.angle_limit = .45
            bpy.ops.object.modifier_apply(modifier=b.name)
            wn = o.modifiers.new('Weighted face normals', 'WEIGHTED_NORMAL')
            wn.keep_sharp = True
            wn.weight = 50
            bpy.ops.object.modifier_apply(modifier=wn.name)
        for p in o.data.polygons:
            p.use_smooth = True
        return o

    def plush_loft(name, profile, mats, cuff=None, N=96):
        rows = []
        for i in range(len(profile) - 1):
            p0 = Vector(profile[max(0, i - 1)])
            p1 = Vector(profile[i])
            p2 = Vector(profile[i + 1])
            p3 = Vector(profile[min(len(profile) - 1, i + 2)])
            for j in range(7):
                t = j / 7
                rows.append(tuple(.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)))
        rows.append(profile[-1])
        v = []
        for z, w, d, cx, cy in rows:
            for k in range(N):
                t = k / N * 2 * pi
                v.append((cx + max(.006, w) * cos(t), cy + max(.006, d) * sin(t), z))
        faces = []
        bands = []
        for r in range(len(rows) - 1):
            for k in range(N):
                faces.append((r * N + k, r * N + (k + 1) % N, (r + 1) * N + (k + 1) % N, (r + 1) * N + k))
                bands.append(1 if cuff is not None and (rows[r][0] + rows[r + 1][0]) * .5 < cuff else 0)
        faces.extend([tuple(reversed(range(N))), tuple(range((len(rows) - 1) * N, len(rows) * N))])
        bands.extend([1 if cuff is not None else 0, 0])
        me = bpy.data.meshes.new(name)
        me.from_pydata(v, [], faces)
        me.update()
        ob = bpy.data.objects.new(name, me)
        col.objects.link(ob)
        for m in mats:
            me.materials.append(m)
        for p, idx in zip(me.polygons, bands):
            p.use_smooth = True
            p.material_index = idx
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        return ob

    def catmull(points, n=8):
        arr = []
        for i in range(len(points)):
            p0 = Vector(points[(i - 1) % len(points)])
            p1 = Vector(points[i])
            p2 = Vector(points[(i + 1) % len(points)])
            p3 = Vector(points[(i + 2) % len(points)])
            for j in range(n):
                t = j / n
                v = .5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)
                arr.append(tuple(v))
        return arr

    def cubic2(a, b, c, d, n=4):
        return [tuple((1 - t) ** 3 * a[k] + 3 * (1 - t) ** 2 * t * b[k] + 3 * (1 - t) * t * t * c[k] + t ** 3 * d[k] for k in range(2)) for t in [j / n for j in range(n)]]

    # ==========================================================================
    # 1. HEAD LOFT & CHARACTER EARS / CREST
    # ==========================================================================
    profile = [
        (2.73, .015, .10), (2.755, .18, .20), (2.80, .37, .31), (2.90, .55, .40),
        (2.98, .65, .46), (3.13, .82, .53), (3.32, .97, .59), (3.52, 1.065, .65),
        (3.71, 1.108, .67), (3.90, 1.095, .65), (4.02, 1.045, .62), (4.12, .89, .56),
        (4.24, .75, .53), (4.37, .65, .42), (4.48, .50, .30), (4.56, .33, .19),
        (4.59, .20, .115), (4.605, .02, .025)
    ]
    def prof(z):
        for i in range(len(profile) - 1):
            a, b = profile[i], profile[i + 1]
            if z <= b[0]:
                t = max(0, min(1, (z - a[0]) / (b[0] - a[0])))
                return a[1] * (1 - t) + b[1] * t, a[2] * (1 - t) + b[2] * t
        return profile[-1][1:]

    ringdata = []
    for i in range(len(profile) - 1):
        p0 = Vector(profile[max(0, i - 1)])
        p1 = Vector(profile[i])
        p2 = Vector(profile[i + 1])
        p3 = Vector(profile[min(len(profile) - 1, i + 2)])
        for j in range(8):
            t = j / 8
            p = .5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t * t * t)
            ringdata.append(tuple(p))
    ringdata.append(profile[-1])
    verts = []
    n = 128
    for z, w, d in ringdata:
        for j in range(n):
            a = j / n * 2 * pi
            verts.append((max(.007, w) * cos(a), max(.015, d) * sin(a) + .035, z))

    def facial_volume(x, z):
        return (
            .055 * math.exp(-(((abs(x) - .40) / .38) ** 2 + ((z - 3.965) / .17) ** 2))
            + .040 * math.exp(-((x / .70) ** 2 + ((z - 2.91) / .16) ** 2))
            + .092 * math.exp(-((x / .31) ** 2 + ((z - 3.99) / .21) ** 2))
            + .045 * math.exp(-(((abs(x) - .79) / .24) ** 2 + ((z - 3.98) / .26) ** 2))
        )

    verts = [(x, y - facial_volume(x, z) * max(0, min(1, (.035 - y) / .18)), z) for x, y, z in verts]
    faces = []
    for i in range(len(ringdata) - 1):
        for j in range(n):
            faces.append((i * n + j, i * n + (j + 1) % n, (i + 1) * n + (j + 1) % n, (i + 1) * n + j))
    faces.extend([tuple(reversed(range(n))), tuple(range((len(ringdata) - 1) * n, len(ringdata) * n))])
    me = bpy.data.meshes.new(f'{spec["title"]} reference silhouette loft')
    me.from_pydata(verts, [], faces)
    me.update()
    head_base_mat = cuff_mat if CHAR_SLUG == "baba_chops" else main_mat
    head = bpy.data.objects.new('Head • reference traced crown and fused ear roots', me)
    col.objects.link(head)
    me.materials.append(head_base_mat)
    for p in me.polygons:
        p.use_smooth = True
    bpy.ops.object.select_all(action='DESELECT')
    head.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

    def ear_shell(name, outline, cx, cz, outer_mat, inner_mat=ear_dark, y_shift=0.0):
        points = catmull(outline, 3)
        N = len(points)
        verts = []
        rings = [(.012, .095 + y_shift), (.30, .08 + y_shift), (.58, .025 + y_shift), (.70, -.045 + y_shift), (.75, -.115 + y_shift), (.86, -.145 + y_shift), (1.0, -.065 + y_shift)]
        for f, y in rings:
            for x, z in points:
                verts.append((cx + (x - cx) * f, y, cz + (z - cz) * f))
        back_start = len(verts)
        for f, y in [(1, .035 + y_shift), (.72, .155 + y_shift), (.32, .215 + y_shift), (.012, .23 + y_shift)]:
            for x, z in points:
                verts.append((cx + (x - cx) * f, y, cz + (z - cz) * f))
        faces = []
        mi = []
        for r in range(len(rings) - 1):
            for j in range(N):
                faces.append((r * N + j, r * N + (j + 1) % N, (r + 1) * N + (j + 1) % N, (r + 1) * N + j))
                mi.append(1 if r < 3 else 0)
        faces.append(tuple(reversed(range(N))))
        mi.append(1)
        off = (len(rings) - 1) * N
        for j in range(N):
            faces.append((off + j, off + (j + 1) % N, back_start + (j + 1) % N, back_start + j))
            mi.append(0)
        for r in range(3):
            for j in range(N):
                faces.append((back_start + r * N + j, back_start + r * N + (j + 1) % N, back_start + (r + 1) * N + (j + 1) % N, back_start + (r + 1) * N + j))
                mi.append(0)
        faces.append(tuple(range(back_start + 3 * N, back_start + 4 * N)))
        mi.append(0)
        me = bpy.data.meshes.new(name)
        me.from_pydata(verts, [], faces)
        me.update()
        ob = bpy.data.objects.new(name, me)
        col.objects.link(ob)
        me.materials.append(outer_mat)
        me.materials.append(inner_mat)
        for p, idx in zip(me.polygons, mi):
            p.use_smooth = True
            p.material_index = idx
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        su = ob.modifiers.new('Soft ear subsurf', 'SUBSURF')
        su.levels = 2
        bpy.ops.object.modifier_apply(modifier=su.name)
        return ob

    ears = []
    if CHAR_SLUG == "bobby_bearhug":
        # Round C-shaped teddy bear ears
        ear_outline = []
        for k in range(16):
            ang = 2 * pi * k / 16
            ear_outline.append((.64 + .31 * cos(ang), 4.54 + .30 * sin(ang)))
        for sg, label in [(-1, 'L'), (1, 'R')]:
            pts = [(sg * x, z) for x, z in ear_outline]
            ears.append(ear_shell('Ear.' + label, pts, sg * .64, 4.54, main_mat, cuff_mat))
    elif CHAR_SLUG == "bubba_bubbaphant":
        # Large C-shaped curved elephant ears
        ear_outline = [
            (.48, 4.46), (.64, 4.86), (.98, 4.94), (1.32, 4.70),
            (1.42, 4.24), (1.34, 3.70), (1.04, 3.42), (.68, 3.52), (.52, 3.92)
        ]
        for sg, label in [(-1, 'L'), (1, 'R')]:
            pts = [(sg * x, z) for x, z in ear_outline]
            ears.append(ear_shell('Ear.' + label, pts, sg * .95, 4.18, main_mat, cuff_mat, y_shift=0.06))
    elif CHAR_SLUG == "craftycorn":
        # Upright pointed equine unicorn ears
        ear_outline = []
        for segment in [
            ((.34, 4.44), (.42, 4.72), (.64, 4.98), (.80, 5.04)),
            ((.80, 5.04), (.84, 5.05), (.88, 5.03), (.90, 4.98)),
            ((.90, 4.98), (.98, 4.78), (.98, 4.38), (.86, 4.12)),
            ((.86, 4.12), (.64, 4.10), (.44, 4.24), (.34, 4.44)),
        ]:
            ear_outline += cubic2(*segment)
        for sg, label in [(-1, 'L'), (1, 'R')]:
            pts = [(sg * x, z) for x, z in ear_outline]
            ears.append(ear_shell('Ear.' + label, pts, sg * .68, 4.52, main_mat, ear_dark))
    elif CHAR_SLUG == "hoppy_hopscotch":
        # Long tall upright rabbit ears
        ear_outline = [
            (.16, 4.48), (.14, 4.95), (.20, 5.48), (.34, 5.82),
            (.50, 5.86), (.64, 5.62), (.66, 5.12), (.58, 4.65), (.44, 4.40)
        ]
        for sg, label in [(-1, 'L'), (1, 'R')]:
            pts = [(sg * x, z) for x, z in ear_outline]
            ears.append(ear_shell('Ear.' + label, pts, sg * .42, 5.10, main_mat, cuff_mat))
    elif CHAR_SLUG == "picky_piggy":
        # Wide outward-swept pointed floppy pig ears
        ear_outline = [
            (.34, 4.46), (.58, 4.72), (.96, 4.86), (1.26, 4.80),
            (1.22, 4.52), (1.04, 4.22), (.76, 4.10), (.48, 4.20)
        ]
        for sg, label in [(-1, 'L'), (1, 'R')]:
            pts = [(sg * x, z) for x, z in ear_outline]
            ears.append(ear_shell('Ear.' + label, pts, sg * .82, 4.48, main_mat, cuff_mat))
    elif CHAR_SLUG == "baba_chops":
        # Horizontal outward-pointing off-white sheep ears
        ear_outline = [
            (.58, 4.46), (.84, 4.64), (1.18, 4.66), (1.36, 4.50),
            (1.28, 4.26), (1.02, 4.14), (.74, 4.18)
        ]
        for sg, label in [(-1, 'L'), (1, 'R')]:
            pts = [(sg * x, z) for x, z in ear_outline]
            ears.append(ear_shell('Ear.' + label, pts, sg * .96, 4.38, cuff_mat, ear_dark))
    elif CHAR_SLUG == "dogday":
        # Long floppy rust-brown spaniel ears arching out and down from crown (strictly monotonic z for clean loft!)
        for sg, label in [(-1, 'L'), (1, 'R')]:
            flop_prof = [
                (3.62, .03, .03, sg * 1.62, -.04),
                (3.70, .18, .09, sg * 1.55, -.03),
                (3.88, .27, .12, sg * 1.38, -.01),
                (4.10, .30, .13, sg * 1.16, .01),
                (4.30, .28, .13, sg * .92, .02),
                (4.44, .25, .13, sg * .66, .03),
                (4.52, .20, .12, sg * .44, .03),
                (4.56, .08, .08, sg * .30, .03),
            ]
            ob = plush_loft('Ear.' + label, flop_prof, [main_mat, cuff_mat])
            for f in ob.data.polygons:
                f.material_index = 1
            ears.append(ob)
    elif CHAR_SLUG == "kickin_chicken":
        # 3-lobed puffy golden-yellow chicken comb / feather crest on top of head (strictly monotonic z!)
        comb_lobes = [
            # Left sweeping feather lobe over brow
            [
                (4.16, .04, .05, -1.04, -.08),
                (4.24, .16, .15, -.96, -.07),
                (4.38, .23, .20, -.76, -.05),
                (4.50, .25, .22, -.48, -.03),
                (4.58, .22, .20, -.24, -.01),
                (4.62, .07, .09, -.08, .01),
            ],
            # Center crown feather lobe
            [
                (4.40, .05, .08, .04, .01),
                (4.54, .18, .18, .06, -.01),
                (4.78, .24, .21, .08, -.03),
                (4.98, .21, .19, .09, -.04),
                (5.06, .06, .07, .09, -.04),
            ],
            # Right crown feather lobe
            [
                (4.35, .05, .08, .28, .02),
                (4.50, .17, .17, .36, .00),
                (4.74, .23, .20, .44, -.02),
                (4.92, .19, .18, .48, -.03),
                (4.99, .05, .07, .50, -.03),
            ],
        ]
        for idx, cprof in enumerate(comb_lobes):
            ob = plush_loft(f'Crest.{idx}', cprof, [main_mat, main_mat])
            ears.append(ob)

    ear_surfaces = []
    for ob in ears:
        ear_surfaces.append((
            BVHTree.FromPolygons([v.co for v in ob.data.vertices], [list(f.vertices) for f in ob.data.polygons]),
            [f.material_index for f in ob.data.polygons]
        ))

    bpy.ops.object.select_all(action='DESELECT')
    for ob in [head] + ears:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    mo = head.modifiers.new('Continuous plush ear roots', 'REMESH')
    mo.mode = 'VOXEL'
    mo.voxel_size = .012
    mo.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=mo.name)
    mo = head.modifiers.new('Soft root transition', 'SMOOTH')
    mo.factor = .65
    mo.iterations = 7
    bpy.ops.object.modifier_apply(modifier=mo.name)

    # ==========================================================================
    # 2. BOOLEAN-CARVED HOLLOW GRIN & ROLLED CLOTH LIP
    # ==========================================================================
    pixels = [
        (525, 266), (550, 268), (585, 288), (625, 307), (665, 317), (700, 317),
        (730, 309), (750, 302), (770, 309), (800, 317), (835, 317), (875, 307),
        (915, 288), (950, 268), (975, 266), (999, 285), (1010, 320), (1012, 355),
        (1000, 395), (978, 441), (950, 477), (915, 515), (875, 542), (835, 562),
        (790, 572), (750, 575), (710, 572), (665, 562), (625, 542), (585, 515),
        (550, 477), (522, 441), (500, 395), (488, 355), (490, 320), (501, 285)
    ]
    ctrl = [((x - 750) / 258, 2.76 + (595 - y) / 258) for x, y in pixels]
    outline = catmull(ctrl)
    cutter = polyextrude('TEMP • mouth subtraction', outline, -1.1, -.005, None)
    bpy.context.view_layer.objects.active = head
    mod = head.modifiers.new('True hollow grin', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.data.objects.remove(cutter, do_unlink=True)

    mo = head.modifiers.new('Continuous rounded mouth opening', 'REMESH')
    mo.mode = 'VOXEL'
    mo.voxel_size = .009
    mo.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=mo.name)

    vg = head.vertex_groups.new(name='Mouth cloth rollover')
    for v in head.data.vertices:
        x, y, z = v.co
        if z < 4.10 and y < .08:
            vg.add([v.index], 1.0, 'REPLACE')
    mo = head.modifiers.new('Broad soft cloth transition', 'SMOOTH')
    mo.vertex_group = vg.name
    mo.factor = .72
    mo.iterations = 48
    bpy.ops.object.modifier_apply(modifier=mo.name)

    # Set up head materials:
    # slot 0: head base (main_mat, or cuff_mat for Baba Chops)
    # slot 1: inner ear / secondary head patch (ear_dark or cuff_mat)
    # slot 2: tertiary head zone (belly_mat for DogDay yellow muzzle / Bobby pink muzzle / Hoppy ear tips)
    # slot 3: inside (mouth cavity black)
    head.data.materials.clear()
    head.data.materials.append(head_base_mat)
    head.data.materials.append(cuff_mat if CHAR_SLUG in ("dogday", "bobby_bearhug", "bubba_bubbaphant", "hoppy_hopscotch", "picky_piggy") else ear_dark)
    head.data.materials.append(belly_mat if CHAR_SLUG in ("dogday", "bobby_bearhug") else cuff_mat)
    head.data.materials.append(inside)

    def in_mouth(x, z):
        inside_poly = False
        for i, (ax, az) in enumerate(outline):
            bx, bz = outline[(i + 1) % len(outline)]
            if (az > z) != (bz > z) and x < (bx - ax) * (z - az) / (bz - az) + ax:
                inside_poly = not inside_poly
        return inside_poly

    def dist_to_mouth_outline(x, z):
        return min(sqrt((x - mx) ** 2 + (z - mz) ** 2) for mx, mz in outline[::2])

    for face in head.data.polygons:
        face.use_smooth = True
        c = face.center
        face.material_index = 0
        for tree, indices in ear_surfaces:
            co, no, idx, dist = tree.find_nearest(c)
            if idx is not None and dist < .04 and indices[idx] == 1:
                face.material_index = 1
        if CHAR_SLUG == "dogday":
            # Dark rust-brown patch over DogDay's left eye (viewer's right: x > 0.0)
            if c.x > 0.0 and c.z > 3.92 and c.y < 0.12 and face.material_index == 0:
                face.material_index = 1
            # Bright yellow muzzle & mouth rollover band around the grin
            if c.y < -0.14 and (dist_to_mouth_outline(c.x, c.z) < 0.145 or (abs(c.x) < 0.42 and 3.82 < c.z < 4.08)):
                face.material_index = 2
        elif CHAR_SLUG == "bobby_bearhug":
            # Pastel pink upper muzzle band beneath eyes and around nose
            if c.y < -0.32 and ((c.x / 0.46) ** 2 + ((c.z - 3.99) / 0.13) ** 2 < 1.0):
                face.material_index = 2
        elif CHAR_SLUG == "hoppy_hopscotch":
            # Asymmetrical forest-green patchwork ear tips
            if (c.x < -0.05 and c.z > 5.34) or (c.x > 0.05 and c.z > 5.20):
                face.material_index = 2
        if -.025 < c.y < .02 and face.normal.y < -.65 and in_mouth(c.x, c.z):
            face.material_index = 3

    head_tree = BVHTree.FromPolygons([v.co for v in head.data.vertices], [list(f.vertices) for f in head.data.polygons])
    def analyticfront(x, z):
        w, d = prof(z)
        return .035 - d * sqrt(max(.025, 1 - (x / max(.01, w)) ** 2)) - facial_volume(x, z)

    def fronty(x, z):
        loc, normal, idx, dist = head_tree.ray_cast(Vector((x, -2, z)), Vector((0, 1, 0)), 4)
        return loc.y if loc is not None else analyticfront(x, z)

    # Smooth recessed mouth bowl
    verts = []
    N = len(outline)
    fractions = [.995, .975, .93, .85, .72, .56, .38, .20, .06]
    for f in fractions:
        for x, z in outline:
            xx = x * f
            zz = 3.40 + (z - 3.40) * f
            edge = analyticfront(x, z)
            blend = max(0, min(1, (f - .60) / .40))
            blend = blend * blend * (3 - 2 * blend)
            yy = (-.012 - .26 * f * f) * (1 - blend) + (edge * (f * f) + (-.012) * (1 - f * f) + .065 * f ** 6) * blend
            verts.append((xx, yy, zz))
    faces = []
    for r in range(len(fractions) - 1):
        for i in range(N):
            faces.append((r * N + i, r * N + (i + 1) % N, (r + 1) * N + (i + 1) % N, (r + 1) * N + i))
    verts.append((0, -.012, 3.40))
    ci = len(verts) - 1
    for i in range(N):
        faces.append(((len(fractions) - 1) * N + i, (len(fractions) - 1) * N + (i + 1) % N, ci))
    me = bpy.data.meshes.new('Continuous curved mouth bowl')
    me.from_pydata(verts, [], faces)
    me.update()
    lining = bpy.data.objects.new('Mouth • smoothly recessed lining', me)
    col.objects.link(lining)
    me.materials.append(inside)
    for p in me.polygons:
        p.use_smooth = True
    sub = lining.modifiers.new('Smooth cavity surface', 'SUBSURF')
    sub.levels = 1
    bpy.context.view_layer.objects.active = lining
    bpy.ops.object.modifier_apply(modifier=sub.name)

    # ==========================================================================
    # 3. SKIN-FITTED DOMED BUTTON EYES & CHARACTER NOSE / SNOUT / TRUNK / BEAK / MANE
    # ==========================================================================
    def fitted_eye(sg, label):
        cx = sg * .338
        cz = 4.205
        N = 96
        vs = []
        rs = [.015, .15, .30, .45, .60, .72, .82, .90, .96, 1.0]
        for r in rs:
            for j in range(N):
                a = j / N * 2 * pi
                x = cx + .225 * r * cos(a)
                z = cz + .222 * r * sin(a)
                base = fronty(cx, cz)
                dx = (fronty(cx + .01, cz) - fronty(cx - .01, cz)) / .02
                dz = (fronty(cx, cz + .01) - fronty(cx, cz - .01)) / .02
                tangent = base + dx * (x - cx) + dz * (z - cz)
                blend = max(0, min(1, (r - .80) / .20))
                blend = blend * blend * (3 - 2 * blend)
                y = tangent * (1 - blend) + fronty(x, z) * blend - .003 - .155 * sqrt(max(0, 1 - r * r))
                vs.append((x, y, z))
        fs = []
        for k in range(len(rs) - 1):
            for j in range(N):
                fs.append((k * N + j, k * N + (j + 1) % N, (k + 1) * N + (j + 1) % N, (k + 1) * N + j))
        fs.append(tuple(reversed(range(N))))
        off = len(vs)
        for j in range(N):
            x, y, z = vs[(len(rs) - 1) * N + j]
            vs.append((x, y + .025, z))
        for j in range(N):
            fs.append(((len(rs) - 1) * N + j, (len(rs) - 1) * N + (j + 1) % N, off + (j + 1) % N, off + j))
        fs.append(tuple(range(off, off + N)))
        me = bpy.data.meshes.new('Fitted eye dome')
        me.from_pydata(vs, [], fs)
        me.update()
        ob = bpy.data.objects.new('Eye.' + label + ' • skin-fitted dome', me)
        col.objects.link(ob)
        me.materials.append(black)
        for f in me.polygons:
            f.use_smooth = True
        bpy.ops.object.select_all(action='DESELECT')
        ob.select_set(True)
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')

    for sg, label in [(-1, 'L'), (1, 'R')]:
        fitted_eye(sg, label)

    def build_seated_nose(pts_ctrl, nose_mat, z_center=3.989, depth=.045):
        nose_outline = catmull(pts_ctrl, 8)
        vs = []
        N = len(nose_outline)
        rs = [.015, .20, .40, .60, .78, .90, .97, 1.0]
        for r in rs:
            for x, z in nose_outline:
                xx = x * r
                zz = z_center + (z - z_center) * r
                base = analyticfront(0, z_center) + .30 * (zz - z_center)
                yy = base * (1 - r ** 6) + analyticfront(xx, zz) * r ** 6 - .003 - depth * sqrt(max(0, 1 - r * r))
                vs.append((xx, yy, zz))
        fs = [tuple(reversed(range(N)))]
        for k in range(len(rs) - 1):
            for j in range(N):
                fs.append((k * N + j, k * N + (j + 1) % N, (k + 1) * N + (j + 1) % N, (k + 1) * N + j))
        off = len(vs)
        for x, y, z in vs[(len(rs) - 1) * N:]:
            vs.append((x, y + .045, z))
        for j in range(N):
            fs.append(((len(rs) - 1) * N + j, (len(rs) - 1) * N + (j + 1) % N, off + (j + 1) % N, off + j))
        fs.append(tuple(range(off, off + N)))
        me = bpy.data.meshes.new('Soft nose volume')
        me.from_pydata(vs, [], fs)
        me.update()
        nose = bpy.data.objects.new('Nose • flush seated padded nose', me)
        col.objects.link(nose)
        me.materials.append(nose_mat)
        for f in me.polygons:
            f.use_smooth = True
        bpy.ops.object.select_all(action='DESELECT')
        nose.select_set(True)
        bpy.context.view_layer.objects.active = nose
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.normals_make_consistent(inside=False)
        bpy.ops.object.mode_set(mode='OBJECT')
        return nose

    if CHAR_SLUG in ("dogday", "bobby_bearhug"):
        # Broad rounded dog/bear black nose
        build_seated_nose([(-.17, 4.035), (0, 4.055), (.17, 4.035), (.12, 3.965), (0, 3.885), (-.12, 3.965)], nose_black, depth=.062)
    elif CHAR_SLUG == "hoppy_hopscotch":
        build_seated_nose([(-.13, 4.031), (0, 4.044), (.13, 4.031), (.09, 3.980), (0, 3.901), (-.09, 3.980)], nose_black, depth=.048)
    elif CHAR_SLUG == "picky_piggy":
        # Prominent oval pink pig snout with two recessed dark nostrils
        snout_mat = mat('Snout • pig snout pink', (.45, .10, .22), .82, bump=True)
        snout = build_seated_nose([
            (-.22, 4.02), (-.12, 4.10), (.12, 4.10), (.22, 4.02),
            (.20, 3.91), (.10, 3.87), (-.10, 3.87), (-.20, 3.91)
        ], snout_mat, z_center=3.99, depth=.115)
        for sg in (-1, 1):
            ell(f'Nose • nostril {sg}', (sg * .082, analyticfront(sg * .082, 3.99) - .095, 3.99), (.036, .028, .048), inside, 24, 16)
    elif CHAR_SLUG == "kickin_chicken":
        # 3D projecting curved orange upper beak over the top of the grin
        beak_outline = [(-.26, 3.96), (-.14, 4.08), (0, 4.12), (.14, 4.08), (.26, 3.96), (.16, 3.86), (0, 3.81), (-.16, 3.86)]
        build_seated_nose(beak_outline, cuff_mat, z_center=3.97, depth=.145)
    elif CHAR_SLUG == "bubba_bubbaphant":
        # Long curved plush elephant trunk arching down from between the eyes over the grin
        trunk_prof = [
            (3.26, .02, .02, 0.0, -.76),
            (3.28, .155, .145, 0.0, -.76),
            (3.42, .165, .155, 0.0, -.74),
            (3.62, .180, .170, 0.0, -.71),
            (3.84, .195, .185, 0.0, -.67),
            (4.02, .205, .195, 0.0, -.60),
            (4.14, .175, .175, 0.0, -.52),
            (4.20, .06, .08, 0.0, -.46),
        ]
        trunk = plush_loft('Nose • elephant trunk', trunk_prof, [main_mat, cuff_mat], cuff=3.34)
    elif CHAR_SLUG == "craftycorn":
        # 3-lobed aqua-turquoise forelock bang + spiraled metallic silver-white unicorn horn
        forelock_blobs = [
            (-.26, -.52, 4.48, (.22, .18, .17)),
            (0.00, -.56, 4.44, (.24, .20, .19)),
            (0.26, -.52, 4.48, (.22, .18, .17)),
            (-.14, -.46, 4.58, (.22, .19, .16)),
            (0.14, -.46, 4.58, (.22, .19, .16)),
        ]
        f_objs = [ell(f'Mane.f.{i}', (x, y, z), sc, cuff_mat, 32, 24) for i, (x, y, z, sc) in enumerate(forelock_blobs)]
        bpy.ops.object.select_all(action='DESELECT')
        for o in f_objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = f_objs[0]
        bpy.ops.object.join()
        f_objs[0].name = 'Nose • aqua forelock mane'
        rm = f_objs[0].modifiers.new('Forelock remesh', 'REMESH')
        rm.mode = 'VOXEL'
        rm.voxel_size = .014
        rm.use_smooth_shade = True
        bpy.ops.object.modifier_apply(modifier=rm.name)
        sm = f_objs[0].modifiers.new('Forelock smooth', 'SMOOTH')
        sm.factor = .6
        sm.iterations = 6
        bpy.ops.object.modifier_apply(modifier=sm.name)

        # Spiraled metallic silver-white unicorn horn
        horn_mat = mat('Horn • pearlescent silver', (.88, .86, .92), .24, .38)
        N_h = 48
        R_h = 40
        h_verts = []
        for r in range(R_h):
            u = r / (R_h - 1)
            z = 4.54 + u * .72
            y_c = -.44 - u * .10
            rad_base = .155 * (1 - u * .92)
            for j in range(N_h):
                ang = 2 * pi * j / N_h
                rib = 1.0 + .08 * sin(ang * 2 + u * 5 * 2 * pi) * (1 - u)
                rad = max(.003, rad_base * rib)
                h_verts.append((rad * cos(ang), y_c + rad * sin(ang), z))
        h_faces = []
        for r in range(R_h - 1):
            for j in range(N_h):
                h_faces.append((r * N_h + j, r * N_h + (j + 1) % N_h, (r + 1) * N_h + (j + 1) % N_h, (r + 1) * N_h + j))
        h_faces.extend([tuple(reversed(range(N_h))), tuple(range((R_h - 1) * N_h, R_h * N_h))])
        hme = bpy.data.meshes.new('Unicorn horn')
        hme.from_pydata(h_verts, [], h_faces)
        hme.update()
        horn = bpy.data.objects.new('Nose • spiraled unicorn horn', hme)
        finish(horn, horn_mat)
    elif CHAR_SLUG == "baba_chops":
        # Padded off-white sheep snout, heavy half-lidded eyelids, two big white buck teeth, and black wool hood!
        build_seated_nose([(-.15, 4.04), (0, 4.07), (.15, 4.04), (.12, 3.96), (0, 3.91), (-.12, 3.96)], cuff_mat, depth=.055)
        # Half-lidded brooding upper eyelids over the domed eyes
        for sg, label in [(-1, 'L'), (1, 'R')]:
            lid_pts = [
                (sg * .12, 4.21), (sg * .22, 4.36), (sg * .35, 4.42),
                (sg * .49, 4.36), (sg * .55, 4.22), (sg * .34, 4.23)
            ]
            if sg < 0:
                lid_pts = list(reversed(lid_pts))
            polyextrude(f'Nose • eyelid {label}', catmull(lid_pts, 4), fronty(sg * .338, 4.28) - .155, fronty(sg * .338, 4.28) - .04, cuff_mat, .012)
        # Two big rounded-rectangular off-white buck teeth hanging from top of grin
        for sg, label in [(-1, 'L'), (1, 'R')]:
            cx = sg * .115
            tooth_pts = [
                (cx - .105, 3.92), (cx + .105, 3.92),
                (cx + .098, 3.58), (cx + .05, 3.53),
                (cx - .05, 3.53), (cx - .098, 3.58)
            ]
            polyextrude(f'Nose • buck tooth {label}', catmull(tooth_pts, 4), -.60, -.46, cuff_mat, .016)
        # Sculpted charcoal-black sheep wool hood surrounding the crown, temples, cheeks & neck collar
        # (Side & lower puffs sit at y >= +0.10 behind the white smile rim so the white jaw rim is 100% unbroken!)
        wool_puffs = [
            # Forehead & crown wool bangs hanging above eyes
            (0.00, -.44, 4.58, .30), (-.28, -.42, 4.56, .29), (.28, -.42, 4.56, .29),
            (-.54, -.34, 4.50, .28), (.54, -.34, 4.50, .28),
            (0.00, -.20, 4.82, .36), (-.36, -.18, 4.78, .34), (.36, -.18, 4.78, .34),
            (-.68, -.08, 4.60, .32), (.68, -.08, 4.60, .32),
            (0.00, -.02, 5.00, .34), (-.32, -.02, 4.94, .32), (.32, -.02, 4.94, .32),
            # Side & cheek wool framing BEHIND the pale face (y = +0.10..+0.16)
            (-.96, .10, 4.20, .32), (.96, .10, 4.20, .32),
            (-1.06, .12, 3.80, .34), (1.06, .12, 3.80, .34),
            (-.96, .14, 3.40, .30), (.96, .14, 3.40, .30),
            (-.74, .14, 3.06, .27), (.74, .14, 3.06, .27),
            # Neck wool collar below/behind chin (y = +0.06..+0.10 so chin rim stays clean in front)
            (-.36, .06, 2.74, .22), (0.00, .06, 2.70, .22), (.36, .06, 2.74, .22),
            # Back of head wool
            (0.00, .28, 4.52, .44), (-.48, .24, 4.38, .40), (.48, .24, 4.38, .40),
            (0.00, .42, 3.92, .48), (-.56, .34, 3.82, .42), (.56, .34, 3.82, .42),
            (0.00, .34, 3.28, .40),
        ]
        w_objs = [ell(f'Wool.{i}', (x, y, z), (r, r * .92, r * .95), main_mat, 28, 20) for i, (x, y, z, r) in enumerate(wool_puffs)]
        bpy.ops.object.select_all(action='DESELECT')
        for o in w_objs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = w_objs[0]
        bpy.ops.object.join()
        wool_ob = w_objs[0]
        wool_ob.name = 'Wool • sculpted dark fleece hood'
        rm = wool_ob.modifiers.new('Wool remesh', 'REMESH')
        rm.mode = 'VOXEL'
        rm.voxel_size = .018
        rm.use_smooth_shade = True
        bpy.ops.object.modifier_apply(modifier=rm.name)
        sm = wool_ob.modifiers.new('Wool smooth', 'SMOOTH')
        sm.factor = .55
        sm.iterations = 5
        bpy.ops.object.modifier_apply(modifier=sm.name)

    # ==========================================================================
    # 4. RECESSED PERFORATED SPEAKER GRILLE IN SMILE CAVITY
    # ==========================================================================
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=.213, depth=.042, location=(0, -.130, 3.29), rotation=(pi / 2, 0, 0))
    plate = finish(bpy.context.object, speaker)
    plate.name = 'Mouth • perforated speaker grille'
    holes = []
    for row in range(-4, 5):
        for col_i in range(-4, 5):
            x = (col_i + .5 * (row % 2)) * .043
            z = row * .038
            if x * x + z * z < .18 ** 2:
                bpy.ops.mesh.primitive_cylinder_add(vertices=12, radius=.012, depth=.12, location=(x, -.130, 3.29 + z), rotation=(pi / 2, 0, 0))
                holes.append(bpy.context.object)
    bpy.ops.object.select_all(action='DESELECT')
    for ob in holes:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = holes[0]
    bpy.ops.object.join()
    cut = holes[0]
    bpy.context.view_layer.objects.active = plate
    mo = plate.modifiers.new('Actual speaker perforations', 'BOOLEAN')
    mo.operation = 'DIFFERENCE'
    mo.object = cut
    bpy.ops.object.modifier_apply(modifier=mo.name)
    bpy.data.objects.remove(cut, do_unlink=True)
    for face in plate.data.polygons:
        face.use_smooth = False
    bpy.ops.mesh.primitive_torus_add(major_segments=96, minor_segments=12, major_radius=.214, minor_radius=.009, location=(0, -.153, 3.29), rotation=(pi / 2, 0, 0))
    finish(bpy.context.object, speaker).name = 'Mouth • speaker rim'

    # ==========================================================================
    # 5. CONTINUOUS VOXEL-UNIONED BODY, ARMS, LEGS & CHARACTER TAIL (v09 recipe)
    # ==========================================================================
    parts = []
    body_profile = [
        (1.37, .08, .11), (1.405, .37, .25), (1.48, .51, .35), (1.68, .58, .41),
        (1.90, .60, .43), (2.10, .565, .415), (2.32, .48, .36), (2.50, .44, .31),
        (2.63, .35, .275), (2.73, .26, .24), (2.82, .16, .20), (2.85, .06, .12)
    ]
    body = plush_loft('Body • continuous plush shell', [(z, w, d, 0, 0) for z, w, d in body_profile], [main_mat, cuff_mat, belly_mat])
    parts.append(body)

    for sg, label in [(-1, 'L'), (1, 'R')]:
        legp = [
            (.275, .045, .07, sg * .44, -.07), (.29, .10, .115, sg * .44, -.07),
            (.34, .225, .22, sg * .44, -.05), (.45, .33, .28, sg * .44, -.02),
            (.65, .355, .295, sg * .445, .005), (.88, .32, .28, sg * .41, .02),
            (1.10, .285, .26, sg * .375, .025), (1.31, .25, .245, sg * .34, .025),
            (1.49, .23, .235, sg * .32, .025), (1.61, .15, .18, sg * .30, .025),
            (1.67, .035, .06, sg * .29, .025)
        ]
        ob = plush_loft('Leg.' + label + ' • softly rounded sole and smooth inner line', legp, [main_mat, cuff_mat])
        parts.append(ob)
        for f in ob.data.polygons:
            c = f.center
            if c.z < .55 + .08 * ((abs(c.x) - .44) / .35) ** 2:
                f.material_index = 1

        armp = [
            (1.375, .04, .06, sg * .97, -.065), (1.40, .12, .125, sg * .98, -.065),
            (1.47, .195, .175, sg * .99, -.065), (1.58, .225, .20, sg * .965, -.055),
            (1.74, .205, .195, sg * .87, -.035), (1.96, .18, .185, sg * .735, -.005),
            (2.18, .175, .18, sg * .60, .015), (2.39, .19, .185, sg * .46, .025),
            (2.55, .18, .185, sg * .35, .025), (2.68, .125, .14, sg * .26, .025),
            (2.75, .025, .045, sg * .20, .025)
        ]
        ob = plush_loft('Arm.' + label + ' • curved mitten and seated shoulder', armp, [main_mat, cuff_mat])
        parts.append(ob)
        for f in ob.data.polygons:
            c = f.center
            if CHAR_SLUG != "kickin_chicken" and c.z - .60 * (abs(c.x) - .90) < 1.74:
                f.material_index = 1

    # Character-Specific Tail
    tail_centers = []
    if CHAR_SLUG in ("bobby_bearhug", "hoppy_hopscotch", "baba_chops"):
        # Round puffy stub tail on lower back
        t_ob = ell('Tail • round plush puff', (0.0, .42, 1.56), (.22, .20, .22), main_mat, 32, 24)
        parts.append(t_ob)
    elif CHAR_SLUG == "dogday":
        # Wagging upward-swept orange dog tail visible on side/back
        tail_prof = [
            (1.52, .05, .05, .10, .32),
            (1.58, .14, .14, .28, .38),
            (1.72, .17, .16, .52, .42),
            (1.92, .16, .15, .68, .40),
            (2.14, .12, .12, .72, .35),
            (2.28, .03, .03, .66, .30),
        ]
        t_ob = plush_loft('Tail • wagging dog tail', tail_prof, [main_mat, cuff_mat])
        parts.append(t_ob)
        tail_centers = [Vector((cx, cy, z)) for z, _, _, cx, cy in tail_prof]
    elif CHAR_SLUG == "bubba_bubbaphant":
        # Slender curved elephant tail sweeping out to the left with royal-blue teardrop tuft (strictly monotonic z!)
        tail_prof = [
            (1.42, .06, .06, -.22, .26),
            (1.46, .090, .090, -.55, .20),
            (1.52, .085, .085, -.88, .12),
            (1.60, .080, .080, -1.16, .04),
            (1.70, .080, .080, -1.34, -.02),
            (1.82, .135, .095, -1.42, -.05),
            (1.96, .120, .085, -1.45, -.06),
            (2.06, .030, .030, -1.46, -.06),
        ]
        t_ob = plush_loft('Tail • elephant tail with tuft', tail_prof, [main_mat, cuff_mat])
        for f in t_ob.data.polygons:
            if f.center.z > 1.74 and f.center.x < -1.30:
                f.material_index = 1
        parts.append(t_ob)
        tail_centers = [Vector((cx, cy, z)) for z, _, _, cx, cy in tail_prof]
    elif CHAR_SLUG == "craftycorn":
        # Fluffy aqua-turquoise unicorn tail + neck mane
        tail_prof = [
            (1.05, .04, .04, .34, .34),
            (1.18, .22, .20, .38, .42),
            (1.42, .26, .24, .32, .46),
            (1.65, .18, .18, .16, .38),
            (1.72, .06, .06, .05, .30),
        ]
        t_ob = plush_loft('Tail • aqua unicorn tail', tail_prof, [main_mat, cuff_mat])
        for f in t_ob.data.polygons:
            f.material_index = 1
        parts.append(t_ob)
    elif CHAR_SLUG == "kickin_chicken":
        # Upward-projecting yellow tail feather tuft
        tail_prof = [
            (1.54, .06, .06, -.12, .32),
            (1.66, .18, .15, -.32, .38),
            (1.86, .21, .16, -.44, .40),
            (2.08, .14, .12, -.46, .36),
            (2.18, .03, .03, -.44, .32),
        ]
        t_ob = plush_loft('Tail • chicken tail feathers', tail_prof, [main_mat, cuff_mat])
        parts.append(t_ob)
    elif CHAR_SLUG == "picky_piggy":
        # Coiled 3D corkscrew pig tail peeking out on the left-back hip
        cork_pts = []
        for i in range(44):
            u = i / 43
            ang = u * 3.4 * pi
            cx = -.36 - u * .68 + .13 * cos(ang)
            cy = .24 - u * .20 + .09 * sin(ang)
            cz = 1.54 + u * .52 + .13 * sin(ang)
            cork_pts.append((cx, cy, cz))
        cork_ob = bezier_curve('Tail • corkscrew pig tail', cork_pts, .046, main_mat)
        bpy.ops.object.select_all(action='DESELECT')
        cork_ob.select_set(True)
        bpy.context.view_layer.objects.active = cork_ob
        bpy.ops.object.convert(target='MESH')
        parts.append(cork_ob)

    source_surfaces = []
    for ob in parts:
        source_surfaces.append((
            BVHTree.FromPolygons([v.co for v in ob.data.vertices], [list(f.vertices) for f in ob.data.polygons]),
            [f.material_index for f in ob.data.polygons]
        ))

    bpy.ops.object.select_all(action='DESELECT')
    for ob in parts:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()
    mo = body.modifiers.new('Joined shoulders hips and tail base', 'REMESH')
    mo.mode = 'VOXEL'
    mo.voxel_size = .008
    mo.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=mo.name)
    mo = body.modifiers.new('Soft cloth transitions', 'SMOOTH')
    mo.factor = .62
    mo.iterations = 10
    bpy.ops.object.modifier_apply(modifier=mo.name)

    vg = body.vertex_groups.new(name='Shoulder transition')
    for v in body.data.vertices:
        x, y, z = v.co
        w = math.exp(-(((abs(x) - .37) / .26) ** 2 + ((z - 2.53) / .23) ** 2))
        if w > .01:
            vg.add([v.index], w, 'REPLACE')
    mo = body.modifiers.new('Rounded shoulder insertion', 'SMOOTH')
    mo.vertex_group = vg.name
    mo.factor = .65
    mo.iterations = 36
    bpy.ops.object.modifier_apply(modifier=mo.name)

    body.data.materials.clear()
    body.data.materials.append(main_mat)
    body.data.materials.append(cuff_mat)
    body.data.materials.append(belly_mat)

    for f in body.data.polygons:
        f.use_smooth = True
        c = f.center
        best = (100, 0, 0)
        for part_index, (tree, indices) in enumerate(source_surfaces):
            co, no, idx, dist = tree.find_nearest(c)
            if idx is not None and dist < best[0]:
                best = (dist, part_index, indices[idx])
        f.material_index = 0
        # Arm mittens (skip for KickinChicken who has solid yellow feather wings)
        if CHAR_SLUG != "kickin_chicken" and best[1] in (2, 4) and c.z - .60 * (abs(c.x) - .90) < 1.74:
            f.material_index = 1
        # Leg / foot cuffs
        if best[1] in (1, 3) and c.z < .55 + .08 * ((abs(c.x) - .44) / .35) ** 2:
            f.material_index = 1
        # Tail secondary color (Bubba tuft or CraftyCorn aqua tail)
        if best[1] == 5 and best[2] == 1:
            f.material_index = 1
        # Oval belly patch on DogDay (yellow) and Bobby BearHug (pastel pink)
        if CHAR_SLUG in ("dogday", "bobby_bearhug") and best[1] == 0:
            if c.y < -.12 and ((c.x / .38) ** 2 + ((c.z - 1.94) / .49) ** 2 < 1.0):
                f.material_index = 2

    # ==========================================================================
    # 6. SURFACE-FITTED ZIPPER & CHARACTER PENDANT (v10-final recipe)
    # ==========================================================================
    btree = BVHTree.FromPolygons([v.co for v in body.data.vertices], [list(f.vertices) for f in body.data.polygons])
    def torso_y(z):
        hit, no, idx, dist = btree.ray_cast(Vector((0, -2, z)), Vector((0, 1, 0)), 4)
        return hit.y if hit else -.35

    bezier_curve('Zipper • surface fitted dark tape', [(0, torso_y(z) - .015, z) for z in [2.62, 2.45, 2.25, 2.00, 1.75, 1.51, 1.46]], .025, zipmat)
    for i in range(27):
        z = 1.49 + i * .039
        yy = torso_y(z) - .043
        bpy.ops.mesh.primitive_cube_add(size=1, location=((-.012 if i % 2 else .012), yy, z))
        ob = bpy.context.object
        ob.name = 'Zipper tooth %02d' % i
        ob.scale = (.019, .014, .012)
        bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
        finish(ob, teeth)
        be = ob.modifiers.new('rounded tooth', 'BEVEL')
        be.width = .004
        be.segments = 2
        bpy.ops.object.modifier_apply(modifier=be.name)

    # Character-Specific Beveled 3D Pendant (all top edges meet the bail at z=2.57!)
    if CHAR_SLUG == "dogday":
        # 8-ray orange sunburst outer medallion + golden circular center disc
        sun_rays = []
        for k in range(16):
            ang = 2 * pi * k / 16
            r = .285 if k % 2 == 0 else .215
            sun_rays.append((r * cos(ang), 2.30 + r * sin(ang)))
        polyextrude('Pendant • orange sun rays', catmull(sun_rays, 3), -.53, -.45, pendant_alt, .010)
        disc_pts = [(.165 * cos(2 * pi * k / 32), 2.30 + .165 * sin(2 * pi * k / 32)) for k in range(32)]
        polyextrude('Pendant • golden sun center', disc_pts, -.565, -.48, pendant_mat, .010)
    elif CHAR_SLUG == "bobby_bearhug":
        # Beveled ruby-red 3D heart pendant
        heart_pts = []
        for k in range(64):
            t = 2 * pi * k / 64
            hx = .0165 * (16 * sin(t) ** 3)
            hz = 2.38 + .0165 * (13 * cos(t) - 5 * cos(2 * t) - 2 * cos(3 * t) - cos(4 * t))
            heart_pts.append((hx, hz))
        polyextrude('Pendant • ruby red heart', heart_pts, -.55, -.45, pendant_mat, .012)
    elif CHAR_SLUG == "bubba_bubbaphant":
        # Yellow lightbulb globe + royal-blue screw base
        bulb_pts = [
            (0.0, 2.55), (.14, 2.52), (.23, 2.42), (.24, 2.29),
            (.16, 2.17), (.11, 2.08), (-.11, 2.08), (-.16, 2.17),
            (-.24, 2.29), (-.23, 2.42), (-.14, 2.52)
        ]
        polyextrude('Pendant • yellow lightbulb globe', catmull(bulb_pts, 5), -.55, -.45, pendant_mat, .012)
        base_pts = [(-.11, 2.10), (.11, 2.10), (.095, 1.96), (-.095, 1.96)]
        polyextrude('Pendant • blue screw base', catmull(base_pts, 4), -.56, -.44, pendant_alt, .010)
    elif CHAR_SLUG == "craftycorn":
        # 5-petal rainbow flower pendant + yellow center disc
        petal_colors = [
            (.55, .015, .025), # Red
            (.65, .18, .010),  # Orange
            (.04, .45, .025),  # Green
            (.02, .18, .62),   # Blue
            (.28, .03, .52),   # Purple
        ]
        for idx, pcol in enumerate(petal_colors):
            pm = mat(f'06p • flower petal {idx}', pcol, .25, .15)
            ang = pi / 2 + idx * 2 * pi / 5
            px = .175 * cos(ang)
            pz = 2.28 + .175 * sin(ang)
            p_pts = [(px + .115 * cos(2 * pi * k / 24), pz + .115 * sin(2 * pi * k / 24)) for k in range(24)]
            polyextrude(f'Pendant • petal {idx}', p_pts, -.54, -.45, pm, .010)
        c_pts = [(.125 * cos(2 * pi * k / 32), 2.28 + .125 * sin(2 * pi * k / 32)) for k in range(32)]
        polyextrude('Pendant • flower center', c_pts, -.57, -.47, pendant_mat, .010)
    elif CHAR_SLUG == "hoppy_hopscotch":
        # Sharp beveled yellow lightning bolt pendant
        bolt_pts = [
            (.04, 2.57), (-.20, 2.28), (-.03, 2.26),
            (-.14, 1.97), (.21, 2.29), (.03, 2.31)
        ]
        polyextrude('Pendant • yellow lightning bolt', bolt_pts, -.55, -.45, pendant_mat, .008)
    elif CHAR_SLUG == "kickin_chicken":
        # 5-pointed ruby-red star pendant
        star_pts = []
        for k in range(10):
            ang = pi / 2 + k * pi / 5
            r = .28 if k % 2 == 0 else .125
            star_pts.append((r * cos(ang), 2.30 + r * sin(ang)))
        polyextrude('Pendant • ruby star', star_pts, -.55, -.45, pendant_mat, .009)
    elif CHAR_SLUG == "picky_piggy":
        # Glossy crimson-red apple pendant + green leaf
        apple_pts = [
            (0.0, 2.50), (.12, 2.55), (.24, 2.47), (.26, 2.31),
            (.20, 2.13), (.08, 2.05), (0.0, 2.09), (-.08, 2.05),
            (-.20, 2.13), (-.26, 2.31), (-.24, 2.47), (-.12, 2.55)
        ]
        polyextrude('Pendant • red apple', catmull(apple_pts, 5), -.55, -.45, pendant_mat, .012)
        leaf_mat = mat('Pendant • apple leaf green', (.06, .48, .02), .30)
        leaf_pts = [(.02, 2.52), (.14, 2.60), (.18, 2.55), (.08, 2.49)]
        polyextrude('Pendant • apple leaf', catmull(leaf_pts, 4), -.54, -.46, leaf_mat, .006)
    elif CHAR_SLUG == "baba_chops":
        # Weathered dark bronze/gunmetal Skull pendant with recessed eye sockets & nose
        skull_pts = [
            (0.0, 2.56), (.16, 2.53), (.25, 2.41), (.24, 2.25),
            (.15, 2.16), (.14, 2.01), (.05, 2.01), (.05, 2.07),
            (-.05, 2.07), (-.05, 2.01), (-.14, 2.01), (-.15, 2.16),
            (-.24, 2.25), (-.25, 2.41), (-.16, 2.53)
        ]
        polyextrude('Pendant • weathered skull', catmull(skull_pts, 4), -.55, -.45, pendant_mat, .010)
        for sg in (-1, 1):
            ell(f'Pendant • skull eye {sg}', (sg * .095, -.552, 2.33), (.065, .022, .065), inside, 24, 16)
        ell('Pendant • skull nasal', (0.0, -.552, 2.20), (.035, .020, .045), inside, 20, 14)

    bpy.ops.mesh.primitive_torus_add(major_segments=48, minor_segments=16, location=(0, -.46, 2.58), rotation=(pi / 2, 0, 0), major_radius=.041, minor_radius=.012)
    b = finish(bpy.context.object, pendant_mat)
    b.name = 'Pendant • bail'
    ell('Pendant • rounded attachment seat', (0, -.491, 2.55), (.052, .036, .032), pendant_mat, 32, 20)

    # ==========================================================================
    # 7. SURFACE-PROJECTED 3D COTTON STITCH ARCS (v11 recipe)
    # ==========================================================================
    root = bpy.data.objects.new(f'{CHAR_SLUG.upper()}_ROOT • unrigged shape draft', None)
    col.objects.link(root)
    for o in list(col.objects):
        if o != root:
            o.parent = root

    def make_tree(o):
        return BVHTree.FromPolygons([v.co for v in o.data.vertices], [list(p.vertices) for p in o.data.polygons])

    bt, ht, mt = make_tree(body), make_tree(head), make_tree(lining)

    def poly_curve(name, paths, r, m):
        cu = bpy.data.curves.new(name, 'CURVE')
        cu.dimensions = '3D'
        cu.resolution_u = 2
        cu.bevel_depth = r
        cu.bevel_resolution = 3
        cu.use_fill_caps = True
        for pts in paths:
            sp = cu.splines.new('POLY')
            sp.points.add(len(pts) - 1)
            for p, co in zip(sp.points, pts):
                p.co = (*co, 1)
        o = bpy.data.objects.new(name, cu)
        col.objects.link(o)
        o.parent = root
        cu.materials.append(m)
        return o

    counts = {}
    def seam(name, points, bvh, closed=False, spacing=.032, m=thread):
        pts = [Vector(p) for p in points]
        if len(pts) < 2:
            return
        if closed:
            pts.append(pts[0])
        samples = []
        walk = 0
        nextd = 0
        for a, b in zip(pts, pts[1:]):
            le = (b - a).length
            if le < 1e-8:
                continue
            while nextd <= walk + le:
                p = a + (b - a) * ((nextd - walk) / le)
                q, n, _, _ = bvh.find_nearest(p)
                if q is not None:
                    samples.append((q, n))
                nextd += spacing
            walk += le
        if len(samples) < 3:
            return
        seampts = [p + n * .0003 for p, n in samples]
        if closed:
            seampts.append(seampts[0])
        poly_curve('Seam • ' + name, [seampts], .0018, groove)
        paths = []
        for i, (p, n) in enumerate(samples):
            t_vec = (samples[min(i + 1, len(samples) - 1)][0] - samples[max(0, i - 1)][0]).normalized()
            side = n.cross(t_vec).normalized()
            s_pts = []
            for j in range(7):
                u = j / 6
                co = p + t_vec * ((u - .5) * .014) + side * ((u - .5) * .010)
                q, nn, _, _ = bvh.find_nearest(co)
                if q is not None:
                    s_pts.append(q + nn * (-.0006 + .0038 * math.sin(math.pi * u)))
            if len(s_pts) >= 2:
                paths.append(s_pts)
        poly_curve('Stitches • ' + name, paths, .0022, m)
        counts[name] = len(paths)

    def frontpoints(xz, bvh):
        arr = []
        for x, z in xz:
            q, n, _, _ = bvh.ray_cast(Vector((x, -3, z)), Vector((0, 1, 0)), 6)
            if q is not None:
                arr.append(q)
        return arr

    def boundaries(ob, bvh, label, max_loops=12, skip_slots=(3,)):
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bm.verts.ensure_lookup_table()
        adj = {}
        for e in bm.edges:
            if len(e.link_faces) == 2:
                m0, m1 = e.link_faces[0].material_index, e.link_faces[1].material_index
                if m0 != m1 and not any(s in (m0, m1) for s in skip_slots):
                    a, b = [v.index for v in e.verts]
                    adj.setdefault(a, []).append(b)
                    adj.setdefault(b, []).append(a)
        seen = set()
        num = 0
        for start in adj:
            if start in seen:
                continue
            path = []
            cur = start
            prev = -1
            while cur not in seen:
                seen.add(cur)
                path.append(bm.verts[cur].co.copy())
                nxt = [x for x in adj[cur] if x != prev and x not in seen]
                if not nxt:
                    break
                prev, cur = cur, nxt[0]
            if len(path) < 35:
                continue
            for _ in range(6):
                path = [(path[i - 1] + 2 * p + path[(i + 1) % len(path)]) / 4 for i, p in enumerate(path)]
            num += 1
            closed_loop = (path[0] - path[-1]).length < 0.12
            seam(label + str(num), path, bvh, closed=closed_loop)
            if num >= max_loops:
                break
        bm.free()

    boundaries(body, bt, 'Cuff ')
    head_skip = (2, 3) if CHAR_SLUG == "hoppy_hopscotch" else (3,)
    boundaries(head, ht, 'Ear panel ', skip_slots=head_skip)

    if CHAR_SLUG == "bubba_bubbaphant":
        # Forehead seam above trunk root only (since trunk covers upper lip)
        seam('Forehead', frontpoints([(0, 4.59 - i * .008) for i in range(48)], ht), ht, spacing=.029)
    elif CHAR_SLUG != "craftycorn":
        seam('Forehead', frontpoints([(0, 4.59 - i * .008) for i in range(66)], ht), ht, spacing=.029)
    else:
        # CraftyCorn has two subtle stitched nostrils on the cream muzzle
        for sg in (-1, 1):
            seam(f'Nostril {sg}', frontpoints([(sg * (.07 + .02 * sin(i / 8 * pi)), 3.96 + i * .009) for i in range(9)], ht), ht, spacing=.018)

    seam('Chin', frontpoints([(0, 2.76 + i * .004) for i in range(19)], ht), ht, spacing=.028)
    for lo, hi in [(2.86, 3.055), (3.52, 3.94)]:
        seam('Mouth lining ' + str(lo), frontpoints([(0, lo + i * (hi - lo) / 80) for i in range(81)], mt), mt, spacing=.033, m=mouththread)

    if CHAR_SLUG == "dogday":
        # Long stitched ridge along each floppy spaniel ear
        for sg in (-1, 1):
            seam(f'Floppy ear {sg}', frontpoints([(sg * (.48 + i * .028), 4.52 - i * .021) for i in range(38)], ht), ht, spacing=.034)

    for sg in (-1, 1):
        seam('Inner leg ' + str(sg), frontpoints([(sg * (.17 + .045 * math.sin(i / 60 * math.pi)), .48 + i * .014) for i in range(61)], bt), bt, spacing=.039)
        seam('Shoulder ' + str(sg), frontpoints([(sg * (.29 + i * .0035), 2.69 - i * .006) for i in range(38)], bt), bt, spacing=.037, m=mouththread)

    arr = []
    for i in range(100):
        z = 1.46 + i * .011
        q, n, _, _ = bt.ray_cast(Vector((0, 3, z)), Vector((0, -1, 0)), 6)
        if q is not None:
            arr.append(q)
    seam('Back body', arr, bt, spacing=.036, m=mouththread)

    # ==========================================================================
    # 8. STUDIO CAMERAS & LIGHTING (Exact critter-3d v07/v11 setup)
    # ==========================================================================
    floor = mat('Studio neutral floor', (.19, .205, .23), .85)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, .20))
    o = bpy.context.object
    o.name = 'Studio floor'
    move(o, studio)
    o.data.materials.append(floor)
    o.hide_render = True

    def aim(o, point):
        o.rotation_euler = (Vector(point) - o.location).to_track_quat('-Z', 'Y').to_euler()

    def area(name, loc, power, size, color):
        da = bpy.data.lights.new(name, 'AREA')
        da.energy = power
        da.shape = 'DISK'
        da.size = size
        da.color = color
        o = bpy.data.objects.new(name, da)
        studio.objects.link(o)
        o.location = loc
        aim(o, (0, 0, 2.6))

    area('Key • large neutral softbox', (-3.8, -5, 7), 700, 5, (1, .94, .88))
    area('Fill • frontal', (4, -4, 4.6), 500, 4, (.90, .94, 1))
    area('Separation', (2, 3, 6), 800, 4, (1, 1, 1))

    world = bpy.data.worlds.new('Neutral studio') if not bpy.data.worlds else bpy.data.worlds[0]
    bpy.context.scene.world = world
    world.use_nodes = True
    world.node_tree.nodes.get('Background').inputs[0].default_value = (.16, .18, .22, 1)
    world.node_tree.nodes.get('Background').inputs[1].default_value = .4

    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = 'AgX'
    sc.render.image_settings.file_format = 'PNG'
    sc.render.film_transparent = True
    sc.render.image_settings.color_mode = 'RGBA'

    ortho_scale = 6.8 if CHAR_SLUG == "hoppy_hopscotch" else 6.5
    z_center = 2.45 if CHAR_SLUG == "hoppy_hopscotch" else 2.25
    for name, loc, scale in [
        ('Front', (0, -12, z_center), ortho_scale),
        ('Three-quarter', (6, -12, z_center + 1.0), ortho_scale + 0.1),
        ('Side', (12, 0, z_center), ortho_scale),
        ('Back', (0, 12, z_center), ortho_scale),
    ]:
        da = bpy.data.cameras.new(name)
        da.type = 'ORTHO'
        da.ortho_scale = scale
        o = bpy.data.objects.new(name, da)
        studio.objects.link(o)
        o.location = loc
        aim(o, (0, 0, z_center))

    da = bpy.data.cameras.new('Stitch-detail')
    da.type = 'ORTHO'
    da.ortho_scale = 2.5
    close = bpy.data.objects.new('Stitch-detail', da)
    studio.objects.link(close)
    close.location = (0, -12, 1.85)
    aim(close, (0, 0, 1.85))

    return col, studio, root, {"stitch_counts": counts, "total_stitches": sum(counts.values())}


col, studio, root, stitch_info = build_character_scene()
sc = bpy.context.scene

if MODE == "preview":
    sc.cycles.samples = 24
    for cam_name in ['Front', 'Three-quarter']:
        cam = bpy.data.objects[cam_name]
        sc.camera = cam
        sc.render.resolution_x = 900
        sc.render.resolution_y = 1125
        sc.render.filepath = os.path.join(WORK_DIR, f"{CHAR_SLUG}_{cam_name}.png")
        bpy.ops.render.render(write_still=True)
    print("PREVIEW_RENDER_COMPLETE:", CHAR_SLUG, stitch_info)
    sys.exit(0)

# ==============================================================================
# 9. FULL PRODUCTION PIPELINE:
#    (A) Render Front, Three-quarter, Back, Stitch-detail on 100% full-res mesh
#    (B) Generate <slug>_blender_cycles_render.png & <slug>_3d_preview.png
#    (C) Decimate voxel shells (ratio=0.10) & export .blend, .glb, .obj/.mtl
#    (D) Render 36-frame 3D Fart Blast Animation (.mp4, .gif, .webp, _storyboard.png)
# ==============================================================================
sc.cycles.samples = 32
view_files = {}
for cam_name, (rx, ry) in [
    ('Front', (1080, 1350)),
    ('Three-quarter', (1080, 1350)),
    ('Back', (1080, 1350)),
    ('Stitch-detail', (1080, 1080)),
]:
    out_png = os.path.join(OUT_MODELS_DIR, f"{CHAR_SLUG}_{cam_name}.png")
    view_files[cam_name] = out_png
    if os.path.exists(out_png) and os.path.getmtime(out_png) > 1760844800:
        print("Reusing fresh studio render:", out_png)
        continue
    cam = bpy.data.objects[cam_name]
    sc.camera = cam
    sc.render.resolution_x = rx
    sc.render.resolution_y = ry
    sc.render.filepath = out_png
    bpy.ops.render.render(write_still=True)

# Copy Front render to <slug>_blender_cycles_render.png
hero_render_path = os.path.join(OUT_MODELS_DIR, f"{CHAR_SLUG}_blender_cycles_render.png")
shutil.copyfile(view_files['Front'], hero_render_path)

# Build 4-panel comparison sheet (<slug>_3d_preview.png) via ffmpeg hstack (zero PIL dependency!)
preview_sheet_path = os.path.join(OUT_MODELS_DIR, f"{CHAR_SLUG}_3d_preview.png")
ref_img_path = REF_MAP[CHAR_SLUG]
subprocess.run([
    "ffmpeg", "-y",
    "-i", ref_img_path,
    "-i", view_files['Front'],
    "-i", view_files['Three-quarter'],
    "-i", view_files['Stitch-detail'],
    "-filter_complex",
    "[0:v]scale=480:600:force_original_aspect_ratio=decrease,pad=480:600:(ow-iw)/2:(oh-ih)/2:color=#1e293b[v0];"
    "[1:v]scale=480:600:force_original_aspect_ratio=decrease,pad=480:600:(ow-iw)/2:(oh-ih)/2:color=#1e293b[v1];"
    "[2:v]scale=480:600:force_original_aspect_ratio=decrease,pad=480:600:(ow-iw)/2:(oh-ih)/2:color=#1e293b[v2];"
    "[3:v]scale=480:600:force_original_aspect_ratio=decrease,pad=480:600:(ow-iw)/2:(oh-ih)/2:color=#1e293b[v3];"
    "[v0][v1][v2][v3]hstack=inputs=4[out]",
    "-map", "[out]", "-frames:v", "1", preview_sheet_path
], check=True)

# Decimate dense voxel shells AFTER high-res studio renders so .blend & .glb are ~4.5 MB
for obj in list(col.objects):
    if obj.type == 'MESH' and any(k in obj.name for k in ('Head •', 'Body •', 'Wool •', 'Nose • aqua forelock')):
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        dec = obj.modifiers.new('Export decimate', 'DECIMATE')
        dec.ratio = 0.10 if 'Wool' not in obj.name else 0.20
        bpy.ops.object.modifier_apply(modifier=dec.name)

blend_path = os.path.join(OUT_MODELS_DIR, f"{CHAR_SLUG}_plush_base_model.blend")
glb_path = os.path.join(OUT_MODELS_DIR, f"{CHAR_SLUG}_plush_base_model.glb")
obj_path = os.path.join(OUT_MODELS_DIR, f"{CHAR_SLUG}_plush_base_model.obj")

if os.path.exists(blend_path):
    os.remove(blend_path)
bpy.ops.wm.save_as_mainfile(filepath=blend_path, compress=True)

# Select character collection objects for GLB and OBJ export
bpy.ops.object.select_all(action='DESELECT')
for o in col.objects:
    o.select_set(True)

bpy.ops.export_scene.gltf(
    filepath=glb_path,
    use_selection=True,
    export_format='GLB',
    export_apply=True,
    export_materials='EXPORT',
)
bpy.ops.wm.obj_export(
    filepath=obj_path,
    export_selected_objects=True,
    export_materials=True,
)

# ==============================================================================
# 10. 36-FRAME 3D FART BLAST ANIMATION ON THE NEW CRITTER-3D v11 MODEL
# ==============================================================================
anim_frames_dir = os.path.join(WORK_DIR, "fart_frames")
os.makedirs(anim_frames_dir, exist_ok=True)

# Create toxic green volumetric plush fart cloud puffs behind the tail
fart_mat = bpy.data.materials.new('FartCloud • toxic green')
fart_mat.use_nodes = True
fnodes = fart_mat.node_tree.nodes
fbsdf = fnodes.get('Principled BSDF')
fbsdf.inputs['Base Color'].default_value = (.12, .68, .04, 1)
fbsdf.inputs['Roughness'].default_value = .65
fbsdf.inputs['Emission Color'].default_value = (.18, .85, .06, 1)
fbsdf.inputs['Emission Strength'].default_value = .45

puff_specs = [
    (0.0,  0.65, 1.45, 0.28),
    (-0.22, 0.92, 1.52, 0.36),
    (0.24,  0.88, 1.40, 0.34),
    (0.0,  1.22, 1.58, 0.46),
    (-0.34, 1.38, 1.68, 0.42),
    (0.32,  1.34, 1.48, 0.40),
    (0.0,  1.65, 1.75, 0.55),
]
puff_objs = []
for idx, (px, py, pz, pr) in enumerate(puff_specs):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=16, radius=pr, location=(px, py, pz))
    po = bpy.context.object
    po.name = f'FartPuff.{idx}'
    po.data.materials.append(fart_mat)
    for p in po.data.polygons:
        p.use_smooth = True
    puff_objs.append((po, Vector((px, py, pz)), pr))

# Set up perspective animation camera looking at 3/4 side-back view during blast
anim_cam_da = bpy.data.cameras.new('FartAnimCam')
anim_cam_da.type = 'ORTHO'
anim_cam_da.ortho_scale = 6.8 if CHAR_SLUG == "hoppy_hopscotch" else 6.4
anim_cam = bpy.data.objects.new('FartAnimCam', anim_cam_da)
studio.objects.link(anim_cam)
sc.camera = anim_cam
sc.cycles.samples = 8
sc.render.resolution_x = 480
sc.render.resolution_y = 480
sc.render.film_transparent = False
sc.world.node_tree.nodes.get('Background').inputs[0].default_value = (.08, .10, .15, 1)
sc.world.node_tree.nodes.get('Background').inputs[1].default_value = 1.0

z_target = 2.40 if CHAR_SLUG == "hoppy_hopscotch" else 2.25
N_FRAMES = 24
for f_idx in range(N_FRAMES):
    u = f_idx / (N_FRAMES - 1)
    # Phase 1 (0..0.28): Turn from front to 3/4 back-side
    # Phase 2 (0.28..0.50): Deep squat & build pressure
    # Phase 3 (0.50..0.82): Explosive green fart blast + recoil hop!
    # Phase 4 (0.82..1.00): Return to cheerful idle
    if u < 0.28:
        t = u / 0.28
        yaw = t * (pi * 0.68)
        pitch = 0.0
        z_off = 0.0
        sz = 1.0
    elif u < 0.50:
        t = (u - 0.28) / 0.22
        yaw = pi * 0.68 + 0.08 * sin(t * 4 * pi)
        pitch = 0.22 * t
        z_off = -0.22 * t
        sz = 1.0 - 0.10 * t
    elif u < 0.82:
        t = (u - 0.50) / 0.32
        yaw = pi * 0.68
        pitch = 0.22 - 0.34 * sin(t * pi)
        z_off = -0.22 + 0.45 * sin(t * pi)
        sz = 0.90 + 0.16 * sin(t * pi)
    else:
        t = (u - 0.82) / 0.18
        yaw = (1 - t) * (pi * 0.68)
        pitch = 0.0
        z_off = 0.0
        sz = 1.0

    root.rotation_euler = (pitch, 0.0, yaw)
    root.location = (0.0, 0.0, z_off)
    root.scale = (1.0 / sqrt(sz), 1.0 / sqrt(sz), sz)

    # Animate fart puffs during Phase 3 (0.48 <= u <= 0.92)
    for p_i, (po, base_loc, pr) in enumerate(puff_objs):
        delay = p_i * 0.035
        pu = (u - (0.48 + delay)) / 0.36
        if 0.0 < pu < 1.0:
            po.hide_render = False
            scale_f = sin(pu * pi) * (0.6 + 0.8 * pu)
            po.scale = (scale_f, scale_f, scale_f)
            # Blast outward along -Y/X in world space behind the rotated character
            blast_dir = Vector((-sin(yaw), -cos(yaw), 0.18)).normalized()
            po.location = Vector((0, 0, 1.45 + z_off)) + blast_dir * (0.45 + 1.55 * pu + p_i * 0.14)
        else:
            po.hide_render = True

    anim_cam.location = (3.5, -11.5, z_target + 0.6)
    anim_cam.rotation_euler = (Vector((0, 0, z_target)) - anim_cam.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = os.path.join(anim_frames_dir, f"frame_{f_idx:03d}.png")
    bpy.ops.render.render(write_still=True)

# Compile MP4, GIF, WEBP, and 4-panel Storyboard via ffmpeg (zero PIL dependency!)
mp4_path = os.path.join(OUT_ANIMS_DIR, f"{CHAR_SLUG}_fart_animation.mp4")
gif_path = os.path.join(OUT_ANIMS_DIR, f"{CHAR_SLUG}_fart_animation.gif")
webp_path = os.path.join(OUT_ANIMS_DIR, f"{CHAR_SLUG}_fart_animation.webp")
story_path = os.path.join(OUT_ANIMS_DIR, f"{CHAR_SLUG}_fart_storyboard.png")

subprocess.run([
    "ffmpeg", "-y", "-framerate", "12",
    "-i", os.path.join(anim_frames_dir, "frame_%03d.png"),
    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", mp4_path
], check=True)

subprocess.run([
    "ffmpeg", "-y", "-framerate", "12",
    "-i", os.path.join(anim_frames_dir, "frame_%03d.png"),
    "-vf", "split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
    "-loop", "0", gif_path
], check=True)

# Try libwebp_anim or copy gif if libwebp not compiled into ffmpeg
res_webp = subprocess.run([
    "ffmpeg", "-y", "-framerate", "12",
    "-i", os.path.join(anim_frames_dir, "frame_%03d.png"),
    "-loop", "0", "-q:v", "80", webp_path
])

subprocess.run([
    "ffmpeg", "-y",
    "-i", os.path.join(anim_frames_dir, "frame_000.png"),
    "-i", os.path.join(anim_frames_dir, "frame_009.png"),
    "-i", os.path.join(anim_frames_dir, "frame_014.png"),
    "-i", os.path.join(anim_frames_dir, "frame_018.png"),
    "-filter_complex", "[0:v][1:v][2:v][3:v]hstack=inputs=4[out]",
    "-map", "[out]", "-frames:v", "1", story_path
], check=True)

# Save per-character Blender generator script in models/build_<slug>_blender.py
with open(__file__, "r", encoding="utf-8") as f_in:
    src_code = f_in.read()
src_code = src_code.replace('CHAR_SLUG = argv[0] if len(argv) >= 1 else "bobby_bearhug"', f'CHAR_SLUG = argv[0] if len(argv) >= 1 else "{CHAR_SLUG}"')
with open(os.path.join(OUT_MODELS_DIR, f"build_{CHAR_SLUG}_blender.py"), "w", encoding="utf-8") as f_out:
    f_out.write(src_code)

print("FULL_PIPELINE_COMPLETE:", CHAR_SLUG, stitch_info)

