
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
 * CraftyCorn 3D Plush Base Model Generator (Three.js r161 ESM)
 * ============================================================================
 * 1:1 High-Precision 3D Recreation of `images/011_CraftyCorn_Plushie.webp`
 * Official Poppy Playtime Chapter 3 (Smiling Critters) CraftyCorn Plush
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
      if (mode === 'mane') {
        const c1 = Math.sin(nx * Math.PI * 14) * Math.cos(ny * Math.PI * 14);
        const c2 = Math.sin((nx + ny) * Math.PI * 26) * Math.cos((nx - ny) * Math.PI * 26);
        const hash = Math.sin((x * 12.9898 + y * 78.233)) * 43758.5453;
        const grain = (hash - Math.floor(hash)) - 0.5;
        v = Math.max(0, Math.min(255, Math.floor(128 + 46 * c1 + 32 * c2 + 24 * grain)));
      } else {
        const hash = Math.sin((x * 12.9898 + y * 78.233)) * 43758.5453;
        const grain = (hash - Math.floor(hash)) - 0.5;
        const weave = Math.sin(nx * Math.PI * 64) * Math.cos(ny * Math.PI * 64);
        v = Math.max(0, Math.min(255, Math.floor(128 + 24 * weave + 32 * grain)));
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
  tex.repeat.set(mode === 'mane' ? 4 : 6, mode === 'mane' ? 4 : 6);
  return tex;
}

