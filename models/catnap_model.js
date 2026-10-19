
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
 * CatNap 3D Plush Base Model Generator (Three.js r161 ESM)
 * ============================================================================
 * 1:1 High-Precision 3D Recreation of `images/022_CatNap_Plushie.webp` & `images/035_Catnapplush.webp`
 * Official Poppy Playtime Chapter 3 (Smiling Critters) CatNap Plush
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
      if (mode === 'cloud') {
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
  tex.repeat.set(mode === 'cloud' ? 4 : 6, mode === 'cloud' ? 4 : 6);
  return tex;
}

export function buildCatNapPlushModel(THREE) {
  const root = new THREE.Group();
  root.name = 'CatNap_Plush_BaseModel';

  const bodyRig = new THREE.Group();
  bodyRig.name = 'Body_Rig_Root';
  root.add(bodyRig);

  const velourBump = createPlushBumpTexture(THREE, 'velour');
  const cloudBump = createPlushBumpTexture(THREE, 'cloud');

  const materials = {
    purplePlush: new THREE.MeshStandardMaterial({
      name: 'CatNap_Royal_Purple_Plush',
      color: 0x6b3fa0,
      roughness: 0.82,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.010
    }),
    pastelLavender: new THREE.MeshStandardMaterial({
      name: 'CatNap_Pastel_Lavender_Plush',
      color: 0xb89ce0,
      roughness: 0.78,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    darkPawPurple: new THREE.MeshStandardMaterial({
      name: 'CatNap_Dark_Paw_Purple',
      color: 0x4a2574,
      roughness: 0.84,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.009
    }),
    seamPurple: new THREE.MeshStandardMaterial({
      name: 'CatNap_Deep_Violet_Seam',
      color: 0x311652,
      roughness: 0.88,
      metalness: 0.02
    }),
    mouthCavity: new THREE.MeshBasicMaterial({
      name: 'CatNap_Recessed_Mouth_Void',
      color: 0x040406,
      side: THREE.DoubleSide
    }),
    voiceBoxDark: new THREE.MeshStandardMaterial({
      name: 'CatNap_Mouth_VoiceBox_Disc',
      color: 0x0e0e14,
      roughness: 0.72,
      metalness: 0.08
    }),
    glossyEye: new THREE.MeshPhysicalMaterial({
      name: 'CatNap_Glossy_Acrylic_Eye',
      color: 0x020204,
      roughness: 0.05,
      metalness: 0.0,
      envMapIntensity: 0.14,
      clearcoat: 1.0,
      clearcoatRoughness: 0.03,
      reflectivity: 0.96
    }),
    eyeHighlight: new THREE.MeshBasicMaterial({
      name: 'CatNap_Eye_Crescent_Shine',
      color: 0xffffff
    }),
    noseBlack: new THREE.MeshStandardMaterial({
      name: 'CatNap_Velvet_Black_Nose',
      color: 0x0a0a0f,
      roughness: 0.65,
      metalness: 0.04
    }),
    goldPendant: new THREE.MeshStandardMaterial({
      name: 'CatNap_Gold_Crescent_Moon_Pendant',
      color: 0xf5c518,
      emissive: 0x423000,
      emissiveIntensity: 0.12,
      roughness: 0.24,
      metalness: 0.78
    }),
    metalZipper: new THREE.MeshStandardMaterial({
      name: 'CatNap_Zipper_Hardware',
      color: 0xc8cdd6,
      roughness: 0.28,
      metalness: 0.82
    }),
    zipperTrack: new THREE.MeshStandardMaterial({
      name: 'CatNap_Zipper_Track_Black',
      color: 0x0e0e13,
      roughness: 0.88,
      metalness: 0.02
    }),
    fartLime: new THREE.MeshStandardMaterial({
      name: 'CatNap_Fart_Cloud_Lime',
      color: 0x4ce629,
      emissive: 0x228b12,
      emissiveIntensity: 0.35,
      roughness: 0.65,
      metalness: 0.02,
      bumpMap: cloudBump,
      bumpScale: 0.015
    }),
    fartNeon: new THREE.MeshStandardMaterial({
      name: 'CatNap_Fart_Cloud_Neon_YellowGreen',
      color: 0xc4ff33,
      emissive: 0x84cc16,
      emissiveIntensity: 0.50,
      roughness: 0.45,
      metalness: 0.05
    }),
    fartPurple: new THREE.MeshStandardMaterial({
      name: 'CatNap_Fart_Cloud_RedGas_Purple',
      color: 0x9d4edd,
      emissive: 0x5b21b6,
      emissiveIntensity: 0.38,
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
  // 1. TORSO (Pear-Shaped Royal Purple Plush Body + Pastel Lavender Belly Patch)
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
      const seamDepth = (1.0 - Math.abs(rx) / 0.036) * 0.008;
      rz -= seamDepth;
    }
    tPos.setXYZ(i, rx, ry, rz);
  }
  torsoGeo.computeVertexNormals();
  const torsoMesh = new THREE.Mesh(torsoGeo, materials.purplePlush);
  torsoMesh.castShadow = true;
  torsoMesh.receiveShadow = true;
  torsoGroup.add(torsoMesh);

  // Pastel Lavender Belly Patch conformed onto front torso
  const bellyGeo = new THREE.SphereGeometry(1, 32, 24, 0, Math.PI * 2, 0, Math.PI * 0.45);
  const bPos = bellyGeo.attributes.position;
  for (let i = 0; i < bPos.count; i++) {
    const u = bPos.getX(i);
    const v = bPos.getZ(i);
    const bx = u * 0.185 * (1.0 - 0.18 * v);
    const by = 0.735 - v * 0.215;
    const bz = torsoFrontZ(by, bx) + 0.004;
    bPos.setXYZ(i, bx, by, bz);
  }
  bellyGeo.computeVertexNormals();
  const bellyMesh = new THREE.Mesh(bellyGeo, materials.pastelLavender);
  bellyMesh.receiveShadow = true;
  torsoGroup.add(bellyMesh);

  // ============================================================================
  // 2. BLACK ZIPPER TRACK, GOLD SLIDER & ICONIC GOLD CRESCENT MOON PENDANT
  // ============================================================================
  const zipperGroup = new THREE.Group();
  zipperGroup.name = 'Zipper_Hardware_Group';
  torsoGroup.add(zipperGroup);

  const toothGeo = new THREE.BoxGeometry(0.019, 0.0085, 0.018);
  const backingSegGeo = new THREE.BoxGeometry(0.040, 0.018, 0.014);
  for (let i = 0; i < 33; i++) {
    const ty = 0.495 + i * 0.0155;
    const zSurf = torsoFrontZ(ty, 0);
    const side = (i % 2 === 0) ? -0.007 : 0.007;

    const backSeg = new THREE.Mesh(backingSegGeo, materials.zipperTrack);
    backSeg.position.set(0, ty, zSurf - 0.002);
    zipperGroup.add(backSeg);

    const tooth = new THREE.Mesh(toothGeo, materials.metalZipper);
    tooth.position.set(side, ty, zSurf + 0.004);
    zipperGroup.add(tooth);
  }

  const zCollar = torsoFrontZ(0.985, 0);
  const sliderBody = new THREE.Mesh(new THREE.BoxGeometry(0.048, 0.056, 0.036), materials.goldPendant);
  sliderBody.position.set(0, 0.990, zCollar + 0.008);
  sliderBody.rotation.x = -0.22;
  zipperGroup.add(sliderBody);

  // Gold Crescent Moon Pendant Group (pivots at y = 0.935 on upper chest)
  const zChest = torsoFrontZ(0.80, 0);
  const pendantGroup = new THREE.Group();
  pendantGroup.name = 'Gold_Crescent_Moon_Pendant_Group';
  pendantGroup.position.set(0, 0.935, zChest + 0.014);
  pendantGroup.rotation.x = -0.08;
  torsoGroup.add(pendantGroup);

  const bailLoop = new THREE.Mesh(new THREE.BoxGeometry(0.036, 0.042, 0.024), materials.goldPendant);
  bailLoop.position.set(0, -0.012, 0.0);
  pendantGroup.add(bailLoop);

  // Build smooth 3D C-shaped Crescent Moon geometry
  const moonPts = [];
  const moonRadii = [];
  const rArc = 0.115;
  for (let i = 0; i <= 40; i++) {
    const t = i / 40;
    const ang = (0.28 + 1.44 * t) * Math.PI;
    const mx = 0.015 + Math.cos(ang) * rArc;
    const my = -0.145 + Math.sin(ang) * rArc;
    const sProf = Math.pow(Math.sin(Math.PI * t), 0.82);
    const radXY = 0.004 + 0.048 * sProf;
    moonPts.push(new THREE.Vector3(mx - Math.cos(ang) * radXY * 0.35, my - Math.sin(ang) * radXY * 0.35, 0));
    moonRadii.push(radXY);
  }
  const moonCurve = new THREE.CatmullRomCurve3(moonPts);
  const moonGeo = new THREE.TubeGeometry(moonCurve, 48, 0.042, 24, false);
  const mPos = moonGeo.attributes.position;
  for (let i = 0; i < mPos.count; i++) {
    const ringIdx = Math.min(48, Math.floor(i / 25));
    const u = ringIdx / 48;
    const centerPt = moonCurve.getPointAt(u);
    const taper = Math.pow(Math.sin(Math.PI * u), 0.80);
    const dx = (mPos.getX(i) - centerPt.x) * (0.08 + 1.15 * taper);
    const dy = (mPos.getY(i) - centerPt.y) * (0.08 + 1.15 * taper);
    const dz = (mPos.getZ(i) - centerPt.z) * (0.08 + 0.48 * taper);
    mPos.setXYZ(i, centerPt.x + dx, centerPt.y + dy, centerPt.z + dz);
  }
  moonGeo.computeVertexNormals();
  const moonMesh = new THREE.Mesh(moonGeo, materials.goldPendant);
  moonMesh.castShadow = true;
  pendantGroup.add(moonMesh);

  // ============================================================================
  // 3. SPLAYED PURPLE PLUSH ARMS & DARKER PURPLE CAT PAWS (#4A2574)
  // ============================================================================
  function createArm(side) {
    const armGroup = new THREE.Group();
    armGroup.name = side < 0 ? 'Left_Arm_Group' : 'Right_Arm_Group';
    armGroup.position.set(side * 0.195, 0.955, 0.01);
    armGroup.rotation.z = side * 0.72;
    torsoGroup.add(armGroup);

    const sleeveGeo = new THREE.CylinderGeometry(0.080, 0.102, 0.31, 24, 12);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, materials.purplePlush);
    sleeveMesh.position.set(0, -0.145, 0);
    sleeveMesh.castShadow = true;
    armGroup.add(sleeveMesh);

    const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.080, 20, 16), materials.purplePlush);
    armGroup.add(shoulderCap);

    const pawGroup = new THREE.Group();
    pawGroup.position.set(0, -0.34, 0.01);
    armGroup.add(pawGroup);

    const pawGeo = new THREE.SphereGeometry(0.114, 30, 22);
    pawGeo.scale(1.06, 1.14, 0.88);
    const pawMesh = new THREE.Mesh(pawGeo, materials.darkPawPurple);
    pawMesh.castShadow = true;
    pawGroup.add(pawMesh);

    // 2 cat toe-stitch seams on each paw
    const seamGeo = new THREE.CylinderGeometry(0.0035, 0.0035, 0.085, 8);
    [-0.032, 0.032].forEach(tx => {
      const seam = new THREE.Mesh(seamGeo, materials.seamPurple);
      seam.position.set(tx, -0.045, 0.082);
      seam.rotation.x = 0.35;
      pawGroup.add(seam);
    });

    return armGroup;
  }

  const leftArmGroup = createArm(-1);
  const rightArmGroup = createArm(1);

  // ============================================================================
  // 4. LEGS & DARKER PURPLE CAT FOOT PAWS (A-Stance Standing on y = 0.0)
  // ============================================================================
  function createLeg(side) {
    const legGroup = new THREE.Group();
    legGroup.name = side < 0 ? 'Left_Leg_Group' : 'Right_Leg_Group';
    legGroup.position.set(side * 0.14, 0.50, 0.0);
    legGroup.rotation.z = side * 0.07;
    bodyRig.add(legGroup);

    const legGeo = new THREE.CylinderGeometry(0.092, 0.098, 0.34, 24, 10);
    const legMesh = new THREE.Mesh(legGeo, materials.purplePlush);
    legMesh.position.set(0, -0.17, 0);
    legMesh.castShadow = true;
    legGroup.add(legMesh);

    const footGeo = new THREE.SphereGeometry(0.116, 28, 22);
    const fPos = footGeo.attributes.position;
    for (let i = 0; i < fPos.count; i++) {
      let x = fPos.getX(i) * 1.06;
      let y = fPos.getY(i);
      let z = fPos.getZ(i) * 1.16;
      y *= (y < 0) ? 0.72 : 0.92;
      fPos.setXYZ(i, x, y, z);
    }
    footGeo.computeVertexNormals();
    const footMesh = new THREE.Mesh(footGeo, materials.darkPawPurple);
    footMesh.position.set(0, -0.405, 0.02);
    footMesh.rotation.z = -side * 0.07;
    footMesh.castShadow = true;
    footMesh.receiveShadow = true;
    legGroup.add(footMesh);

    // 2 cat toe-stitch seams on front of each foot paw
    const fSeamGeo = new THREE.CylinderGeometry(0.0038, 0.0038, 0.092, 8);
    [-0.036, 0.036].forEach(tx => {
      const fSeam = new THREE.Mesh(fSeamGeo, materials.seamPurple);
      fSeam.position.set(tx, -0.415, 0.142);
      fSeam.rotation.x = -0.35;
      legGroup.add(fSeam);
    });

    return legGroup;
  }

  const leftLegGroup = createLeg(-1);
  const rightLegGroup = createLeg(1);

  // ============================================================================
  // 5. LONG CURLED PURPLE CAT TAIL (`Tail_Group`)
  // ============================================================================
  const tailGroup = new THREE.Group();
  tailGroup.name = 'Tail_Group';
  tailGroup.position.set(0, 0.52, -0.18);
  bodyRig.add(tailGroup);

  const tailCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.00, 0.00, 0.00),
    new THREE.Vector3(-0.14, -0.06, -0.06),
    new THREE.Vector3(-0.34, -0.16, -0.02),
    new THREE.Vector3(-0.52, -0.26, 0.10),
    new THREE.Vector3(-0.62, -0.34, 0.28),
    new THREE.Vector3(-0.58, -0.38, 0.46),
    new THREE.Vector3(-0.42, -0.40, 0.60),
    new THREE.Vector3(-0.18, -0.40, 0.66),
    new THREE.Vector3(0.08, -0.38, 0.62)
  ]);
  const tailGeo = new THREE.TubeGeometry(tailCurve, 52, 0.058, 20, false);
  const tailMesh = new THREE.Mesh(tailGeo, materials.purplePlush);
  tailMesh.castShadow = true;
  tailGroup.add(tailMesh);

  const tailTip = new THREE.Mesh(new THREE.SphereGeometry(0.058, 18, 14), materials.purplePlush);
  tailTip.position.set(0.08, -0.38, 0.62);
  tailGroup.add(tailTip);

  // ============================================================================
  // 6. WIDE CAT HEAD, POINTED TRIANGULAR CAT EARS, EYES, NOSE & GRINNING MOUTH
  // ============================================================================
  const headGroup = new THREE.Group();
  headGroup.name = 'Head_Group';
  headGroup.position.set(0, 1.06, 0);
  bodyRig.add(headGroup);

  const HEAD_RX = 0.50, HEAD_RY = 0.43, HEAD_RZ = 0.42, HEAD_CY = 0.44;
  function headFrontZ(x, y) {
    const nx = x / HEAD_RX;
    const ny = (y - HEAD_CY) / HEAD_RY;
    const r2 = nx * nx + ny * ny;
    if (r2 >= 0.96) return HEAD_RZ * 0.20;
    return HEAD_RZ * Math.sqrt(1.0 - r2);
  }

  // Wide Royal Purple Plush Cat Head with sculpted cheek flare
  const headCoreGeo = new THREE.SphereGeometry(1, 48, 36);
  const hPos = headCoreGeo.attributes.position;
  for (let i = 0; i < hPos.count; i++) {
    let x = hPos.getX(i) * HEAD_RX;
    let y = hPos.getY(i) * HEAD_RY;
    let z = hPos.getZ(i) * HEAD_RZ;
    const cheekFlare = 1.0 + 0.14 * Math.exp(-Math.pow((y + 0.06) / 0.18, 2));
    x *= cheekFlare;
    hPos.setXYZ(i, x, y + HEAD_CY, z);
  }
  headCoreGeo.computeVertexNormals();
  const headCore = new THREE.Mesh(headCoreGeo, materials.purplePlush);
  headCore.castShadow = true;
  headGroup.add(headCore);

  // Pointed Upright Triangular Cat Ears (Left & Right) with Pastel Lavender Inner Cups
  function createCatEar(side) {
    const earGroup = new THREE.Group();
    earGroup.name = side < 0 ? 'Left_Ear_Group' : 'Right_Ear_Group';
    earGroup.position.set(side * 0.27, 0.78, 0.02);
    earGroup.rotation.z = side * -0.22;
    earGroup.rotation.x = 0.06;
    headGroup.add(earGroup);

    // Outer purple plush triangular cat ear cone
    const outerGeo = new THREE.ConeGeometry(0.185, 0.38, 28, 12);
    outerGeo.scale(1.0, 1.0, 0.52);
    const outerMesh = new THREE.Mesh(outerGeo, materials.purplePlush);
    outerMesh.position.set(0, 0.16, 0);
    outerMesh.castShadow = true;
    earGroup.add(outerMesh);

    // Inner pastel lavender recessed triangle cup
    const innerGeo = new THREE.ConeGeometry(0.128, 0.30, 24, 8);
    innerGeo.scale(1.0, 1.0, 0.26);
    const innerMesh = new THREE.Mesh(innerGeo, materials.pastelLavender);
    innerMesh.position.set(0, 0.15, 0.042);
    earGroup.add(innerMesh);

    return earGroup;
  }

  const leftEarGroup = createCatEar(-1);
  const rightEarGroup = createCatEar(1);

  // ============================================================================
  // 7. LARGE GLOSSY BLACK EYES, WHITE CRESCENT EYE-SHINES & PURPLE BROW RIMS
  // ============================================================================
  const eyesGroup = new THREE.Group();
  eyesGroup.name = 'Eyes_And_Brows_Group';
  headGroup.add(eyesGroup);

  function createEyeAssembly(side) {
    const ex = side * 0.158;
    const ey = 0.515;
    const ez = headFrontZ(ex, ey) - 0.012;

    const eyeWrap = new THREE.Group();
    eyeWrap.position.set(ex, ey, ez);
    eyeWrap.rotation.y = side * 0.20;
    eyesGroup.add(eyeWrap);

    const socketGeo = new THREE.SphereGeometry(0.112, 28, 20);
    socketGeo.scale(1.08, 1.06, 0.58);
    const socketMesh = new THREE.Mesh(socketGeo, materials.seamPurple);
    socketMesh.position.set(0, 0, -0.008);
    eyeWrap.add(socketMesh);

    const eyeSphereGeo = new THREE.SphereGeometry(0.105, 36, 28);
    eyeSphereGeo.scale(1.05, 1.04, 0.74);
    const eyeMesh = new THREE.Mesh(eyeSphereGeo, materials.glossyEye);
    eyeWrap.add(eyeMesh);

    // Iconic White Crescent Eye-Shine arc inside upper-inner eye
    const cresPts = [];
    for (let k = 0; k <= 14; k++) {
      const t = k / 14;
      const ang = 0.32 * Math.PI + t * 0.86 * Math.PI;
      const lx = -side * 0.015 + Math.cos(ang) * 0.042;
      const ly = 0.010 + Math.sin(ang) * 0.042;
      cresPts.push(new THREE.Vector3(lx, ly, 0.076));
    }
    const cresCurve = new THREE.CatmullRomCurve3(cresPts);
    const cresGeo = new THREE.TubeGeometry(cresCurve, 20, 0.012, 12, false);
    const cresMesh = new THREE.Mesh(cresGeo, materials.eyeHighlight);
    eyeWrap.add(cresMesh);

    const catch2 = new THREE.Mesh(new THREE.SphereGeometry(0.009, 12, 10), materials.eyeHighlight);
    catch2.position.set(side * 0.032, -0.028, 0.072);
    eyeWrap.add(catch2);

    // Upper purple plush brow rim
    const browPts = [];
    for (let k = 0; k <= 16; k++) {
      const t = (k / 16) * 2.0 - 1.0;
      const bx = t * 0.112;
      const by = 0.088 - 0.038 * t * t;
      browPts.push(new THREE.Vector3(bx, by, 0.056 * (1.0 - 0.35 * t * t)));
    }
    const browGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(browPts), 20, 0.016, 12, false);
    const browMesh = new THREE.Mesh(browGeo, materials.purplePlush);
    eyeWrap.add(browMesh);
  }

  createEyeAssembly(-1);
  createEyeAssembly(1);

  // Black Triangular Cat Nose
  const noseShape = new THREE.Shape();
  noseShape.moveTo(0, -0.032);
  noseShape.quadraticCurveTo(0.048, 0.012, 0.042, 0.028);
  noseShape.quadraticCurveTo(0, 0.035, -0.042, 0.028);
  noseShape.quadraticCurveTo(-0.048, 0.012, 0, -0.032);
  const noseGeo = new THREE.ExtrudeGeometry(noseShape, {
    depth: 0.022,
    bevelEnabled: true,
    bevelSegments: 4,
    steps: 1,
    bevelSize: 0.008,
    bevelThickness: 0.008
  });
  noseGeo.center();
  const noseMesh = new THREE.Mesh(noseGeo, materials.noseBlack);
  noseMesh.position.set(0, 0.425, headFrontZ(0, 0.425) + 0.022);
  noseMesh.rotation.x = -0.14;
  headGroup.add(noseMesh);

  // ============================================================================
  // 8. WIDE CAVERNOUS BLACK GRINNING MOUTH, VOICEBOX DISC & PURPLE LIP RIMS
  // ============================================================================
  const jawGroup = new THREE.Group();
  jawGroup.name = 'Mouth_And_Jaw_Group';
  headGroup.add(jawGroup);

  function upperLipPoint(t) {
    const x = t * 0.445;
    const cheekLift = 0.095 * Math.pow(t, 2) - 0.015 * Math.pow(t, 4);
    const y = 0.355 + cheekLift;
    const zBase = headFrontZ(x, y);
    const zSnout = 0.018 + 0.012 * Math.cos(t * (Math.PI * 0.46));
    return new THREE.Vector3(x, y, zBase + zSnout);
  }

  function lowerLipPoint(t) {
    const ang = t * (Math.PI * 0.49);
    const x = Math.sin(ang) * 0.445;
    const y = 0.435 - Math.cos(ang) * 0.345;
    const zBase = headFrontZ(x, y);
    const zArch = 0.016 + 0.010 * Math.cos(ang * 0.85);
    return new THREE.Vector3(x, y, zBase + zArch);
  }

  const cavityCols = 40;
  const cavityRows = 16;
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

  // Subtle dark circular voicebox disc inside center of mouth cavity (matches 022_CatNap_Plushie.webp)
  const voiceDiscGeo = new THREE.CylinderGeometry(0.068, 0.068, 0.012, 24);
  const voiceDisc = new THREE.Mesh(voiceDiscGeo, materials.voiceBoxDark);
  voiceDisc.rotation.x = Math.PI / 2 - 0.16;
  voiceDisc.position.set(0, 0.245, headFrontZ(0, 0.245) + 0.006);
  jawGroup.add(voiceDisc);

  const upperLipPts = [];
  for (let i = 0; i <= 40; i++) {
    upperLipPts.push(upperLipPoint((i / 40) * 2.0 - 1.0));
  }
  const upperLipGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(upperLipPts), 56, 0.026, 20, false);
  const upperLipMesh = new THREE.Mesh(upperLipGeo, materials.purplePlush);
  upperLipMesh.castShadow = true;
  jawGroup.add(upperLipMesh);

  const lowerLipPts = [];
  for (let i = 0; i <= 40; i++) {
    lowerLipPts.push(lowerLipPoint((i / 40) * 2.0 - 1.0));
  }
  const lowerLipGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(lowerLipPts), 56, 0.025, 20, false);
  const lowerLipMesh = new THREE.Mesh(lowerLipGeo, materials.purplePlush);
  lowerLipMesh.castShadow = true;
  jawGroup.add(lowerLipMesh);

  [-1, 1].forEach(side => {
    const pCorner = upperLipPoint(side);
    const cornerCap = new THREE.Mesh(new THREE.SphereGeometry(0.030, 16, 12), materials.purplePlush);
    cornerCap.position.copy(pCorner);
    jawGroup.add(cornerCap);
  });

  // ============================================================================
  // 9. 3D SCULPTED CARTOON FART CLOUD CLUSTER (FOR `CatNap_Fart_Blast` ANIMATION)
  // ============================================================================
  const basePuffGeo = new THREE.SphereGeometry(1, 20, 16);
  const bpPos = basePuffGeo.attributes.position;
  for (let i = 0; i < bpPos.count; i++) {
    const vx = bpPos.getX(i);
    const vy = bpPos.getY(i);
    const vz = bpPos.getZ(i);
    const disp = 1.0 + 0.07 * Math.sin(vx * 7.0) * Math.cos(vy * 7.0) * Math.sin(vz * 7.0);
    bpPos.setXYZ(i, vx * disp, vy * disp, vz * disp);
  }
  basePuffGeo.computeVertexNormals();

  const fartCloudGroup = new THREE.Group();
  fartCloudGroup.name = 'CatNap_Fart_Cloud_Group';
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
    [0.07, -0.02, -0.15, 0.095, 0.09, 0.095, materials.fartPurple]
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
    [0.14, 0.03, -0.03, 0.155, 0.15, 0.155, materials.fartPurple],
    [0.00, 0.12, -0.06, 0.17, 0.16, 0.16, materials.fartNeon],
    [-0.11, -0.08, 0.02, 0.135, 0.12, 0.135, materials.fartLime],
    [0.11, -0.08, 0.02, 0.135, 0.12, 0.135, materials.fartLime],
    [0.00, 0.02, -0.16, 0.20, 0.19, 0.19, materials.fartLime],
    [-0.16, 0.08, -0.15, 0.15, 0.15, 0.15, materials.fartNeon],
    [0.16, 0.07, -0.15, 0.15, 0.15, 0.15, materials.fartPurple],
    [-0.09, 0.15, -0.18, 0.14, 0.135, 0.14, materials.fartLime],
    [0.09, 0.15, -0.18, 0.14, 0.135, 0.14, materials.fartPurple]
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


  loadCritterV11GLB(THREE, './models/catnap_plush_base_model.glb', { root, bodyRig, headGroup, pendantGroup: pendantGroup, fartCloudGroup }, velourBump);

  return {
    root,
    bodyRig,
    torsoGroup,
    headGroup,
    leftEarGroup,
    rightEarGroup,
    eyesGroup,
    jawGroup,
    leftArmGroup,
    rightArmGroup,
    leftLegGroup,
    rightLegGroup,
    pendantGroup,
    skullPendantGroup: pendantGroup,
    tailGroup,
    fartCloudGroup,
    fartStage1,
    fartStage2,
    fartStage3,
    materials
  };
}

export const buildCatnapPlushModel = buildCatNapPlushModel;
