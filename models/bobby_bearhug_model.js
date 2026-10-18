/**
 * Bobby BearHug 3D Plush Base Model Generator (Three.js r161 ESM)
 * ============================================================================
 * 1:1 High-Precision 3D Recreation of `images/026_Bobby_BearHug_s_second_cutout_artwork_pose.webp`
 * Official Poppy Playtime Chapter 3 (Smiling Critters) Bobby BearHug Plush
 * Featuring Golden-Bordered Red Heart Pendant & 3-Stage `Bobby_Fart_Blast` 3D Cloud
 */

function createPlushBumpTexture(THREE, mode = 'velour') {
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
        const hash = Math.sin((x * 12.9898 + y * 78.233)) * 43758.5453;
        const grain = (hash - Math.floor(hash)) - 0.5;
        v = Math.max(0, Math.min(255, Math.floor(128 + 56 * c1 + 34 * c2 + 24 * grain)));
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

export function buildBobbyBearHugPlushModel(THREE) {
  const root = new THREE.Group();
  root.name = 'BobbyBearHug_Plush_BaseModel';

  const bodyRig = new THREE.Group();
  bodyRig.name = 'Body_Rig_Root';
  root.add(bodyRig);

  const woolBump = createPlushBumpTexture(THREE, 'wool');
  const velourBump = createPlushBumpTexture(THREE, 'velour');

  // Calibrated PBR Material Palette matched to `026_Bobby_BearHug_s_second_cutout_artwork_pose.webp`
  const materials = {
    crimsonPlush: new THREE.MeshStandardMaterial({
      name: 'Bobby_Crimson_Plush',
      color: 0xc92a42,
      roughness: 0.85,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.009
    }),
    rosePink: new THREE.MeshStandardMaterial({
      name: 'Bobby_Rose_Pink_Plush',
      color: 0xf497a9,
      roughness: 0.80,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.007
    }),
    rubyDark: new THREE.MeshStandardMaterial({
      name: 'Bobby_Ruby_Dark_Pad',
      color: 0x8f192b,
      roughness: 0.62,
      metalness: 0.04,
      bumpMap: velourBump,
      bumpScale: 0.006
    }),
    pendantGold: new THREE.MeshStandardMaterial({
      name: 'Bobby_Pendant_Gold_Border',
      color: 0xf5c542,
      roughness: 0.24,
      metalness: 0.88
    }),
    cheekBlush: new THREE.MeshStandardMaterial({
      name: 'Bobby_Cheek_Blush',
      color: 0xe6486b,
      roughness: 0.78,
      metalness: 0.02
    }),
    mouthCavity: new THREE.MeshBasicMaterial({
      name: 'Bobby_Recessed_Mouth_Void',
      color: 0x050507,
      side: THREE.DoubleSide
    }),
    glossyEye: new THREE.MeshPhysicalMaterial({
      name: 'Bobby_Glossy_Acrylic_Eye',
      color: 0x020204,
      roughness: 0.05,
      metalness: 0.0,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04,
      reflectivity: 0.95
    }),
    eyeHighlight: new THREE.MeshBasicMaterial({
      name: 'Bobby_Eye_Pupil_White',
      color: 0xffffff
    }),
    metalZipper: new THREE.MeshStandardMaterial({
      name: 'Bobby_Silver_Zipper_Hardware',
      color: 0xc8cdd6,
      roughness: 0.28,
      metalness: 0.82
    }),
    seamDark: new THREE.MeshStandardMaterial({
      name: 'Bobby_Zipper_Collar_Track',
      color: 0x101014,
      roughness: 0.90,
      metalness: 0.02
    }),
    fartLime: new THREE.MeshStandardMaterial({
      name: 'Bobby_Fart_Cloud_Lime',
      color: 0x4ce629,
      emissive: 0x228b12,
      emissiveIntensity: 0.35,
      roughness: 0.65,
      metalness: 0.02,
      bumpMap: woolBump,
      bumpScale: 0.015
    }),
    fartNeon: new THREE.MeshStandardMaterial({
      name: 'Bobby_Fart_Cloud_Neon_YellowGreen',
      color: 0xc4ff33,
      emissive: 0x84cc16,
      emissiveIntensity: 0.50,
      roughness: 0.45,
      metalness: 0.05
    }),
    fartPurple: new THREE.MeshStandardMaterial({
      name: 'Bobby_Fart_Cloud_Purple',
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
  // 1. TORSO, ROSE-PINK BELLY PATCH & ROUND BEAR TAIL
  // ============================================================================
  const torsoGroup = new THREE.Group();
  torsoGroup.name = 'Torso_And_Pendant_Group';
  bodyRig.add(torsoGroup);

  const torsoGeo = new THREE.SphereGeometry(1, 40, 32);
  const tPos = torsoGeo.attributes.position;
  for (let i = 0; i < tPos.count; i++) {
    const x = tPos.getX(i);
    const y = tPos.getY(i);
    const z = tPos.getZ(i);
    const widthProfile = 0.285 * (1.0 - 0.24 * y - 0.10 * y * y);
    const depthProfile = 0.245 * (1.0 - 0.20 * y - 0.08 * y * y);
    tPos.setXYZ(i, x * widthProfile, 0.755 + y * 0.325, z * depthProfile);
  }
  torsoGeo.computeVertexNormals();
  const torsoMesh = new THREE.Mesh(torsoGeo, materials.crimsonPlush);
  torsoMesh.castShadow = true;
  torsoMesh.receiveShadow = true;
  torsoGroup.add(torsoMesh);

  // Soft Rose-Pink Oval Belly Patch (`#F497A9`)
  const bellyGeo = new THREE.SphereGeometry(1, 32, 24);
  const bPos = bellyGeo.attributes.position;
  for (let i = 0; i < bPos.count; i++) {
    const x = bPos.getX(i) * 0.155;
    const y = 0.735 + bPos.getY(i) * 0.195;
    const zRaw = bPos.getZ(i);
    const zSurf = torsoFrontZ(y, x);
    const z = zRaw > 0 ? zSurf + zRaw * 0.016 : zSurf - 0.010;
    bPos.setXYZ(i, x, y, z);
  }
  bellyGeo.computeVertexNormals();
  const bellyMesh = new THREE.Mesh(bellyGeo, materials.rosePink);
  torsoGroup.add(bellyMesh);

  // Cute Round Crimson Bear Tail on the back of Pelvis
  const tailGroup = new THREE.Group();
  tailGroup.name = 'Bear_Tail_Group';
  tailGroup.position.set(0, 0.56, -0.25);
  torsoGroup.add(tailGroup);
  const tailMesh = new THREE.Mesh(new THREE.SphereGeometry(0.086, 20, 16), materials.crimsonPlush);
  tailMesh.castShadow = true;
  tailGroup.add(tailMesh);

  // ============================================================================
  // 2. BLACK COLLAR ZIPPER & GOLDEN-BORDERED RED HEART PENDANT
  // ============================================================================
  const zipperGroup = new THREE.Group();
  zipperGroup.name = 'Collar_Zipper_Group';
  torsoGroup.add(zipperGroup);

  const collarRing = new THREE.Mesh(new THREE.TorusGeometry(0.195, 0.015, 12, 32), materials.seamDark);
  collarRing.position.set(0, 1.00, 0.0);
  collarRing.rotation.x = Math.PI / 2 + 0.08;
  zipperGroup.add(collarRing);

  const zCollar = torsoFrontZ(0.985, 0);
  const sliderBody = new THREE.Mesh(new THREE.BoxGeometry(0.044, 0.052, 0.032), materials.metalZipper);
  sliderBody.position.set(0, 0.982, zCollar + 0.008);
  zipperGroup.add(sliderBody);

  // Golden-Bordered Red Heart Pendant Group (kept as `skullPendantGroup` alias for studio compatibility)
  const zChest = torsoFrontZ(0.82, 0);
  const skullPendantGroup = new THREE.Group();
  skullPendantGroup.name = 'Heart_Pendant_Group';
  skullPendantGroup.position.set(0, 0.935, zChest + 0.016);
  skullPendantGroup.rotation.x = -0.06;
  torsoGroup.add(skullPendantGroup);

  const goldBail = new THREE.Mesh(new THREE.BoxGeometry(0.036, 0.040, 0.024), materials.pendantGold);
  goldBail.position.set(0, -0.012, 0.0);
  skullPendantGroup.add(goldBail);

  // Parametric Heart Shape for Golden Outer Rim + Ruby-Red Inner Heart
  function createHeartShape(scale) {
    const shape = new THREE.Shape();
    const steps = 64;
    for (let i = 0; i <= steps; i++) {
      const t = (i / steps) * Math.PI * 2;
      const hx = scale * Math.pow(Math.sin(t), 3);
      const hy = -0.145 + scale * 0.92 * (
        0.8125 * Math.cos(t) -
        0.3125 * Math.cos(2 * t) -
        0.125 * Math.cos(3 * t) -
        0.0625 * Math.cos(4 * t)
      );
      if (i === 0) shape.moveTo(hx, hy);
      else shape.lineTo(hx, hy);
    }
    return shape;
  }

  const goldHeartGeo = new THREE.ExtrudeGeometry(createHeartShape(0.142), {
    depth: 0.018,
    bevelEnabled: true,
    bevelSegments: 4,
    steps: 1,
    bevelSize: 0.012,
    bevelThickness: 0.010
  });
  const goldHeartMesh = new THREE.Mesh(goldHeartGeo, materials.pendantGold);
  goldHeartMesh.position.set(0, 0, -0.008);
  goldHeartMesh.castShadow = true;
  skullPendantGroup.add(goldHeartMesh);

  const rubyHeartGeo = new THREE.ExtrudeGeometry(createHeartShape(0.124), {
    depth: 0.024,
    bevelEnabled: true,
    bevelSegments: 4,
    steps: 1,
    bevelSize: 0.008,
    bevelThickness: 0.010
  });
  const rubyHeartMesh = new THREE.Mesh(rubyHeartGeo, materials.rubyDark);
  rubyHeartMesh.position.set(0, 0, -0.005);
  rubyHeartMesh.castShadow = true;
  skullPendantGroup.add(rubyHeartMesh);

  // ============================================================================
  // 3. WELCOMING BEAR-HUG ARMS & ROSE-PINK PAWS WITH RUBY PALM PADS
  // ============================================================================
  function createBearArm(side) {
    const armGroup = new THREE.Group();
    armGroup.name = side < 0 ? 'Left_Arm_Group' : 'Right_Arm_Group';
    armGroup.position.set(side * 0.195, 0.955, 0.01);
    armGroup.rotation.z = side * 0.78;
    torsoGroup.add(armGroup);

    const sleeveGeo = new THREE.CylinderGeometry(0.082, 0.102, 0.30, 24, 10);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, materials.crimsonPlush);
    sleeveMesh.position.set(0, -0.14, 0);
    sleeveMesh.castShadow = true;
    armGroup.add(sleeveMesh);

    const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.082, 18, 14), materials.crimsonPlush);
    armGroup.add(shoulderCap);

    const pawGroup = new THREE.Group();
    pawGroup.position.set(0, -0.34, 0.015);
    armGroup.add(pawGroup);

    const palmMesh = new THREE.Mesh(new THREE.SphereGeometry(0.112, 24, 18), materials.rosePink);
    palmMesh.scale.set(1.08, 1.05, 0.78);
    palmMesh.castShadow = true;
    pawGroup.add(palmMesh);

    // Thumb + 3 rounded bear fingers
    const fingerOffsets = [
      [side * -0.085, 0.065, 0.01, 0.042, 0.064, 0.042],
      [side * 0.055, -0.082, 0.01, 0.045, 0.062, 0.042],
      [0.0, -0.105, 0.01, 0.045, 0.064, 0.042],
      [side * -0.055, -0.088, 0.01, 0.042, 0.058, 0.040]
    ];
    fingerOffsets.forEach(([fx, fy, fz, sx, sy, sz]) => {
      const fMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 14, 12), materials.rosePink);
      fMesh.position.set(fx, fy, fz);
      fMesh.scale.set(sx, sy, sz);
      pawGroup.add(fMesh);
    });

    // Ruby palm pad
    const palmPad = new THREE.Mesh(new THREE.SphereGeometry(0.055, 16, 12), materials.rubyDark);
    palmPad.scale.set(1.05, 0.95, 0.35);
    palmPad.position.set(0, -0.01, 0.078);
    pawGroup.add(palmPad);

    return armGroup;
  }

  const leftArmGroup = createBearArm(-1);
  const rightArmGroup = createBearArm(1);

  // ============================================================================
  // 4. LEGS & 3-TOED ROSE-PINK FOOT PAWS WITH RUBY SOLES
  // ============================================================================
  function createBearLeg(side) {
    const legGroup = new THREE.Group();
    legGroup.name = side < 0 ? 'Left_Leg_Group' : 'Right_Leg_Group';
    legGroup.position.set(side * 0.14, 0.50, 0.0);
    legGroup.rotation.z = side * 0.075;
    bodyRig.add(legGroup);

    const legGeo = new THREE.CylinderGeometry(0.094, 0.100, 0.34, 24, 10);
    const legMesh = new THREE.Mesh(legGeo, materials.crimsonPlush);
    legMesh.position.set(0, -0.17, 0);
    legMesh.castShadow = true;
    legGroup.add(legMesh);

    const footGeo = new THREE.SphereGeometry(0.118, 28, 20);
    const fPos = footGeo.attributes.position;
    for (let i = 0; i < fPos.count; i++) {
      let x = fPos.getX(i) * 1.06;
      let y = fPos.getY(i);
      let z = fPos.getZ(i) * 1.16;
      y *= (y < 0) ? 0.70 : 0.92;
      fPos.setXYZ(i, x, y, z);
    }
    footGeo.computeVertexNormals();
    const footMesh = new THREE.Mesh(footGeo, materials.rosePink);
    footMesh.position.set(0, -0.405, 0.025);
    footMesh.rotation.z = -side * 0.075;
    footMesh.castShadow = true;
    footMesh.receiveShadow = true;
    legGroup.add(footMesh);

    // 2 dark stitch toe grooves forming 3 cute toes
    [-0.036, 0.036].forEach(gx => {
      const groove = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, 0.095, 8), materials.rubyDark);
      groove.position.set(gx, -0.01, 0.125);
      groove.rotation.x = 0.25;
      footMesh.add(groove);
    });

    return legGroup;
  }

  const leftLegGroup = createBearLeg(-1);
  const rightLegGroup = createBearLeg(1);

  // ============================================================================
  // 5. HEAD, CHEEK FUR TUFTS, ROUND BEAR EARS, EYES, MUZZLE & LOVING SMILE
  // ============================================================================
  const headGroup = new THREE.Group();
  headGroup.name = 'Head_Group';
  headGroup.position.set(0, 1.06, 0);
  bodyRig.add(headGroup);

  const HEAD_RX = 0.445, HEAD_RY = 0.415, HEAD_RZ = 0.405, HEAD_CY = 0.43;
  function headFrontZ(x, y) {
    const nx = x / HEAD_RX;
    const ny = (y - HEAD_CY) / HEAD_RY;
    const r2 = nx * nx + ny * ny;
    if (r2 >= 0.96) return HEAD_RZ * 0.20;
    return HEAD_RZ * Math.sqrt(1.0 - r2);
  }

  const headCoreGeo = new THREE.SphereGeometry(1, 44, 34);
  headCoreGeo.scale(HEAD_RX, HEAD_RY, HEAD_RZ);
  const headCore = new THREE.Mesh(headCoreGeo, materials.crimsonPlush);
  headCore.position.set(0, HEAD_CY, 0);
  headCore.castShadow = true;
  headGroup.add(headCore);

  // Signature Double Cheek Fur Tufts on Left & Right Cheeks (`026_Bobby_BearHug_s_second_cutout_artwork_pose.webp`)
  const woolGroup = new THREE.Group();
  woolGroup.name = 'Cheek_Fur_Tufts_Group';
  headGroup.add(woolGroup);

  [-1, 1].forEach(side => {
    const tuft1 = new THREE.Mesh(new THREE.ConeGeometry(0.068, 0.16, 16), materials.crimsonPlush);
    tuft1.position.set(side * 0.43, 0.48, 0.04);
    tuft1.rotation.z = -side * 1.25;
    woolGroup.add(tuft1);

    const tuft2 = new THREE.Mesh(new THREE.ConeGeometry(0.065, 0.15, 16), materials.crimsonPlush);
    tuft2.position.set(side * 0.44, 0.39, 0.05);
    tuft2.rotation.z = -side * 1.38;
    woolGroup.add(tuft2);
  });

  // ============================================================================
  // 6. ROUNDED CIRCULAR TEDDY-BEAR EARS WITH ROSE-PINK INNER EAR DISCS
  // ============================================================================
  function createBearEar(side) {
    const earGroup = new THREE.Group();
    earGroup.name = side < 0 ? 'Left_Ear_Group' : 'Right_Ear_Group';
    earGroup.position.set(side * 0.33, 0.76, 0.02);
    earGroup.rotation.z = -side * 0.42;
    headGroup.add(earGroup);

    const outerEar = new THREE.Mesh(new THREE.SphereGeometry(0.172, 28, 20), materials.crimsonPlush);
    outerEar.scale.set(1.0, 1.0, 0.45);
    outerEar.castShadow = true;
    earGroup.add(outerEar);

    const innerEar = new THREE.Mesh(new THREE.SphereGeometry(0.105, 22, 16), materials.rosePink);
    innerEar.scale.set(1.0, 1.0, 0.32);
    innerEar.position.set(0, -0.005, 0.052);
    earGroup.add(innerEar);

    return earGroup;
  }

  const leftEarGroup = createBearEar(-1);
  const rightEarGroup = createBearEar(1);

  // ============================================================================
  // 7. VERTICAL OVAL BLACK EYES, WHITE OVAL PUPILS, ARCHED BROWS & CHEEK BLUSH
  // ============================================================================
  const eyesGroup = new THREE.Group();
  eyesGroup.name = 'Eyes_And_Brows_Group';
  headGroup.add(eyesGroup);

  [-1, 1].forEach(side => {
    const ex = side * 0.142;
    const ey = 0.495;
    const ez = headFrontZ(ex, ey) - 0.015;

    const eyeWrap = new THREE.Group();
    eyeWrap.position.set(ex, ey, ez);
    eyeWrap.rotation.y = side * 0.18;
    eyesGroup.add(eyeWrap);

    const eyeDome = new THREE.Mesh(new THREE.SphereGeometry(0.096, 32, 24), materials.glossyEye);
    eyeDome.scale.set(1.0, 1.32, 0.68);
    eyeWrap.add(eyeDome);

    // Signature Large Vertical White Oval Pupil (`#026`)
    const whitePupil = new THREE.Mesh(new THREE.SphereGeometry(0.044, 20, 16), materials.eyeHighlight);
    whitePupil.scale.set(1.0, 1.48, 0.32);
    whitePupil.position.set(-side * 0.008, -0.012, 0.060);
    eyeWrap.add(whitePupil);

    // High Arched Black Eyebrow above eye
    const browCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(side * 0.075, 0.72, headFrontZ(side * 0.075, 0.72) + 0.012),
      new THREE.Vector3(side * 0.145, 0.76, headFrontZ(side * 0.145, 0.76) + 0.012),
      new THREE.Vector3(side * 0.215, 0.71, headFrontZ(side * 0.215, 0.71) + 0.012)
    ]);
    const browMesh = new THREE.Mesh(new THREE.TubeGeometry(browCurve, 16, 0.012, 10, false), materials.glossyEye);
    eyesGroup.add(browMesh);

    // Warm Rosy Cheek Blush
    const blush = new THREE.Mesh(new THREE.SphereGeometry(0.056, 18, 14), materials.cheekBlush);
    blush.scale.set(1.15, 0.75, 0.35);
    blush.position.set(side * 0.31, 0.38, headFrontZ(side * 0.31, 0.38) - 0.005);
    blush.rotation.y = side * 0.52;
    eyesGroup.add(blush);
  });

  // ============================================================================
  // 8. ROSE-PINK MUZZLE PADS, HEART NOSE, WIDE LOVING SMILE & PINK TONGUE
  // ============================================================================
  const jawGroup = new THREE.Group();
  jawGroup.name = 'Muzzle_And_Jaw_Group';
  headGroup.add(jawGroup);

  // Twin Soft Rose-Pink Muzzle Pads right below the nose
  [-1, 1].forEach(side => {
    const mPad = new THREE.Mesh(new THREE.SphereGeometry(0.084, 22, 16), materials.rosePink);
    mPad.scale.set(1.08, 0.65, 0.65);
    mPad.position.set(side * 0.068, 0.355, headFrontZ(side * 0.068, 0.355) + 0.018);
    mPad.rotation.z = -side * 0.16;
    jawGroup.add(mPad);
  });

  // Heart-Shaped Dark Nose
  const noseMesh = new THREE.Mesh(new THREE.SphereGeometry(0.048, 20, 16), materials.glossyEye);
  noseMesh.scale.set(1.18, 0.88, 0.72);
  noseMesh.position.set(0, 0.388, headFrontZ(0, 0.388) + 0.036);
  jawGroup.add(noseMesh);

  function upperLipPoint(t) {
    const x = t * 0.305;
    const y = 0.315 + 0.065 * (t * t);
    const z = headFrontZ(x, y) + 0.018 * (1.0 - 0.35 * t * t);
    return new THREE.Vector3(x, y, z);
  }

  function lowerLipPoint(t) {
    const ang = t * (Math.PI * 0.49);
    const x = Math.sin(ang) * 0.305;
    const y = 0.315 - Math.cos(ang) * 0.235;
    const z = headFrontZ(x, y) + 0.014 * Math.cos(ang * 0.85);
    return new THREE.Vector3(x, y, z);
  }

  const cavityCols = 36, cavityRows = 14;
  const cavPositions = [], cavIndices = [];
  for (let r = 0; r <= cavityRows; r++) {
    const v = r / cavityRows;
    for (let c = 0; c <= cavityCols; c++) {
      const t = (c / cavityCols) * 2.0 - 1.0;
      const pLow = lowerLipPoint(t);
      const pUp = upperLipPoint(t);
      const x = THREE.MathUtils.lerp(pLow.x, pUp.x, v);
      const y = THREE.MathUtils.lerp(pLow.y, pUp.y, v);
      const z = headFrontZ(x, y) + 0.005;
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
  jawGroup.add(new THREE.Mesh(mouthPlateGeo, materials.mouthCavity));

  const upperLipPts = [], lowerLipPts = [];
  for (let i = 0; i <= 36; i++) {
    const t = (i / 36) * 2.0 - 1.0;
    upperLipPts.push(upperLipPoint(t));
    lowerLipPts.push(lowerLipPoint(t));
  }
  const upperLipMesh = new THREE.Mesh(
    new THREE.TubeGeometry(new THREE.CatmullRomCurve3(upperLipPts), 48, 0.022, 16, false),
    materials.crimsonPlush
  );
  const lowerLipMesh = new THREE.Mesh(
    new THREE.TubeGeometry(new THREE.CatmullRomCurve3(lowerLipPts), 48, 0.022, 16, false),
    materials.crimsonPlush
  );
  jawGroup.add(upperLipMesh, lowerLipMesh);

  // Cute Rose-Pink Double-Lobed Tongue at bottom of open mouth
  [-1, 1].forEach(side => {
    const tongueLobe = new THREE.Mesh(new THREE.SphereGeometry(0.062, 18, 14), materials.rosePink);
    tongueLobe.scale.set(1.05, 0.58, 0.42);
    const tx = side * 0.044, ty = 0.125;
    tongueLobe.position.set(tx, ty, headFrontZ(tx, ty) + 0.012);
    tongueLobe.rotation.z = -side * 0.12;
    jawGroup.add(tongueLobe);
  });

  // ============================================================================
  // 9. 3D SCULPTED CARTOON FART CLOUD CLUSTER (FOR `Bobby_Fart_Blast` ANIMATION)
  // ============================================================================
  const baseTuftGeo = new THREE.SphereGeometry(1, 18, 14);
  const btPos = baseTuftGeo.attributes.position;
  for (let i = 0; i < btPos.count; i++) {
    const vx = btPos.getX(i), vy = btPos.getY(i), vz = btPos.getZ(i);
    const disp = 1.0 + 0.07 * Math.sin(vx * 7.0) * Math.cos(vy * 7.0) * Math.sin(vz * 7.0);
    btPos.setXYZ(i, vx * disp, vy * disp, vz * disp);
  }
  baseTuftGeo.computeVertexNormals();

  const fartCloudGroup = new THREE.Group();
  fartCloudGroup.name = 'Bobby_Fart_Cloud_Group';
  fartCloudGroup.visible = false;
  root.add(fartCloudGroup);

  const fartStage1 = new THREE.Group();
  fartStage1.position.set(0, 0.56, -0.26);
  fartCloudGroup.add(fartStage1);

  const shockRing = new THREE.Mesh(
    new THREE.TorusGeometry(0.16, 0.024, 14, 28),
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
    pendantGroup: skullPendantGroup,
    fartCloudGroup,
    fartStage1,
    fartStage2,
    fartStage3,
    materials
  };
}
