
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
 * PickyPiggy 3D Plush Base Model Generator (Three.js r161 ESM)
 * ============================================================================
 * 1:1 High-Precision 3D Recreation of `images/025_PickyPiggy_Plushie.webp`
 * Official Poppy Playtime Chapter 3 (Smiling Critters) PickyPiggy Plush
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
  tex.repeat.set(mode === 'cloud' ? 4 : 6, mode === 'cloud' ? 4 : 6);
  return tex;
}

export function buildPickyPiggyPlushModel(THREE) {
  const root = new THREE.Group();
  root.name = 'PickyPiggy_Plush_BaseModel';

  const bodyRig = new THREE.Group();
  bodyRig.name = 'Body_Rig_Root';
  root.add(bodyRig);

  const cloudBump = createPlushBumpTexture(THREE, 'cloud');
  const velourBump = createPlushBumpTexture(THREE, 'velour');

  const materials = {
    pinkPlush: new THREE.MeshStandardMaterial({
      name: 'Picky_Bubblegum_Pink_Plush',
      color: 0xec5b98,
      roughness: 0.84,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    pastelBelly: new THREE.MeshStandardMaterial({
      name: 'Picky_Pastel_Pink_Belly',
      color: 0xfbcfe8,
      roughness: 0.85,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.007
    }),
    hoofMagenta: new THREE.MeshStandardMaterial({
      name: 'Picky_Hoof_Magenta_Rose',
      color: 0xc2185b,
      roughness: 0.78,
      metalness: 0.03,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    snoutRose: new THREE.MeshStandardMaterial({
      name: 'Picky_Snout_Rose_Velour',
      color: 0xe02874,
      roughness: 0.74,
      metalness: 0.03,
      bumpMap: velourBump,
      bumpScale: 0.006
    }),
    nostrilDark: new THREE.MeshStandardMaterial({
      name: 'Picky_Nostril_Dark_Crimson',
      color: 0x6a0b31,
      roughness: 0.88,
      metalness: 0.02
    }),
    appleRed: new THREE.MeshPhysicalMaterial({
      name: 'Picky_Apple_Pendant_Red',
      color: 0xd5001c,
      roughness: 0.22,
      metalness: 0.12,
      clearcoat: 0.85,
      clearcoatRoughness: 0.06
    }),
    appleLeafGreen: new THREE.MeshPhysicalMaterial({
      name: 'Picky_Apple_Leaf_Green',
      color: 0x38e54d,
      roughness: 0.28,
      metalness: 0.05,
      clearcoat: 0.60,
      clearcoatRoughness: 0.08
    }),
    appleStemBrown: new THREE.MeshStandardMaterial({
      name: 'Picky_Apple_Stem_Brown',
      color: 0x6d3b1a,
      roughness: 0.60,
      metalness: 0.04
    }),
    tongueCoral: new THREE.MeshStandardMaterial({
      name: 'Picky_Tongue_Coral_Pink',
      color: 0xff6b8b,
      roughness: 0.78,
      metalness: 0.02
    }),
    mouthCavity: new THREE.MeshBasicMaterial({
      name: 'Picky_Recessed_Mouth_Void',
      color: 0x050507,
      side: THREE.DoubleSide
    }),
    glossyEye: new THREE.MeshPhysicalMaterial({
      name: 'Picky_Glossy_Acrylic_Eye',
      color: 0x020204,
      roughness: 0.05,
      metalness: 0.0,
      envMapIntensity: 0.14,
      clearcoat: 1.0,
      clearcoatRoughness: 0.03,
      reflectivity: 0.95
    }),
    eyeHighlight: new THREE.MeshBasicMaterial({
      name: 'Picky_Eye_Studio_Catchlight',
      color: 0xffffff
    }),
    metalZipper: new THREE.MeshStandardMaterial({
      name: 'Picky_Silver_Zipper_Hardware',
      color: 0xc8cdd6,
      roughness: 0.28,
      metalness: 0.80
    }),
    seamDark: new THREE.MeshStandardMaterial({
      name: 'Picky_Plush_Seam_Groove',
      color: 0x101014,
      roughness: 0.90,
      metalness: 0.02
    }),
    fartLime: new THREE.MeshStandardMaterial({
      name: 'Picky_Fart_Cloud_Lime',
      color: 0x4ce629,
      emissive: 0x228b12,
      emissiveIntensity: 0.35,
      roughness: 0.65,
      metalness: 0.02,
      bumpMap: cloudBump,
      bumpScale: 0.015
    }),
    fartNeon: new THREE.MeshStandardMaterial({
      name: 'Picky_Fart_Cloud_Neon_YellowGreen',
      color: 0xc4ff33,
      emissive: 0x84cc16,
      emissiveIntensity: 0.50,
      roughness: 0.45,
      metalness: 0.05
    }),
    fartPurple: new THREE.MeshStandardMaterial({
      name: 'Picky_Fart_Cloud_Purple',
      color: 0x9d4edd,
      emissive: 0x5b21b6,
      emissiveIntensity: 0.35,
      roughness: 0.60,
      metalness: 0.04
    })
  };

  function torsoFrontZ(yWorld, xWorld = 0) {
    const yn = Math.max(-1, Math.min(1, (yWorld - 0.755) / 0.325));
    const widthP = 0.295 * (1.0 - 0.22 * yn - 0.10 * yn * yn);
    const depthP = 0.255 * (1.0 - 0.18 * yn - 0.08 * yn * yn);
    const xRatio = Math.min(0.95, Math.abs(xWorld) / Math.max(0.05, widthP));
    const zHoriz = Math.sqrt(Math.max(0.01, 1.0 - yn * yn)) * Math.sqrt(Math.max(0.01, 1.0 - xRatio * xRatio));
    return depthP * zHoriz;
  }

  // ============================================================================
  // 1. TORSO (Plump Pear-Shaped Bubblegum-Pink Plush Body + Pastel Belly Patch)
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
    const widthProfile = 0.295 * (1.0 - 0.22 * y - 0.10 * y * y);
    const depthProfile = 0.255 * (1.0 - 0.18 * y - 0.08 * y * y);
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
  const torsoMesh = new THREE.Mesh(torsoGeo, materials.pinkPlush);
  torsoMesh.castShadow = true;
  torsoMesh.receiveShadow = true;
  torsoGroup.add(torsoMesh);

  // Soft Pastel-Pink Belly Patch (#FBCFE8) behind zipper track
  const bellyGeo = new THREE.SphereGeometry(1, 28, 22);
  bellyGeo.scale(0.185, 0.195, 0.055);
  const bellyMesh = new THREE.Mesh(bellyGeo, materials.pastelBelly);
  bellyMesh.position.set(0, 0.69, torsoFrontZ(0.69, 0) - 0.042);
  torsoGroup.add(bellyMesh);

  // ============================================================================
  // 2. BLACK COLLAR ZIPPER & ICONIC SHINY RED APPLE WITH GREEN LEAF PENDANT
  // ============================================================================
  const zipperGroup = new THREE.Group();
  zipperGroup.name = 'Zipper_Hardware_Group';
  torsoGroup.add(zipperGroup);

  const toothGeo = new THREE.BoxGeometry(0.018, 0.008, 0.016);
  const backingSegGeo = new THREE.BoxGeometry(0.042, 0.018, 0.014);
  for (let i = 0; i < 33; i++) {
    const ty = 0.495 + i * 0.0155;
    const zSurf = torsoFrontZ(ty, 0);
    const side = (i % 2 === 0) ? -0.007 : 0.007;

    const backSeg = new THREE.Mesh(backingSegGeo, materials.seamDark);
    backSeg.position.set(0, ty, zSurf - 0.002);
    zipperGroup.add(backSeg);

    const tooth = new THREE.Mesh(toothGeo, materials.metalZipper);
    tooth.position.set(side, ty, zSurf + 0.004);
    zipperGroup.add(tooth);
  }

  const zCollar = torsoFrontZ(0.985, 0);
  const sliderBody = new THREE.Mesh(new THREE.BoxGeometry(0.048, 0.056, 0.034), materials.metalZipper);
  sliderBody.position.set(0, 0.990, zCollar + 0.006);
  sliderBody.rotation.x = -0.20;
  zipperGroup.add(sliderBody);

  // Shiny Red Apple Pendant Group (aliased as both pendantGroup and skullPendantGroup)
  const zChest = torsoFrontZ(0.81, 0);
  const pendantGroup = new THREE.Group();
  pendantGroup.name = 'Apple_Pendant_Group';
  pendantGroup.position.set(0, 0.935, zChest + 0.010);
  pendantGroup.rotation.x = -0.07;
  torsoGroup.add(pendantGroup);

  // Exact bilobed heart-apple 2D contour extruded in 3D
  const appleShape = new THREE.Shape();
  appleShape.moveTo(0, -0.055);
  appleShape.bezierCurveTo(0.045, -0.010, 0.145, -0.015, 0.148, -0.115);
  appleShape.bezierCurveTo(0.150, -0.215, 0.072, -0.285, 0.014, -0.278);
  appleShape.quadraticCurveTo(0, -0.265, -0.014, -0.278);
  appleShape.bezierCurveTo(-0.072, -0.285, -0.150, -0.215, -0.148, -0.115);
  appleShape.bezierCurveTo(-0.145, -0.015, -0.045, -0.010, 0, -0.055);

  const appleBorderGeo = new THREE.ExtrudeGeometry(appleShape, {
    depth: 0.022,
    bevelEnabled: true,
    bevelSegments: 4,
    steps: 1,
    bevelSize: 0.014,
    bevelThickness: 0.008
  });
  appleBorderGeo.center();
  const appleBorderMesh = new THREE.Mesh(appleBorderGeo, materials.seamDark);
  appleBorderMesh.position.set(0, -0.155, -0.004);
  pendantGroup.add(appleBorderMesh);

  const appleRedGeo = new THREE.ExtrudeGeometry(appleShape, {
    depth: 0.028,
    bevelEnabled: true,
    bevelSegments: 5,
    steps: 1,
    bevelSize: 0.008,
    bevelThickness: 0.010
  });
  appleRedGeo.center();
  const appleRedMesh = new THREE.Mesh(appleRedGeo, materials.appleRed);
  appleRedMesh.position.set(0, -0.155, 0.004);
  appleRedMesh.castShadow = true;
  pendantGroup.add(appleRedMesh);

  // Curved Brown Apple Stem
  const stemCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0.00, -0.068, 0.008),
    new THREE.Vector3(-0.006, -0.032, 0.010),
    new THREE.Vector3(-0.018, 0.005, 0.012)
  ]);
  const stemGeo = new THREE.TubeGeometry(stemCurve, 14, 0.013, 10, false);
  const stemMesh = new THREE.Mesh(stemGeo, materials.appleStemBrown);
  pendantGroup.add(stemMesh);

  // Vibrant Green Apple Leaf
  const leafGeo = new THREE.SphereGeometry(1, 18, 14);
  leafGeo.scale(0.046, 0.022, 0.014);
  const leafMesh = new THREE.Mesh(leafGeo, materials.appleLeafGreen);
  leafMesh.position.set(0.042, -0.026, 0.014);
  leafMesh.rotation.z = 0.42;
  pendantGroup.add(leafMesh);

  // ============================================================================
  // 3. CURLY PINK PIG TAIL (2.5-Turn Helix on Rear Pelvis)
  // ============================================================================
  const tailGroup = new THREE.Group();
  tailGroup.name = 'Curly_Pig_Tail_Group';
  torsoGroup.add(tailGroup);

  const tailPts = [];
  for (let i = 0; i <= 40; i++) {
    const t = i / 40;
    const ang = t * 2.4 * Math.PI * 2.0;
    const rLoop = 0.058 * Math.sin(Math.PI * (0.12 + 0.78 * t));
    tailPts.push(new THREE.Vector3(
      rLoop * Math.cos(ang),
      0.58 + 0.22 * t + rLoop * Math.sin(ang) * 0.65,
      -0.23 - 0.22 * Math.pow(t, 0.85) + 0.025 * Math.sin(ang)
    ));
  }
  const tailCurve = new THREE.CatmullRomCurve3(tailPts);
  const tailGeo = new THREE.TubeGeometry(tailCurve, 48, 0.020, 12, false);
  const tailMesh = new THREE.Mesh(tailGeo, materials.pinkPlush);
  tailMesh.castShadow = true;
  tailGroup.add(tailMesh);

  // ============================================================================
  // 4. ARMS & DARKER MAGENTA-ROSE CLOVEN PIG HOOVES
  // ============================================================================
  function createArm(side) {
    const armGroup = new THREE.Group();
    armGroup.name = side < 0 ? 'Left_Arm_Group' : 'Right_Arm_Group';
    armGroup.position.set(side * 0.195, 0.955, 0.01);
    armGroup.rotation.z = side * 0.72;
    torsoGroup.add(armGroup);

    const sleeveGeo = new THREE.CylinderGeometry(0.082, 0.105, 0.31, 24, 12);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, materials.pinkPlush);
    sleeveMesh.position.set(0, -0.145, 0);
    sleeveMesh.castShadow = true;
    armGroup.add(sleeveMesh);

    const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.082, 20, 16), materials.pinkPlush);
    armGroup.add(shoulderCap);

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
      if (y < -0.02) {
        const cleftFactor = Math.exp(-Math.pow(x / 0.024, 2)) * ((-y - 0.02) / 0.12);
        y += 0.020 * cleftFactor;
        if (z > 0) z -= 0.012 * cleftFactor;
      }
      mPos.setXYZ(i, x, y, z);
    }
    mittenGeo.computeVertexNormals();
    const mittenMesh = new THREE.Mesh(mittenGeo, materials.hoofMagenta);
    mittenMesh.castShadow = true;
    hoofGroup.add(mittenMesh);

    // Cloven hoof seam line
    const cleftSeam = new THREE.Mesh(
      new THREE.CylinderGeometry(0.005, 0.005, 0.11, 8),
      materials.nostrilDark
    );
    cleftSeam.position.set(0, -0.04, 0.095);
    hoofGroup.add(cleftSeam);

    return armGroup;
  }

  const leftArmGroup = createArm(-1);
  const rightArmGroup = createArm(1);

  // ============================================================================
  // 5. LEGS & ROUNDED MAGENTA-ROSE CLOVEN FOOT HOOVES
  // ============================================================================
  function createLeg(side) {
    const legGroup = new THREE.Group();
    legGroup.name = side < 0 ? 'Left_Leg_Group' : 'Right_Leg_Group';
    legGroup.position.set(side * 0.145, 0.50, 0.0);
    legGroup.rotation.z = side * 0.075;
    bodyRig.add(legGroup);

    const legGeo = new THREE.CylinderGeometry(0.096, 0.102, 0.34, 24, 10);
    const legMesh = new THREE.Mesh(legGeo, materials.pinkPlush);
    legMesh.position.set(0, -0.17, 0);
    legMesh.castShadow = true;
    legGroup.add(legMesh);

    const footGeo = new THREE.SphereGeometry(0.122, 28, 22);
    const fPos = footGeo.attributes.position;
    for (let i = 0; i < fPos.count; i++) {
      let x = fPos.getX(i);
      let y = fPos.getY(i);
      let z = fPos.getZ(i);
      x *= 1.08;
      z *= 1.16;
      if (y < 0) y *= 0.72;
      else y *= 0.94;
      fPos.setXYZ(i, x, y, z);
    }
    footGeo.computeVertexNormals();
    const footMesh = new THREE.Mesh(footGeo, materials.hoofMagenta);
    footMesh.position.set(0, -0.405, 0.025);
    footMesh.rotation.z = -side * 0.075;
    footMesh.castShadow = true;
    footMesh.receiveShadow = true;
    legGroup.add(footMesh);

    const footCleft = new THREE.Mesh(
      new THREE.CylinderGeometry(0.0055, 0.0055, 0.11, 8),
      materials.nostrilDark
    );
    footCleft.position.set(0, -0.405, 0.162);
    legGroup.add(footCleft);

    return legGroup;
  }

  const leftLegGroup = createLeg(-1);
  const rightLegGroup = createLeg(1);

  // ============================================================================
  // 6. BUBBLEGUM-PINK PIG HEAD, FLOPPY EARS, EYES, OVAL SNOUT & WIDE GRIN
  // ============================================================================
  const headGroup = new THREE.Group();
  headGroup.name = 'Head_Group';
  headGroup.position.set(0, 1.06, 0);
  bodyRig.add(headGroup);

  const woolGroup = new THREE.Group();
  woolGroup.name = 'Head_Detail_Group';
  headGroup.add(woolGroup);

  const HEAD_RX = 0.465, HEAD_RY = 0.415, HEAD_RZ = 0.405, HEAD_CY = 0.43;
  function headFrontZ(x, y) {
    const ny = (y - HEAD_CY) / HEAD_RY;
    const cheekFlare = Math.exp(-Math.pow((ny + 0.18) / 0.42, 2));
    const rxEff = HEAD_RX * (1.0 + 0.15 * cheekFlare - 0.12 * Math.max(0, ny));
    const nx = x / Math.max(0.12, rxEff);
    const r2 = nx * nx + ny * ny;
    if (r2 >= 0.96) return HEAD_RZ * 0.20;
    return (HEAD_RZ + 0.012) * Math.sqrt(1.0 - r2);
  }

  // Smooth Bubblegum-Pink Plush Head with Wide Smiling Cheek Flare
  const headCoreGeo = new THREE.SphereGeometry(1, 48, 36);
  const hcPos = headCoreGeo.attributes.position;
  for (let i = 0; i < hcPos.count; i++) {
    let x = hcPos.getX(i);
    let y = hcPos.getY(i);
    let z = hcPos.getZ(i);
    const cheekFlare = Math.exp(-Math.pow((y + 0.18) / 0.42, 2));
    x *= HEAD_RX * (1.0 + 0.15 * cheekFlare - 0.12 * Math.max(0, y));
    y *= HEAD_RY;
    z *= HEAD_RZ;
    if (z > 0.15 && Math.abs(x) < 0.36 && y > -0.35 && y < -0.06) {
      z -= 0.025;
    }
    hcPos.setXYZ(i, x, y, z);
  }
  headCoreGeo.computeVertexNormals();
  const headCore = new THREE.Mesh(headCoreGeo, materials.pinkPlush);
  headCore.position.set(0, HEAD_CY, 0);
  headCore.castShadow = true;
  headGroup.add(headCore);

  // Floppy Forward-Folded Pig Ears (Left & Right)
  function createPigEar(side) {
    const earGroup = new THREE.Group();
    earGroup.name = side < 0 ? 'Left_Ear_Group' : 'Right_Ear_Group';
    earGroup.position.set(side * 0.24, 0.72, 0.04);
    earGroup.rotation.z = side * -0.34;
    earGroup.rotation.x = 0.18;
    earGroup.rotation.y = side * -0.14;
    headGroup.add(earGroup);

    const earGeo = new THREE.SphereGeometry(1, 28, 20);
    const ePos = earGeo.attributes.position;
    for (let i = 0; i < ePos.count; i++) {
      let x = ePos.getX(i);
      let y = ePos.getY(i);
      let z = ePos.getZ(i);
      const u = Math.max(0, Math.min(1, (side * x + 1.0) * 0.5));
      const widthEnv = Math.sin(Math.PI * (0.12 + 0.82 * u)) * (1.15 - 0.32 * u);
      x *= 0.175;
      y = y * 0.130 * widthEnv + 0.045 * Math.sin(Math.PI * u) - 0.03 * u * u;
      z = z * 0.056 + 0.068 * Math.pow(u, 1.5);
      ePos.setXYZ(i, x + side * 0.125, y, z);
    }
    earGeo.computeVertexNormals();
    const earMesh = new THREE.Mesh(earGeo, materials.pinkPlush);
    earMesh.castShadow = true;
    earGroup.add(earMesh);

    const innerGeo = new THREE.SphereGeometry(1, 22, 16);
    const iPos = innerGeo.attributes.position;
    for (let i = 0; i < iPos.count; i++) {
      let x = iPos.getX(i);
      let y = iPos.getY(i);
      let z = iPos.getZ(i);
      const u = Math.max(0, Math.min(1, (side * x + 1.0) * 0.5));
      const widthEnv = Math.sin(Math.PI * (0.14 + 0.80 * u)) * (1.10 - 0.30 * u);
      x *= 0.130;
      y = y * 0.090 * widthEnv + 0.035 * Math.sin(Math.PI * u) - 0.022 * u * u;
      z = z * 0.025 + 0.055 * Math.pow(u, 1.5);
      iPos.setXYZ(i, x + side * 0.130, y, z + 0.028);
    }
    innerGeo.computeVertexNormals();
    const innerMesh = new THREE.Mesh(innerGeo, materials.hoofMagenta);
    earGroup.add(innerMesh);

    return earGroup;
  }

  const leftEarGroup = createPigEar(-1);
  const rightEarGroup = createPigEar(1);

  // ============================================================================
  // 7. ROUND GLOSSY BLACK DOME EYES, CATCHLIGHTS & ARCHED EYEBROWS
  // ============================================================================
  const eyesGroup = new THREE.Group();
  eyesGroup.name = 'Eyes_And_Eyelids_Group';
  headGroup.add(eyesGroup);

  function createEyeAssembly(side) {
    const ex = side * 0.145;
    const ey = 0.505;
    const ez = headFrontZ(ex, ey) - 0.012;

    const eyeWrap = new THREE.Group();
    eyeWrap.position.set(ex, ey, ez);
    eyeWrap.rotation.y = side * 0.18;
    eyesGroup.add(eyeWrap);

    const socketGeo = new THREE.SphereGeometry(0.104, 28, 20);
    socketGeo.scale(1.06, 1.06, 0.58);
    const socketMesh = new THREE.Mesh(socketGeo, materials.pinkPlush);
    socketMesh.position.set(0, 0, -0.008);
    eyeWrap.add(socketMesh);

    const eyeSphereGeo = new THREE.SphereGeometry(0.098, 36, 28);
    eyeSphereGeo.scale(1.02, 1.02, 0.74);
    const eyeMesh = new THREE.Mesh(eyeSphereGeo, materials.glossyEye);
    eyeWrap.add(eyeMesh);

    const catchGeo = new THREE.SphereGeometry(1, 16, 12);
    catchGeo.scale(0.020, 0.028, 0.006);
    const catchMesh = new THREE.Mesh(catchGeo, materials.eyeHighlight);
    catchMesh.position.set(side * -0.024, 0.024, 0.070);
    eyeWrap.add(catchMesh);

    const catch2 = new THREE.Mesh(new THREE.SphereGeometry(0.009, 10, 8), materials.eyeHighlight);
    catch2.position.set(side * 0.025, -0.026, 0.068);
    eyeWrap.add(catch2);

    // Arched cartoon eyebrow above eye
    const browCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(side * -0.05, 0.14, 0.02),
      new THREE.Vector3(0.0, 0.17, 0.03),
      new THREE.Vector3(side * 0.06, 0.14, 0.01)
    ]);
    const browGeo = new THREE.TubeGeometry(browCurve, 14, 0.010, 8, false);
    const browMesh = new THREE.Mesh(browGeo, materials.seamDark);
    eyeWrap.add(browMesh);
  }

  createEyeAssembly(-1);
  createEyeAssembly(1);

  // ============================================================================
  // 8. PROMINENT OVAL PIG SNOUT (#E02874 + #C2185B NOSTRILS) & CHEERFUL GRIN
  // ============================================================================
  const jawGroup = new THREE.Group();
  jawGroup.name = 'Snout_And_Jaw_Group';
  headGroup.add(jawGroup);

  // Prominent Oval Pig Snout
  const snoutGeo = new THREE.SphereGeometry(1, 32, 24);
  snoutGeo.scale(0.132, 0.086, 0.092);
  const snoutMesh = new THREE.Mesh(snoutGeo, materials.snoutRose);
  snoutMesh.position.set(0, 0.395, headFrontZ(0, 0.395) + 0.045);
  snoutMesh.rotation.x = -0.08;
  snoutMesh.castShadow = true;
  jawGroup.add(snoutMesh);

  [-1, 1].forEach(side => {
    const nRimGeo = new THREE.SphereGeometry(1, 16, 12);
    nRimGeo.scale(0.025, 0.036, 0.015);
    const nRim = new THREE.Mesh(nRimGeo, materials.hoofMagenta);
    nRim.position.set(side * 0.046, 0.395, headFrontZ(0, 0.395) + 0.125);
    nRim.rotation.z = side * -0.12;
    jawGroup.add(nRim);

    const nHoleGeo = new THREE.SphereGeometry(1, 14, 10);
    nHoleGeo.scale(0.017, 0.027, 0.014);
    const nHole = new THREE.Mesh(nHoleGeo, materials.nostrilDark);
    nHole.position.set(side * 0.046, 0.395, headFrontZ(0, 0.395) + 0.131);
    nHole.rotation.z = side * -0.12;
    jawGroup.add(nHole);
  });

  function upperLipPoint(t) {
    const x = t * 0.425;
    const y = 0.335 + 0.095 * (t * t) - 0.015 * Math.pow(t, 4);
    const zBase = headFrontZ(x, y);
    const zSnout = 0.018 + 0.014 * Math.cos(t * (Math.PI * 0.46));
    return new THREE.Vector3(x, y, zBase + zSnout);
  }

  function lowerLipPoint(t) {
    const ang = t * (Math.PI * 0.49);
    const x = Math.sin(ang) * 0.425;
    const y = 0.365 - Math.cos(ang) * 0.335;
    const zBase = headFrontZ(x, y);
    const zArch = 0.018 + 0.010 * Math.cos(ang * 0.85);
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

  // Coral-Pink Plush Tongue at bottom of wide grin
  const tongueGeo = new THREE.SphereGeometry(1, 22, 16);
  tongueGeo.scale(0.125, 0.042, 0.055);
  const tongueMesh = new THREE.Mesh(tongueGeo, materials.tongueCoral);
  tongueMesh.position.set(0, 0.115, headFrontZ(0, 0.115) + 0.008);
  tongueMesh.rotation.x = 0.18;
  jawGroup.add(tongueMesh);

  // Subtle dark plush scent/speaker disc inside mouth cavity (025_PickyPiggy_Plushie.webp)
  const discGeo = new THREE.SphereGeometry(1, 20, 14);
  discGeo.scale(0.072, 0.072, 0.016);
  const discMesh = new THREE.Mesh(discGeo, materials.seamDark);
  discMesh.position.set(0, 0.245, headFrontZ(0, 0.245) + 0.008);
  jawGroup.add(discMesh);

  const upperLipPts = [];
  for (let i = 0; i <= 40; i++) {
    upperLipPts.push(upperLipPoint((i / 40) * 2.0 - 1.0));
  }
  const upperLipCurve = new THREE.CatmullRomCurve3(upperLipPts);
  const upperLipGeo = new THREE.TubeGeometry(upperLipCurve, 56, 0.030, 20, false);
  const upperLipMesh = new THREE.Mesh(upperLipGeo, materials.pinkPlush);
  upperLipMesh.castShadow = true;
  jawGroup.add(upperLipMesh);

  const lowerLipPts = [];
  for (let i = 0; i <= 40; i++) {
    lowerLipPts.push(lowerLipPoint((i / 40) * 2.0 - 1.0));
  }
  const lowerLipCurve = new THREE.CatmullRomCurve3(lowerLipPts);
  const lowerLipGeo = new THREE.TubeGeometry(lowerLipCurve, 56, 0.030, 20, false);
  const lowerLipMesh = new THREE.Mesh(lowerLipGeo, materials.pinkPlush);
  lowerLipMesh.castShadow = true;
  jawGroup.add(lowerLipMesh);

  [-1, 1].forEach(side => {
    const pCorner = upperLipPoint(side);
    const cornerCap = new THREE.Mesh(new THREE.SphereGeometry(0.036, 16, 12), materials.pinkPlush);
    cornerCap.position.copy(pCorner);
    jawGroup.add(cornerCap);
  });

  // ============================================================================
  // 9. 3D SCULPTED CARTOON FART CLOUD CLUSTER (FOR `PickyPiggy_Fart_Blast`)
  // ============================================================================
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

  const fartCloudGroup = new THREE.Group();
  fartCloudGroup.name = 'PickyPiggy_Fart_Cloud_Group';
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


  loadCritterV11GLB(THREE, './models/picky_piggy_plush_base_model.glb', { root, bodyRig, headGroup, pendantGroup: pendantGroup, fartCloudGroup }, velourBump);

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

export { buildPickyPiggyPlushModel as buildBabaChopsPlushModel };
