
// ============================================================================
// critter-3d (CatNap-Final-v11) Binary GLB Loader (Zero External Dependencies)
// Automatically replaces procedural placeholder primitives with the exact
// voxel-unioned Blender 4.3 plush mesh, recessed perforated speaker grille,
// skin-fitted button eyes, and 700+ 3D cotton stitch arcs.
// ============================================================================
function loadCritterV11GLB(THREE, glbUrl, rigGroups, bumpTex) {
  if (typeof fetch === 'undefined') return;
  fetch(glbUrl)
    .then(res => {
      if (!res.ok) throw new Error('HTTP ' + res.status);
      return res.arrayBuffer();
    })
    .then(buffer => {
      const dv = new DataView(buffer);
      const magic = dv.getUint32(0, true);
      if (magic !== 0x46546C67) throw new Error('Invalid GLB magic');
      const jsonLen = dv.getUint32(12, true);
      const jsonStr = new TextDecoder().decode(new Uint8Array(buffer, 20, jsonLen));
      const gltf = JSON.parse(jsonStr);
      const binOffset = 20 + jsonLen + 8;

      function getAccessorData(accIdx) {
        const acc = gltf.accessors[accIdx];
        const bv = gltf.bufferViews[acc.bufferView];
        const byteOffset = binOffset + (bv.byteOffset || 0) + (acc.byteOffset || 0);
        const numComp = { SCALAR: 1, VEC2: 2, VEC3: 3, VEC4: 4, MAT4: 16 }[acc.type] || 1;
        const TypedArr = {
          5126: Float32Array,
          5123: Uint16Array,
          5125: Uint32Array,
          5121: Uint8Array,
          5122: Int16Array,
          5120: Int8Array
        }[acc.componentType] || Float32Array;
        const elemBytes = TypedArr.BYTES_PER_ELEMENT;
        const stride = bv.byteStride || (numComp * elemBytes);
        if (stride === numComp * elemBytes) {
          return new TypedArr(buffer, byteOffset, acc.count * numComp);
        }
        const out = new TypedArr(acc.count * numComp);
        for (let i = 0; i < acc.count; i++) {
          const rowOff = byteOffset + i * stride;
          for (let c = 0; c < numComp; c++) {
            if (acc.componentType === 5126) out[i * numComp + c] = dv.getFloat32(rowOff + c * 4, true);
            else if (acc.componentType === 5123) out[i * numComp + c] = dv.getUint16(rowOff + c * 2, true);
            else if (acc.componentType === 5125) out[i * numComp + c] = dv.getUint32(rowOff + c * 4, true);
          }
        }
        return out;
      }

      const threeMats = (gltf.materials || []).map(m => {
        const pbr = m.pbrMetallicRoughness || {};
        const bc = pbr.baseColorFactor || [0.8, 0.8, 0.8, 1.0];
        const rough = pbr.roughnessFactor !== undefined ? pbr.roughnessFactor : 0.84;
        const metal = pbr.metallicFactor !== undefined ? pbr.metallicFactor : 0.0;
        const col = new THREE.Color();
        if (col.setRGB) {
          col.setRGB(bc[0], bc[1], bc[2], THREE.LinearSRGBColorSpace || 'srgb-linear');
        } else {
          col.setRGB(Math.pow(bc[0], 1 / 2.2), Math.pow(bc[1], 1 / 2.2), Math.pow(bc[2], 1 / 2.2));
        }
        const isPlush = rough >= 0.78 && metal < 0.1;
        return new THREE.MeshStandardMaterial({
          name: m.name || 'CritterV11Mat',
          color: col,
          roughness: rough,
          metalness: metal,
          bumpMap: isPlush ? bumpTex : null,
          bumpScale: isPlush ? 0.005 : 0.0,
          side: THREE.DoubleSide
        });
      });
      const fallbackMat = new THREE.MeshStandardMaterial({ color: 0xcccccc, roughness: 0.8 });

      // Scale & offset from Blender critter-3d space (feet=0.275, crown=4.6..5.8) to Studio space (feet=0.0, height~2.05)
      const SCALE = 0.44;
      const Y_OFFSET = -0.275 * SCALE;
      const NECK_PIVOT_Y = 2.75 * SCALE + Y_OFFSET;
      const PENDANT_PIVOT_Y = 2.58 * SCALE + Y_OFFSET;
      const PENDANT_PIVOT_Z = 0.46 * SCALE;

      const v11Body = new THREE.Group();
      v11Body.name = 'CritterV11_Body_Group';
      const v11Head = new THREE.Group();
      v11Head.name = 'CritterV11_Head_Group';
      const v11Pendant = new THREE.Group();
      v11Pendant.name = 'CritterV11_Pendant_Group';

      function processNode(nodeIdx, parentMat) {
        const node = gltf.nodes[nodeIdx];
        const localMat = new THREE.Matrix4();
        if (node.matrix) {
          localMat.fromArray(node.matrix);
        } else {
          const pos = node.translation ? new THREE.Vector3(...node.translation) : new THREE.Vector3();
          const quat = node.rotation ? new THREE.Quaternion(...node.rotation) : new THREE.Quaternion();
          const scl = node.scale ? new THREE.Vector3(...node.scale) : new THREE.Vector3(1, 1, 1);
          localMat.compose(pos, quat, scl);
        }
        const worldMat = parentMat.clone().multiply(localMat);

        if (node.mesh !== undefined) {
          const meshDef = gltf.meshes[node.mesh];
          const nName = node.name || meshDef.name || '';
          const isHeadPart = /^(Head|Eye|Mouth|Nose|Wool|Ear|Crest)/i.test(nName) ||
            /(Ear panel|Forehead|Chin|Mouth lining|Floppy ear|Nostril)/i.test(nName);
          const isPendantPart = /^Pendant/i.test(nName);

          for (const prim of meshDef.primitives) {
            if (prim.attributes.POSITION === undefined) continue;
            const geo = new THREE.BufferGeometry();
            const posArr = getAccessorData(prim.attributes.POSITION);
            geo.setAttribute('position', new THREE.BufferAttribute(posArr, 3));
            if (prim.attributes.NORMAL !== undefined) {
              const normArr = getAccessorData(prim.attributes.NORMAL);
              geo.setAttribute('normal', new THREE.BufferAttribute(normArr, 3));
            }
            if (prim.indices !== undefined) {
              const idxArr = getAccessorData(prim.indices);
              geo.setIndex(new THREE.BufferAttribute(idxArr, 1));
            }
            geo.applyMatrix4(worldMat);
            // Convert glTF (+Z front) or Blender (-Y front -> +Z front in glTF) and apply SCALE + Y_OFFSET
            const scaleMat = new THREE.Matrix4().makeScale(SCALE, SCALE, SCALE);
            const transMat = new THREE.Matrix4().makeTranslation(0, Y_OFFSET, 0);
            geo.applyMatrix4(scaleMat);
            geo.applyMatrix4(transMat);
            if (!prim.attributes.NORMAL) geo.computeVertexNormals();

            const mat = (prim.material !== undefined && threeMats[prim.material]) ? threeMats[prim.material] : fallbackMat;
            const mesh = new THREE.Mesh(geo, mat);
            mesh.name = nName;
            mesh.castShadow = true;
            mesh.receiveShadow = true;

            if (isHeadPart) {
              geo.translate(0, -NECK_PIVOT_Y, 0);
              v11Head.add(mesh);
            } else if (isPendantPart) {
              geo.translate(0, -PENDANT_PIVOT_Y, -PENDANT_PIVOT_Z);
              v11Pendant.add(mesh);
            } else {
              v11Body.add(mesh);
            }
          }
        }
        if (node.children) {
          for (const ch of node.children) processNode(ch, worldMat);
        }
      }

      const sceneDef = gltf.scenes[gltf.scene || 0];
      const ident = new THREE.Matrix4();
      for (const rIdx of (sceneDef.nodes || [])) {
        processNode(rIdx, ident);
      }

      // Remove procedural placeholder meshes from bodyRig (preserving fartCloudGroup)
      const { root, bodyRig, headGroup, pendantGroup, fartCloudGroup } = rigGroups;
      const keepGroups = new Set([headGroup, pendantGroup, fartCloudGroup]);
      for (const child of [...bodyRig.children]) {
        if (!keepGroups.has(child)) {
          bodyRig.remove(child);
        }
      }
      if (headGroup) {
        headGroup.clear();
        headGroup.position.set(0, NECK_PIVOT_Y, 0);
        headGroup.rotation.set(0, 0, 0);
        headGroup.add(v11Head);
        if (headGroup.parent !== bodyRig) bodyRig.add(headGroup);
      }
      if (pendantGroup) {
        pendantGroup.clear();
        pendantGroup.position.set(0, PENDANT_PIVOT_Y, PENDANT_PIVOT_Z);
        pendantGroup.rotation.set(0, 0, 0);
        pendantGroup.add(v11Pendant);
        if (pendantGroup.parent !== bodyRig) bodyRig.add(pendantGroup);
      }
      bodyRig.add(v11Body);
    })
    .catch(err => {
      console.warn('CritterV11 GLB fallback to procedural:', err);
    });
}