export function buildCraftyCornPlushModel(THREE) {
  const root = new THREE.Group();
  root.name = 'CraftyCorn_Plush_BaseModel';

  const bodyRig = new THREE.Group();
  bodyRig.name = 'Body_Rig_Root';
  root.add(bodyRig);

  const maneBump = createPlushBumpTexture(THREE, 'mane');
  const velourBump = createPlushBumpTexture(THREE, 'velour');

  const materials = {
    whitePlush: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_SnowWhite_Plush',
      color: 0xf2f5f8,
      roughness: 0.84,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    aquaCyan: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_AquaCyan_Plush',
      color: 0x22b8cf,
      roughness: 0.78,
      metalness: 0.03,
      bumpMap: maneBump,
      bumpScale: 0.012
    }),
    aquaLight: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_AquaLight_Plush',
      color: 0x38bdf8,
      roughness: 0.76,
      metalness: 0.03,
      bumpMap: maneBump,
      bumpScale: 0.010
    }),
    aquaSeam: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_Aqua_Seam_Groove',
      color: 0x0e7490,
      roughness: 0.88,
      metalness: 0.02
    }),
    hornPearl: new THREE.MeshPhysicalMaterial({
      name: 'CraftyCorn_Horn_Pearl_Spiral',
      color: 0xdceef5,
      roughness: 0.24,
      metalness: 0.18,
      clearcoat: 0.65,
      clearcoatRoughness: 0.08
    }),
    hornGroove: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_Horn_Spiral_Ridge',
      color: 0x88b4c8,
      roughness: 0.32,
      metalness: 0.25
    }),
    mouthCavity: new THREE.MeshBasicMaterial({
      name: 'CraftyCorn_Recessed_Mouth_Void',
      color: 0x040508,
      side: THREE.DoubleSide
    }),
    tonguePink: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_Tongue_Pink',
      color: 0xf43f5e,
      roughness: 0.80,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.006
    }),
    glossyEye: new THREE.MeshPhysicalMaterial({
      name: 'CraftyCorn_Glossy_Acrylic_Eye',
      color: 0x020204,
      roughness: 0.05,
      metalness: 0.0,
      envMapIntensity: 0.15,
      clearcoat: 1.0,
      clearcoatRoughness: 0.03,
      reflectivity: 0.95
    }),
    eyeHighlight: new THREE.MeshBasicMaterial({
      name: 'CraftyCorn_Eye_Studio_Catchlight',
      color: 0xffffff
    }),
    metalZipper: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_Silver_Zipper_Hardware',
      color: 0xcbd5e1,
      roughness: 0.26,
      metalness: 0.82
    }),
    seamDark: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_Zipper_Track_Dark',
      color: 0x0f172a,
      roughness: 0.90,
      metalness: 0.02
    }),
    petalYellow: new THREE.MeshPhysicalMaterial({
      name: 'CraftyCorn_Flower_Center_Yellow',
      color: 0xfacc15,
      roughness: 0.24,
      metalness: 0.12,
      clearcoat: 0.55
    }),
    petalOrange: new THREE.MeshPhysicalMaterial({
      name: 'CraftyCorn_Flower_Petal_Orange',
      color: 0xf97316,
      roughness: 0.28,
      metalness: 0.10,
      clearcoat: 0.50
    }),
    petalGreen: new THREE.MeshPhysicalMaterial({
      name: 'CraftyCorn_Flower_Petal_Green',
      color: 0x22c55e,
      roughness: 0.28,
      metalness: 0.10,
      clearcoat: 0.50
    }),
    petalBlue: new THREE.MeshPhysicalMaterial({
      name: 'CraftyCorn_Flower_Petal_Blue',
      color: 0x0ea5e9,
      roughness: 0.28,
      metalness: 0.10,
      clearcoat: 0.50
    }),
    petalPurple: new THREE.MeshPhysicalMaterial({
      name: 'CraftyCorn_Flower_Petal_Purple',
      color: 0x9333ea,
      roughness: 0.28,
      metalness: 0.10,
      clearcoat: 0.50
    }),
    petalRed: new THREE.MeshPhysicalMaterial({
      name: 'CraftyCorn_Flower_Petal_Red',
      color: 0xef4444,
      roughness: 0.28,
      metalness: 0.10,
      clearcoat: 0.50
    }),
    fartLime: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_Fart_Cloud_Lime',
      color: 0x4ce629,
      emissive: 0x228b12,
      emissiveIntensity: 0.35,
      roughness: 0.65,
      metalness: 0.02,
      bumpMap: maneBump,
      bumpScale: 0.015
    }),
    fartNeon: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_Fart_Cloud_Neon_YellowGreen',
      color: 0xc4ff33,
      emissive: 0x84cc16,
      emissiveIntensity: 0.50,
      roughness: 0.45,
      metalness: 0.05
    }),
    fartPurple: new THREE.MeshStandardMaterial({
      name: 'CraftyCorn_Fart_Cloud_Unicorn_Purple',
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
  // 1. TORSO (Pear-Shaped Snow-White Plush Body: y = 0.43 .. 1.08)
  // ============================================================================
  const torsoGroup = new THREE.Group();
  torsoGroup.name = 'Torso_And_Zipper_Group';
  bodyRig.add(torsoGroup);

  const torsoGeo = new THREE.SphereGeometry(1, 44, 36);
  const tPos = torsoGeo.attributes.position;
  for (let i = 0; i < tPos.count; i++) {
    let x = tPos.getX(i);
    let y = tPos.getY(i);
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
  const torsoMesh = new THREE.Mesh(torsoGeo, materials.whitePlush);
  torsoMesh.castShadow = true;
  torsoMesh.receiveShadow = true;
  torsoGroup.add(torsoMesh);

  // ============================================================================
  // 2. BLACK ZIPPER TRACK, CYAN PIPING & RAINBOW FLOWER PENDANT CHARM
  // ============================================================================
  const zipperGroup = new THREE.Group();
  zipperGroup.name = 'Zipper_Hardware_Group';
  torsoGroup.add(zipperGroup);

  const toothGeo = new THREE.BoxGeometry(0.019, 0.0085, 0.018);
  const backingSegGeo = new THREE.BoxGeometry(0.042, 0.018, 0.014);
  const pipeSegGeo = new THREE.BoxGeometry(0.009, 0.018, 0.015);
  for (let i = 0; i < 33; i++) {
    const ty = 0.495 + i * 0.0155;
    const zSurf = torsoFrontZ(ty, 0);
    const side = (i % 2 === 0) ? -0.007 : 0.007;

    const backSeg = new THREE.Mesh(backingSegGeo, materials.seamDark);
    backSeg.position.set(0, ty, zSurf - 0.003);
    zipperGroup.add(backSeg);

    [-0.022, 0.022].forEach(px => {
      const pipeSeg = new THREE.Mesh(pipeSegGeo, materials.aquaCyan);
      pipeSeg.position.set(px, ty, zSurf - 0.001);
      zipperGroup.add(pipeSeg);
    });

    const tooth = new THREE.Mesh(toothGeo, materials.metalZipper);
    tooth.position.set(side, ty, zSurf + 0.003);
    zipperGroup.add(tooth);
  }

  const zCollar = torsoFrontZ(0.985, 0);
  const sliderBody = new THREE.Mesh(new THREE.BoxGeometry(0.048, 0.056, 0.034), materials.metalZipper);
  sliderBody.position.set(0, 0.990, zCollar + 0.006);
  sliderBody.rotation.x = -0.22;
  zipperGroup.add(sliderBody);

  const pullTab = new THREE.Mesh(new THREE.BoxGeometry(0.036, 0.052, 0.016), materials.petalOrange);
  pullTab.position.set(0, 0.948, zCollar + 0.024);
  pullTab.rotation.x = -0.10;
  zipperGroup.add(pullTab);

  // Rainbow-Petaled Flower Pendant Group (pivots at y = 0.925)
  const zChest = torsoFrontZ(0.80, 0);
  const skullPendantGroup = new THREE.Group();
  skullPendantGroup.name = 'Rainbow_Flower_Pendant_Group';
  skullPendantGroup.position.set(0, 0.925, zChest + 0.012);
  skullPendantGroup.rotation.x = -0.08;
  torsoGroup.add(skullPendantGroup);

  const flowerCenterY = -0.135;
  const flowerBackDisc = new THREE.Mesh(
    new THREE.CylinderGeometry(0.115, 0.115, 0.018, 28),
    materials.seamDark
  );
  flowerBackDisc.rotation.x = Math.PI / 2;
  flowerBackDisc.position.set(0, flowerCenterY, 0.0);
  skullPendantGroup.add(flowerBackDisc);

  // 5 Rainbow Petals (Top: Orange, Upper-Right: Green, Lower-Right: Blue, Lower-Left: Purple, Upper-Left: Red)
  const petalConfigs = [
    { deg: 90,   mat: materials.petalOrange },
    { deg: 18,   mat: materials.petalGreen },
    { deg: -54,  mat: materials.petalBlue },
    { deg: -126, mat: materials.petalPurple },
    { deg: 162,  mat: materials.petalRed }
  ];
  const petalOrbit = 0.078;
  petalConfigs.forEach(({ deg, mat }) => {
    const rad = THREE.MathUtils.degToRad(deg);
    const px = Math.cos(rad) * petalOrbit;
    const py = flowerCenterY + Math.sin(rad) * petalOrbit;

    const rimMesh = new THREE.Mesh(new THREE.SphereGeometry(0.058, 20, 14), materials.seamDark);
    rimMesh.scale.set(1.08, 0.96, 0.36);
    rimMesh.position.set(px, py, 0.002);
    rimMesh.rotation.z = rad;
    skullPendantGroup.add(rimMesh);

    const petalMesh = new THREE.Mesh(new THREE.SphereGeometry(0.052, 22, 16), mat);
    petalMesh.scale.set(1.08, 0.95, 0.44);
    petalMesh.position.set(px, py, 0.008);
    petalMesh.rotation.z = rad;
    petalMesh.castShadow = true;
    skullPendantGroup.add(petalMesh);
  });

  // Central Yellow Flower Disc with dark border ring
  const centerRim = new THREE.Mesh(new THREE.SphereGeometry(0.062, 24, 16), materials.seamDark);
  centerRim.scale.set(1.0, 1.0, 0.42);
  centerRim.position.set(0, flowerCenterY, 0.014);
  skullPendantGroup.add(centerRim);

  const centerYellow = new THREE.Mesh(new THREE.SphereGeometry(0.055, 24, 16), materials.petalYellow);
  centerYellow.scale.set(1.0, 1.0, 0.48);
  centerYellow.position.set(0, flowerCenterY, 0.020);
  centerYellow.castShadow = true;
  skullPendantGroup.add(centerYellow);

  // ============================================================================
  // 3. ARMS & BRIGHT CYAN/AQUA PLUSH HOOVES (Splayed Outward at 42°)
  // ============================================================================
  function createArm(side) {
    const armGroup = new THREE.Group();
    armGroup.name = side < 0 ? 'Left_Arm_Group' : 'Right_Arm_Group';
    armGroup.position.set(side * 0.195, 0.955, 0.01);
    armGroup.rotation.z = side * 0.74;
    torsoGroup.add(armGroup);

    const sleeveGeo = new THREE.CylinderGeometry(0.082, 0.105, 0.31, 24, 12);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, materials.whitePlush);
    sleeveMesh.position.set(0, -0.145, 0);
    sleeveMesh.castShadow = true;
    armGroup.add(sleeveMesh);

    const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.082, 20, 16), materials.whitePlush);
    armGroup.add(shoulderCap);

    const hoofGroup = new THREE.Group();
    hoofGroup.position.set(0, -0.345, 0.01);
    armGroup.add(hoofGroup);

    const mittenGeo = new THREE.SphereGeometry(0.116, 28, 22);
    const mPos = mittenGeo.attributes.position;
    for (let i = 0; i < mPos.count; i++) {
      let x = mPos.getX(i) * 1.06;
      let y = mPos.getY(i) * 1.16;
      let z = mPos.getZ(i) * 0.88;
      if (y < -0.02) {
        const cleftFactor = Math.exp(-Math.pow(x / 0.022, 2)) * ((-y - 0.02) / 0.12);
        y += 0.016 * cleftFactor;
        if (z > 0) z -= 0.010 * cleftFactor;
      }
      mPos.setXYZ(i, x, y, z);
    }
    mittenGeo.computeVertexNormals();
    const mittenMesh = new THREE.Mesh(mittenGeo, materials.aquaCyan);
    mittenMesh.castShadow = true;
    hoofGroup.add(mittenMesh);

    const seamLine = new THREE.Mesh(new THREE.CylinderGeometry(0.0045, 0.0045, 0.095, 8), materials.aquaSeam);
    seamLine.position.set(0, -0.055, 0.092);
    seamLine.rotation.x = 0.22;
    hoofGroup.add(seamLine);

    return armGroup;
  }

  const leftArmGroup = createArm(-1);
  const rightArmGroup = createArm(1);

  // ============================================================================
  // 4. LEGS, CYAN FOOT HOOVES & FLUFFY CURLED UNICORN TAIL
  // ============================================================================
  function createLeg(side) {
    const legGroup = new THREE.Group();
    legGroup.name = side < 0 ? 'Left_Leg_Group' : 'Right_Leg_Group';
    legGroup.position.set(side * 0.14, 0.50, 0.0);
    legGroup.rotation.z = side * 0.075;
    bodyRig.add(legGroup);

    const legGeo = new THREE.CylinderGeometry(0.094, 0.100, 0.34, 24, 10);
    const legMesh = new THREE.Mesh(legGeo, materials.whitePlush);
    legMesh.position.set(0, -0.17, 0);
    legMesh.castShadow = true;
    legGroup.add(legMesh);

    const footGeo = new THREE.SphereGeometry(0.116, 28, 22);
    const fPos = footGeo.attributes.position;
    for (let i = 0; i < fPos.count; i++) {
      let x = fPos.getX(i) * 1.05;
      let y = fPos.getY(i);
      let z = fPos.getZ(i) * 1.15;
      if (y < 0) y *= 0.72;
      else y *= 0.92;
      fPos.setXYZ(i, x, y, z);
    }
    footGeo.computeVertexNormals();
    const footMesh = new THREE.Mesh(footGeo, materials.aquaCyan);
    footMesh.position.set(0, -0.405, 0.02);
    footMesh.rotation.z = -side * 0.075;
    footMesh.castShadow = true;
    footMesh.receiveShadow = true;
    legGroup.add(footMesh);

    const fSeam = new THREE.Mesh(new THREE.CylinderGeometry(0.0045, 0.0045, 0.090, 8), materials.aquaSeam);
    fSeam.position.set(0, -0.41, 0.148);
    fSeam.rotation.x = -0.18;
    legGroup.add(fSeam);

    return legGroup;
  }

  const leftLegGroup = createLeg(-1);
  const rightLegGroup = createLeg(1);

  // Fluffy Curled Cyan/Aqua Unicorn Tail
  const tailGroup = new THREE.Group();
  tailGroup.name = 'Unicorn_Tail_Group';
  torsoGroup.add(tailGroup);

  const tailCurvePts = [];
  for (let i = 0; i <= 16; i++) {
    const t = i / 16.0;
    const tx = 0.08 * t + 0.32 * Math.pow(t, 1.35) - 0.05 * Math.sin(Math.PI * t * 1.5);
    const ty = 0.54 - 0.06 * Math.sin(Math.PI * t) + 0.24 * Math.pow(t, 1.7);
    const tz = -0.22 - 0.14 * Math.sin(Math.PI * t * 0.85);
    tailCurvePts.push(new THREE.Vector3(tx, ty, tz));
  }
  const tailCurve = new THREE.CatmullRomCurve3(tailCurvePts);
  const tailTubeGeo = new THREE.TubeGeometry(tailCurve, 28, 0.068, 16, false);
  const tailTubeMesh = new THREE.Mesh(tailTubeGeo, materials.aquaCyan);
  tailTubeMesh.castShadow = true;
  tailGroup.add(tailTubeMesh);

  [
    [0.34, 0.72, -0.30, 0.095, materials.aquaLight],
    [0.39, 0.64, -0.28, 0.088, materials.aquaCyan],
    [0.28, 0.61, -0.32, 0.082, materials.aquaLight]
  ].forEach(([tx, ty, tz, r, mat]) => {
    const p = new THREE.Mesh(new THREE.SphereGeometry(r, 18, 14), mat);
    p.position.set(tx, ty, tz);
    p.castShadow = true;
    tailGroup.add(p);
  });

  // ============================================================================
  // 5. HEAD, CYAN MANE CREST, SPIRALED UNICORN HORN, EARS, EYES & WIDE SMILE
  // ============================================================================
  const headGroup = new THREE.Group();
  headGroup.name = 'Head_Group';
  headGroup.position.set(0, 1.06, 0);
  bodyRig.add(headGroup);

  const HEAD_RX = 0.455, HEAD_RY = 0.420, HEAD_RZ = 0.410, HEAD_CY = 0.44;
  function headFrontZ(x, y) {
    const nx = x / HEAD_RX;
    const ny = (y - HEAD_CY) / HEAD_RY;
    const r2 = nx * nx + ny * ny;
    if (r2 >= 0.96) return HEAD_RZ * 0.20;
    return HEAD_RZ * Math.sqrt(1.0 - r2);
  }

  // Snow-White Plush Head Sphere with Flared Smiling Cheeks
  const headCoreGeo = new THREE.SphereGeometry(1, 44, 36);
  const hcPos = headCoreGeo.attributes.position;
  for (let i = 0; i < hcPos.count; i++) {
    let x = hcPos.getX(i) * HEAD_RX;
    let y = hcPos.getY(i) * HEAD_RY;
    let z = hcPos.getZ(i) * HEAD_RZ;
    const ny = y / HEAD_RY;
    if (ny > -0.55 && ny < 0.15) {
      const swell = Math.exp(-Math.pow((ny + 0.18) / 0.28, 2)) * Math.pow(Math.min(1.0, Math.abs(x) / 0.30), 1.2);
      x *= (1.0 + 0.16 * swell);
      if (z > 0) z *= (1.0 + 0.07 * swell);
    }
    hcPos.setXYZ(i, x, y, z);
  }
  headCoreGeo.computeVertexNormals();
  const headCore = new THREE.Mesh(headCoreGeo, materials.whitePlush);
  headCore.position.set(0, HEAD_CY, 0);
  headCore.castShadow = true;
  headGroup.add(headCore);

  // Scalloped Cyan Forehead Bangs Crest & Flowing Back/Side Mane Locks (`woolGroup` alias)
  const woolGroup = new THREE.Group();
  woolGroup.name = 'Cyan_Mane_Crest_And_Horn_Group';
  headGroup.add(woolGroup);

  const baseTuftGeo = new THREE.SphereGeometry(1, 20, 16);
  const bPos = baseTuftGeo.attributes.position;
  for (let i = 0; i < bPos.count; i++) {
    const vx = bPos.getX(i);
    const vy = bPos.getY(i);
    const vz = bPos.getZ(i);
    const disp = 1.0 + 0.045 * Math.sin(vx * 6.0) * Math.cos(vy * 6.0) * Math.sin(vz * 6.0);
    bPos.setXYZ(i, vx * disp, vy * disp, vz * disp);
  }
  baseTuftGeo.computeVertexNormals();

  const maneTufts = [
    // Top forehead crown cushion
    [0.00, 0.78, 0.14, 0.22, 0.13, 0.19, materials.aquaCyan],
    // 3 scalloped forehead bangs lobes (center + left + right)
    [0.00, 0.64, 0.33, 0.125, 0.105, 0.115, materials.aquaLight],
    [-0.135, 0.66, 0.30, 0.115, 0.098, 0.110, materials.aquaCyan],
    [0.135, 0.66, 0.30, 0.115, 0.098, 0.110, materials.aquaCyan],
    [-0.235, 0.68, 0.22, 0.105, 0.092, 0.102, materials.aquaLight],
    [0.235, 0.68, 0.22, 0.105, 0.092, 0.102, materials.aquaLight],
    // Flowing back mane crest & side neck curls
    [0.00, 0.81, -0.08, 0.18, 0.14, 0.18, materials.aquaCyan],
    [0.00, 0.73, -0.26, 0.18, 0.15, 0.17, materials.aquaCyan],
    [0.00, 0.56, -0.36, 0.17, 0.16, 0.16, materials.aquaLight],
    [0.00, 0.38, -0.38, 0.16, 0.15, 0.15, materials.aquaCyan],
    [0.00, 0.22, -0.34, 0.15, 0.13, 0.14, materials.aquaLight],
    [0.34, 0.38, -0.10, 0.115, 0.092, 0.105, materials.aquaCyan],
    [0.37, 0.26, -0.09, 0.110, 0.085, 0.098, materials.aquaLight],
    [-0.34, 0.37, -0.11, 0.110, 0.088, 0.100, materials.aquaCyan],
    [-0.36, 0.25, -0.10, 0.105, 0.082, 0.095, materials.aquaLight]
  ];
  maneTufts.forEach(([tx, ty, tz, sx, sy, sz, mat]) => {
    const m = new THREE.Mesh(baseTuftGeo, mat);
    m.position.set(tx, ty, tz);
    m.scale.set(sx, sy, sz);
    m.castShadow = true;
    woolGroup.add(m);
  });

  // Spiraled Unicorn Horn Centered on Forehead
  const hornGroup = new THREE.Group();
  hornGroup.position.set(0, 0.70, 0.28);
  hornGroup.rotation.x = 0.58;
  woolGroup.add(hornGroup);

  const hornConeGeo = new THREE.CylinderGeometry(0.012, 0.074, 0.38, 24, 16);
  const hornConeMesh = new THREE.Mesh(hornConeGeo, materials.hornPearl);
  hornConeMesh.position.set(0, 0.19, 0);
  hornConeMesh.castShadow = true;
  hornGroup.add(hornConeMesh);

  const hornTipCap = new THREE.Mesh(new THREE.SphereGeometry(0.013, 14, 10), materials.hornPearl);
  hornTipCap.position.set(0, 0.38, 0);
  hornGroup.add(hornTipCap);

  // Helical spiral ridge around the unicorn horn
  const spiralPts = [];
  for (let k = 0; k <= 48; k++) {
    const t = 0.04 + 0.90 * (k / 48.0);
    const r = (0.074 * (1.0 - t) + 0.012 * t) * 0.98;
    const ang = t * 4.5 * Math.PI * 2.0;
    spiralPts.push(new THREE.Vector3(Math.cos(ang) * r, t * 0.38, Math.sin(ang) * r));
  }
  const spiralCurve = new THREE.CatmullRomCurve3(spiralPts);
  const spiralGeo = new THREE.TubeGeometry(spiralCurve, 56, 0.0085, 10, false);
  const spiralMesh = new THREE.Mesh(spiralGeo, materials.hornGroove);
  hornGroup.add(spiralMesh);

  // ============================================================================
  // 6. UPRIGHT UNICORN EARS (Snow-White Outer + Cyan/Aqua Inner Recess)
  // ============================================================================
  function createUnicornEar(side) {
    const earGroup = new THREE.Group();
    earGroup.name = side < 0 ? 'Left_Ear_Group' : 'Right_Ear_Group';
    earGroup.position.set(side * 0.33, 0.74, 0.04);
    earGroup.rotation.z = side * -0.34;
    earGroup.rotation.y = side * -0.14;
    earGroup.rotation.x = 0.08;
    headGroup.add(earGroup);

    const earGeo = new THREE.SphereGeometry(1, 24, 18);
    earGeo.scale(0.118, 0.185, 0.072);
    const earMesh = new THREE.Mesh(earGeo, materials.whitePlush);
    earMesh.position.set(0, 0.06, 0);
    earMesh.castShadow = true;
    earGroup.add(earMesh);

    const innerGeo = new THREE.SphereGeometry(1, 20, 14);
    innerGeo.scale(0.075, 0.132, 0.032);
    const innerMesh = new THREE.Mesh(innerGeo, materials.aquaCyan);
    innerMesh.position.set(0, 0.055, 0.052);
    earGroup.add(innerMesh);

    return earGroup;
  }

  const leftEarGroup = createUnicornEar(-1);
  const rightEarGroup = createUnicornEar(1);

  // ============================================================================
  // 7. LARGE GLOSSY JET-BLACK OVAL EYES, STUDIO CATCHLIGHTS & HAPPY BROWS
  // ============================================================================
  const eyesGroup = new THREE.Group();
  eyesGroup.name = 'Eyes_And_Eyelids_Group';
  headGroup.add(eyesGroup);

  function createEyeAssembly(side) {
    const ex = side * 0.142;
    const ey = 0.478;
    const ez = headFrontZ(ex, ey) - 0.012;

    const eyeWrap = new THREE.Group();
    eyeWrap.position.set(ex, ey, ez);
    eyeWrap.rotation.y = side * 0.20;
    eyesGroup.add(eyeWrap);

    const eyeSphereGeo = new THREE.SphereGeometry(0.096, 32, 24);
    eyeSphereGeo.scale(0.96, 1.08, 0.72);
    const eyeMesh = new THREE.Mesh(eyeSphereGeo, materials.glossyEye);
    eyeWrap.add(eyeMesh);

    const catchGeo = new THREE.SphereGeometry(1, 16, 12);
    catchGeo.scale(0.022, 0.032, 0.006);
    const catchMesh = new THREE.Mesh(catchGeo, materials.eyeHighlight);
    catchMesh.position.set(side * -0.022, 0.026, 0.068);
    eyeWrap.add(catchMesh);

    const catch2 = new THREE.Mesh(new THREE.SphereGeometry(0.009, 10, 8), materials.eyeHighlight);
    catch2.position.set(side * 0.024, -0.028, 0.065);
    eyeWrap.add(catch2);
  }

  createEyeAssembly(-1);
  createEyeAssembly(1);

  // ============================================================================
  // 8. WIDE CHEERFUL SMILING MOUTH RIM, BLACK CAVITY, PINK TONGUE & SNOUT
  // ============================================================================
  const jawGroup = new THREE.Group();
  jawGroup.name = 'Muzzle_And_Jaw_Group';
  headGroup.add(jawGroup);

  function upperLipPoint(t) {
    const x = t * 0.415;
    const snoutArch = 0.022 * Math.exp(-Math.pow(t / 0.42, 2));
    const cheekLift = 0.036 * Math.pow(Math.abs(t), 1.5) * (1.0 - 0.28 * Math.pow(t, 4));
    const y = 0.368 + snoutArch + cheekLift - 0.032 * Math.pow(t, 6);
    const zBase = headFrontZ(x, y);
    const zSnout = 0.020 + 0.015 * Math.cos(t * (Math.PI * 0.46));
    return new THREE.Vector3(x, y, zBase + zSnout);
  }

  function lowerLipPoint(t) {
    const ang = t * (Math.PI * 0.49);
    const x = Math.sin(ang) * 0.415;
    const y = 0.365 - Math.cos(ang) * 0.332;
    const zBase = headFrontZ(x, y);
    const zArch = 0.018 + 0.010 * Math.cos(ang * 0.85);
    return new THREE.Vector3(x, y, zBase + zArch);
  }

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
  jawGroup.add(new THREE.Mesh(mouthPlateGeo, materials.mouthCavity));

  // Cute Coral-Pink Plush Tongue at bottom of smiling mouth cavity
  const tongueGeo = new THREE.SphereGeometry(0.115, 22, 16);
  tongueGeo.scale(1.05, 0.55, 0.32);
  const tongueMesh = new THREE.Mesh(tongueGeo, materials.tonguePink);
  tongueMesh.position.set(0, 0.155, headFrontZ(0, 0.155) + 0.012);
  tongueMesh.rotation.x = 0.36;
  jawGroup.add(tongueMesh);

  // Upper & Lower Snow-White Smiling Lip Rims
  const upperLipPts = [];
  for (let i = 0; i <= 36; i++) {
    upperLipPts.push(upperLipPoint((i / 36) * 2.0 - 1.0));
  }
  const upperLipCurve = new THREE.CatmullRomCurve3(upperLipPts);
  const upperLipGeo = new THREE.TubeGeometry(upperLipCurve, 48, 0.032, 18, false);
  const upperLipMesh = new THREE.Mesh(upperLipGeo, materials.whitePlush);
  upperLipMesh.castShadow = true;
  jawGroup.add(upperLipMesh);

  // Snout bridge & nostrils
  const pCenterSnout = upperLipPoint(0);
  const snoutBridge = new THREE.Mesh(new THREE.SphereGeometry(1, 20, 14), materials.whitePlush);
  snoutBridge.scale.set(0.115, 0.055, 0.065);
  snoutBridge.position.set(0, pCenterSnout.y + 0.025, pCenterSnout.z + 0.004);
  jawGroup.add(snoutBridge);

  const nostrilGeo = new THREE.SphereGeometry(1, 12, 10);
  nostrilGeo.scale(0.011, 0.006, 0.007);
  [-1, 1].forEach(side => {
    const nMesh = new THREE.Mesh(nostrilGeo, materials.mouthCavity);
    nMesh.position.set(side * 0.042, pCenterSnout.y + 0.034, pCenterSnout.z + 0.056);
    nMesh.rotation.z = -side * 0.20;
    jawGroup.add(nMesh);
  });

  const lowerLipPts = [];
  for (let i = 0; i <= 36; i++) {
    lowerLipPts.push(lowerLipPoint((i / 36) * 2.0 - 1.0));
  }
  const lowerLipCurve = new THREE.CatmullRomCurve3(lowerLipPts);
  const lowerLipGeo = new THREE.TubeGeometry(lowerLipCurve, 48, 0.030, 18, false);
  const lowerLipMesh = new THREE.Mesh(lowerLipGeo, materials.whitePlush);
  lowerLipMesh.castShadow = true;
  jawGroup.add(lowerLipMesh);

  [-1, 1].forEach(side => {
    const pCorner = upperLipPoint(side);
    const cornerCap = new THREE.Mesh(new THREE.SphereGeometry(0.038, 16, 12), materials.whitePlush);
    cornerCap.position.copy(pCorner);
    jawGroup.add(cornerCap);
  });

  // ============================================================================
  // 9. 3D SCULPTED CARTOON FART CLOUD CLUSTER (FOR `CraftyCorn_Fart_Blast`)
  // ============================================================================
  const fartCloudGroup = new THREE.Group();
  fartCloudGroup.name = 'CraftyCorn_Fart_Cloud_Group';
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


  loadCritterV11GLB(THREE, './models/craftycorn_plush_base_model.glb', { root, bodyRig, headGroup, pendantGroup: skullPendantGroup, fartCloudGroup }, velourBump);

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
    tailGroup,
    skullPendantGroup,
    pendantGroup: skullPendantGroup,
    fartCloudGroup,
    fartStage1,
    fartStage2,
    fartStage3,
    materials
  };
}

export { buildCraftyCornPlushModel as buildBabaChopsPlushModel };
