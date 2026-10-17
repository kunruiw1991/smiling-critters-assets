/**
 * Baba Chops 3D Plush Base Model Generator (Three.js r161 ESM)
 * ============================================================================
 * 1:1 High-Precision 3D Recreation of `images/121_BabaChopsPlush1.webp`
 * Official Poppy Playtime Chapter 4 (Nightmare Critters) Baba Chops Plush
 */

function createPlushBumpTexture(THREE, mode = 'wool') {
  if (typeof document === 'undefined') return null;
  const size = 256;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d');
  const imgData = ctx.createImageData(size, size);
  const data = imgData.data;

  for (let y = 0; y < size; y++) {
    for (let x = 0; x < size; x++) {
      const idx = (y * size + x) * 4;
      const nx = x / size;
      const ny = y / size;
      let v = 128;
      if (mode === 'wool') {
        const c1 = Math.sin(nx * Math.PI * 16) * Math.cos(ny * Math.PI * 16);
        const c2 = Math.sin((nx + ny) * Math.PI * 28) * Math.cos((nx - ny) * Math.PI * 28);
        const c3 = Math.sin(nx * Math.PI * 52 + 1.3) * Math.sin(ny * Math.PI * 52 + 0.7);
        const hash = Math.sin((x * 12.9898 + y * 78.233)) * 43758.5453;
        const grain = (hash - Math.floor(hash)) - 0.5;
        v = Math.max(0, Math.min(255, Math.floor(128 + 58 * c1 + 36 * c2 + 20 * c3 + 24 * grain)));
      } else {
        const hash = Math.sin((x * 12.9898 + y * 78.233)) * 43758.5453;
        const grain = (hash - Math.floor(hash)) - 0.5;
        const weave = Math.sin(nx * Math.PI * 64) * Math.cos(ny * Math.PI * 64);
        v = Math.max(0, Math.min(255, Math.floor(128 + 26 * weave + 34 * grain)));
      }
      data[idx] = v;
      data[idx + 1] = v;
      data[idx + 2] = v;
      data[idx + 3] = 255;
    }
  }
  ctx.putImageData(imgData, 0, 0);
  const tex = new THREE.CanvasTexture(canvas);
  tex.wrapS = THREE.RepeatWrapping;
  tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(mode === 'wool' ? 4 : 6, mode === 'wool' ? 4 : 6);
  return tex;
}