/**
 * DogDay 3D Plush Base Model Generator (Three.js r161 ESM)
 * ============================================================================
 * 1:1 High-Precision 3D Recreation of `images/008_DogDay_Plushie.webp`
 * Official Poppy Playtime Chapter 3 (Smiling Critters) DogDay Plush
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
      if (mode === 'fleece') {
        const c1 = Math.sin(nx * Math.PI * 18) * Math.cos(ny * Math.PI * 18);
        const c2 = Math.sin((nx + ny) * Math.PI * 32) * Math.cos((nx - ny) * Math.PI * 32);
        const hash = Math.sin((x * 12.9898 + y * 78.233)) * 43758.5453;
        const grain = (hash - Math.floor(hash)) - 0.5;
        v = Math.max(0, Math.min(255, Math.floor(128 + 44 * c1 + 28 * c2 + 26 * grain)));
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
  tex.repeat.set(mode === 'fleece' ? 5 : 6, mode === 'fleece' ? 5 : 6);
  return tex;
}

export function buildDogDayPlushModel(THREE) {
  const root = new THREE.Group();
  root.name = 'DogDay_Plush_BaseModel';

  const bodyRig = new THREE.Group();
  bodyRig.name = 'Body_Rig_Root';
  root.add(bodyRig);

  const fleeceBump = createPlushBumpTexture(THREE, 'fleece');
  const velourBump = createPlushBumpTexture(THREE, 'velour');

  // Calibrated PBR Material Palette matched to `images/008_DogDay_Plushie.webp`
  const materials = {
    sunnyOrange: new THREE.MeshStandardMaterial({
      name: 'DogDay_Sunny_Orange_Fleece',
      color: 0xe87a24,
      roughness: 0.85,
      metalness: 0.02,
      bumpMap: fleeceBump,
      bumpScale: 0.012
    }),
    goldenYellow: new THREE.MeshStandardMaterial({
      name: 'DogDay_Golden_Yellow_Plush',
      color: 0xf9c851,
      roughness: 0.80,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    rustOrange: new THREE.MeshStandardMaterial({
      name: 'DogDay_Rust_Orange_Plush',
      color: 0xd44820,
      roughness: 0.84,
      metalness: 0.02,
      bumpMap: fleeceBump,
      bumpScale: 0.011
    }),
    collarRed: new THREE.MeshStandardMaterial({
      name: 'DogDay_Collar_Belt_Red',
      color: 0xb82914,
      roughness: 0.76,
      metalness: 0.04,
      bumpMap: velourBump,
      bumpScale: 0.006
    }),
    noseBrown: new THREE.MeshStandardMaterial({
      name: 'DogDay_Nose_Dark_Brown',
      color: 0x24140e,
      roughness: 0.24,
      metalness: 0.06
    }),
    tongueRed: new THREE.MeshStandardMaterial({
      name: 'DogDay_Tongue_Coral_Red',
      color: 0xe63946,
      roughness: 0.72,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.006
    }),
    sunRayOrange: new THREE.MeshStandardMaterial({
      name: 'DogDay_Sun_Pendant_Rays',
      color: 0xf26419,
      roughness: 0.34,
      metalness: 0.22
    }),
    sunCenterGold: new THREE.MeshStandardMaterial({
      name: 'DogDay_Sun_Pendant_Gold',
      color: 0xffd147,
      roughness: 0.28,
      metalness: 0.38
    }),
    mouthCavity: new THREE.MeshBasicMaterial({
      name: 'DogDay_Recessed_Mouth_Void',
      color: 0x050507,
      side: THREE.DoubleSide
    }),
    glossyEye: new THREE.MeshPhysicalMaterial({
      name: 'DogDay_Glossy_Acrylic_Eye',
      color: 0x020204,
      roughness: 0.05,
      metalness: 0.0,
      envMapIntensity: 0.14,
      clearcoat: 1.0,
      clearcoatRoughness: 0.04,
      reflectivity: 0.95
    }),
    eyeHighlight: new THREE.MeshBasicMaterial({
      name: 'DogDay_Eye_Studio_Catchlight',
      color: 0xffffff
    }),
    seamDark: new THREE.MeshStandardMaterial({
      name: 'DogDay_Plush_Seam_Groove',
      color: 0x141010,
      roughness: 0.90,
      metalness: 0.04
    }),
    fartLime: new THREE.MeshStandardMaterial({
      name: 'DogDay_Fart_Cloud_Lime',
      color: 0x4ce629,
      emissive: 0x228b12,
      emissiveIntensity: 0.35,
      roughness: 0.65,
      metalness: 0.02,
      bumpMap: fleeceBump,
      bumpScale: 0.015
    }),
    fartNeon: new THREE.MeshStandardMaterial({
      name: 'DogDay_Fart_Cloud_Neon_YellowGreen',
      color: 0xc4ff33,
      emissive: 0x84cc16,
      emissiveIntensity: 0.50,
      roughness: 0.45,
      metalness: 0.05
    }),
    fartPurple: new THREE.MeshStandardMaterial({
      name: 'DogDay_Fart_Cloud_Purple',
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
  // 1. TORSO (Pear-Shaped Sunny Orange Body + Golden-Yellow Belly Patch)
  // ============================================================================
  const torsoGroup = new THREE.Group();
  torsoGroup.name = 'Torso_And_SunPendant_Group';
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
  const torsoMesh = new THREE.Mesh(torsoGeo, materials.sunnyOrange);
  torsoMesh.castShadow = true;
  torsoMesh.receiveShadow = true;
  torsoGroup.add(torsoMesh);

  // Golden-Yellow Belly Patch conformed to front torso
  const bellyGeo = new THREE.SphereGeometry(1, 32, 24);
  const bPos = bellyGeo.attributes.position;
  for (let i = 0; i < bPos.count; i++) {
    const x = bPos.getX(i) * 0.195;
    const y = 0.735 + bPos.getY(i) * 0.215;
    const z = bPos.getZ(i);
    const zSurf = torsoFrontZ(y, x);
    const rz = z > 0 ? zSurf + 0.006 * z : zSurf - 0.015;
    bPos.setXYZ(i, x, y, rz);
  }
  bellyGeo.computeVertexNormals();
  const bellyMesh = new THREE.Mesh(bellyGeo, materials.goldenYellow);
  bellyMesh.castShadow = true;
  torsoGroup.add(bellyMesh);

  // Red Collar Trim Ring & Zipper Border Piping
  const collarRing = new THREE.Mesh(
    new THREE.TorusGeometry(0.185, 0.016, 12, 32),
    materials.collarRed
  );
  collarRing.position.set(0, 1.03, 0.01);
  collarRing.rotation.x = Math.PI / 2 + 0.06;
  torsoGroup.add(collarRing);

  // ============================================================================
  // 2. ZIPPER TRACK, RED/GOLD TRIM & ICONIC GOLDEN SUN PENDANT CHARM
  // ============================================================================
  const zipperGroup = new THREE.Group();
  zipperGroup.name = 'Zipper_Hardware_Group';
  torsoGroup.add(zipperGroup);

  const trackSegGeo = new THREE.BoxGeometry(0.026, 0.018, 0.014);
  const trimSegGeo = new THREE.BoxGeometry(0.012, 0.018, 0.015);
  for (let i = 0; i < 30; i++) {
    const ty = 0.505 + i * 0.0165;
    const zSurf = torsoFrontZ(ty, 0);

    const backSeg = new THREE.Mesh(trackSegGeo, materials.seamDark);
    backSeg.position.set(0, ty, zSurf + 0.004);
    zipperGroup.add(backSeg);

    [-0.018, 0.018].forEach(sx => {
      const trimSeg = new THREE.Mesh(trimSegGeo, materials.collarRed);
      trimSeg.position.set(sx, ty, zSurf + 0.005);
      zipperGroup.add(trimSeg);
    });
  }

  const zCollar = torsoFrontZ(0.985, 0);
  const sliderBody = new THREE.Mesh(new THREE.BoxGeometry(0.046, 0.052, 0.032), materials.sunRayOrange);
  sliderBody.position.set(0, 0.988, zCollar + 0.010);
  sliderBody.rotation.x = -0.20;
  zipperGroup.add(sliderBody);

  // Golden Sun Pendant Group (`sunPendantGroup` / `skullPendantGroup`)
  const zChest = torsoFrontZ(0.84, 0);
  const sunPendantGroup = new THREE.Group();
  sunPendantGroup.name = 'Sun_Pendant_Group';
  sunPendantGroup.position.set(0, 0.94, zChest + 0.018);
  sunPendantGroup.rotation.x = -0.06;
  torsoGroup.add(sunPendantGroup);

  // 10-Ray Wavy Starburst Sun Charm (#F26419)
  const sunRayShape = new THREE.Shape();
  const nRays = 10;
  const totalPts = nRays * 8;
  for (let i = 0; i <= totalPts; i++) {
    const ang = (i / totalPts) * Math.PI * 2;
    const wave = Math.pow(0.5 * (1.0 + Math.cos(nRays * ang)), 0.72);
    const r = 0.088 + 0.052 * wave;
    const px = Math.cos(ang) * r;
    const py = -0.115 + Math.sin(ang) * r;
    if (i === 0) sunRayShape.moveTo(px, py);
    else sunRayShape.lineTo(px, py);
  }
  const sunRayExtrude = new THREE.ExtrudeGeometry(sunRayShape, {
    depth: 0.022,
    bevelEnabled: true,
    bevelSegments: 3,
    steps: 1,
    bevelSize: 0.006,
    bevelThickness: 0.006
  });
  const sunRaysMesh = new THREE.Mesh(sunRayExtrude, materials.sunRayOrange);
  sunRaysMesh.position.set(0, 0, -0.011);
  sunRaysMesh.castShadow = true;
  sunPendantGroup.add(sunRaysMesh);

  // Dark outline torus ring around the Golden Center Disc
  const sunRim = new THREE.Mesh(
    new THREE.TorusGeometry(0.078, 0.0065, 12, 32),
    materials.noseBrown
  );
  sunRim.position.set(0, -0.115, 0.016);
  sunPendantGroup.add(sunRim);

  // Raised Golden-Yellow Sun Disc Center (#FFD147)
  const sunCenterGeo = new THREE.SphereGeometry(0.075, 28, 20);
  sunCenterGeo.scale(1.0, 1.0, 0.34);
  const sunCenterMesh = new THREE.Mesh(sunCenterGeo, materials.sunCenterGold);
  sunCenterMesh.position.set(0, -0.115, 0.012);
  sunPendantGroup.add(sunCenterMesh);

  // ============================================================================
  // 3. ARMS & RUST-ORANGE / GOLDEN-YELLOW PAWS
  // ============================================================================
  function createArm(side) {
    const armGroup = new THREE.Group();
    armGroup.name = side < 0 ? 'Left_Arm_Group' : 'Right_Arm_Group';
    armGroup.position.set(side * 0.195, 0.955, 0.01);
    armGroup.rotation.z = side * 0.72;
    torsoGroup.add(armGroup);

    const sleeveGeo = new THREE.CylinderGeometry(0.078, 0.098, 0.30, 24, 10);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, materials.sunnyOrange);
    sleeveMesh.position.set(0, -0.14, 0);
    sleeveMesh.castShadow = true;
    armGroup.add(sleeveMesh);

    const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.078, 18, 14), materials.sunnyOrange);
    armGroup.add(shoulderCap);

    const pawGroup = new THREE.Group();
    pawGroup.position.set(0, -0.335, 0.01);
    armGroup.add(pawGroup);

    const pawGeo = new THREE.SphereGeometry(0.110, 28, 20);
    pawGeo.scale(1.04, 1.15, 0.88);
    const pawMesh = new THREE.Mesh(pawGeo, materials.rustOrange);
    pawMesh.castShadow = true;
    pawGroup.add(pawMesh);

    // Golden-yellow inner palm pad
    const palmPad = new THREE.Mesh(
      new THREE.SphereGeometry(0.056, 16, 12),
      materials.goldenYellow
    );
    palmPad.scale.set(1.0, 1.12, 0.45);
    palmPad.position.set(0, -0.01, 0.082);
    pawGroup.add(palmPad);

    return armGroup;
  }

  const leftArmGroup = createArm(-1);
  const rightArmGroup = createArm(1);

  // ============================================================================
  // 4. LEGS, RUST-ORANGE FEET & GOLDEN-YELLOW SOLES + WAGGING DOG TAIL
  // ============================================================================
  function createLeg(side) {
    const legGroup = new THREE.Group();
    legGroup.name = side < 0 ? 'Left_Leg_Group' : 'Right_Leg_Group';
    legGroup.position.set(side * 0.14, 0.50, 0.0);
    legGroup.rotation.z = side * 0.075;
    bodyRig.add(legGroup);

    const legGeo = new THREE.CylinderGeometry(0.092, 0.098, 0.34, 24, 10);
    const legMesh = new THREE.Mesh(legGeo, materials.sunnyOrange);
    legMesh.position.set(0, -0.17, 0);
    legMesh.castShadow = true;
    legGroup.add(legMesh);

    const footGeo = new THREE.SphereGeometry(0.122, 28, 22);
    const fPos = footGeo.attributes.position;
    for (let i = 0; i < fPos.count; i++) {
      let x = fPos.getX(i) * 1.06;
      let y = fPos.getY(i);
      let z = fPos.getZ(i) * 1.18;
      if (y < 0) y *= 0.68;
      else y *= 0.92;
      fPos.setXYZ(i, x, y, z);
    }
    footGeo.computeVertexNormals();
    const footMesh = new THREE.Mesh(footGeo, materials.rustOrange);
    footMesh.position.set(0, -0.405, 0.03);
    footMesh.rotation.z = -side * 0.075;
    footMesh.castShadow = true;
    footMesh.receiveShadow = true;
    legGroup.add(footMesh);

    // Golden-yellow lower sole pad
    const soleMesh = new THREE.Mesh(new THREE.CylinderGeometry(0.112, 0.112, 0.025, 24), materials.goldenYellow);
    soleMesh.scale.set(1.0, 1.0, 1.15);
    soleMesh.position.set(0, -0.475, 0.03);
    soleMesh.rotation.z = -side * 0.075;
    legGroup.add(soleMesh);

    return legGroup;
  }

  const leftLegGroup = createLeg(-1);
  const rightLegGroup = createLeg(1);

  // Wagging Orange Dog Tail (`tailGroup`)
  const tailGroup = new THREE.Group();
  tailGroup.name = 'Tail_Group';
  tailGroup.position.set(0, 0.56, -0.20);
  bodyRig.add(tailGroup);

  const tailCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.00, 0.00, 0.00),
    new THREE.Vector3(0.05, 0.06, -0.12),
    new THREE.Vector3(0.11, 0.16, -0.20),
    new THREE.Vector3(0.14, 0.28, -0.22)
  ]);
  const tailGeo = new THREE.TubeGeometry(tailCurve, 20, 0.054, 14, false);
  const tailMesh = new THREE.Mesh(tailGeo, materials.sunnyOrange);
  tailMesh.castShadow = true;
  tailGroup.add(tailMesh);

  const tailTip = new THREE.Mesh(new THREE.SphereGeometry(0.056, 16, 12), materials.goldenYellow);
  tailTip.position.set(0.14, 0.28, -0.22);
  tailGroup.add(tailTip);

  // ============================================================================
  // 5. HEAD, FLOPPY SPANIEL EARS, EYE PATCH, EYES, GOLDEN MUZZLE & RED TONGUE
  // ============================================================================
  const headGroup = new THREE.Group();
  headGroup.name = 'Head_Group';
  headGroup.position.set(0, 1.06, 0);
  bodyRig.add(headGroup);

  const HEAD_RX = 0.455, HEAD_RY = 0.420, HEAD_RZ = 0.405, HEAD_CY = 0.44;
  function headFrontZ(x, y) {
    const nx = x / HEAD_RX;
    const ny = (y - HEAD_CY) / HEAD_RY;
    const r2 = nx * nx + ny * ny;
    if (r2 >= 0.96) return HEAD_RZ * 0.20;
    return HEAD_RZ * Math.sqrt(1.0 - r2);
  }

  // Base Sunny Orange Plush Head Sphere
  const headCoreGeo = new THREE.SphereGeometry(1, 44, 36);
  headCoreGeo.scale(HEAD_RX, HEAD_RY, HEAD_RZ);
  const headCore = new THREE.Mesh(headCoreGeo, materials.sunnyOrange);
  headCore.position.set(0, HEAD_CY, 0);
  headCore.castShadow = true;
  headGroup.add(headCore);

  // Cute top crown dog hair tufts (`woolGroup` compatibility handle)
  const woolGroup = new THREE.Group();
  woolGroup.name = 'Crown_Tufts_Group';
  headGroup.add(woolGroup);

  [
    [-0.05, 0.85, 0.04, 0.06, 0.09, 0.045, 0.25],
    [ 0.05, 0.86, 0.04, 0.065, 0.10, 0.045, -0.22]
  ].forEach(([tx, ty, tz, sx, sy, sz, rz]) => {
    const tMesh = new THREE.Mesh(new THREE.SphereGeometry(1, 16, 12), materials.sunnyOrange);
    tMesh.position.set(tx, ty, tz);
    tMesh.scale.set(sx, sy, sz);
    tMesh.rotation.z = rz;
    woolGroup.add(tMesh);
  });

  // ============================================================================
  // 6. LONG FLOPPY SPANIEL DOG EARS (`leftEarGroup`, `rightEarGroup`)
  // ============================================================================
  function createSpanielEar(side) {
    const earGroup = new THREE.Group();
    earGroup.name = side < 0 ? 'Left_Ear_Group' : 'Right_Ear_Group';
    earGroup.position.set(side * 0.30, 0.72, 0.02);
    headGroup.add(earGroup);

    const earCurvePts = [];
    for (let k = 0; k <= 16; k++) {
      const t = k / 16;
      let ex, ey, ez;
      if (t < 0.25) {
        const u = t / 0.25;
        ex = side * (0.16 * u);
        ey = 0.08 * Math.sin(u * Math.PI * 0.85);
        ez = 0.02 * u;
      } else {
        const u = (t - 0.25) / 0.75;
        ex = side * (0.16 + 0.10 * Math.sin(u * Math.PI * 0.75));
        ey = 0.04 - 0.66 * Math.pow(u, 1.08);
        ez = 0.02 + 0.05 * Math.sin(u * Math.PI * 0.8);
      }
      earCurvePts.push(new THREE.Vector3(ex, ey, ez));
    }
    const earCurve = new THREE.CatmullRomCurve3(earCurvePts);
    const earGeo = new THREE.TubeGeometry(earCurve, 28, 0.11, 18, false);
    const ePos = earGeo.attributes.position;
    for (let i = 0; i < ePos.count; i++) {
      let x = ePos.getX(i);
      let y = ePos.getY(i);
      let z = ePos.getZ(i);
      // Flatten thickness laterally and widen into a soft spaniel ear paddle towards the bottom
      const drop = Math.max(0, Math.min(1, (0.06 - y) / 0.68));
      const paddleWidth = 0.85 + 0.65 * Math.sin(drop * Math.PI * 0.88);
      z *= paddleWidth * 1.15;
      ePos.setXYZ(i, x, y, z);
    }
    earGeo.computeVertexNormals();
    const earOuterMesh = new THREE.Mesh(earGeo, materials.rustOrange);
    earOuterMesh.castShadow = true;
    earGroup.add(earOuterMesh);

    // Rounded ear paddle lobe cap at bottom tip
    const tipCap = new THREE.Mesh(new THREE.SphereGeometry(0.115, 20, 14), materials.rustOrange);
    tipCap.scale.set(0.55, 0.85, 1.25);
    tipCap.position.copy(earCurvePts[earCurvePts.length - 1]);
    earGroup.add(tipCap);

    // Golden-yellow inner ear lining
    const innerGeo = earGeo.clone();
    innerGeo.scale(0.86, 0.94, 0.75);
    const earInnerMesh = new THREE.Mesh(innerGeo, materials.goldenYellow);
    earInnerMesh.position.set(-side * 0.018, -0.01, 0.024);
    earGroup.add(earInnerMesh);

    return earGroup;
  }

  const leftEarGroup = createSpanielEar(-1);
  const rightEarGroup = createSpanielEar(1);

  // ============================================================================
  // 7. LEFT EYE PATCH, GOLDEN-YELLOW EYE RING & LARGE GLOSSY BLACK DOME EYES
  // ============================================================================
  const eyesGroup = new THREE.Group();
  eyesGroup.name = 'Eyes_And_Patch_Group';
  headGroup.add(eyesGroup);

  // Character's left eye patch (viewer's right, side = +1)
  const patchRingGeo = new THREE.SphereGeometry(0.165, 28, 20);
  patchRingGeo.scale(1.05, 1.02, 0.42);
  const patchRing = new THREE.Mesh(patchRingGeo, materials.goldenYellow);
  patchRing.position.set(0.148, 0.485, headFrontZ(0.148, 0.485) - 0.028);
  patchRing.rotation.y = 0.22;
  patchRing.rotation.z = -0.12;
  eyesGroup.add(patchRing);

  const patchInnerGeo = new THREE.SphereGeometry(0.152, 28, 20);
  patchInnerGeo.scale(1.04, 1.00, 0.45);
  const patchInner = new THREE.Mesh(patchInnerGeo, materials.rustOrange);
  patchInner.position.set(0.148, 0.485, headFrontZ(0.148, 0.485) - 0.020);
  patchInner.rotation.y = 0.22;
  patchInner.rotation.z = -0.12;
  eyesGroup.add(patchInner);

  function createEyeAssembly(side) {
    const ex = side * 0.145;
    const ey = 0.482;
    const ez = headFrontZ(ex, ey) - 0.012;

    const eyeWrap = new THREE.Group();
    eyeWrap.position.set(ex, ey, ez);
    eyeWrap.rotation.y = side * 0.20;
    eyesGroup.add(eyeWrap);

    const socketGeo = new THREE.SphereGeometry(0.098, 24, 18);
    socketGeo.scale(1.10, 1.04, 0.56);
    const socketMesh = new THREE.Mesh(socketGeo, side < 0 ? materials.goldenYellow : materials.rustOrange);
    socketMesh.position.set(0, 0, -0.008);
    eyeWrap.add(socketMesh);

    const eyeSphereGeo = new THREE.SphereGeometry(0.094, 32, 24);
    eyeSphereGeo.scale(1.04, 1.02, 0.72);
    const eyeMesh = new THREE.Mesh(eyeSphereGeo, materials.glossyEye);
    eyeWrap.add(eyeMesh);

    // Bright studio catchlights
    const catchGeo = new THREE.SphereGeometry(1, 14, 10);
    catchGeo.scale(0.018, 0.026, 0.006);
    const catchMesh = new THREE.Mesh(catchGeo, materials.eyeHighlight);
    catchMesh.position.set(-side * 0.022, 0.020, 0.066);
    eyeWrap.add(catchMesh);

    const catch2 = new THREE.Mesh(new THREE.SphereGeometry(0.008, 10, 8), materials.eyeHighlight);
    catch2.position.set(side * 0.024, -0.024, 0.063);
    eyeWrap.add(catch2);

    // Cheerful arched eyebrow above eye
    const browCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-side * 0.065, 0.125, 0.025),
      new THREE.Vector3(0, 0.152, 0.032),
      new THREE.Vector3(side * 0.072, 0.118, 0.020)
    ]);
    const browMesh = new THREE.Mesh(new THREE.TubeGeometry(browCurve, 12, 0.011, 8, false), materials.noseBrown);
    eyeWrap.add(browMesh);
  }

  createEyeAssembly(-1);
  createEyeAssembly(1);

  // ============================================================================
  // 8. GOLDEN-YELLOW MUZZLE RIM, DARK BROWN DOG NOSE, WIDE GRIN & RED TONGUE
  // ============================================================================
  const jawGroup = new THREE.Group();
  jawGroup.name = 'Muzzle_And_Jaw_Group';
  headGroup.add(jawGroup);

  function upperLipPoint(t) {
    const x = t * 0.395;
    const snoutArch = 0.028 * Math.exp(-Math.pow(t / 0.42, 2));
    const cheekLift = 0.038 * Math.pow(Math.abs(t), 1.5) * (1.0 - 0.28 * Math.pow(t, 4));
    const y = 0.365 + snoutArch + cheekLift - 0.032 * Math.pow(t, 6);
    const zBase = headFrontZ(x, y);
    const zSnout = 0.022 + 0.018 * Math.cos(t * (Math.PI * 0.46));
    return new THREE.Vector3(x, y, zBase + zSnout);
  }

  function lowerLipPoint(t) {
    const ang = t * (Math.PI * 0.49);
    const x = Math.sin(ang) * 0.395;
    const y = 0.362 - Math.cos(ang) * 0.320;
    const zBase = headFrontZ(x, y);
    const zArch = 0.018 + 0.010 * Math.cos(ang * 0.85);
    return new THREE.Vector3(x, y, zBase + zArch);
  }

  // Recessed black mouth cavity
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
  jawGroup.add(new THREE.Mesh(mouthPlateGeo, materials.mouthCavity));

  // Upper Golden-Yellow Muzzle & Lip Tube
  const upperLipPts = [];
  for (let i = 0; i <= 36; i++) {
    upperLipPts.push(upperLipPoint((i / 36) * 2.0 - 1.0));
  }
  const upperLipGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(upperLipPts), 48, 0.036, 20, false);
  const ulPos = upperLipGeo.attributes.position;
  for (let i = 0; i < ulPos.count; i++) {
    const ux = ulPos.getX(i);
    let uy = ulPos.getY(i);
    let uz = ulPos.getZ(i);
    const centerFactor = Math.exp(-Math.pow(ux / 0.18, 2));
    if (uy > 0.372) uy += (uy - 0.372) * 0.45 * centerFactor;
    const zSurf = headFrontZ(ux, uy);
    if (uz < zSurf + 0.022) uz -= 0.032;
    ulPos.setXYZ(i, ux, uy, uz);
  }
  upperLipGeo.computeVertexNormals();
  const upperLipMesh = new THREE.Mesh(upperLipGeo, materials.goldenYellow);
  upperLipMesh.castShadow = true;
  jawGroup.add(upperLipMesh);

  // Dark Brown Rounded Triangular Dog Nose
  const pNoseBase = upperLipPoint(0);
  const noseGeo = new THREE.SphereGeometry(0.066, 24, 18);
  noseGeo.scale(1.18, 0.78, 0.75);
  const noseMesh = new THREE.Mesh(noseGeo, materials.noseBrown);
  noseMesh.position.set(0, pNoseBase.y + 0.038, pNoseBase.z + 0.036);
  noseMesh.rotation.x = -0.18;
  jawGroup.add(noseMesh);

  // Lower Golden-Yellow Lip Deep U-Curve
  const lowerLipPts = [];
  for (let i = 0; i <= 36; i++) {
    lowerLipPts.push(lowerLipPoint((i / 36) * 2.0 - 1.0));
  }
  const lowerLipGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(lowerLipPts), 48, 0.032, 18, false);
  const llPos = lowerLipGeo.attributes.position;
  for (let i = 0; i < llPos.count; i++) {
    const lx = llPos.getX(i);
    const ly = llPos.getY(i);
    let lz = llPos.getZ(i);
    const zSurf = headFrontZ(lx, ly);
    if (lz < zSurf + 0.018) lz -= 0.036;
    llPos.setXYZ(i, lx, ly, lz);
  }
  lowerLipGeo.computeVertexNormals();
  const lowerLipMesh = new THREE.Mesh(lowerLipGeo, materials.goldenYellow);
  lowerLipMesh.castShadow = true;
  jawGroup.add(lowerLipMesh);

  // Cheek Corner Caps & Furry Golden-Yellow Cheek Tufts
  [-1, 1].forEach(side => {
    const pCorner = upperLipPoint(side);
    const cornerCap = new THREE.Mesh(new THREE.SphereGeometry(0.038, 16, 12), materials.goldenYellow);
    cornerCap.position.copy(pCorner);
    jawGroup.add(cornerCap);

    const cheekTuft = new THREE.Mesh(new THREE.SphereGeometry(0.042, 14, 10), materials.goldenYellow);
    cheekTuft.scale.set(1.35, 0.65, 0.75);
    cheekTuft.position.set(pCorner.x + side * 0.025, pCorner.y + 0.01, pCorner.z - 0.01);
    cheekTuft.rotation.z = -side * 0.35;
    jawGroup.add(cheekTuft);
  });

  // Cheerful Coral-Red Plush Tongue inside lower mouth cavity
  const tongueGeo = new THREE.SphereGeometry(0.105, 24, 18);
  tongueGeo.scale(1.05, 0.88, 0.32);
  const tongueMesh = new THREE.Mesh(tongueGeo, materials.tongueRed);
  tongueMesh.position.set(0, 0.145, headFrontZ(0, 0.145) + 0.016);
  tongueMesh.rotation.x = -0.36;
  jawGroup.add(tongueMesh);

  // ============================================================================
  // 9. 3D SCULPTED CARTOON FART CLOUD CLUSTER (FOR `DogDay_Fart_Blast` ANIMATION)
  // ============================================================================
  const fartCloudGroup = new THREE.Group();
  fartCloudGroup.name = 'DogDay_Fart_Cloud_Group';
  fartCloudGroup.visible = false;
  root.add(fartCloudGroup);

  const basePuffGeo = new THREE.SphereGeometry(1, 18, 14);
  const fpPos = basePuffGeo.attributes.position;
  for (let i = 0; i < fpPos.count; i++) {
    const vx = fpPos.getX(i);
    const vy = fpPos.getY(i);
    const vz = fpPos.getZ(i);
    const disp = 1.0 + 0.07 * Math.sin(vx * 7.0) * Math.cos(vy * 7.0) * Math.sin(vz * 7.0);
    fpPos.setXYZ(i, vx * disp, vy * disp, vz * disp);
  }
  basePuffGeo.computeVertexNormals();

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
    const p = new THREE.Mesh(basePuffGeo, mat);
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
    const p = new THREE.Mesh(basePuffGeo, mat);
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
    const p = new THREE.Mesh(basePuffGeo, mat);
    p.position.set(fx, fy, fz);
    p.scale.set(sx, sy, sz);
    fartStage3.add(p);
  });


  loadCritterV11GLB(THREE, './models/dogday_plush_base_model.glb', { root, bodyRig, headGroup, pendantGroup: skullPendantGroup, fartCloudGroup }, velourBump);

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
    sunPendantGroup,
    skullPendantGroup: sunPendantGroup,
    tailGroup,
    fartCloudGroup,
    fartStage1,
    fartStage2,
    fartStage3,
    materials
  };
}

export { buildDogDayPlushModel as buildBabaChopsPlushModel };
