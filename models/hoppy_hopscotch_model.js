/**
 * Hoppy Hopscotch 3D Plush Base Model Generator (Three.js r161 ESM)
 * ============================================================================
 * 1:1 High-Precision 3D Recreation of `images/012_Hoppy_Hopscotch_Plushie.webp`
 * Official Poppy Playtime Chapter 3 (Smiling Critters) Hoppy Hopscotch Plush
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
        v = Math.max(0, Math.min(255, Math.floor(128 + 52 * c1 + 32 * c2 + 24 * grain)));
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
  tex.repeat.set(6, 6);
  return tex;
}

export function buildHoppyHopscotchPlushModel(THREE) {
  const root = new THREE.Group();
  root.name = 'HoppyHopscotch_Plush_BaseModel';

  const bodyRig = new THREE.Group();
  bodyRig.name = 'Body_Rig_Root';
  root.add(bodyRig);

  const woolBump = createPlushBumpTexture(THREE, 'wool');
  const velourBump = createPlushBumpTexture(THREE, 'velour');

  // Calibrated PBR Material Palette matched to `images/012_Hoppy_Hopscotch_Plushie.webp`
  const materials = {
    bodyGreen: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Emerald_Mint_Plush',
      color: 0x34b857,
      roughness: 0.84,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.010
    }),
    pastelMint: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Pastel_Mint_Plush',
      color: 0xa7f3d0,
      roughness: 0.80,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    forestGreen: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Forest_Green_Plush',
      color: 0x1e7e38,
      roughness: 0.85,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.010
    }),
    nosePink: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Pink_Rabbit_Nose',
      color: 0xf472b6,
      roughness: 0.68,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.005
    }),
    toothWhite: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Buck_Teeth_White',
      color: 0xffffff,
      roughness: 0.42,
      metalness: 0.02
    }),
    pendantYellow: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Lightning_Pendant_Yellow',
      color: 0xffd60a,
      emissive: 0xf59e0b,
      emissiveIntensity: 0.14,
      roughness: 0.28,
      metalness: 0.12
    }),
    mouthCavity: new THREE.MeshBasicMaterial({
      name: 'Hoppy_Recessed_Mouth_Void',
      color: 0x050507,
      side: THREE.DoubleSide
    }),
    glossyEye: new THREE.MeshPhysicalMaterial({
      name: 'Hoppy_Glossy_Acrylic_Eye',
      color: 0x020204,
      roughness: 0.05,
      metalness: 0.0,
      envMapIntensity: 0.14,
      clearcoat: 1.0,
      clearcoatRoughness: 0.03,
      reflectivity: 0.95
    }),
    eyeHighlight: new THREE.MeshBasicMaterial({
      name: 'Hoppy_Eye_Studio_Catchlight',
      color: 0xffffff
    }),
    metalZipper: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Gold_Zipper_Hardware',
      color: 0xeab308,
      roughness: 0.24,
      metalness: 0.85
    }),
    seamDark: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Zipper_Track_Black',
      color: 0x101216,
      roughness: 0.90,
      metalness: 0.04
    }),
    fartLime: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Fart_Cloud_Lime',
      color: 0x4ce629,
      emissive: 0x228b12,
      emissiveIntensity: 0.35,
      roughness: 0.65,
      metalness: 0.02,
      bumpMap: woolBump,
      bumpScale: 0.015
    }),
    fartNeon: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Fart_Cloud_Neon_YellowGreen',
      color: 0xc4ff33,
      emissive: 0x84cc16,
      emissiveIntensity: 0.50,
      roughness: 0.45,
      metalness: 0.05
    }),
    fartPurple: new THREE.MeshStandardMaterial({
      name: 'Hoppy_Fart_Cloud_Purple',
      color: 0x9d4edd,
      emissive: 0x5b21b6,
      emissiveIntensity: 0.35,
      roughness: 0.60,
      metalness: 0.04
    })
  };

  function torsoFrontZ(yWorld, xWorld = 0) {
    const yn = Math.max(-1, Math.min(1, (yWorld - 0.72) / 0.32));
    const widthP = 0.275 * (1.0 - 0.22 * yn - 0.10 * yn * yn);
    const depthP = 0.240 * (1.0 - 0.18 * yn - 0.08 * yn * yn);
    const xRatio = Math.min(0.95, Math.abs(xWorld) / Math.max(0.05, widthP));
    const zHoriz = Math.sqrt(Math.max(0.01, 1.0 - yn * yn)) * Math.sqrt(Math.max(0.01, 1.0 - xRatio * xRatio));
    return depthP * zHoriz;
  }

  // ============================================================================
  // 1. TORSO, PASTEL MINT BELLY & FLUFFY COTTON-TAIL BUNNY PUFFBALL
  // ============================================================================
  const torsoGroup = new THREE.Group();
  torsoGroup.name = 'Torso_And_Zipper_Group';
  bodyRig.add(torsoGroup);

  const torsoGeo = new THREE.SphereGeometry(1, 40, 32);
  const tPos = torsoGeo.attributes.position;
  for (let i = 0; i < tPos.count; i++) {
    let x = tPos.getX(i);
    let y = tPos.getY(i);
    let z = tPos.getZ(i);
    const widthProfile = 0.275 * (1.0 - 0.22 * y - 0.10 * y * y);
    const depthProfile = 0.240 * (1.0 - 0.18 * y - 0.08 * y * y);
    const rx = x * widthProfile;
    const ry = 0.72 + y * 0.32;
    let rz = z * depthProfile;
    if (rz > 0 && Math.abs(rx) < 0.034) {
      rz -= (1.0 - Math.abs(rx) / 0.034) * 0.007;
    }
    tPos.setXYZ(i, rx, ry, rz);
  }
  torsoGeo.computeVertexNormals();
  const torsoMesh = new THREE.Mesh(torsoGeo, materials.bodyGreen);
  torsoMesh.castShadow = true;
  torsoMesh.receiveShadow = true;
  torsoGroup.add(torsoMesh);

  // Pastel Mint-Green Belly Patch (#A7F3D0)
  const bellyGeo = new THREE.SphereGeometry(1, 28, 22);
  bellyGeo.scale(0.175, 0.205, 0.085);
  const bellyMesh = new THREE.Mesh(bellyGeo, materials.pastelMint);
  bellyMesh.position.set(0, 0.68, 0.188);
  bellyMesh.rotation.x = -0.06;
  torsoGroup.add(bellyMesh);

  // Fluffy Round Puffball Bunny Tail (`tailGroup`)
  const tailGroup = new THREE.Group();
  tailGroup.name = 'Bunny_Tail_Group';
  tailGroup.position.set(0, 0.56, -0.22);
  torsoGroup.add(tailGroup);

  const tailPuffs = [
    [0.00, 0.00, -0.04, 0.105, 0.100, 0.105, materials.bodyGreen],
    [-0.055, 0.025, -0.055, 0.065, 0.065, 0.065, materials.bodyGreen],
    [0.055, 0.025, -0.055, 0.065, 0.065, 0.065, materials.bodyGreen],
    [0.00, 0.055, -0.05, 0.068, 0.065, 0.065, materials.pastelMint],
    [0.00, 0.005, -0.095, 0.075, 0.075, 0.072, materials.pastelMint]
  ];
  tailPuffs.forEach(([tx, ty, tz, sx, sy, sz, mat]) => {
    const tp = new THREE.Mesh(new THREE.SphereGeometry(1, 18, 14), mat);
    tp.position.set(tx, ty, tz);
    tp.scale.set(sx, sy, sz);
    tp.castShadow = true;
    tailGroup.add(tp);
  });

  // ============================================================================
  // 2. BLACK COLLAR ZIPPER & BRIGHT YELLOW LIGHTNING BOLT PENDANT
  // ============================================================================
  const zipperGroup = new THREE.Group();
  zipperGroup.name = 'Zipper_Hardware_Group';
  torsoGroup.add(zipperGroup);

  const toothGeo = new THREE.BoxGeometry(0.018, 0.008, 0.018);
  const backingSegGeo = new THREE.BoxGeometry(0.038, 0.018, 0.015);
  for (let i = 0; i < 31; i++) {
    const ty = 0.46 + i * 0.0155;
    const zSurf = torsoFrontZ(ty, 0) + 0.012;
    const side = (i % 2 === 0) ? -0.0065 : 0.0065;

    const backSeg = new THREE.Mesh(backingSegGeo, materials.seamDark);
    backSeg.position.set(0, ty, zSurf - 0.003);
    zipperGroup.add(backSeg);

    const tooth = new THREE.Mesh(toothGeo, materials.metalZipper);
    tooth.position.set(side, ty, zSurf + 0.003);
    zipperGroup.add(tooth);
  }

  const zCollar = torsoFrontZ(0.94, 0) + 0.012;
  const sliderBody = new THREE.Mesh(new THREE.BoxGeometry(0.046, 0.054, 0.034), materials.metalZipper);
  sliderBody.position.set(0, 0.94, zCollar + 0.006);
  sliderBody.rotation.x = -0.18;
  zipperGroup.add(sliderBody);

  // Lightning Bolt Pendant Group (`skullPendantGroup` / `pendantGroup`)
  const zChest = torsoFrontZ(0.82, 0) + 0.018;
  const skullPendantGroup = new THREE.Group();
  skullPendantGroup.name = 'Lightning_Pendant_Group';
  skullPendantGroup.position.set(0, 0.90, zChest + 0.012);
  skullPendantGroup.rotation.x = -0.08;
  torsoGroup.add(skullPendantGroup);

  const bailLoop = new THREE.Mesh(new THREE.BoxGeometry(0.034, 0.042, 0.024), materials.metalZipper);
  bailLoop.position.set(0, -0.012, 0.0);
  skullPendantGroup.add(bailLoop);

  // Exact 2D contour of Hoppy Hopscotch's Bright Yellow Lightning Bolt Charm
  const boltShape = new THREE.Shape();
  boltShape.moveTo(0.018, -0.025);
  boltShape.lineTo(-0.088, -0.165);
  boltShape.lineTo(-0.012, -0.165);
  boltShape.lineTo(-0.065, -0.310);
  boltShape.lineTo(0.092, -0.145);
  boltShape.lineTo(0.015, -0.145);
  boltShape.closePath();

  const borderExtrude = new THREE.ExtrudeGeometry(boltShape, {
    depth: 0.018,
    bevelEnabled: true,
    bevelSegments: 3,
    steps: 1,
    bevelSize: 0.010,
    bevelThickness: 0.008
  });
  const borderMesh = new THREE.Mesh(borderExtrude, materials.seamDark);
  borderMesh.position.set(0, 0, -0.006);
  skullPendantGroup.add(borderMesh);

  const boltExtrude = new THREE.ExtrudeGeometry(boltShape, {
    depth: 0.022,
    bevelEnabled: true,
    bevelSegments: 4,
    steps: 1,
    bevelSize: 0.004,
    bevelThickness: 0.006
  });
  const boltMesh = new THREE.Mesh(boltExtrude, materials.pendantYellow);
  boltMesh.position.set(0, 0, -0.002);
  boltMesh.castShadow = true;
  skullPendantGroup.add(boltMesh);

  // ============================================================================
  // 3. ARMS, FOREST-GREEN HAND PAWS & PASTEL MINT PAW PADS
  // ============================================================================
  function createArm(side) {
    const armGroup = new THREE.Group();
    armGroup.name = side < 0 ? 'Left_Arm_Group' : 'Right_Arm_Group';
    armGroup.position.set(side * 0.185, 0.91, 0.02);
    armGroup.rotation.z = side * 0.68;
    torsoGroup.add(armGroup);

    const sleeveGeo = new THREE.CylinderGeometry(0.076, 0.096, 0.29, 24, 10);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, materials.bodyGreen);
    sleeveMesh.position.set(0, -0.135, 0);
    sleeveMesh.castShadow = true;
    armGroup.add(sleeveMesh);

    const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.078, 18, 14), materials.bodyGreen);
    armGroup.add(shoulderCap);

    const pawGroup = new THREE.Group();
    pawGroup.position.set(0, -0.32, 0.01);
    armGroup.add(pawGroup);

    const pawGeo = new THREE.SphereGeometry(0.106, 28, 20);
    pawGeo.scale(1.04, 1.15, 0.86);
    const pawMesh = new THREE.Mesh(pawGeo, materials.forestGreen);
    pawMesh.castShadow = true;
    pawGroup.add(pawMesh);

    const padGeo = new THREE.SphereGeometry(0.056, 18, 14);
    padGeo.scale(1.0, 1.12, 0.45);
    const padMesh = new THREE.Mesh(padGeo, materials.pastelMint);
    padMesh.position.set(0, -0.01, 0.078);
    pawGroup.add(padMesh);

    return armGroup;
  }

  const leftArmGroup = createArm(-1);
  const rightArmGroup = createArm(1);

  // ============================================================================
  // 4. LEGS, DARK FOREST-GREEN BUNNY FEET & PASTEL SOLE PAW PADS
  // ============================================================================
  function createLeg(side) {
    const legGroup = new THREE.Group();
    legGroup.name = side < 0 ? 'Left_Leg_Group' : 'Right_Leg_Group';
    legGroup.position.set(side * 0.145, 0.46, 0.02);
    legGroup.rotation.z = side * 0.08;
    bodyRig.add(legGroup);

    const legGeo = new THREE.CylinderGeometry(0.092, 0.098, 0.30, 24, 10);
    const legMesh = new THREE.Mesh(legGeo, materials.bodyGreen);
    legMesh.position.set(0, -0.15, 0);
    legMesh.castShadow = true;
    legGroup.add(legMesh);

    const footGroup = new THREE.Group();
    footGroup.position.set(side * 0.02, -0.35, 0.07);
    footGroup.rotation.z = -side * 0.08;
    legGroup.add(footGroup);

    const footGeo = new THREE.SphereGeometry(0.132, 28, 20);
    footGeo.scale(1.06, 0.84, 1.12);
    const footMesh = new THREE.Mesh(footGeo, materials.forestGreen);
    footMesh.castShadow = true;
    footMesh.receiveShadow = true;
    footGroup.add(footMesh);

    const solePadGeo = new THREE.SphereGeometry(0.084, 20, 14);
    solePadGeo.scale(1.05, 0.88, 0.38);
    const solePad = new THREE.Mesh(solePadGeo, materials.pastelMint);
    solePad.position.set(0, -0.005, 0.128);
    footGroup.add(solePad);

    return legGroup;
  }

  const leftLegGroup = createLeg(-1);
  const rightLegGroup = createLeg(1);

  // ============================================================================
  // 5. HEAD, TALL UPRIGHT LONG BUNNY EARS, PINK NOSE, WIDE GRIN & BUCK TEETH
  // ============================================================================
  const headGroup = new THREE.Group();
  headGroup.name = 'Head_Group';
  headGroup.position.set(0, 1.00, 0);
  bodyRig.add(headGroup);

  const HEAD_RX = 0.455, HEAD_RY = 0.365, HEAD_RZ = 0.395, HEAD_CY = 0.36;
  function headFrontZ(x, y) {
    const nx = x / HEAD_RX;
    const ny = (y - HEAD_CY) / HEAD_RY;
    const r2 = nx * nx + ny * ny;
    if (r2 >= 0.96) return HEAD_RZ * 0.20;
    return HEAD_RZ * Math.sqrt(1.0 - r2);
  }

  const headCoreGeo = new THREE.SphereGeometry(1, 44, 34);
  const hPos = headCoreGeo.attributes.position;
  for (let i = 0; i < hPos.count; i++) {
    let x = hPos.getX(i) * HEAD_RX;
    let y = hPos.getY(i) * HEAD_RY;
    let z = hPos.getZ(i) * HEAD_RZ;
    if (y < 0.05 && y > -0.25) {
      const flare = Math.exp(-Math.pow((y + 0.08) / 0.14, 2)) * (Math.abs(x) / HEAD_RX);
      x *= (1.0 + 0.12 * flare);
    }
    hPos.setXYZ(i, x, y + HEAD_CY, z);
  }
  headCoreGeo.computeVertexNormals();
  const headCore = new THREE.Mesh(headCoreGeo, materials.bodyGreen);
  headCore.castShadow = true;
  headGroup.add(headCore);

  // Cute Bunny Cheek Fur Tufts (`woolGroup` for compatibility)
  const woolGroup = new THREE.Group();
  woolGroup.name = 'Cheek_And_Crown_Tufts_Group';
  headGroup.add(woolGroup);

  [-1, 1].forEach(side => {
    [
      [side * 0.45, 0.36, 0.06, 0.09, 0.042, 0.06, side * -0.25],
      [side * 0.44, 0.30, 0.07, 0.08, 0.038, 0.05, side * -0.42]
    ].forEach(([tx, ty, tz, sx, sy, sz, rz]) => {
      const m = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12), materials.bodyGreen);
      m.position.set(tx, ty, tz);
      m.scale.set(sx, sy, sz);
      m.rotation.z = rz;
      woolGroup.add(m);
    });
  });

  // ============================================================================
  // 6. TALL UPRIGHT LONG BUNNY RABBIT EARS (`leftEarGroup`, `rightEarGroup`)
  // ============================================================================
  function createBunnyEar(side) {
    const earGroup = new THREE.Group();
    earGroup.name = side < 0 ? 'Left_Ear_Group' : 'Right_Ear_Group';
    earGroup.position.set(side * 0.15, 0.66, -0.01);
    // Jaunty asymmetric bunny ear tilt matching 012_Hoppy_Hopscotch_Plushie.webp!
    earGroup.rotation.z = (side > 0) ? -0.32 : 0.07;
    earGroup.rotation.x = 0.05;
    headGroup.add(earGroup);

    // Lower/Middle Bright Green Ear Paddle
    const lowerGeo = new THREE.SphereGeometry(1, 28, 22);
    lowerGeo.scale(0.132, 0.245, 0.058);
    const lowerMesh = new THREE.Mesh(lowerGeo, materials.bodyGreen);
    lowerMesh.position.set(0, 0.22, 0);
    lowerMesh.castShadow = true;
    earGroup.add(lowerMesh);

    // Dipped Top Forest-Green Ear Tip Cap (top third of ear)
    const tipGeo = new THREE.SphereGeometry(1, 26, 18);
    tipGeo.scale(0.130, 0.155, 0.056);
    const tipMesh = new THREE.Mesh(tipGeo, materials.forestGreen);
    tipMesh.position.set(0, 0.46, 0);
    tipMesh.castShadow = true;
    earGroup.add(tipMesh);

    // Pastel Mint-Green Inner Ear Rim
    const mintInnerGeo = new THREE.SphereGeometry(1, 24, 16);
    mintInnerGeo.scale(0.088, 0.215, 0.024);
    const mintInnerMesh = new THREE.Mesh(mintInnerGeo, materials.pastelMint);
    mintInnerMesh.position.set(0, 0.28, 0.032);
    earGroup.add(mintInnerMesh);

    // Darker Forest-Green Inner Ear Center Scoop
    const coreInnerGeo = new THREE.SphereGeometry(1, 22, 14);
    coreInnerGeo.scale(0.060, 0.175, 0.016);
    const coreInnerMesh = new THREE.Mesh(coreInnerGeo, materials.forestGreen);
    coreInnerMesh.position.set(0, 0.275, 0.044);
    earGroup.add(coreInnerMesh);

    return earGroup;
  }

  const leftEarGroup = createBunnyEar(-1);
  const rightEarGroup = createBunnyEar(1);

  // ============================================================================
  // 7. LARGE GLOSSY BLACK EYES, CATCHLIGHTS, EYELIDS & ARCHED BROWS
  // ============================================================================
  const eyesGroup = new THREE.Group();
  eyesGroup.name = 'Eyes_And_Brows_Group';
  headGroup.add(eyesGroup);

  function createEyeAssembly(side) {
    const ex = side * 0.142;
    const ey = 0.435;
    const ez = headFrontZ(ex, ey) - 0.012;

    const eyeWrap = new THREE.Group();
    eyeWrap.position.set(ex, ey, ez);
    eyeWrap.rotation.y = side * 0.18;
    eyesGroup.add(eyeWrap);

    const eyeSphereGeo = new THREE.SphereGeometry(0.095, 32, 24);
    eyeSphereGeo.scale(1.02, 1.10, 0.72);
    const eyeMesh = new THREE.Mesh(eyeSphereGeo, materials.glossyEye);
    eyeWrap.add(eyeMesh);

    const catchGeo = new THREE.SphereGeometry(1, 16, 12);
    catchGeo.scale(0.022, 0.032, 0.006);
    const catchMesh = new THREE.Mesh(catchGeo, materials.eyeHighlight);
    catchMesh.position.set(side * -0.018, 0.022, 0.066);
    eyeWrap.add(catchMesh);

    const catch2 = new THREE.Mesh(new THREE.SphereGeometry(0.008, 10, 8), materials.eyeHighlight);
    catch2.position.set(side * 0.024, -0.026, 0.064);
    eyeWrap.add(catch2);

    // Subtle upper forest-green eyelid rim
    const lidGeo = new THREE.TorusGeometry(0.096, 0.012, 10, 24, Math.PI * 0.85);
    const lidMesh = new THREE.Mesh(lidGeo, materials.forestGreen);
    lidMesh.rotation.z = Math.PI * 0.075;
    lidMesh.position.set(0, 0.008, 0.032);
    eyeWrap.add(lidMesh);

    // High arched dark brow
    const browGeo = new THREE.TorusGeometry(0.088, 0.009, 8, 20, Math.PI * 0.72);
    const browMesh = new THREE.Mesh(browGeo, materials.seamDark);
    browMesh.rotation.z = Math.PI * 0.14 - side * 0.08;
    browMesh.position.set(0, 0.072, 0.025);
    eyeWrap.add(browMesh);
  }

  createEyeAssembly(-1);
  createEyeAssembly(1);

  // ============================================================================
  // 8. PINK TRIANGULAR RABBIT NOSE, WIDE HAPPY GRIN, BUCK TEETH & PINK TONGUE
  // ============================================================================
  const jawGroup = new THREE.Group();
  jawGroup.name = 'Muzzle_And_Jaw_Group';
  headGroup.add(jawGroup);

  // Pink Triangular Rabbit Nose
  const noseGeo = new THREE.SphereGeometry(1, 24, 18);
  const nPos = noseGeo.attributes.position;
  for (let i = 0; i < nPos.count; i++) {
    let x = nPos.getX(i) * 0.048;
    let y = nPos.getY(i) * 0.034;
    let z = nPos.getZ(i) * 0.030;
    const ty = (y + 0.034) / 0.068;
    x *= (0.38 + 0.85 * Math.max(0, Math.min(1.2, ty)));
    nPos.setXYZ(i, x, y, z);
  }
  noseGeo.computeVertexNormals();
  const noseMesh = new THREE.Mesh(noseGeo, materials.nosePink);
  noseMesh.position.set(0, 0.345, headFrontZ(0, 0.345) + 0.018);
  noseMesh.rotation.x = -0.12;
  jawGroup.add(noseMesh);

  function upperLipPoint(t) {
    const x = t * 0.36;
    const y = 0.285 + 0.075 * (t * t) - 0.012 * Math.pow(t, 4);
    const z = headFrontZ(x, y) + 0.018 * (1.0 - 0.32 * t * t);
    return new THREE.Vector3(x, y, z);
  }

  function lowerLipPoint(t) {
    const ang = t * (Math.PI * 0.49);
    const x = Math.sin(ang) * 0.36;
    const y = 0.345 - Math.cos(ang) * 0.295;
    const z = headFrontZ(x, y) + 0.015 * Math.cos(ang * 0.82);
    return new THREE.Vector3(x, y, z);
  }

  // Deep pitch-black recessed mouth cavity mesh
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
  const mouthPlateMesh = new THREE.Mesh(mouthPlateGeo, materials.mouthCavity);
  jawGroup.add(mouthPlateMesh);

  // Cute Pink Bunny Tongue at bottom of wide grin
  const tongueGeo = new THREE.SphereGeometry(1, 20, 14);
  tongueGeo.scale(0.105, 0.048, 0.022);
  const tongueMesh = new THREE.Mesh(tongueGeo, materials.nosePink);
  tongueMesh.position.set(0, 0.115, headFrontZ(0, 0.115) + 0.008);
  tongueMesh.rotation.x = 0.35;
  jawGroup.add(tongueMesh);

  // Upper & Lower Green Plush Smiling Lip Rims
  const upperLipPts = [];
  const lowerLipPts = [];
  for (let i = 0; i <= 36; i++) {
    const t = (i / 36) * 2.0 - 1.0;
    upperLipPts.push(upperLipPoint(t));
    lowerLipPts.push(lowerLipPoint(t));
  }
  const upperLipGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(upperLipPts), 48, 0.024, 16, false);
  const lowerLipGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(lowerLipPts), 48, 0.022, 16, false);
  jawGroup.add(new THREE.Mesh(upperLipGeo, materials.bodyGreen));
  jawGroup.add(new THREE.Mesh(lowerLipGeo, materials.bodyGreen));

  // Twin White Bunny Buck Teeth inside wide grin
  function createBuckTooth(side) {
    const toothShape = new THREE.Shape();
    toothShape.moveTo(-0.036, 0.062);
    toothShape.lineTo(0.036, 0.062);
    toothShape.lineTo(0.036, -0.018);
    toothShape.quadraticCurveTo(0.036, -0.058, 0.0, -0.060);
    toothShape.quadraticCurveTo(-0.036, -0.058, -0.036, -0.018);
    toothShape.closePath();

    const tGeo = new THREE.ExtrudeGeometry(toothShape, {
      depth: 0.018,
      bevelEnabled: true,
      bevelSegments: 4,
      steps: 1,
      bevelSize: 0.008,
      bevelThickness: 0.008
    });
    tGeo.center();
    const tMesh = new THREE.Mesh(tGeo, materials.toothWhite);
    const zTooth = headFrontZ(0, 0.235) + 0.014;
    tMesh.position.set(side * 0.042, 0.235, zTooth);
    tMesh.rotation.y = side * 0.05;
    tMesh.rotation.x = -0.28;
    tMesh.castShadow = true;
    return tMesh;
  }

  jawGroup.add(createBuckTooth(-1));
  jawGroup.add(createBuckTooth(1));

  const toothSeam = new THREE.Mesh(
    new THREE.CylinderGeometry(0.0035, 0.0035, 0.115, 8),
    materials.seamDark
  );
  toothSeam.position.set(0, 0.238, headFrontZ(0, 0.238) + 0.024);
  toothSeam.rotation.x = -0.28;
  jawGroup.add(toothSeam);

  // ============================================================================
  // 9. 3D SCULPTED CARTOON FART CLOUD CLUSTER (FOR `Hoppy_Fart_Blast` ANIMATION)
  // ============================================================================
  const fartCloudGroup = new THREE.Group();
  fartCloudGroup.name = 'Hoppy_Fart_Cloud_Group';
  fartCloudGroup.visible = false;
  root.add(fartCloudGroup);

  const baseTuftGeo = new THREE.SphereGeometry(1, 18, 14);
  const bPos = baseTuftGeo.attributes.position;
  for (let i = 0; i < bPos.count; i++) {
    const vx = bPos.getX(i);
    const vy = bPos.getY(i);
    const vz = bPos.getZ(i);
    const disp = 1.0 + 0.07 * Math.sin(vx * 7.0) * Math.cos(vy * 7.0) * Math.sin(vz * 7.0);
    bPos.setXYZ(i, vx * disp, vy * disp, vz * disp);
  }
  baseTuftGeo.computeVertexNormals();

  const fartStage1 = new THREE.Group();
  fartStage1.position.set(0, 0.56, -0.28);
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
  fartStage2.position.set(0, 0.60, -0.54);
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
  fartStage3.position.set(0, 0.70, -0.86);
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
