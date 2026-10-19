
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
 * Bubba Bubbaphant 3D Plush Base Model Generator (Three.js r161 ESM)
 * ============================================================================
 * 1:1 High-Precision 3D Recreation of `images/029_Bubba_Bubbaphant_Plushie.webp`
 * Official Poppy Playtime Chapter 3 (Smiling Critters) Bubba Bubbaphant Plush
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
        const c1 = Math.sin(nx * Math.PI * 14) * Math.cos(ny * Math.PI * 14);
        const c2 = Math.sin((nx + ny) * Math.PI * 24) * Math.cos((nx - ny) * Math.PI * 24);
        const hash = Math.sin((x * 12.9898 + y * 78.233)) * 43758.5453;
        const grain = (hash - Math.floor(hash)) - 0.5;
        v = Math.max(0, Math.min(255, Math.floor(128 + 52 * c1 + 32 * c2 + 24 * grain)));
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
  tex.repeat.set(mode === 'cloud' ? 4 : 6, mode === 'cloud' ? 4 : 6);
  return tex;
}

export function buildBubbaBubbaphantPlushModel(THREE) {
  const root = new THREE.Group();
  root.name = 'BubbaBubbaphant_Plush_BaseModel';

  const bodyRig = new THREE.Group();
  bodyRig.name = 'Body_Rig_Root';
  root.add(bodyRig);

  const velourBump = createPlushBumpTexture(THREE, 'velour');
  const cloudBump = createPlushBumpTexture(THREE, 'cloud');

  // Calibrated PBR Material Palette matched to `images/029_Bubba_Bubbaphant_Plushie.webp`
  const materials = {
    ceruleanPlush: new THREE.MeshStandardMaterial({
      name: 'Bubba_Cerulean_Plush_Body',
      color: 0x2e8bc0,
      roughness: 0.82,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.009
    }),
    iceBlueAccent: new THREE.MeshStandardMaterial({
      name: 'Bubba_IceBlue_Plush_Accent',
      color: 0x9ad9f5,
      roughness: 0.78,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.007
    }),
    deepAzurePlush: new THREE.MeshStandardMaterial({
      name: 'Bubba_DeepAzure_InnerEar_Cuff',
      color: 0x1a659e,
      roughness: 0.85,
      metalness: 0.02,
      bumpMap: velourBump,
      bumpScale: 0.008
    }),
    lightbulbYellow: new THREE.MeshStandardMaterial({
      name: 'Bubba_Lightbulb_Pendant_Yellow',
      color: 0xffd60a,
      emissive: 0xf59e0b,
      emissiveIntensity: 0.24,
      roughness: 0.24,
      metalness: 0.08
    }),
    filamentAmber: new THREE.MeshStandardMaterial({
      name: 'Bubba_Lightbulb_Filament_Amber',
      color: 0xb45309,
      emissive: 0xd97706,
      emissiveIntensity: 0.18,
      roughness: 0.32,
      metalness: 0.65
    }),
    screwBaseBlue: new THREE.MeshStandardMaterial({
      name: 'Bubba_ScrewBase_Cobalt_Blue',
      color: 0x1d4ed8,
      roughness: 0.28,
      metalness: 0.78
    }),
    tonguePink: new THREE.MeshStandardMaterial({
      name: 'Bubba_Tongue_Rose_Pink',
      color: 0xf472b6,
      roughness: 0.78,
      metalness: 0.02
    }),
    mouthCavity: new THREE.MeshBasicMaterial({
      name: 'Bubba_Recessed_Mouth_Void',
      color: 0x050507,
      side: THREE.DoubleSide
    }),
    glossyEye: new THREE.MeshPhysicalMaterial({
      name: 'Bubba_Glossy_Acrylic_Eye',
      color: 0x020204,
      roughness: 0.05,
      metalness: 0.0,
      envMapIntensity: 0.14,
      clearcoat: 1.0,
      clearcoatRoughness: 0.03,
      reflectivity: 0.96
    }),
    eyeHighlight: new THREE.MeshBasicMaterial({
      name: 'Bubba_Eye_Studio_Catchlight',
      color: 0xffffff
    }),
    metalZipper: new THREE.MeshStandardMaterial({
      name: 'Bubba_Silver_Zipper_Hardware',
      color: 0xd8dde6,
      roughness: 0.24,
      metalness: 0.85
    }),
    seamDark: new THREE.MeshStandardMaterial({
      name: 'Bubba_Zipper_Track_Black',
      color: 0x0e1015,
      roughness: 0.90,
      metalness: 0.02
    }),
    fartLime: new THREE.MeshStandardMaterial({
      name: 'Bubba_Fart_Cloud_Lime',
      color: 0x4ce629,
      emissive: 0x228b12,
      emissiveIntensity: 0.35,
      roughness: 0.65,
      metalness: 0.02,
      bumpMap: cloudBump,
      bumpScale: 0.015
    }),
    fartNeon: new THREE.MeshStandardMaterial({
      name: 'Bubba_Fart_Cloud_Neon_YellowGreen',
      color: 0xc4ff33,
      emissive: 0x84cc16,
      emissiveIntensity: 0.50,
      roughness: 0.45,
      metalness: 0.05
    }),
    fartPurple: new THREE.MeshStandardMaterial({
      name: 'Bubba_Fart_Cloud_Purple',
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
  // 1. TORSO, PALE ICE-BLUE BELLY PATCH & SMALL TUFTED BLUE ELEPHANT TAIL
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
  const torsoMesh = new THREE.Mesh(torsoGeo, materials.ceruleanPlush);
  torsoMesh.castShadow = true;
  torsoMesh.receiveShadow = true;
  torsoGroup.add(torsoMesh);

  // Pale Ice-Blue (#9AD9F5) Conformed Oval Belly Patch
  const bellyGeo = new THREE.SphereGeometry(1, 32, 24);
  const bPos = bellyGeo.attributes.position;
  for (let i = 0; i < bPos.count; i++) {
    const ux = bPos.getX(i) * 0.175;
    const uy = 0.735 + bPos.getY(i) * 0.195;
    const uz = bPos.getZ(i);
    const zSurf = torsoFrontZ(uy, ux);
    const rz = uz > 0 ? (zSurf + 0.004 * uz) : (zSurf - 0.015);
    bPos.setXYZ(i, ux, uy, rz);
  }
  bellyGeo.computeVertexNormals();
  const bellyMesh = new THREE.Mesh(bellyGeo, materials.iceBlueAccent);
  torsoGroup.add(bellyMesh);

  // Small Tufted Blue Elephant Tail at Rear Pelvis
  const tailGroup = new THREE.Group();
  tailGroup.name = 'Tail_Group';
  tailGroup.position.set(0, 0.56, -0.22);
  torsoGroup.add(tailGroup);

  const tailCurve = new THREE.CatmullRomCurve3([
    new THREE.Vector3(0, 0.0, 0.0),
    new THREE.Vector3(0, -0.02, -0.10),
    new THREE.Vector3(0, 0.03, -0.20),
    new THREE.Vector3(0, 0.09, -0.26)
  ]);
  const tailShaftGeo = new THREE.TubeGeometry(tailCurve, 20, 0.024, 14, false);
  const tailShaftMesh = new THREE.Mesh(tailShaftGeo, materials.ceruleanPlush);
  tailShaftMesh.castShadow = true;
  tailGroup.add(tailShaftMesh);

  const tailTuftGeo = new THREE.SphereGeometry(0.044, 18, 14);
  tailTuftGeo.scale(0.95, 1.10, 1.45);
  const tailTuftMesh = new THREE.Mesh(tailTuftGeo, materials.deepAzurePlush);
  tailTuftMesh.position.set(0, 0.11, -0.29);
  tailTuftMesh.rotation.x = 0.45;
  tailGroup.add(tailTuftMesh);

  // ============================================================================
  // 2. BLACK COLLAR ZIPPER & BRIGHT YELLOW GLOWING LIGHTBULB PENDANT
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

    const backSeg = new THREE.Mesh(backingSegGeo, materials.seamDark);
    backSeg.position.set(0, ty, zSurf - 0.002);
    zipperGroup.add(backSeg);

    const tooth = new THREE.Mesh(toothGeo, materials.metalZipper);
    tooth.position.set(side, ty, zSurf + 0.004);
    zipperGroup.add(tooth);
  }

  const zCollar = torsoFrontZ(0.985, 0);
  const sliderBody = new THREE.Mesh(new THREE.BoxGeometry(0.048, 0.056, 0.036), materials.screwBaseBlue);
  sliderBody.position.set(0, 0.990, zCollar + 0.008);
  sliderBody.rotation.x = -0.20;
  zipperGroup.add(sliderBody);

  // Lightbulb Pendant Group (`SkullPendant` / `Pendant` bone equivalent)
  const zChest = torsoFrontZ(0.80, 0);
  const skullPendantGroup = new THREE.Group();
  skullPendantGroup.name = 'Lightbulb_Pendant_Group';
  skullPendantGroup.position.set(0, 0.935, zChest + 0.012);
  skullPendantGroup.rotation.x = -0.08;
  torsoGroup.add(skullPendantGroup);

  const claspLoop = new THREE.Mesh(new THREE.BoxGeometry(0.038, 0.042, 0.024), materials.screwBaseBlue);
  claspLoop.position.set(0, -0.012, 0.0);
  skullPendantGroup.add(claspLoop);

  // Pear-Shaped Bright Yellow Glowing Lightbulb Globe
  const bulbGeo = new THREE.SphereGeometry(0.118, 32, 24);
  const lbPos = bulbGeo.attributes.position;
  for (let i = 0; i < lbPos.count; i++) {
    let lx = lbPos.getX(i);
    let ly = lbPos.getY(i);
    let lz = lbPos.getZ(i) * 0.36;
    const ny = ly / 0.118;
    if (ny < -0.15) {
      const u = Math.min(1.0, (-0.15 - ny) / 0.85);
      lx *= (1.0 - 0.42 * Math.pow(u, 1.1));
    }
    lbPos.setXYZ(i, lx, ly, lz);
  }
  bulbGeo.computeVertexNormals();
  const bulbMesh = new THREE.Mesh(bulbGeo, materials.lightbulbYellow);
  bulbMesh.position.set(0, -0.125, 0.006);
  bulbMesh.castShadow = true;
  skullPendantGroup.add(bulbMesh);

  // Heart-Shaped Glowing Filament on Front of Yellow Lightbulb
  const filPts = [];
  for (let k = 0; k <= 28; k++) {
    const u = k / 28.0;
    const ang = (u - 0.5) * Math.PI * 1.75;
    const fx = 0.052 * Math.sin(ang) * (1.0 - 0.25 * Math.pow(u - 0.5, 2));
    const fy = -0.165 + 0.076 * Math.cos(ang * 0.65) - 0.028 * Math.abs(Math.sin(ang * 1.1));
    filPts.push(new THREE.Vector3(fx, fy, 0.044));
  }
  const filCurve = new THREE.CatmullRomCurve3(filPts);
  const filGeo = new THREE.TubeGeometry(filCurve, 32, 0.0065, 10, false);
  const filMesh = new THREE.Mesh(filGeo, materials.filamentAmber);
  skullPendantGroup.add(filMesh);

  // Cobalt-Blue Threaded Screw Base at Bottom of Lightbulb
  const screwBaseGeo = new THREE.CylinderGeometry(0.052, 0.046, 0.058, 24);
  screwBaseGeo.scale(1.0, 1.0, 0.65);
  const screwBaseMesh = new THREE.Mesh(screwBaseGeo, materials.screwBaseBlue);
  screwBaseMesh.position.set(0, -0.242, 0.006);
  skullPendantGroup.add(screwBaseMesh);

  [-0.226, -0.242, -0.258].forEach(ty => {
    const threadRing = new THREE.Mesh(
      new THREE.TorusGeometry(0.051, 0.0055, 10, 24),
      materials.metalZipper
    );
    threadRing.rotation.x = Math.PI / 2;
    threadRing.scale.set(1.0, 0.66, 1.0);
    threadRing.position.set(0, ty, 0.006);
    skullPendantGroup.add(threadRing);
  });

  const contactTip = new THREE.Mesh(
    new THREE.SphereGeometry(0.028, 16, 12),
    materials.mouthCavity
  );
  contactTip.scale.set(1.0, 0.55, 0.65);
  contactTip.position.set(0, -0.275, 0.006);
  skullPendantGroup.add(contactTip);

  // ============================================================================
  // 3. SPLAYED PLUSH ARMS & ELEPHANT CUFF PAWS WITH 3 ICE-BLUE TOE-NAIL PADS
  // ============================================================================
  function createArm(side) {
    const armGroup = new THREE.Group();
    armGroup.name = side < 0 ? 'Left_Arm_Group' : 'Right_Arm_Group';
    armGroup.position.set(side * 0.195, 0.955, 0.01);
    armGroup.rotation.z = side * 0.72;
    torsoGroup.add(armGroup);

    const sleeveGeo = new THREE.CylinderGeometry(0.084, 0.106, 0.30, 24, 12);
    const sleeveMesh = new THREE.Mesh(sleeveGeo, materials.ceruleanPlush);
    sleeveMesh.position.set(0, -0.145, 0);
    sleeveMesh.castShadow = true;
    armGroup.add(sleeveMesh);

    const shoulderCap = new THREE.Mesh(new THREE.SphereGeometry(0.084, 20, 16), materials.ceruleanPlush);
    armGroup.add(shoulderCap);

    const pawGroup = new THREE.Group();
    pawGroup.position.set(0, -0.34, 0.01);
    armGroup.add(pawGroup);

    const pawGeo = new THREE.SphereGeometry(0.114, 28, 22);
    pawGeo.scale(1.05, 1.12, 0.90);
    const pawMesh = new THREE.Mesh(pawGeo, materials.deepAzurePlush);
    pawMesh.castShadow = true;
    pawGroup.add(pawMesh);

    // 3 Pale Ice-Blue (#9AD9F5) Elephant Toe-Nail Pads on Paw
    [-0.042, 0.0, 0.042].forEach(tz => {
      const toeGeo = new THREE.SphereGeometry(0.024, 14, 10);
      toeGeo.scale(0.85, 1.15, 0.75);
      const toeMesh = new THREE.Mesh(toeGeo, materials.iceBlueAccent);
      toeMesh.position.set(side * 0.055, -0.095, 0.065 + tz);
      pawGroup.add(toeMesh);
    });

    return armGroup;
  }

  const leftArmGroup = createArm(-1);
  const rightArmGroup = createArm(1);

  // ============================================================================
  // 4. STOUT ELEPHANT LEGS & ROUNDED FEET WITH 3 ICE-BLUE TOE-NAIL PADS
  // ============================================================================
  function createLeg(side) {
    const legGroup = new THREE.Group();
    legGroup.name = side < 0 ? 'Left_Leg_Group' : 'Right_Leg_Group';
    legGroup.position.set(side * 0.15, 0.50, 0.0);
    legGroup.rotation.z = side * 0.065;
    bodyRig.add(legGroup);

    const legGeo = new THREE.CylinderGeometry(0.098, 0.105, 0.34, 24, 10);
    const legMesh = new THREE.Mesh(legGeo, materials.ceruleanPlush);
    legMesh.position.set(0, -0.17, 0);
    legMesh.castShadow = true;
    legGroup.add(legMesh);

    const footGroup = new THREE.Group();
    footGroup.position.set(0, -0.405, 0.03);
    footGroup.rotation.z = -side * 0.065;
    legGroup.add(footGroup);

    const footGeo = new THREE.SphereGeometry(0.124, 28, 22);
    const fPos = footGeo.attributes.position;
    for (let i = 0; i < fPos.count; i++) {
      let x = fPos.getX(i) * 1.06;
      let y = fPos.getY(i);
      let z = fPos.getZ(i) * 1.16;
      if (y < 0) y *= 0.70;
      else y *= 0.94;
      fPos.setXYZ(i, x, y, z);
    }
    footGeo.computeVertexNormals();
    const footMesh = new THREE.Mesh(footGeo, materials.deepAzurePlush);
    footMesh.castShadow = true;
    footMesh.receiveShadow = true;
    footGroup.add(footMesh);

    // 3 Pale Ice-Blue (#9AD9F5) Elephant Toe-Nail Pads on Front of Each Foot
    [-0.42, 0.0, 0.42].forEach(ang => {
      const ftoeGeo = new THREE.SphereGeometry(0.032, 16, 12);
      ftoeGeo.scale(0.95, 1.20, 0.62);
      const ftoeMesh = new THREE.Mesh(ftoeGeo, materials.iceBlueAccent);
      ftoeMesh.position.set(Math.sin(ang) * 0.082, -0.022, Math.cos(ang) * 0.136);
      ftoeMesh.rotation.y = ang;
      ftoeMesh.rotation.x = -0.15;
      footGroup.add(ftoeMesh);
    });

    return legGroup;
  }

  const leftLegGroup = createLeg(-1);
  const rightLegGroup = createLeg(1);

  // ============================================================================
  // 5. HEAD, WIDE FANNING ELEPHANT EARS, UPWARD-CURLED TRUNK, EYES & GRIN
  // ============================================================================
  const headGroup = new THREE.Group();
  headGroup.name = 'Head_Group';
  headGroup.position.set(0, 1.06, 0);
  bodyRig.add(headGroup);

  const HEAD_RX = 0.445, HEAD_RY = 0.415, HEAD_RZ = 0.410, HEAD_CY = 0.43;
  function headFrontZ(x, y) {
    const nx = x / HEAD_RX;
    const ny = (y - HEAD_CY) / HEAD_RY;
    const r2 = nx * nx + ny * ny;
    if (r2 >= 0.96) return HEAD_RZ * 0.20;
    return HEAD_RZ * Math.sqrt(1.0 - r2);
  }

  // Smooth Plush Elephant Head with Flared Smiling Cheeks
  const headCoreGeo = new THREE.SphereGeometry(1, 44, 36);
  const hcPos = headCoreGeo.attributes.position;
  for (let i = 0; i < hcPos.count; i++) {
    let x = hcPos.getX(i);
    let y = hcPos.getY(i);
    let z = hcPos.getZ(i);
    if (y > 0.15) {
      const u = (y - 0.15) / 0.85;
      x *= (1.0 - 0.16 * Math.pow(u, 1.3));
      z *= (1.0 - 0.08 * Math.pow(u, 1.2));
    } else {
      const cheekU = Math.exp(-Math.pow((y + 0.12) / 0.42, 2));
      x *= (1.0 + 0.12 * cheekU);
      if (z > 0) z *= (1.0 + 0.05 * cheekU);
    }
    hcPos.setXYZ(i, x * HEAD_RX, y * HEAD_RY, z * HEAD_RZ);
  }
  headCoreGeo.computeVertexNormals();
  const headCore = new THREE.Mesh(headCoreGeo, materials.ceruleanPlush);
  headCore.position.set(0, HEAD_CY, 0);
  headCore.castShadow = true;
  headGroup.add(headCore);

  // ============================================================================
  // 6. LARGE WIDE FANNING ELEPHANT EARS (`Ear.L`, `Ear.R`)
  // ============================================================================
  function createElephantEar(side) {
    const earGroup = new THREE.Group();
    earGroup.name = side < 0 ? 'Left_Ear_Group' : 'Right_Ear_Group';
    earGroup.position.set(side * 0.38, 0.50, -0.02);
    earGroup.rotation.z = side * -0.08;
    earGroup.rotation.y = side * -0.16;
    headGroup.add(earGroup);

    const earGeo = new THREE.SphereGeometry(1, 32, 24);
    const ePos = earGeo.attributes.position;
    for (let i = 0; i < ePos.count; i++) {
      let x = ePos.getX(i) * 0.27;
      let y = ePos.getY(i) * 0.34;
      let z = ePos.getZ(i) * 0.075;
      const ux = (side * x) / 0.27;
      const uy = y / 0.34;
      y *= (0.88 + 0.24 * Math.max(0, ux + 0.2) + 0.10 * uy);
      z -= 0.030 * Math.pow(Math.max(0, ux), 2);
      ePos.setXYZ(i, x + side * 0.18, y, z);
    }
    earGeo.computeVertexNormals();
    const earMesh = new THREE.Mesh(earGeo, materials.ceruleanPlush);
    earMesh.castShadow = true;
    earGroup.add(earMesh);

    const iceRimGeo = new THREE.SphereGeometry(1, 26, 20);
    const rPos = iceRimGeo.attributes.position;
    for (let i = 0; i < rPos.count; i++) {
      let x = rPos.getX(i) * 0.205;
      let y = rPos.getY(i) * 0.265;
      let z = rPos.getZ(i) * 0.035;
      const ux = (side * x) / 0.205;
      const uy = y / 0.265;
      y *= (0.88 + 0.22 * Math.max(0, ux + 0.2) + 0.08 * uy);
      z -= 0.022 * Math.pow(Math.max(0, ux), 2);
      rPos.setXYZ(i, x + side * 0.19, y - 0.005, z + 0.034);
    }
    iceRimGeo.computeVertexNormals();
    const iceRimMesh = new THREE.Mesh(iceRimGeo, materials.iceBlueAccent);
    earGroup.add(iceRimMesh);

    const innerGeo = new THREE.SphereGeometry(1, 26, 20);
    const iPos = innerGeo.attributes.position;
    for (let i = 0; i < iPos.count; i++) {
      let x = iPos.getX(i) * 0.188;
      let y = iPos.getY(i) * 0.246;
      let z = iPos.getZ(i) * 0.032;
      const ux = (side * x) / 0.188;
      const uy = y / 0.246;
      y *= (0.88 + 0.22 * Math.max(0, ux + 0.2) + 0.08 * uy);
      z -= 0.022 * Math.pow(Math.max(0, ux), 2);
      iPos.setXYZ(i, x + side * 0.192, y - 0.006, z + 0.040);
    }
    innerGeo.computeVertexNormals();
    const innerMesh = new THREE.Mesh(innerGeo, materials.deepAzurePlush);
    earGroup.add(innerMesh);

    return earGroup;
  }

  const leftEarGroup = createElephantEar(-1);
  const rightEarGroup = createElephantEar(1);

  // ============================================================================
  // 7. GLOSSY JET-BLACK DOME EYES, CATCHLIGHTS & ARCHED EYEBROWS
  // ============================================================================
  const eyesGroup = new THREE.Group();
  eyesGroup.name = 'Eyes_And_Brows_Group';
  headGroup.add(eyesGroup);

  function createEyeAssembly(side) {
    const ex = side * 0.135;
    const ey = 0.505;
    const ez = headFrontZ(ex, ey) - 0.012;

    const eyeWrap = new THREE.Group();
    eyeWrap.position.set(ex, ey, ez);
    eyeWrap.rotation.y = side * 0.16;
    eyesGroup.add(eyeWrap);

    const socketGeo = new THREE.SphereGeometry(0.098, 24, 18);
    socketGeo.scale(1.04, 1.10, 0.58);
    const socketMesh = new THREE.Mesh(socketGeo, materials.ceruleanPlush);
    socketMesh.position.set(0, 0, -0.008);
    eyeWrap.add(socketMesh);

    const eyeSphereGeo = new THREE.SphereGeometry(0.090, 32, 24);
    eyeSphereGeo.scale(1.02, 1.08, 0.72);
    const eyeMesh = new THREE.Mesh(eyeSphereGeo, materials.glossyEye);
    eyeWrap.add(eyeMesh);

    const catchGeo = new THREE.SphereGeometry(1, 14, 10);
    catchGeo.scale(0.018, 0.028, 0.006);
    const catchMesh = new THREE.Mesh(catchGeo, materials.eyeHighlight);
    catchMesh.position.set(-side * 0.018, 0.016, 0.064);
    eyeWrap.add(catchMesh);

    const catch2 = new THREE.Mesh(new THREE.SphereGeometry(0.008, 10, 8), materials.eyeHighlight);
    catch2.position.set(side * 0.022, -0.024, 0.062);
    eyeWrap.add(catch2);

    // Arched Black Eyebrow above eye
    const browPts = [];
    for (let k = 0; k <= 10; k++) {
      const t = k / 10.0;
      const bx = side * (0.06 + 0.14 * t);
      const by = 0.65 + 0.042 * Math.sin(Math.PI * t);
      const bz = headFrontZ(bx, by) + 0.012;
      browPts.push(new THREE.Vector3(bx, by, bz));
    }
    const browCurve = new THREE.CatmullRomCurve3(browPts);
    const browGeo = new THREE.TubeGeometry(browCurve, 16, 0.011, 8, false);
    const browMesh = new THREE.Mesh(browGeo, materials.mouthCavity);
    eyesGroup.add(browMesh);
  }

  createEyeAssembly(-1);
  createEyeAssembly(1);

  // ============================================================================
  // 8. WIDE CHEERFUL OPEN GRIN, ROSY TONGUE & ICONIC UPWARD-CURLED ELEPHANT TRUNK
  // ============================================================================
  const jawGroup = new THREE.Group();
  jawGroup.name = 'Muzzle_Trunk_And_Jaw_Group';
  headGroup.add(jawGroup);

  function upperLipPoint(t) {
    const x = t * 0.355;
    const cheekLift = 0.075 * Math.pow(t, 2) - 0.015 * Math.pow(t, 4);
    const y = 0.355 + cheekLift;
    const zBase = headFrontZ(x, y);
    return new THREE.Vector3(x, y, zBase + 0.020 * (1.0 - 0.3 * t * t));
  }

  function lowerLipPoint(t) {
    const ang = t * (Math.PI * 0.49);
    const x = Math.sin(ang) * 0.355;
    const y = 0.365 - Math.cos(ang) * 0.265;
    const zBase = headFrontZ(x, y);
    return new THREE.Vector3(x, y, zBase + 0.018 * Math.cos(ang * 0.85));
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

  // Rosy-Pink Plush Tongue inside lower mouth cavity
  [-1, 1].forEach(side => {
    const tongueGeo = new THREE.SphereGeometry(0.085, 18, 14);
    tongueGeo.scale(1.0, 0.45, 0.55);
    const tongueMesh = new THREE.Mesh(tongueGeo, materials.tonguePink);
    tongueMesh.position.set(side * 0.048, 0.165, headFrontZ(side * 0.048, 0.165) + 0.012);
    tongueMesh.rotation.z = -side * 0.12;
    jawGroup.add(tongueMesh);
  });

  // Upper & Lower Smiling Cerulean Plush Lip Rims
  const upperLipPts = [];
  const lowerLipPts = [];
  for (let i = 0; i <= 36; i++) {
    const t = (i / 36) * 2.0 - 1.0;
    upperLipPts.push(upperLipPoint(t));
    lowerLipPts.push(lowerLipPoint(t));
  }
  const upperLipGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(upperLipPts), 48, 0.028, 16, false);
  const lowerLipGeo = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(lowerLipPts), 48, 0.025, 16, false);
  jawGroup.add(new THREE.Mesh(upperLipGeo, materials.ceruleanPlush));
  jawGroup.add(new THREE.Mesh(lowerLipGeo, materials.ceruleanPlush));

  [-1, 1].forEach(side => {
    const pCorner = upperLipPoint(side);
    const cornerCap = new THREE.Mesh(new THREE.SphereGeometry(0.032, 16, 12), materials.ceruleanPlush);
    cornerCap.position.copy(pCorner);
    jawGroup.add(cornerCap);
  });

  // Iconic Upward-Curled Plush Elephant Trunk (`trunkGroup`)
  const trunkGroup = new THREE.Group();
  trunkGroup.name = 'Elephant_Trunk_Group';
  jawGroup.add(trunkGroup);

  const trunkPts = [];
  for (let k = 0; k < 24; k++) {
    const u = k / 23.0;
    const tx = -0.014 * Math.sin(u * Math.PI * 0.85);
    let ty, tz;
    if (u < 0.62) {
      const v = u / 0.62;
      ty = 0.435 - 0.285 * Math.pow(v, 1.08);
      tz = 0.395 + 0.155 * Math.sin(v * Math.PI * 0.62);
    } else {
      const v = (u - 0.62) / 0.38;
      const ang = v * Math.PI * 0.78;
      ty = 0.150 + 0.088 * (1.0 - Math.cos(ang));
      tz = 0.535 + 0.105 * Math.sin(ang);
    }
    trunkPts.push(new THREE.Vector3(tx, ty, tz));
  }
  const trunkCurve = new THREE.CatmullRomCurve3(trunkPts);
  const trunkGeo = new THREE.TubeGeometry(trunkCurve, 44, 0.082, 22, false);
  const trPos = trunkGeo.attributes.position;
  for (let i = 0; i < trPos.count; i++) {
    // Taper trunk radius slightly from root to curled tip
    const vx = trPos.getX(i);
    const vy = trPos.getY(i);
    const vz = trPos.getZ(i);
    const uApprox = Math.max(0, Math.min(1, (0.435 - vy) / 0.28));
    const scaleR = 1.0 - 0.16 * uApprox;
    trPos.setXYZ(i, vx * scaleR, vy, vz);
  }
  trunkGeo.computeVertexNormals();
  const trunkMesh = new THREE.Mesh(trunkGeo, materials.ceruleanPlush);
  trunkMesh.castShadow = true;
  trunkGroup.add(trunkMesh);

  // Pale Ice-Blue (#9AD9F5) Trunk Tip Pad & Deep-Azure Nostril Dimple
  const pTip = trunkPts[trunkPts.length - 1];
  const trunkTipPad = new THREE.Mesh(
    new THREE.SphereGeometry(0.064, 20, 14),
    materials.iceBlueAccent
  );
  trunkTipPad.scale.set(1.0, 1.0, 0.38);
  trunkTipPad.position.set(pTip.x, pTip.y + 0.008, pTip.z + 0.012);
  trunkTipPad.rotation.x = -0.55;
  trunkGroup.add(trunkTipPad);

  const trunkNostril = new THREE.Mesh(
    new THREE.SphereGeometry(0.036, 16, 12),
    materials.deepAzurePlush
  );
  trunkNostril.scale.set(1.0, 0.88, 0.32);
  trunkNostril.position.set(pTip.x, pTip.y + 0.012, pTip.z + 0.022);
  trunkNostril.rotation.x = -0.55;
  trunkGroup.add(trunkNostril);

  // ============================================================================
  // 9. 3D SCULPTED CARTOON FART CLOUD CLUSTER (FOR `Bubba_Fart_Blast` ANIMATION)
  // ============================================================================
  const basePuffGeo = new THREE.SphereGeometry(1, 20, 16);
  const pPos = basePuffGeo.attributes.position;
  for (let i = 0; i < pPos.count; i++) {
    const vx = pPos.getX(i);
    const vy = pPos.getY(i);
    const vz = pPos.getZ(i);
    const disp = 1.0 + 0.07 * Math.sin(vx * 7.0) * Math.cos(vy * 7.0) * Math.sin(vz * 7.0);
    pPos.setXYZ(i, vx * disp, vy * disp, vz * disp);
  }
  basePuffGeo.computeVertexNormals();

  const fartCloudGroup = new THREE.Group();
  fartCloudGroup.name = 'Bubba_Fart_Cloud_Group';
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


  loadCritterV11GLB(THREE, './models/bubba_bubbaphant_plush_base_model.glb', { root, bodyRig, headGroup, pendantGroup: skullPendantGroup, fartCloudGroup }, velourBump);

  return {
    root,
    bodyRig,
    torsoGroup,
    headGroup,
    trunkGroup,
    tailGroup,
    leftEarGroup,
    rightEarGroup,
    eyesGroup,
    jawGroup,
    leftArmGroup,
    rightArmGroup,
    leftLegGroup,
    rightLegGroup,
    pendantGroup: skullPendantGroup,
    skullPendantGroup,
    fartCloudGroup,
    fartStage1,
    fartStage2,
    fartStage3,
    materials
  };
}

export { buildBubbaBubbaphantPlushModel as buildBabaChopsPlushModel };
