/**
 * KickinChicken 3D Plush Base Model Generator (Three.js r161 ESM)
 * ============================================================================
 * 1:1 High-Precision 3D Plush Recreation of `images/053_KickinChicken.webp`
 * Smiling Critters — KickinChicken Plush Rig + 3-Stage 3D Fart Blast Cloud
 */

function createPlushBumpTexture(THREE, mode = 'plush') {
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
      if (mode === 'feather') {
        const c1 = Math.sin(nx * Math.PI * 18) * Math.cos(ny * Math.PI * 18);
        const c2 = Math.sin((nx + ny) * Math.PI * 32) * Math.cos((nx - ny) * Math.PI * 32);
        const hash = Math.sin((x * 12.9898 + y * 78.233)) * 43758.5453;
        const grain = (hash - Math.floor(hash)) - 0.5;
        v = Math.max(0, Math.min(255, Math.floor(128 + 46 * c1 + 28 * c2 + 24 * grain)));
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
  tex.repeat.set(mode === 'feather' ? 4 : 6, mode === 'feather' ? 4 : 6);
  return tex;
}

export function buildKickinChickenPlushModel(THREE) {
  const root = new THREE.Group();
  root.name = 'KickinChicken_Plush_BaseModel';

  const bodyRig = new THREE.Group();
  bodyRig.name = 'Body_Rig_Root';
  root.add(bodyRig);

  const featherBump = createPlushBumpTexture(THREE, 'feather');
  const velourBump = createPlushBumpTexture(THREE, 'velour');

  const materials = {
    yellowPlush: new THREE.MeshStandardMaterial({
      name: 'Kickin_Yellow_Plush_Fleece',
      color: 0xf5b700,
      roughness: 0.82,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.009
    }),
    yellowCrest: new THREE.MeshStandardMaterial({
      name: 'Kickin_Crest_Feather_Yellow',
      color: 0xfacc15,
      roughness: 0.78,
      metalness: 0.03,
      bumpMap: featherBump,
      bumpScale: 0.011
    }),
    bellyCream: new THREE.MeshStandardMaterial({
      name: 'Kickin_Cream_Belly_Patch',
      color: 0xfef08a,
      roughness: 0.80,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.007
    }),
    beakOrange: new THREE.MeshStandardMaterial({
      name: 'Kickin_Beak_And_Feet_Orange',
      color: 0xea580c,
      roughness: 0.72,
      metalness: 0.03,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    tonguePink: new THREE.MeshStandardMaterial({
      name: 'Kickin_Tongue_Pink',
      color: 0xf43f5e,
      roughness: 0.76,
      metalness: 0.02
    }),
    starGold: new THREE.MeshStandardMaterial({
      name: 'Kickin_Golden_Star_Pendant',
      color: 0xf59e0b,
      emissive: 0xd97706,
      emissiveIntensity: 0.14,
      roughness: 0.25,
      metalness: 0.68
    }),
    mouthCavity: new THREE.MeshBasicMaterial({
      name: 'Kickin_Recessed_Mouth_Void',
      color: 0x050507,
      side: THREE.DoubleSide
    }),
    glossyEye: new THREE.MeshPhysicalMaterial({
      name: 'Kickin_Glossy_Black_Eye',
      color: 0x030306,
      roughness: 0.06,
      metalness: 0.0,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04,
      reflectivity: 0.95
    }),
    eyeHighlight: new THREE.MeshBasicMaterial({
      name: 'Kickin_White_Oval_Pupil',
      color: 0xffffff
    }),
    metalZipper: new THREE.MeshStandardMaterial({
      name: 'Kickin_Silver_Zipper_Hardware',
      color: 0xd8dde6,
      roughness: 0.24,
      metalness: 0.84
    }),
    seamDark: new THREE.MeshStandardMaterial({
      name: 'Kickin_Collar_Zipper_Dark',
      color: 0x101116,
      roughness: 0.88,
      metalness: 0.04
    }),
    fartLime: new THREE.MeshStandardMaterial({
      name: 'Kickin_Fart_Cloud_Lime',
      color: 0x4ce629,
      emissive: 0x228b12,
      emissiveIntensity: 0.35,
      roughness: 0.65,
      metalness: 0.02,
      bumpMap: featherBump,
      bumpScale: 0.015
    }),
    fartNeon: new THREE.MeshStandardMaterial({
      name: 'Kickin_Fart_Cloud_Neon_YellowGreen',
      color: 0xc4ff33,
      emissive: 0x84cc16,
      emissiveIntensity: 0.50,
      roughness: 0.45,
      metalness: 0.05
    }),
    fartPurple: new THREE.MeshStandardMaterial({
      name: 'Kickin_Fart_Cloud_Nightmare_Purple',
      color: 0x9d4edd,
      emissive: 0x5b21b6,
      emissiveIntensity: 0.35,
      roughness: 0.60,
      metalness: 0.04
    })
  };

  function torsoFrontZ(yWorld, xWorld = 0) {
    const yn = Math.max(-1, Math.min(1, (yWorld - 0.755) / 0.325));
    const widthP = 0.285 * (1.0 - 0.24 * yn - 0.10 * yn * yn);
    const depthP = 0.245 * (1.0 - 0.20 * yn - 0.08 * yn * yn);
    const xRatio = Math.min(0.95, Math.abs(xWorld) / Math.max(0.05, widthP));
    const zHoriz = Math.sqrt(Math.max(0.01, 1.0 - yn * yn)) * Math.sqrt(Math.max(0.01, 1.0 - xRatio * xRatio));
    return depthP * zHoriz;
  }

  // ============================================================================
  // 1. TORSO (Pear-Shaped Golden-Yellow Plush Body + Cream Belly Patch)
  // ============================================================================
  const torsoGroup = new THREE.Group();
  torsoGroup.name = 'Torso_And_Zipper_Group';
  bodyRig.add(torsoGroup);

  const torsoGeo = new THREE.SphereGeometry(1, 44, 36);
  const tPos = torsoGeo.attributes.position;
  for (let i = 0; i < tPos.count; i++) {
    const x = tPos.getX(i);
    const y = tPos.getY(i);
    const z = tPos.getZ(i);
    const widthProfile = 0.285 * (1.0 - 0.24 * y - 0.10 * y * y);
    const depthProfile = 0.245 * (1.0 - 0.20 * y - 0.08 * y * y);
    const rx = x * widthProfile;
    const ry = 0.755 + y * 0.325;
    let rz = z * depthProfile;
    if (rz > 0 && Math.abs(rx) < 0.036) {
      rz -= (1.0 - Math.abs(rx) / 0.036) * 0.008;
    }
    tPos.setXYZ(i, rx, ry, rz);
  }
  torsoGeo.computeVertexNormals();
  const torsoMesh = new THREE.Mesh(torsoGeo, materials.yellowPlush);
  torsoMesh.castShadow = true;
  torsoMesh.receiveShadow = true;
  torsoGroup.add(torsoMesh);

  // Warm Cream-Yellow Belly Patch (#FEF08A)
  const bellyGeo = new THREE.SphereGeometry(1, 32, 24);
  const bPos = bellyGeo.attributes.position;
  for (let i = 0; i < bPos.count; i++) {
    const x = bPos.getX(i) * 0.185;
    const y = 0.745 + bPos.getY(i) * 0.215;
    const z = bPos.getZ(i);
    const zSurf = torsoFrontZ(y, x);
    const rz = z > 0 ? zSurf + 0.006 * z : zSurf - 0.015;
    bPos.setXYZ(i, x, y, rz);
  }
  bellyGeo.computeVertexNormals();
  const bellyMesh = new THREE.Mesh(bellyGeo, materials.bellyCream);
  torsoGroup.add(bellyMesh);

  // ============================================================================
  // 2. BLACK COLLAR, ZIPPER TRACK & ICONIC GOLDEN 5-POINTED STAR PENDANT
  // ============================================================================
  const zipperGroup = new THREE.Group();
  zipperGroup.name = 'Zipper_Hardware_Group';
  torsoGroup.add(zipperGroup);

  const collarRing = new THREE.Mesh(
    new THREE.TorusGeometry(0.185, 0.016, 12, 32),
    materials.seamDark
  );
  collarRing.position.set(0, 1.03, 0.0);
  collarRing.rotation.x = Math.PI / 2 + 0.08;
  zipperGroup.add(collarRing);

  const toothGeo = new THREE.BoxGeometry(0.019, 0.0085, 0.018);
  const backingSegGeo = new THREE.BoxGeometry(0.038, 0.018, 0.014);
  for (let i = 0; i < 31; i++) {
    const ty = 0.505 + i * 0.0155;
    const zSurf = torsoFrontZ(ty, 0);
    const side = (i % 2 === 0) ? -0.007 : 0.007;

    const backSeg = new THREE.Mesh(backingSegGeo, materials.seamDark);
    backSeg.position.set(0, ty, zSurf - 0.001);
    zipperGroup.add(backSeg);

    const tooth = new THREE.Mesh(toothGeo, materials.metalZipper);
    tooth.position.set(side, ty, zSurf + 0.005);
    zipperGroup.add(tooth);
  }

  const zCollar = torsoFrontZ(0.985, 0);
  const sliderBody = new THREE.Mesh(new THREE.BoxGeometry(0.048, 0.054, 0.034), materials.metalZipper);
  sliderBody.position.set(0, 0.990, zCollar + 0.008);
  sliderBody.rotation.x = -0.20;
  zipperGroup.add(sliderBody);

  // Golden 5-Pointed Star Pendant Group (pivots at y = 0.925)
  const zChest = torsoFrontZ(0.80, 0);
  const skullPendantGroup = new THREE.Group();
  skullPendantGroup.name = 'Star_Pendant_Group';
  skullPendantGroup.position.set(0, 0.925, zChest + 0.012);
  skullPendantGroup.rotation.x = -0.08;
  torsoGroup.add(skullPendantGroup);

  const bailLoop = new THREE.Mesh(new THREE.BoxGeometry(0.036, 0.042, 0.022), materials.metalZipper);
  bailLoop.position.set(0, -0.012, 0.0);
  skullPendantGroup.add(bailLoop);

  function createFivePointStarShape(rOuter, rInner) {
    const shape = new THREE.Shape();
    for (let i = 0; i < 10; i++) {
      const ang = Math.PI / 2 + i * (Math.PI / 5);
      const r = (i % 2 === 0) ? rOuter : rInner;
      const px = Math.cos(ang) * r;
      const py = Math.sin(ang) * r;
      if (i === 0) shape.moveTo(px, py);
      else shape.lineTo(px, py);
    }
    shape.closePath();
    return shape;
  }

  const starOutlineGeo = new THREE.ExtrudeGeometry(createFivePointStarShape(0.145, 0.066), {
    depth: 0.018,
    bevelEnabled: true,
    bevelSegments: 3,
    steps: 1,
    bevelSize: 0.008,
    bevelThickness: 0.008
  });
  starOutlineGeo.center();
  const starOutlineMesh = new THREE.Mesh(starOutlineGeo, materials.seamDark);
  starOutlineMesh.position.set(0, -0.145, -0.004);
  skullPendantGroup.add(starOutlineMesh);

  const starGoldGeo = new THREE.ExtrudeGeometry(createFivePointStarShape(0.130, 0.058), {
    depth: 0.024,
    bevelEnabled: true,
    bevelSegments: 4,
    steps: 1,
    bevelSize: 0.009,
    bevelThickness: 0.009
  });
  starGoldGeo.center();
  const starGoldMesh = new THREE.Mesh(starGoldGeo, materials.starGold);
  starGoldMesh.position.set(0, -0.145, 0.004);
  starGoldMesh.castShadow = true;
  skullPendantGroup.add(starGoldMesh);

  // ============================================================================
  // 3. FEATHERED WING-ARMS (With 3 Wing-Tip Feather Fingers on Hands)
  // ============================================================================
  function createWingArm(side) {
    const armGroup = new THREE.Group();
    armGroup.name = side < 0 ? 'Left_Arm_Group' : 'Right_Arm_Group';
    armGroup.position.set(side * 0.195, 0.955, 0.01);
    armGroup.rotation.z = side * 0.72;
    torsoGroup.add(armGroup);

    const sleeveGeo = new THREE.CylinderGeometry(0.080, 0.102, 0.30, 24, 10);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, materials.yellowPlush);
    sleeveMesh.position.set(0, -0.14, 0);
    sleeveMesh.castShadow = true;
    armGroup.add(sleeveMesh);

    const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.080, 18, 14), materials.yellowPlush);
    armGroup.add(shoulderCap);

    const wingHandGroup = new THREE.Group();
    wingHandGroup.position.set(0, -0.32, 0.01);
    armGroup.add(wingHandGroup);

    const palmGeo = new THREE.SphereGeometry(0.102, 24, 18);
    palmGeo.scale(1.04, 1.08, 0.84);
    const palmMesh = new THREE.Mesh(palmGeo, materials.yellowPlush);
    palmMesh.castShadow = true;
    wingHandGroup.add(palmMesh);

    // 3 Feathered Wing-Tips at the end of each hand
    [-0.32, 0.0, 0.32].forEach((ang, idx) => {
      const featherTipGeo = new THREE.SphereGeometry(0.042, 16, 12);
      featherTipGeo.scale(0.85, 2.15, 0.68);
      const featherTip = new THREE.Mesh(featherTipGeo, materials.yellowCrest);
      featherTip.position.set(Math.sin(ang) * 0.068, -0.095 - (idx === 1 ? 0.018 : 0), (idx - 1) * 0.014);
      featherTip.rotation.z = ang * 0.65;
      featherTip.castShadow = true;
      wingHandGroup.add(featherTip);
    });

    return armGroup;
  }

  const leftArmGroup = createWingArm(-1);
  const rightArmGroup = createWingArm(1);

  // ============================================================================
  // 4. YELLOW UPPER LEGS, ORANGE LOWER SHINS & 3-TOED CHICKEN FEET
  // ============================================================================
  function createChickenLeg(side) {
    const legGroup = new THREE.Group();
    legGroup.name = side < 0 ? 'Left_Leg_Group' : 'Right_Leg_Group';
    legGroup.position.set(side * 0.145, 0.50, 0.0);
    legGroup.rotation.z = side * 0.075;
    bodyRig.add(legGroup);

    // Upper Yellow Plush Thigh
    const thighGeo = new THREE.CylinderGeometry(0.098, 0.092, 0.21, 24, 8);
    const thighMesh = new THREE.Mesh(thighGeo, materials.yellowPlush);
    thighMesh.position.set(0, -0.105, 0);
    thighMesh.castShadow = true;
    legGroup.add(thighMesh);

    // Lower Tangerine-Orange Shin
    const shinGeo = new THREE.CylinderGeometry(0.088, 0.084, 0.16, 22, 8);
    const shinMesh = new THREE.Mesh(shinGeo, materials.beakOrange);
    shinMesh.position.set(0, -0.285, 0.005);
    shinMesh.castShadow = true;
    legGroup.add(shinMesh);

    // Orange 3-Toed Chicken Foot Assembly
    const footWrap = new THREE.Group();
    footWrap.position.set(0, -0.415, 0.02);
    footWrap.rotation.z = -side * 0.075;
    legGroup.add(footWrap);

    const padGeo = new THREE.SphereGeometry(0.104, 24, 18);
    padGeo.scale(1.06, 0.72, 1.08);
    const padMesh = new THREE.Mesh(padGeo, materials.beakOrange);
    padMesh.castShadow = true;
    padMesh.receiveShadow = true;
    footWrap.add(padMesh);

    // 3 Forward Chicken Toes
    [-0.36, 0.0, 0.36].forEach((tAng, idx) => {
      const toeLen = idx === 1 ? 0.145 : 0.125;
      const toeGeo = new THREE.SphereGeometry(0.046, 18, 14);
      toeGeo.scale(0.92, 0.68, toeLen / 0.046);
      const toeMesh = new THREE.Mesh(toeGeo, materials.beakOrange);
      toeMesh.position.set(Math.sin(tAng) * 0.085, -0.022, 0.055 + Math.cos(tAng) * 0.055);
      toeMesh.rotation.y = tAng;
      toeMesh.castShadow = true;
      toeMesh.receiveShadow = true;
      footWrap.add(toeMesh);
    });

    return legGroup;
  }

  const leftLegGroup = createChickenLeg(-1);
  const rightLegGroup = createChickenLeg(1);

  // ============================================================================
  // 5. FEATHERED YELLOW ROOSTER TAIL (3 Upward-Curving Plumes on Pelvis)
  // ============================================================================
  const tailGroup = new THREE.Group();
  tailGroup.name = 'Feathered_Tail_Group';
  tailGroup.position.set(0, 0.60, -0.22);
  torsoGroup.add(tailGroup);

  [
    [0.00, 0.32, 0.095, 0.0],
    [-0.09, 0.24, 0.072, -0.22],
    [0.09, 0.24, 0.072, 0.22]
  ].forEach(([txOff, tHeight, tRad, yaw]) => {
    const pts = [];
    for (let k = 0; k <= 10; k++) {
      const u = k / 10;
      pts.push(new THREE.Vector3(
        txOff * (0.5 + 0.8 * u),
        tHeight * Math.pow(u, 1.2),
        -0.24 * Math.sin(0.65 * Math.PI * u)
      ));
    }
    const curve = new THREE.CatmullRomCurve3(pts);
    const tGeo = new THREE.TubeGeometry(curve, 20, tRad, 14, false);
    const pos = tGeo.attributes.position;
    for (let i = 0; i < pos.count; i++) {
      const py = pos.getY(i);
      const u = Math.max(0, Math.min(1, py / Math.max(0.05, tHeight)));
      const taper = Math.sin(Math.PI * (0.15 + 0.80 * u));
      pos.setX(i, pos.getX(i) * (0.5 + 0.5 * taper));
    }
    tGeo.computeVertexNormals();
    const tailPlume = new THREE.Mesh(tGeo, materials.yellowCrest);
    tailPlume.rotation.y = yaw;
    tailPlume.castShadow = true;
    tailGroup.add(tailPlume);
  });

  // ============================================================================
  // 6. HEAD, CHEEK FEATHER TUFTS & 3-TUFT YELLOW ROOSTER CREST FEATHERS
  // ============================================================================
  const headGroup = new THREE.Group();
  headGroup.name = 'Head_Group';
  headGroup.position.set(0, 1.06, 0);
  bodyRig.add(headGroup);

  const HEAD_RX = 0.455, HEAD_RY = 0.425, HEAD_RZ = 0.425, HEAD_CY = 0.44;
  function headFrontZ(x, y) {
    const nx = x / HEAD_RX;
    const ny = (y - HEAD_CY) / HEAD_RY;
    const r2 = nx * nx + ny * ny;
    if (r2 >= 0.96) return HEAD_RZ * 0.20;
    return HEAD_RZ * Math.sqrt(1.0 - r2);
  }

  const headCoreGeo = new THREE.SphereGeometry(1, 44, 36);
  headCoreGeo.scale(HEAD_RX, HEAD_RY, HEAD_RZ);
  const headCore = new THREE.Mesh(headCoreGeo, materials.yellowPlush);
  headCore.position.set(0, HEAD_CY, 0);
  headCore.castShadow = true;
  headGroup.add(headCore);

  // Cheek Feather Tufts (2 flared tufts on each cheek)
  const woolGroup = new THREE.Group();
  woolGroup.name = 'Cheek_And_Crest_Feathers_Group';
  headGroup.add(woolGroup);

  [-1, 1].forEach(side => {
    [
      [0.44, 0.46, 0.08, 0.14, 0.058, -0.28],
      [0.43, 0.37, 0.10, 0.12, 0.050, -0.42]
    ].forEach(([cx, cy, cz, len, rad, tiltZ]) => {
      const tuftGeo = new THREE.SphereGeometry(1, 18, 14);
      tuftGeo.scale(len, rad, rad * 0.72);
      const tuftMesh = new THREE.Mesh(tuftGeo, materials.yellowCrest);
      tuftMesh.position.set(side * cx, cy, cz);
      tuftMesh.rotation.z = side * tiltZ;
      tuftMesh.castShadow = true;
      woolGroup.add(tuftMesh);
    });
  });

  // Helper to build a plump tapered rooster crest plume along 3D curve points
  function buildRoosterPlumeMesh(pts, maxRadius) {
    const curve = new THREE.CatmullRomCurve3(pts.map(p => new THREE.Vector3(...p)));
    const geo = new THREE.TubeGeometry(curve, 28, maxRadius, 18, false);
    const pos = geo.attributes.position;
    const ringCount = 29;
    const radialSegs = 19;
    for (let r = 0; r < ringCount; r++) {
      const u = r / (ringCount - 1);
      const env = Math.sin(Math.PI * (0.10 + 0.86 * u)) * (1.0 - 0.18 * u);
      const center = curve.getPointAt(u);
      for (let j = 0; j < radialSegs; j++) {
        const idx = r * radialSegs + j;
        const vx = pos.getX(idx) - center.x;
        const vy = pos.getY(idx) - center.y;
        const vz = pos.getZ(idx) - center.z;
        pos.setXYZ(idx, center.x + vx * env, center.y + vy * env, center.z + vz * env * 0.65);
      }
    }
    geo.computeVertexNormals();
    const mesh = new THREE.Mesh(geo, materials.yellowCrest);
    mesh.castShadow = true;
    return mesh;
  }

  // LeftEarGroup (Viewer's Left / -X sweeping rooster crest plume + half of central dome plume)
  const leftEarGroup = new THREE.Group();
  leftEarGroup.name = 'Left_Crest_Feather_Group';
  leftEarGroup.position.set(-0.08, 0.80, 0.02);
  headGroup.add(leftEarGroup);

  const leftPlume = buildRoosterPlumeMesh([
    [0.05, 0.00, 0.02],
    [-0.12, 0.16, 0.02],
    [-0.30, 0.18, 0.01],
    [-0.45, 0.02, 0.00]
  ], 0.115);
  leftEarGroup.add(leftPlume);

  const centerPlume = buildRoosterPlumeMesh([
    [-0.08, 0.02, 0.00],
    [0.04, 0.25, 0.00],
    [0.18, 0.22, -0.01],
    [0.26, 0.06, -0.02]
  ], 0.128);
  leftEarGroup.add(centerPlume);

  // RightEarGroup (Viewer's Right / +X curved rooster crest plume)
  const rightEarGroup = new THREE.Group();
  rightEarGroup.name = 'Right_Crest_Feather_Group';
  rightEarGroup.position.set(0.10, 0.78, -0.01);
  headGroup.add(rightEarGroup);

  const rightPlume = buildRoosterPlumeMesh([
    [0.00, 0.00, 0.00],
    [0.18, 0.15, 0.00],
    [0.28, 0.08, -0.01],
    [0.26, -0.08, -0.02]
  ], 0.098);
  rightEarGroup.add(rightPlume);

  // ============================================================================
  // 7. EYES, LARGE WHITE OVAL PUPILS & CONFIDENT ARCHED ROOSTER BROWS
  // ============================================================================
  const eyesGroup = new THREE.Group();
  eyesGroup.name = 'Eyes_And_Brows_Group';
  headGroup.add(eyesGroup);

  function createRoosterEye(side) {
    const ex = side * 0.145;
    const ey = 0.505;
    const ez = headFrontZ(ex, ey) - 0.012;

    const eyeWrap = new THREE.Group();
    eyeWrap.position.set(ex, ey, ez);
    eyeWrap.rotation.y = side * 0.20;
    eyeWrap.rotation.z = -side * 0.08;
    eyesGroup.add(eyeWrap);

    const eyeGeo = new THREE.SphereGeometry(0.108, 32, 24);
    eyeGeo.scale(0.98, 1.18, 0.68);
    const eyeMesh = new THREE.Mesh(eyeGeo, materials.glossyEye);
    eyeWrap.add(eyeMesh);

    // Bold White Oval Pupil centered inside the black eye socket (053_KickinChicken.webp)
    const pupilGeo = new THREE.SphereGeometry(1, 20, 16);
    pupilGeo.scale(0.044, 0.065, 0.018);
    const pupilMesh = new THREE.Mesh(pupilGeo, materials.eyeHighlight);
    pupilMesh.position.set(-side * 0.008, -0.008, 0.066);
    eyeWrap.add(pupilMesh);

    // Confident Arched Rooster Eyebrow above the eye
    const browPts = [];
    for (let k = 0; k <= 12; k++) {
      const t = (k / 12) * 2.0 - 1.0;
      const bx = t * 0.108;
      const by = (side < 0)
        ? 0.145 + 0.036 * (1.0 - t * t) - 0.012 * t
        : 0.125 + 0.026 * (1.0 - t * t) + 0.032 * t;
      browPts.push(new THREE.Vector3(bx, by, 0.048));
    }
    const browCurve = new THREE.CatmullRomCurve3(browPts);
    const browMesh = new THREE.Mesh(
      new THREE.TubeGeometry(browCurve, 20, 0.011, 10, false),
      materials.seamDark
    );
    eyeWrap.add(browMesh);
  }

  createRoosterEye(-1);
  createRoosterEye(1);

  // ============================================================================
  // 8. TANGERINE-ORANGE BEAK DOME, WIDE BLACK GRIN, PINK TONGUE & BEAK LIPS
  // ============================================================================
  const jawGroup = new THREE.Group();
  jawGroup.name = 'Beak_And_Jaw_Group';
  headGroup.add(jawGroup);

  // Rounded Tangerine-Orange Upper Beak Mound right between/below the eyes
  const beakDomeGeo = new THREE.SphereGeometry(1, 28, 20);
  beakDomeGeo.scale(0.118, 0.070, 0.095);
  const beakDomeMesh = new THREE.Mesh(beakDomeGeo, materials.beakOrange);
  beakDomeMesh.position.set(0, 0.375, headFrontZ(0, 0.375) + 0.018);
  beakDomeMesh.rotation.x = 0.06;
  beakDomeMesh.castShadow = true;
  jawGroup.add(beakDomeMesh);

  function upperLipPoint(t) {
    const x = t * 0.395;
    const y = 0.345 + 0.068 * (t * t) - 0.015 * Math.pow(t, 4);
    const zBase = headFrontZ(x, y);
    return new THREE.Vector3(x, y, zBase + 0.022 * (1.0 - 0.25 * t * t));
  }

  function lowerLipPoint(t) {
    const ang = t * (Math.PI * 0.49);
    const x = Math.sin(ang) * 0.395;
    const y = 0.345 - Math.cos(ang) * 0.295;
    const zBase = headFrontZ(x, y);
    return new THREE.Vector3(x, y, zBase + 0.018 * (1.0 - 0.25 * t * t));
  }

  // Pitch-Black Recessed Mouth Cavity
  const cavityCols = 36;
  const cavityRows = 14;
  const cavPositions = [];
  const cavIndices = [];
  for (let r = 0; r <= cavityRows; r++) {
    const v = r / cavityRows;
    for (let c = 0; c <= cavityCols; c++) {
      const t = (c / cavityCols) * 2.0 - 1.0;
      const pLow = lowerLipPoint(t);
      const pUp = upperLipPoint(t);
      const x = THREE.MathUtils.lerp(pLow.x, pUp.x, v);
      const y = THREE.MathUtils.lerp(pLow.y, pUp.y, v);
      const z = headFrontZ(x, y) + 0.008;
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

  // Coral-Pink Bilobed Plush Tongue inside bottom of mouth cavity
  [-1, 1].forEach(side => {
    const lobeGeo = new THREE.SphereGeometry(1, 18, 14);
    lobeGeo.scale(0.068, 0.036, 0.016);
    const lobeMesh = new THREE.Mesh(lobeGeo, materials.tonguePink);
    const tx = side * 0.046;
    const ty = 0.115;
    lobeMesh.position.set(tx, ty, headFrontZ(tx, ty) + 0.016);
    lobeMesh.rotation.z = -side * 0.14;
    lobeMesh.rotation.x = 0.28;
    jawGroup.add(lobeMesh);
  });

  // Sculpted Tangerine-Orange Upper & Lower Beak Lips
  const upperLipPts = [];
  const lowerLipPts = [];
  for (let i = 0; i <= 36; i++) {
    const t = (i / 36) * 2.0 - 1.0;
    upperLipPts.push(upperLipPoint(t));
    lowerLipPts.push(lowerLipPoint(t));
  }
  const upperLipMesh = new THREE.Mesh(
    new THREE.TubeGeometry(new THREE.CatmullRomCurve3(upperLipPts), 48, 0.025, 16, false),
    materials.beakOrange
  );
  upperLipMesh.castShadow = true;
  jawGroup.add(upperLipMesh);

  const lowerLipMesh = new THREE.Mesh(
    new THREE.TubeGeometry(new THREE.CatmullRomCurve3(lowerLipPts), 48, 0.022, 16, false),
    materials.beakOrange
  );
  lowerLipMesh.castShadow = true;
  jawGroup.add(lowerLipMesh);

  // ============================================================================
  // 9. 3D SCULPTED CARTOON FART CLOUD CLUSTER (FOR `Kickin_Fart_Blast` ANIMATION)
  // ============================================================================
  const baseTuftGeo = new THREE.SphereGeometry(1, 18, 14);
  const btPos = baseTuftGeo.attributes.position;
  for (let i = 0; i < btPos.count; i++) {
    const vx = btPos.getX(i);
    const vy = btPos.getY(i);
    const vz = btPos.getZ(i);
    const disp = 1.0 + 0.07 * Math.sin(vx * 7.0) * Math.cos(vy * 7.0) * Math.sin(vz * 7.0);
    btPos.setXYZ(i, vx * disp, vy * disp, vz * disp);
  }
  baseTuftGeo.computeVertexNormals();

  const fartCloudGroup = new THREE.Group();
  fartCloudGroup.name = 'Kickin_Fart_Cloud_Group';
  fartCloudGroup.visible = false;
  root.add(fartCloudGroup);

  const fartStage1 = new THREE.Group();
  fartStage1.position.set(0, 0.56, -0.26);
  fartCloudGroup.add(fartStage1);

  const shockRing = new THREE.Mesh(
    new THREE.TorusGeometry(0.16, 0.024, 16, 32),
    materials.fartNeon
  );
  shockRing.position.set(0, 0, -0.10);
  fartStage1.add(shockRing);

  [
    [0.00, 0.00, -0.04, 0.08, 0.075, 0.09, materials.fartNeon],
    [0.00, 0.01, -0.13, 0.12, 0.11, 0.12, materials.fartLime],
    [-0.07, 0.03, -0.15, 0.095, 0.09, 0.095, materials.fartLime],
    [0.07, -0.02, -0.15, 0.095, 0.09, 0.095, materials.fartLime]
  ].forEach(([fx, fy, fz, sx, sy, sz, mat]) => {
    const p = new THREE.Mesh(baseTuftGeo, mat);
    p.position.set(fx, fy, fz);
    p.scale.set(sx, sy, sz);
    fartStage1.add(p);
  });

  const fartStage2 = new THREE.Group();
  fartStage2.position.set(0, 0.60, -0.52);
  fartCloudGroup.add(fartStage2);

  [
    [0.00, 0.00, 0.00, 0.19, 0.18, 0.19, materials.fartLime],
    [-0.14, 0.04, -0.03, 0.155, 0.15, 0.155, materials.fartLime],
    [0.14, 0.03, -0.03, 0.155, 0.15, 0.155, materials.fartLime],
    [0.00, 0.12, -0.06, 0.17, 0.16, 0.16, materials.fartNeon],
    [-0.11, -0.08, 0.02, 0.135, 0.12, 0.135, materials.fartLime],
    [0.11, -0.08, 0.02, 0.135, 0.12, 0.135, materials.fartLime],
    [0.00, 0.02, -0.16, 0.20, 0.19, 0.19, materials.fartLime],
    [-0.16, 0.08, -0.15, 0.15, 0.15, 0.15, materials.fartNeon],
    [0.16, 0.07, -0.15, 0.15, 0.15, 0.15, materials.fartPurple],
    [-0.09, 0.15, -0.18, 0.14, 0.135, 0.14, materials.fartLime],
    [0.09, 0.15, -0.18, 0.14, 0.135, 0.14, materials.fartLime]
  ].forEach(([fx, fy, fz, sx, sy, sz, mat]) => {
    const p = new THREE.Mesh(baseTuftGeo, mat);
    p.position.set(fx, fy, fz);
    p.scale.set(sx, sy, sz);
    fartStage2.add(p);
  });

  const fartStage3 = new THREE.Group();
  fartStage3.position.set(0, 0.70, -0.85);
  fartCloudGroup.add(fartStage3);

  [
    [0.00, 0.00, 0.00, 0.21, 0.20, 0.20, materials.fartLime],
    [-0.19, 0.07, 0.02, 0.16, 0.155, 0.16, materials.fartNeon],
    [0.19, 0.06, 0.02, 0.16, 0.155, 0.16, materials.fartLime],
    [0.00, 0.15, -0.03, 0.175, 0.17, 0.17, materials.fartPurple],
    [-0.14, -0.10, 0.04, 0.145, 0.135, 0.145, materials.fartLime],
    [0.14, -0.10, 0.04, 0.145, 0.135, 0.145, materials.fartPurple],
    [-0.24, -0.02, -0.06, 0.12, 0.12, 0.12, materials.fartNeon],
    [0.24, 0.00, -0.06, 0.12, 0.12, 0.12, materials.fartLime],
    [0.00, 0.07, -0.16, 0.15, 0.15, 0.15, materials.fartNeon]
  ].forEach(([fx, fy, fz, sx, sy, sz, mat]) => {
    const p = new THREE.Mesh(baseTuftGeo, mat);
    p.position.set(fx, fy, fz);
    p.scale.set(sx, sy, sz);
    fartStage3.add(p);
  });

  return {
    root,
    bodyRig,
    torsoGroup,
    tailGroup,
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
    starPendantGroup: skullPendantGroup,
    fartCloudGroup,
    fartStage1,
    fartStage2,
    fartStage3,
    materials
  };
}

export { buildKickinChickenPlushModel as buildBabaChopsPlushModel };