export function buildBabaChopsPlushModel(THREE) {
  const root = new THREE.Group();
  root.name = 'BabaChops_Plush_BaseModel';

  const bodyRig = new THREE.Group();
  bodyRig.name = 'Body_Rig_Root';
  root.add(bodyRig);

  const woolBump = createPlushBumpTexture(THREE, 'wool');
  const velourBump = createPlushBumpTexture(THREE, 'velour');

  // Calibrated PBR Material Palette matched to `images/121_BabaChopsPlush1.webp`:
  // Notice in #121 that the muzzle, ears, teeth & hooves are soft medium-light dove grey (#9fa1aa / #b0b2bc),
  // whereas the chest Skull Pendant is stark bright white (#f7f8fa).
  const materials = {
    blackWool: new THREE.MeshStandardMaterial({
      name: 'Baba_Black_Sherpa_Wool',
      color: 0x141418,
      roughness: 0.92,
      metalness: 0.02,
      bumpMap: woolBump,
      bumpScale: 0.018
    }),
    blackPlush: new THREE.MeshStandardMaterial({
      name: 'Baba_Black_Plush_Velour',
      color: 0x18181e,
      roughness: 0.88,
      metalness: 0.03,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    greyPlush: new THREE.MeshStandardMaterial({
      name: 'Baba_DoveGrey_Plush_Velour',
      color: 0x9ca0aa,
      roughness: 0.85,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    greyTeeth: new THREE.MeshStandardMaterial({
      name: 'Baba_LightGrey_Plush_Teeth',
      color: 0xb0b3bd,
      roughness: 0.82,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.006
    }),
    greyEyelid: new THREE.MeshStandardMaterial({
      name: 'Baba_MidGrey_Eyelid_Plush',
      color: 0x8d909a,
      roughness: 0.86,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.007
    }),
    greyInnerEar: new THREE.MeshStandardMaterial({
      name: 'Baba_InnerEar_Shadow_Grey',
      color: 0x686b75,
      roughness: 0.90,
      metalness: 0.02
    }),
    mouthCavity: new THREE.MeshBasicMaterial({
      name: 'Baba_Recessed_Mouth_Void',
      color: 0x050507,
      side: THREE.DoubleSide
    }),
    glossyEye: new THREE.MeshPhysicalMaterial({
      name: 'Baba_Glossy_Acrylic_Eye',
      color: 0x020204,
      roughness: 0.06,
      metalness: 0.0,
      envMapIntensity: 0.12,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04,
      reflectivity: 0.95
    }),
    eyeHighlight: new THREE.MeshBasicMaterial({
      name: 'Baba_Eye_Studio_Catchlight',
      color: 0xffffff
    }),
    skullWhite: new THREE.MeshStandardMaterial({
      name: 'Baba_Skull_Pendant_White',
      color: 0xf7f8fb,
      roughness: 0.36,
      metalness: 0.03
    }),
    skullCutout: new THREE.MeshBasicMaterial({
      name: 'Baba_Skull_Black_Cutout',
      color: 0x08080b
    }),
    metalZipper: new THREE.MeshStandardMaterial({
      name: 'Baba_Silver_Zipper_Hardware',
      color: 0xc8cdd6,
      roughness: 0.28,
      metalness: 0.80
    }),
    seamDark: new THREE.MeshStandardMaterial({
      name: 'Baba_Plush_Seam_Groove',
      color: 0x101014,
      roughness: 0.92,
      metalness: 0.02
    })
  };

  // Helper to compute exact front Z surface of the torso at world y
  function torsoFrontZ(yWorld, xWorld = 0) {
    const yn = Math.max(-1, Math.min(1, (yWorld - 0.755) / 0.325));
    const widthP = 0.285 * (1.0 - 0.24 * yn - 0.10 * yn * yn);
    const depthP = 0.245 * (1.0 - 0.20 * yn - 0.08 * yn * yn);
    const xRatio = Math.min(0.95, Math.abs(xWorld) / Math.max(0.05, widthP));
    const zHoriz = Math.sqrt(Math.max(0.01, 1.0 - yn * yn)) * Math.sqrt(Math.max(0.01, 1.0 - xRatio * xRatio));
    return depthP * zHoriz;
  }

  // ============================================================================
  // 1. TORSO (Pear-Shaped Black Plush Body: y = 0.43 .. 1.08)
  // ============================================================================
  const torsoGroup = new THREE.Group();
  torsoGroup.name = 'Torso_And_Zipper_Group';
  bodyRig.add(torsoGroup);

  const torsoGeo = new THREE.SphereGeometry(1, 44, 36);
  const tPos = torsoGeo.attributes.position;
  for (let i = 0; i < tPos.count; i++) {
    let x = tPos.getX(i);
    let y = tPos.getY(i); // -1 .. +1
    let z = tPos.getZ(i);
    const widthProfile = 0.285 * (1.0 - 0.24 * y - 0.10 * y * y);
    const depthProfile = 0.245 * (1.0 - 0.20 * y - 0.08 * y * y);
    const rx = x * widthProfile;
    const ry = 0.755 + y * 0.325;
    let rz = z * depthProfile;
    if (rz > 0 && Math.abs(rx) < 0.036) {
      const seamDepth = (1.0 - Math.abs(rx) / 0.036) * 0.008;
      rz -= seamDepth;
    }
    tPos.setXYZ(i, rx, ry, rz);
  }
  torsoGeo.computeVertexNormals();
  const torsoMesh = new THREE.Mesh(torsoGeo, materials.blackPlush);
  torsoMesh.castShadow = true;
  torsoMesh.receiveShadow = true;
  torsoGroup.add(torsoMesh);

  // ============================================================================
  // 2. ZIPPER TRACK, COLLAR SLIDER & ICONIC WHITE SKULL PENDANT CHARM
  // ============================================================================
  const zipperGroup = new THREE.Group();
  zipperGroup.name = 'Zipper_Hardware_Group';
  torsoGroup.add(zipperGroup);

  // Curved zipper teeth & dark backing tape hugging the exact torso contour
  const toothGeo = new THREE.BoxGeometry(0.019, 0.0085, 0.018);
  const backingSegGeo = new THREE.BoxGeometry(0.040, 0.018, 0.014);
  for (let i = 0; i < 33; i++) {
    const ty = 0.495 + i * 0.0155;
    const zSurf = torsoFrontZ(ty, 0);
    const side = (i % 2 === 0) ? -0.007 : 0.007;

    const backSeg = new THREE.Mesh(backingSegGeo, materials.seamDark);
    backSeg.position.set(0, ty, zSurf - 0.003);
    zipperGroup.add(backSeg);

    const tooth = new THREE.Mesh(toothGeo, materials.metalZipper);
    tooth.position.set(side, ty, zSurf + 0.003);
    zipperGroup.add(tooth);
  }

  // Metal Zipper Slider Body & Pull Tab embedded cleanly at the collar (y = 0.95 .. 1.01)
  const zCollar = torsoFrontZ(0.985, 0);
  const sliderBody = new THREE.Mesh(new THREE.BoxGeometry(0.050, 0.058, 0.036), materials.metalZipper);
  sliderBody.position.set(0, 0.990, zCollar + 0.006);
  sliderBody.rotation.x = -0.22;
  zipperGroup.add(sliderBody);

  const sliderBridge = new THREE.Mesh(new THREE.TorusGeometry(0.015, 0.005, 10, 18), materials.metalZipper);
  sliderBridge.position.set(0, 0.982, zCollar + 0.022);
  sliderBridge.rotation.y = Math.PI / 2;
  zipperGroup.add(sliderBridge);

  const pullTab = new THREE.Mesh(new THREE.BoxGeometry(0.034, 0.062, 0.014), materials.metalZipper);
  pullTab.position.set(0, 0.948, zCollar + 0.026);
  pullTab.rotation.x = -0.10;
  zipperGroup.add(pullTab);

  // Skull Pendant Group (pivots at y = 0.925, hugging the chest contour)
  const zChest = torsoFrontZ(0.80, 0);
  const skullPendantGroup = new THREE.Group();
  skullPendantGroup.name = 'Skull_Pendant_Group';
  skullPendantGroup.position.set(0, 0.925, zChest + 0.008);
  // Tilt slightly to match upper chest slope so there is zero gap in side profile
  skullPendantGroup.rotation.x = -0.08;
  torsoGroup.add(skullPendantGroup);

  // White top attachment loop on skull charm
  const skullLoop = new THREE.Mesh(new THREE.BoxGeometry(0.042, 0.040, 0.024), materials.skullWhite);
  skullLoop.position.set(0, -0.010, -0.004);
  skullPendantGroup.add(skullLoop);

  // Exact 2D contour of Baba Chops' Skull Charm extruded in 3D with smooth bevel
  const skullShape = new THREE.Shape();
  skullShape.moveTo(0, -0.025);
  skullShape.bezierCurveTo(0.095, -0.025, 0.156, -0.075, 0.156, -0.145);
  skullShape.bezierCurveTo(0.156, -0.195, 0.124, -0.222, 0.100, -0.232);
  skullShape.lineTo(0.100, -0.272);
  skullShape.quadraticCurveTo(0.100, -0.292, 0.076, -0.292);
  skullShape.quadraticCurveTo(0.052, -0.292, 0.050, -0.276);
  skullShape.quadraticCurveTo(0.048, -0.295, 0.025, -0.295);
  skullShape.quadraticCurveTo(0.002, -0.295, 0.0, -0.278);
  skullShape.quadraticCurveTo(-0.002, -0.295, -0.025, -0.295);
  skullShape.quadraticCurveTo(-0.048, -0.295, -0.050, -0.276);
  skullShape.quadraticCurveTo(-0.052, -0.292, -0.076, -0.292);
  skullShape.quadraticCurveTo(-0.100, -0.292, -0.100, -0.272);
  skullShape.lineTo(-0.100, -0.232);
  skullShape.bezierCurveTo(-0.124, -0.222, -0.156, -0.195, -0.156, -0.145);
  skullShape.bezierCurveTo(-0.156, -0.075, -0.095, -0.025, 0, -0.025);

  const skullExtrude = new THREE.ExtrudeGeometry(skullShape, {
    depth: 0.026,
    bevelEnabled: true,
    bevelSegments: 5,
    steps: 1,
    bevelSize: 0.010,
    bevelThickness: 0.010
  });
  skullExtrude.center();
  const skullMesh = new THREE.Mesh(skullExtrude, materials.skullWhite);
  skullMesh.position.set(0, -0.158, 0.0);
  skullMesh.castShadow = true;
  skullPendantGroup.add(skullMesh);

  // Skull Left & Right Angled Black Oval Eyes
  const skullEyeGeo = new THREE.CylinderGeometry(0.041, 0.041, 0.016, 24);
  skullEyeGeo.scale(1.18, 1.0, 0.88);
  const skullEyeL = new THREE.Mesh(skullEyeGeo, materials.skullCutout);
  skullEyeL.rotation.x = Math.PI / 2;
  skullEyeL.rotation.z = 0.28;
  skullEyeL.position.set(-0.062, -0.148, 0.016);
  skullPendantGroup.add(skullEyeL);

  const skullEyeR = new THREE.Mesh(skullEyeGeo, materials.skullCutout);
  skullEyeR.rotation.x = Math.PI / 2;
  skullEyeR.rotation.z = -0.28;
  skullEyeR.position.set(0.062, -0.148, 0.016);
  skullPendantGroup.add(skullEyeR);

  // Skull Central Inverted-Teardrop Black Nose Hole
  const noseShape = new THREE.Shape();
  noseShape.moveTo(0, 0.022);
  noseShape.quadraticCurveTo(0.018, -0.005, 0.014, -0.018);
  noseShape.quadraticCurveTo(0, -0.024, -0.014, -0.018);
  noseShape.quadraticCurveTo(-0.018, -0.005, 0, 0.022);
  const skullNoseGeo = new THREE.ExtrudeGeometry(noseShape, { depth: 0.012, bevelEnabled: false });
  const skullNose = new THREE.Mesh(skullNoseGeo, materials.skullCutout);
  skullNose.position.set(0, -0.198, 0.014);
  skullPendantGroup.add(skullNose);

  // Vertical tooth groove lines on lower skull jaw
  const grooveGeo = new THREE.CylinderGeometry(0.0026, 0.0026, 0.044, 8);
  [-0.047, 0.0, 0.047].forEach(gx => {
    const gr = new THREE.Mesh(grooveGeo, materials.seamDark);
    gr.position.set(gx, -0.264, 0.020);
    skullPendantGroup.add(gr);
  });

  // ============================================================================
  // 3. ARMS & OVERSIZED SOFT-GREY PLUSH HOOF-MITTENS (Splayed Outward at 42°)
  // ============================================================================
  function createArm(side) {
    const armGroup = new THREE.Group();
    armGroup.name = side < 0 ? 'Left_Arm_Group' : 'Right_Arm_Group';
    armGroup.position.set(side * 0.195, 0.955, 0.01);
    armGroup.rotation.z = side * 0.74;
    torsoGroup.add(armGroup);

    // Black plush upper sleeve
    const sleeveGeo = new THREE.CylinderGeometry(0.082, 0.105, 0.31, 24, 12);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, materials.blackPlush);
    sleeveMesh.position.set(0, -0.145, 0);
    sleeveMesh.castShadow = true;
    armGroup.add(sleeveMesh);

    const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.082, 20, 16), materials.blackPlush);
    armGroup.add(shoulderCap);

    // Oversized dove-grey plush hoof-mitten at wrist (with sculpted cloven indentation, no floating stick)
    const hoofGroup = new THREE.Group();
    hoofGroup.position.set(0, -0.345, 0.01);
    armGroup.add(hoofGroup);

    const mittenGeo = new THREE.SphereGeometry(0.116, 32, 24);
    const mPos = mittenGeo.attributes.position;
    for (let i = 0; i < mPos.count; i++) {
      let x = mPos.getX(i);
      let y = mPos.getY(i);
      let z = mPos.getZ(i);
      x *= 1.06;
      y *= 1.16;
      z *= 0.88;
      // Subtle sculpted cloven groove at the tip and front face
      if (y < -0.02) {
        const cleftFactor = Math.exp(-Math.pow(x / 0.022, 2)) * ((-y - 0.02) / 0.12);
        y += 0.016 * cleftFactor;
        if (z > 0) z -= 0.010 * cleftFactor;
      }
      mPos.setXYZ(i, x, y, z);
    }
    mittenGeo.computeVertexNormals();
    const mittenMesh = new THREE.Mesh(mittenGeo, materials.greyPlush);
    mittenMesh.castShadow = true;
    hoofGroup.add(mittenMesh);

    return armGroup;
  }

  const leftArmGroup = createArm(-1);
  const rightArmGroup = createArm(1);

  // ============================================================================
  // 4. LEGS & ROUNDED CLOVEN GREY FOOT HOOVES (A-Stance Standing on y = 0.0)
  // ============================================================================
  function createLeg(side) {
    const legGroup = new THREE.Group();
    legGroup.name = side < 0 ? 'Left_Leg_Group' : 'Right_Leg_Group';
    legGroup.position.set(side * 0.14, 0.50, 0.0);
    legGroup.rotation.z = side * 0.075;
    bodyRig.add(legGroup);

    const legGeo = new THREE.CylinderGeometry(0.094, 0.100, 0.34, 24, 10);
    const legMesh = new THREE.Mesh(legGeo, materials.blackPlush);
    legMesh.position.set(0, -0.17, 0);
    legMesh.castShadow = true;
    legGroup.add(legMesh);

    const footGeo = new THREE.SphereGeometry(0.116, 28, 22);
    const fPos = footGeo.attributes.position;
    for (let i = 0; i < fPos.count; i++) {
      let x = fPos.getX(i);
      let y = fPos.getY(i);
      let z = fPos.getZ(i);
      x *= 1.05;
      z *= 1.15;
      if (y < 0) y *= 0.72;
      else y *= 0.92;
      fPos.setXYZ(i, x, y, z);
    }
    footGeo.computeVertexNormals();
    const footMesh = new THREE.Mesh(footGeo, materials.greyPlush);
    footMesh.position.set(0, -0.405, 0.02);
    footMesh.rotation.z = -side * 0.075;
    footMesh.castShadow = true;
    footMesh.receiveShadow = true;
    legGroup.add(footMesh);

    return legGroup;
  }

  const leftLegGroup = createLeg(-1);
  const rightLegGroup = createLeg(1);

  // ============================================================================
  // 5. HEAD, FLUFFY BLACK SHERPA WOOL CROWN, EARS, EYES, MUZZLE & BUCK TEETH
  // ============================================================================
  const headGroup = new THREE.Group();
  headGroup.name = 'Head_Group';
  headGroup.position.set(0, 1.06, 0);
  bodyRig.add(headGroup);

  // Helper to project any (x, y) point onto the exact front ellipsoid surface of headCore
  const HEAD_RX = 0.465, HEAD_RY = 0.425, HEAD_RZ = 0.415, HEAD_CY = 0.44;
  function headFrontZ(x, y) {
    const nx = x / HEAD_RX;
    const ny = (y - HEAD_CY) / HEAD_RY;
    const r2 = nx * nx + ny * ny;
    if (r2 >= 0.96) return HEAD_RZ * 0.20;
    return HEAD_RZ * Math.sqrt(1.0 - r2);
  }

  // Base Black Plush Head Sphere
  const headCoreGeo = new THREE.SphereGeometry(1, 44, 36);
  headCoreGeo.scale(HEAD_RX, HEAD_RY, HEAD_RZ);
  const headCore = new THREE.Mesh(headCoreGeo, materials.blackWool);
  headCore.position.set(0, HEAD_CY, 0);
  headCore.castShadow = true;
  headGroup.add(headCore);

  // Dense Sculpted Black Sherpa Wool Crown, Overhanging Bangs, Temples & Full Back Fleece
  const woolGroup = new THREE.Group();
  woolGroup.name = 'Wool_Crown_And_Bangs_Group';
  headGroup.add(woolGroup);

  const woolTufts = [
    // High central wool crown (creates the rounded dome top silhouette in 121_BabaChopsPlush1.webp)
    [0.00, 0.83, 0.04, 0.18, 0.14, 0.18],
    [-0.14, 0.80, 0.05, 0.16, 0.13, 0.16],
    [0.14, 0.80, 0.05, 0.16, 0.13, 0.16],
    [-0.26, 0.74, 0.04, 0.15, 0.13, 0.15],
    [0.26, 0.74, 0.04, 0.15, 0.13, 0.15],
    [0.00, 0.78, -0.12, 0.22, 0.15, 0.18],
    [-0.20, 0.74, -0.10, 0.18, 0.14, 0.17],
    [0.20, 0.74, -0.10, 0.18, 0.14, 0.17],
    // Thick, fluffy bangs overhanging the upper forehead & dipping into the V-brow between the eyelids
    [0.00, 0.67, 0.27, 0.135, 0.12, 0.14],
    [-0.11, 0.67, 0.27, 0.13, 0.12, 0.135],
    [0.11, 0.67, 0.27, 0.13, 0.12, 0.135],
    [-0.22, 0.65, 0.24, 0.135, 0.12, 0.135],
    [0.22, 0.65, 0.24, 0.135, 0.12, 0.135],
    [-0.33, 0.61, 0.18, 0.135, 0.12, 0.135],
    [0.33, 0.61, 0.18, 0.135, 0.12, 0.135],
    [-0.41, 0.54, 0.11, 0.125, 0.115, 0.125],
    [0.41, 0.54, 0.11, 0.125, 0.115, 0.125],
    // Central V-brow fur tufts dipping between the two angled grey eyelids (signature #121 look)
    [0.00, 0.555, 0.365, 0.072, 0.075, 0.072],
    [-0.055, 0.585, 0.352, 0.076, 0.072, 0.075],
    [0.055, 0.585, 0.352, 0.076, 0.072, 0.075],
    [-0.15, 0.615, 0.325, 0.085, 0.075, 0.082],
    [0.15, 0.615, 0.325, 0.085, 0.075, 0.082],
    [-0.26, 0.59, 0.275, 0.085, 0.075, 0.082],
    [0.26, 0.59, 0.275, 0.085, 0.075, 0.082],
    // Fuzzy side cheeks & lower jaw framing around the wide grey mouth rim
    [-0.43, 0.31, 0.10, 0.11, 0.12, 0.12],
    [0.43, 0.31, 0.10, 0.11, 0.12, 0.12],
    [-0.40, 0.19, 0.10, 0.11, 0.11, 0.12],
    [0.40, 0.19, 0.10, 0.11, 0.11, 0.12],
    [-0.33, 0.09, 0.09, 0.11, 0.10, 0.11],
    [0.33, 0.09, 0.09, 0.11, 0.10, 0.11],
    [-0.21, 0.03, 0.08, 0.11, 0.09, 0.11],
    [0.21, 0.03, 0.08, 0.11, 0.09, 0.11],
    // Side & Back of head wool puffs so 3/4, Side Profile & Back views have rich curly sheep fleece
    [-0.36, 0.62, -0.08, 0.15, 0.14, 0.15],
    [0.36, 0.62, -0.08, 0.15, 0.14, 0.15],
    [-0.38, 0.44, -0.14, 0.15, 0.14, 0.15],
    [0.38, 0.44, -0.14, 0.15, 0.14, 0.15],
    [-0.34, 0.26, -0.14, 0.14, 0.13, 0.14],
    [0.34, 0.26, -0.14, 0.14, 0.13, 0.14],
    [0.00, 0.64, -0.28, 0.20, 0.17, 0.16],
    [-0.22, 0.58, -0.26, 0.18, 0.16, 0.16],
    [0.22, 0.58, -0.26, 0.18, 0.16, 0.16],
    [0.00, 0.44, -0.34, 0.21, 0.18, 0.16],
    [-0.22, 0.38, -0.30, 0.18, 0.16, 0.16],
    [0.22, 0.38, -0.30, 0.18, 0.16, 0.16],
    [0.00, 0.24, -0.30, 0.19, 0.15, 0.15]
  ];

  const baseTuftGeo = new THREE.SphereGeometry(1, 20, 16);
  const bPos = baseTuftGeo.attributes.position;
  for (let i = 0; i < bPos.count; i++) {
    const vx = bPos.getX(i);
    const vy = bPos.getY(i);
    const vz = bPos.getZ(i);
    const disp = 1.0 + 0.07 * Math.sin(vx * 7.0) * Math.cos(vy * 7.0) * Math.sin(vz * 7.0);
    bPos.setXYZ(i, vx * disp, vy * disp, vz * disp);
  }
  baseTuftGeo.computeVertexNormals();

  woolTufts.forEach(([tx, ty, tz, sx, sy, sz]) => {
    const m = new THREE.Mesh(baseTuftGeo, materials.blackWool);
    m.position.set(tx, ty, tz);
    m.scale.set(sx, sy, sz);
    m.castShadow = true;
    woolGroup.add(m);
  });

  // ============================================================================
  // 6. CUPPED HORIZONTAL LIGHT-GREY SHEEP EARS (Left & Right at y_local = 0.425)
  // ============================================================================
  function createSheepEar(side) {
    const earGroup = new THREE.Group();
    earGroup.name = side < 0 ? 'Left_Ear_Group' : 'Right_Ear_Group';
    earGroup.position.set(side * 0.465, 0.425, 0.04);
    earGroup.rotation.z = side * -0.12;
    earGroup.rotation.y = side * -0.06;
    headGroup.add(earGroup);

    const earGeo = new THREE.SphereGeometry(1, 28, 20);
    const ePos = earGeo.attributes.position;
    for (let i = 0; i < ePos.count; i++) {
      let x = ePos.getX(i);
      let y = ePos.getY(i);
      let z = ePos.getZ(i);
      x *= 0.155;
      y *= 0.064;
      z *= 0.072;
      const distOut = Math.max(0, side * x / 0.155);
      y -= 0.018 * distOut * distOut;
      if (z > 0) {
        const cup = Math.exp(-Math.pow(y / 0.042, 2)) * Math.sin(distOut * Math.PI) * 0.028;
        z -= cup;
      }
      ePos.setXYZ(i, x + side * 0.105, y, z);
    }
    earGeo.computeVertexNormals();
    const earMesh = new THREE.Mesh(earGeo, materials.greyPlush);
    earMesh.castShadow = true;
    earGroup.add(earMesh);

    const innerGeo = new THREE.SphereGeometry(1, 20, 14);
    innerGeo.scale(0.098, 0.032, 0.024);
    const innerMesh = new THREE.Mesh(innerGeo, materials.greyInnerEar);
    innerMesh.position.set(side * 0.115, -0.005, 0.046);
    innerMesh.rotation.z = side * -0.08;
    earGroup.add(innerMesh);

    return earGroup;
  }

  const leftEarGroup = createSheepEar(-1);
  const rightEarGroup = createSheepEar(1);

  // ============================================================================
  // 7. ANGLED GREY PLUSH EYELIDS, CENTRAL BRIDGE & LARGE JET-BLACK DOME EYES
  // ============================================================================
  const eyesGroup = new THREE.Group();
  eyesGroup.name = 'Eyes_And_Eyelids_Group';
  headGroup.add(eyesGroup);

  // Central grey plush bridge between the lower-inner corners of the eyes (matches #121)
  const noseBridgeGeo = new THREE.SphereGeometry(1, 20, 16);
  noseBridgeGeo.scale(0.052, 0.044, 0.045);
  const noseBridge = new THREE.Mesh(noseBridgeGeo, materials.greyEyelid);
  noseBridge.position.set(0, 0.445, headFrontZ(0, 0.445) - 0.01);
  eyesGroup.add(noseBridge);

  function createEyeAssembly(side) {
    const ex = side * 0.145;
    const ey = 0.478;
    const ez = headFrontZ(ex, ey) - 0.015;

    const eyeWrap = new THREE.Group();
    eyeWrap.position.set(ex, ey, ez);
    eyeWrap.rotation.y = side * 0.22;
    eyesGroup.add(eyeWrap);

    // Subtle grey plush socket ring around the eye dome (visible on inner/outer corners in #121)
    const socketGeo = new THREE.SphereGeometry(0.098, 28, 20);
    socketGeo.scale(1.12, 1.02, 0.58);
    const socketMesh = new THREE.Mesh(socketGeo, materials.greyEyelid);
    socketMesh.position.set(0, 0, -0.008);
    eyeWrap.add(socketMesh);

    // Large Deep Jet-Black Glossy Acrylic Dome Eye (prominently visible below eyelid!)
    const eyeSphereGeo = new THREE.SphereGeometry(0.094, 36, 28);
    eyeSphereGeo.scale(1.06, 1.02, 0.72);
    const eyeMesh = new THREE.Mesh(eyeSphereGeo, materials.glossyEye);
    eyeWrap.add(eyeMesh);

    // Crisp vertical white oval catchlight reflection (matches studio softbox reflection in 121_BabaChopsPlush1.webp)
    const catchGeo = new THREE.SphereGeometry(1, 16, 12);
    catchGeo.scale(0.012, 0.033, 0.005);
    const catchMesh = new THREE.Mesh(catchGeo, materials.eyeHighlight);
    catchMesh.position.set(side * -0.015, -0.006, 0.066);
    eyeWrap.add(catchMesh);

    // Secondary tiny pin catchlight
    const catch2 = new THREE.Mesh(new THREE.SphereGeometry(0.005, 10, 8), materials.eyeHighlight);
    catch2.position.set(side * 0.022, -0.026, 0.063);
    eyeWrap.add(catch2);

    // Sculpted Grey Plush Spherical Hood Upper Eyelid (hugs the eyeball dome with zero flat-box protrusion in side view)
    const lidGeo = new THREE.SphereGeometry(0.104, 32, 20, 0, Math.PI * 2, 0, Math.PI * 0.50);
    const lPos = lidGeo.attributes.position;
    for (let i = 0; i < lPos.count; i++) {
      let lx = lPos.getX(i);
      let ly = lPos.getY(i);
      let lz = lPos.getZ(i);
      // Scale to match the eye dome and give a thick plush lower eyelid rim
      lx *= 1.08;
      ly *= 0.88;
      lz *= 0.78;
      // Add plush thickness along the bottom rim of the hood (near ly = 0)
      const rimFactor = Math.exp(-Math.pow(ly / 0.028, 2));
      if (lz > 0) {
        lz += 0.016 * rimFactor;
      }
      lPos.setXYZ(i, lx, ly, lz);
    }
    lidGeo.computeVertexNormals();
    const lidMesh = new THREE.Mesh(lidGeo, materials.greyEyelid);
    lidMesh.position.set(0, 0.006, 0.002);
    // Slant inward toward center bridge (~21 deg) soBaba Chops has her signature mischievous expression
    lidMesh.rotation.z = side * 0.36;
    lidMesh.rotation.x = -0.16;
    eyeWrap.add(lidMesh);
  }

  createEyeAssembly(-1);
  createEyeAssembly(1);

  // ============================================================================
  // 8. WIDE SCULPTED GREY PLUSH MUZZLE RIM, BLACK MOUTH CAVITY & TWIN BUCK TEETH
  //    (With full 3D Jaw Plush Volume so Side Profile is 100% solid & natural)
  // ============================================================================
  const jawGroup = new THREE.Group();
  jawGroup.name = 'Muzzle_And_Jaw_Group';
  headGroup.add(jawGroup);

  // Helper for upper & lower lip Y(t) and Z(t) where t in [-1, 1]
  function upperLipPoint(t) {
    const x = t * 0.415;
    const snoutArch = 0.024 * Math.exp(-Math.pow(t / 0.42, 2));
    const cheekLift = 0.032 * Math.pow(Math.abs(t), 1.5) * (1.0 - 0.30 * Math.pow(t, 4));
    const y = 0.368 + snoutArch + cheekLift - 0.036 * Math.pow(t, 6);
    const zBase = headFrontZ(x, y);
    const zSnout = 0.020 + 0.016 * Math.cos(t * (Math.PI * 0.46));
    return new THREE.Vector3(x, y, zBase + zSnout);
  }

  function lowerLipPoint(t) {
    const ang = t * (Math.PI * 0.49);
    const x = Math.sin(ang) * 0.415;
    const y = 0.365 - Math.cos(ang) * 0.328;
    const zBase = headFrontZ(x, y);
    const zArch = 0.018 + 0.010 * Math.cos(ang * 0.85);
    return new THREE.Vector3(x, y, zBase + zArch);
  }

  // Deep pitch-black recessed mouth cavity mesh conformed onto headFrontZ(x, y) + 0.006
  const cavityCols = 40;
  const cavityRows = 16;
  const cavPositions = [];
  const cavIndices = [];
  for (let r = 0; r <= cavityRows; r++) {
    const v = r / cavityRows; // 0 = lower lip, 1 = upper lip
    for (let c = 0; c <= cavityCols; c++) {
      const t = (c / cavityCols) * 2.0 - 1.0;
      const pLow = lowerLipPoint(t);
      const pUp = upperLipPoint(t);
      const x = THREE.MathUtils.lerp(pLow.x, pUp.x, v);
      const y = THREE.MathUtils.lerp(pLow.y, pUp.y, v);
      const z = headFrontZ(x, y) + 0.006;
      cavPositions.push(x, y, z);
    }
  }
  for (let r = 0; r < cavityRows; r++) {
    for (let c = 0; c < cavityCols; c++) {
      const a = r * (cavityCols + 1) + c;
      const b = a + 1;
      const d = (r + 1) * (cavityCols + 1) + c;
      const e = d + 1;
      cavIndices.push(a, b, d, b, e, d);
    }
  }
  const mouthPlateGeo = new THREE.BufferGeometry();
  mouthPlateGeo.setAttribute('position', new THREE.Float32BufferAttribute(cavPositions, 3));
  mouthPlateGeo.setIndex(cavIndices);
  mouthPlateGeo.computeVertexNormals();
  const mouthPlateMesh = new THREE.Mesh(mouthPlateGeo, materials.mouthCavity);
  jawGroup.add(mouthPlateMesh);

  // Solid Black Plush Lower-Jaw & Cheek Side-Wall Volume (bridges the mouth rim smoothly back into headCore)
  const jawWallPositions = [];
  const jawWallIndices = [];
  for (let r = 0; r <= 8; r++) {
    const u = r / 8; // 0 = along lowerLipPoint, 1 = tucked deep into headCore
    for (let c = 0; c <= cavityCols; c++) {
      const t = (c / cavityCols) * 2.0 - 1.0;
      const pLow = lowerLipPoint(t);
      const x = pLow.x * (1.0 - 0.12 * u);
      const y = pLow.y * (1.0 - 0.05 * u) + 0.12 * u;
      const z = THREE.MathUtils.lerp(pLow.z - 0.008, 0.08, u);
      jawWallPositions.push(x, y, z);
    }
  }
  for (let r = 0; r < 8; r++) {
    for (let c = 0; c < cavityCols; c++) {
      const a = r * (cavityCols + 1) + c;
      const b = a + 1;
      const d = (r + 1) * (cavityCols + 1) + c;
      const e = d + 1;
      jawWallIndices.push(a, d, b, b, d, e);
    }
  }
  const jawWallGeo = new THREE.BufferGeometry();
  jawWallGeo.setAttribute('position', new THREE.Float32BufferAttribute(jawWallPositions, 3));
  jawWallGeo.setIndex(jawWallIndices);
  jawWallGeo.computeVertexNormals();
  const jawWallMat = materials.blackWool.clone();
  jawWallMat.side = THREE.DoubleSide;
  const jawWallMesh = new THREE.Mesh(jawWallGeo, jawWallMat);
  jawGroup.add(jawWallMesh);

  // Continuous Variable-Thickness Upper Grey Plush Snout & Smiling Lip Rim
  const upperLipPts = [];
  for (let i = 0; i <= 40; i++) {
    upperLipPts.push(upperLipPoint((i / 40) * 2.0 - 1.0));
  }
  const upperLipCurve = new THREE.CatmullRomCurve3(upperLipPts);
  const upperLipGeo = new THREE.TubeGeometry(upperLipCurve, 60, 0.036, 24, false);
  // Swell the center of the upper lip into a smooth plush snout bridge and tuck back edge into headCore
  const ulPos = upperLipGeo.attributes.position;
  for (let i = 0; i < ulPos.count; i++) {
    const ux = ulPos.getX(i);
    let uy = ulPos.getY(i);
    let uz = ulPos.getZ(i);
    const centerFactor = Math.exp(-Math.pow(ux / 0.18, 2));
    if (uy > 0.375) {
      uy += (uy - 0.375) * 0.42 * centerFactor;
    }
    // Pull back-facing vertices slightly inward (-Z) so the lip tube blends solidly into the head plush
    const zSurf = headFrontZ(ux, uy);
    if (uz < zSurf + 0.025) {
      uz -= 0.035;
    }
    ulPos.setXYZ(i, ux, uy, uz);
  }
  upperLipGeo.computeVertexNormals();
  const upperLipMesh = new THREE.Mesh(upperLipGeo, materials.greyPlush);
  upperLipMesh.castShadow = true;
  jawGroup.add(upperLipMesh);

  // Two tiny dark embroidered nostrils nestled on the upper slope of the grey snout lip
  const nostrilGeo = new THREE.SphereGeometry(1, 14, 10);
  nostrilGeo.scale(0.011, 0.005, 0.007);
  const pCenterSnout = upperLipPoint(0);
  const nostrilL = new THREE.Mesh(nostrilGeo, materials.skullCutout);
  nostrilL.position.set(-0.046, pCenterSnout.y + 0.042, pCenterSnout.z + 0.024);
  nostrilL.rotation.z = 0.15;
  nostrilL.rotation.x = -0.35;
  jawGroup.add(nostrilL);

  const nostrilR = new THREE.Mesh(nostrilGeo, materials.skullCutout);
  nostrilR.position.set(0.046, pCenterSnout.y + 0.042, pCenterSnout.z + 0.024);
  nostrilR.rotation.z = -0.15;
  nostrilR.rotation.x = -0.35;
  jawGroup.add(nostrilR);

  // Lower Grey Plush Lip Deep U-Curve
  const lowerLipPts = [];
  for (let i = 0; i <= 40; i++) {
    lowerLipPts.push(lowerLipPoint((i / 40) * 2.0 - 1.0));
  }
  const lowerLipCurve = new THREE.CatmullRomCurve3(lowerLipPts);
  const lowerLipGeo = new THREE.TubeGeometry(lowerLipCurve, 56, 0.033, 20, false);
  // Tuck back-facing vertices of lower lip into the chin/jaw plush so side profile is 100% solid
  const llPos = lowerLipGeo.attributes.position;
  for (let i = 0; i < llPos.count; i++) {
    const lx = llPos.getX(i);
    const ly = llPos.getY(i);
    let lz = llPos.getZ(i);
    const zSurf = headFrontZ(lx, ly);
    if (lz < zSurf + 0.020) {
      lz -= 0.040;
    }
    llPos.setXYZ(i, lx, ly, lz);
  }
  lowerLipGeo.computeVertexNormals();
  const lowerLipMesh = new THREE.Mesh(lowerLipGeo, materials.greyPlush);
  lowerLipMesh.castShadow = true;
  jawGroup.add(lowerLipMesh);

  // Rounded Cheek Corner Caps where upper and lower lips meet
  [-1, 1].forEach(side => {
    const pCorner = upperLipPoint(side);
    const cornerCap = new THREE.Mesh(new THREE.SphereGeometry(0.040, 18, 14), materials.greyPlush);
    cornerCap.position.copy(pCorner);
    jawGroup.add(cornerCap);
  });

  // Twin Rounded Light-Grey Plush Buck Teeth (hanging from center of upper lip)
  function createBuckTooth(side) {
    const toothShape = new THREE.Shape();
    toothShape.moveTo(-0.047, 0.084);
    toothShape.lineTo(0.047, 0.084);
    toothShape.lineTo(0.047, -0.024);
    toothShape.quadraticCurveTo(0.047, -0.078, 0.0, -0.080);
    toothShape.quadraticCurveTo(-0.047, -0.078, -0.047, -0.024);
    toothShape.closePath();

    const tGeo = new THREE.ExtrudeGeometry(toothShape, {
      depth: 0.024,
      bevelEnabled: true,
      bevelSegments: 5,
      steps: 1,
      bevelSize: 0.011,
      bevelThickness: 0.011
    });
    tGeo.center();
    const tMesh = new THREE.Mesh(tGeo, materials.greyTeeth);
    // Align buck teeth tangent to headFrontZ(0, y) between y = 0.36 and y = 0.21
    const zTooth = headFrontZ(0, 0.285) + 0.018;
    tMesh.position.set(side * 0.055, 0.285, zTooth);
    tMesh.rotation.y = side * 0.06;
    tMesh.rotation.x = -0.34;
    tMesh.castShadow = true;
    return tMesh;
  }

  jawGroup.add(createBuckTooth(-1));
  jawGroup.add(createBuckTooth(1));

  // Stitched vertical groove between the two buck teeth
  const toothSeam = new THREE.Mesh(
    new THREE.CylinderGeometry(0.0042, 0.0042, 0.155, 10),
    materials.seamDark
  );
  toothSeam.position.set(0, 0.288, headFrontZ(0, 0.288) + 0.031);
  toothSeam.rotation.x = -0.34;
  jawGroup.add(toothSeam);

  return {
    root,
    bodyRig,
    torsoGroup,
    headGroup,
    woolGroup,
    leftEarGroup,
    rightEarGroup,
    eyesGroup,
    jawGroup,
    leftArmGroup,
    rightArmGroup,
    leftLegGroup,
    rightLegGroup,
    skullPendantGroup,
    materials
  };
}
