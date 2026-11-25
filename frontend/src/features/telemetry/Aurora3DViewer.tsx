import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { Box, Maximize2, Minimize2, RotateCw, Sparkles } from 'lucide-react';
import { useI18n } from '../../i18n';
import type { ShipState } from '../../types/mission';

interface Aurora3DViewerProps {
  ship: ShipState;
  scenarioId: string;
  activeNodes: string[];
  expanded?: boolean;
  onToggleExpand?: () => void;
}

function metricColorHex(value: number): number {
  if (value >= 70) return 0x22d3ee; // cyan / healthy glow
  if (value >= 45) return 0xf59e0b; // amber warning
  return 0xef4444; // critical red
}

export function Aurora3DViewer({
  ship,
  scenarioId,
  activeNodes,
  expanded = false,
  onToggleExpand,
}: Aurora3DViewerProps) {
  const { t } = useI18n();
  const mountRef = useRef<HTMLDivElement | null>(null);
  const [hologramMode, setHologramMode] = useState(true);
  const [webglError, setWebglError] = useState(false);

  const shipRef = useRef(ship);
  shipRef.current = ship;

  const scenarioRef = useRef(scenarioId);
  scenarioRef.current = scenarioId;

  const activeNodesRef = useRef(activeNodes);
  activeNodesRef.current = activeNodes;

  const hologramModeRef = useRef(hologramMode);
  hologramModeRef.current = hologramMode;

  const scanPulseRef = useRef(0);
  const prevShipSigRef = useRef('');
  const resetCamRef = useRef<(() => void) | null>(null);

  // Trigger a 3D scan/repair wave across the hull whenever ship telemetry changes
  useEffect(() => {
    const sig = `${ship.energy}-${ship.oxygen}-${ship.hull_integrity}-${ship.engine_condition}-${ship.communication}-${ship.navigation}`;
    if (prevShipSigRef.current && prevShipSigRef.current !== sig) {
      scanPulseRef.current = 1.0;
    }
    prevShipSigRef.current = sig;
  }, [ship]);

  useEffect(() => {
    const container = mountRef.current;
    if (!container) return;

    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: true,
        powerPreference: 'high-performance',
      });
    } catch {
      setWebglError(true);
      return;
    }

    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(container.clientWidth || 240, container.clientHeight || 180);
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    const scene = new THREE.Scene();

    const camera = new THREE.PerspectiveCamera(
      40,
      (container.clientWidth || 240) / Math.max(1, container.clientHeight || 180),
      0.1,
      100
    );
    const defaultCamPos = new THREE.Vector3(4.6, 2.3, 5.0);
    camera.position.copy(defaultCamPos);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.enablePan = false;
    controls.minDistance = 3.0;
    controls.maxDistance = 11.5;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 0.7;

    resetCamRef.current = () => {
      camera.position.copy(defaultCamPos);
      controls.target.set(0, 0, 0);
      controls.update();
    };

    // Lighting — Mass Effect / Homeworld cool rim + warm key
    const ambient = new THREE.AmbientLight(0x334155, 1.4);
    scene.add(ambient);

    const keyLight = new THREE.DirectionalLight(0xe0f2fe, 2.2);
    keyLight.position.set(6, 7, 5);
    scene.add(keyLight);

    const rimLight = new THREE.DirectionalLight(0x06b6d4, 2.0);
    rimLight.position.set(-6, -3, -5);
    scene.add(rimLight);

    const coreLight = new THREE.PointLight(0x22d3ee, 2.5, 6);
    coreLight.position.set(-0.6, 0, 0);
    scene.add(coreLight);

    // Subtle holographic floor grid
    const grid = new THREE.GridHelper(10, 18, 0x0e7490, 0x1e293b);
    grid.position.y = -1.65;
    const gridMat = grid.material as THREE.Material;
    gridMat.transparent = true;
    gridMat.opacity = 0.25;
    scene.add(grid);

    // Starfield particles
    const starCount = 260;
    const starPos = new Float32Array(starCount * 3);
    for (let i = 0; i < starCount; i++) {
      const r = 14 + Math.random() * 18;
      const theta = Math.random() * Math.PI * 2;
      const phi = Math.acos(2 * Math.random() - 1);
      starPos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
      starPos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
      starPos[i * 3 + 2] = r * Math.cos(phi);
    }
    const starGeo = new THREE.BufferGeometry();
    starGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
    const starMat = new THREE.PointsMaterial({
      color: 0xbae6fd,
      size: 0.08,
      transparent: true,
      opacity: 0.65,
    });
    scene.add(new THREE.Points(starGeo, starMat));

    // === AURORA-7 PROCEDURAL 3D SPACECRAFT ===
    const shipRoot = new THREE.Group();
    scene.add(shipRoot);

    const hullMat = new THREE.MeshStandardMaterial({
      color: 0x1e293b,
      metalness: 0.72,
      roughness: 0.28,
      emissive: 0x082f49,
      emissiveIntensity: 0.45,
      transparent: true,
      opacity: 0.9,
    });

    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.28,
    });

    const accentMat = new THREE.MeshStandardMaterial({
      color: 0x334155,
      metalness: 0.85,
      roughness: 0.2,
    });

    const addPartWithWire = (
      geo: THREE.BufferGeometry,
      mat: THREE.Material,
      pos: [number, number, number],
      rot: [number, number, number] = [0, 0, 0],
      parent: THREE.Object3D = shipRoot
    ) => {
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(...pos);
      mesh.rotation.set(...rot);
      parent.add(mesh);

      const wire = new THREE.Mesh(geo, wireMat);
      wire.scale.setScalar(1.008);
      mesh.add(wire);
      return mesh;
    };

    // 1. Central Spine & Forward Fuselage (along X axis: +X is bow, -X is stern)
    addPartWithWire(
      new THREE.CylinderGeometry(0.32, 0.48, 2.9, 12),
      hullMat,
      [0.15, 0, 0],
      [0, 0, -Math.PI / 2]
    );

    // 2. Forward Navigation Nose Cone & Sensor Needle
    const navMat = new THREE.MeshStandardMaterial({
      color: 0x0ea5e9,
      emissive: 0x22d3ee,
      emissiveIntensity: 1.1,
      metalness: 0.5,
      roughness: 0.2,
    });
    addPartWithWire(
      new THREE.ConeGeometry(0.32, 1.1, 12),
      hullMat,
      [2.15, 0, 0],
      [0, 0, -Math.PI / 2]
    );
    const navBeacon = new THREE.Mesh(new THREE.SphereGeometry(0.11, 16, 16), navMat);
    navBeacon.position.set(2.72, 0, 0);
    shipRoot.add(navBeacon);

    // Command Bridge Dorsal Deck
    addPartWithWire(new THREE.BoxGeometry(0.95, 0.24, 0.5), accentMat, [1.05, 0.36, 0]);
    const bridgeWindow = new THREE.Mesh(
      new THREE.BoxGeometry(0.38, 0.08, 0.44),
      new THREE.MeshBasicMaterial({ color: 0x38bdf8 })
    );
    bridgeWindow.position.set(1.38, 0.4, 0);
    shipRoot.add(bridgeWindow);

    // 3. Rotating Habitat Gravity Ring (Oxygen & Crew Health)
    const habGroup = new THREE.Group();
    habGroup.position.set(0.55, 0, 0);
    shipRoot.add(habGroup);

    const habGlowMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      emissive: 0x22d3ee,
      emissiveIntensity: 0.85,
      metalness: 0.6,
      roughness: 0.25,
    });
    const habRing = new THREE.Mesh(new THREE.TorusGeometry(0.98, 0.12, 12, 36), habGlowMat);
    habRing.rotation.y = Math.PI / 2;
    habGroup.add(habRing);

    const habRingWire = new THREE.Mesh(new THREE.TorusGeometry(0.98, 0.125, 8, 36), wireMat);
    habRingWire.rotation.y = Math.PI / 2;
    habGroup.add(habRingWire);

    // 4 Spokes connecting Habitat Ring to Spine
    for (let i = 0; i < 4; i++) {
      const spoke = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 1.9, 8), accentMat);
      spoke.rotation.x = (i * Math.PI) / 4;
      habGroup.add(spoke);
    }

    // 4. Reactor Core (Energy) — Glowing Plasma Sphere inside Structural Cage
    const reactorMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x22d3ee,
      emissiveIntensity: 1.8,
      roughness: 0.1,
    });
    const reactorCore = new THREE.Mesh(new THREE.IcosahedronGeometry(0.34, 1), reactorMat);
    reactorCore.position.set(-0.65, 0, 0);
    shipRoot.add(reactorCore);

    const reactorRing = new THREE.Mesh(
      new THREE.TorusGeometry(0.52, 0.035, 8, 24),
      new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.65 })
    );
    reactorRing.position.set(-0.65, 0, 0);
    reactorRing.rotation.y = Math.PI / 2;
    shipRoot.add(reactorRing);

    // 5. Symmetrical Solar / Radiator Wings
    const wingGeo = new THREE.BoxGeometry(1.45, 0.05, 1.45);
    const leftWing = addPartWithWire(wingGeo, hullMat, [-0.55, 0, 1.18]);
    leftWing.rotation.x = 0.08;
    const rightWing = addPartWithWire(wingGeo, hullMat, [-0.55, 0, -1.18]);
    rightWing.rotation.x = -0.08;

    // 6. Communications Dish & Signal Pulse Rings (Communication)
    const commsMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      emissive: 0x22d3ee,
      emissiveIntensity: 1.0,
    });
    const dishMast = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.04, 0.55, 8), accentMat);
    dishMast.position.set(1.25, 0.65, 0);
    shipRoot.add(dishMast);

    const dishMesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.24, 16, 12, 0, Math.PI * 2, 0, Math.PI * 0.45),
      commsMat
    );
    dishMesh.position.set(1.25, 0.92, 0);
    dishMesh.rotation.z = -0.45;
    shipRoot.add(dishMesh);

    const signalRingMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.0,
      side: THREE.DoubleSide,
    });
    const signalRing = new THREE.Mesh(new THREE.RingGeometry(0.28, 0.34, 32), signalRingMat);
    signalRing.position.set(1.42, 1.05, 0);
    signalRing.rotation.y = Math.PI / 2;
    shipRoot.add(signalRing);

    // 7. Aft Propulsion Assembly & 3 Thruster Plumes (Engine Condition)
    addPartWithWire(
      new THREE.CylinderGeometry(0.54, 0.42, 0.65, 12),
      accentMat,
      [-1.55, 0, 0],
      [0, 0, -Math.PI / 2]
    );

    const plumeMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      transparent: true,
      opacity: 0.8,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const nozzleOffsets: Array<[number, number, number]> = [
      [-1.95, 0, 0],
      [-1.9, 0.28, 0.22],
      [-1.9, -0.28, -0.22],
    ];
    const plumes: THREE.Mesh[] = [];
    for (const [nx, ny, nz] of nozzleOffsets) {
      const isMain = ny === 0;
      const nozzle = new THREE.Mesh(
        new THREE.CylinderGeometry(isMain ? 0.16 : 0.1, isMain ? 0.24 : 0.15, 0.35, 12),
        accentMat
      );
      nozzle.position.set(nx, ny, nz);
      nozzle.rotation.z = -Math.PI / 2;
      shipRoot.add(nozzle);

      const plume = new THREE.Mesh(
        new THREE.ConeGeometry(isMain ? 0.2 : 0.12, isMain ? 1.15 : 0.75, 14),
        plumeMat
      );
      plume.position.set(nx - (isMain ? 0.72 : 0.52), ny, nz);
      plume.rotation.z = Math.PI / 2;
      shipRoot.add(plume);
      plumes.push(plume);
    }

    // 8. Magnetic Radiation Shield Dome (Solar Storm / Stabilized)
    const shieldMat = new THREE.MeshBasicMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.0,
    });
    const shieldDome = new THREE.Mesh(new THREE.SphereGeometry(2.65, 24, 16), shieldMat);
    shieldDome.scale.set(1.22, 0.72, 0.85);
    shipRoot.add(shieldDome);

    // 9. Telemetry Repair / Scan Wave Ring
    const scanRingMat = new THREE.MeshBasicMaterial({
      color: 0x34d399,
      transparent: true,
      opacity: 0.0,
      side: THREE.DoubleSide,
    });
    const scanRing = new THREE.Mesh(new THREE.RingGeometry(1.15, 1.32, 36), scanRingMat);
    scanRing.rotation.y = Math.PI / 2;
    shipRoot.add(scanRing);

    // ResizeObserver for crisp responsive viewport
    const resizeObserver = new ResizeObserver(() => {
      if (!container) return;
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w > 0 && h > 0) {
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
        renderer.setSize(w, h);
      }
    });
    resizeObserver.observe(container);

    // Animation loop
    let frameId = 0;
    const clock = new THREE.Clock();

    const animate = () => {
      frameId = window.requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();
      const s = shipRef.current;
      const sc = scenarioRef.current;
      const isHolo = hologramModeRef.current;

      // Smooth float & habitat rotation
      shipRoot.position.y = Math.sin(elapsed * 1.1) * 0.07;
      habGroup.rotation.x = elapsed * (s.oxygen >= 50 ? 0.45 : 0.15);
      reactorCore.rotation.y = elapsed * 0.9;
      reactorCore.rotation.x = elapsed * 0.6;

      // Toggle Hologram vs Solid Hull styling
      hullMat.opacity = isHolo ? 0.62 : 0.96;
      wireMat.opacity = isHolo ? 0.34 : 0.09;

      // Map live telemetry to subsystem colors
      const hullColor = metricColorHex(s.hull_integrity);
      wireMat.color.setHex(hullColor);

      const reactorColor = metricColorHex(s.energy);
      reactorMat.color.setHex(reactorColor);
      reactorMat.emissive.setHex(reactorColor);
      coreLight.color.setHex(reactorColor);
      const reactorPulse = 1.3 + Math.sin(elapsed * (s.energy < 50 ? 9 : 2.8)) * 0.45;
      reactorMat.emissiveIntensity = reactorPulse;

      const habMetric = Math.min(s.oxygen, s.crew_health);
      const habColor = metricColorHex(habMetric);
      habGlowMat.emissive.setHex(habColor);
      habGlowMat.emissiveIntensity =
        habMetric < 55 ? 0.65 + Math.abs(Math.sin(elapsed * 6.5)) * 0.9 : 0.55;

      const navColor = metricColorHex(s.navigation);
      navMat.emissive.setHex(navColor);

      const commsColor = metricColorHex(s.communication);
      commsMat.emissive.setHex(commsColor);

      // Engine plume dynamics
      const engColor = metricColorHex(s.engine_condition);
      plumeMat.color.setHex(engColor);
      const engScale = 0.45 + (s.engine_condition / 100) * 0.75;
      const flicker =
        s.engine_condition < 50
          ? 0.55 + Math.random() * 0.6
          : 0.92 + Math.sin(elapsed * 18) * 0.08;
      plumes.forEach((p, idx) => {
        const baseScale = idx === 0 ? 1.0 : 0.8;
        p.scale.set(1, engScale * flicker * baseScale, 1);
      });

      // Scenario-specific effects
      if (sc === 'solar_storm' || s.mission_status === 'Stabilized') {
        shieldDome.rotation.y = elapsed * 0.25;
        shieldMat.color.setHex(sc === 'solar_storm' && s.mission_status !== 'Stabilized' ? 0xf59e0b : 0x34d399);
        shieldMat.opacity = 0.08 + Math.abs(Math.sin(elapsed * 2.2)) * 0.09;
      } else {
        shieldMat.opacity = 0;
      }

      if (sc === 'unknown_signal' || s.communication < 65) {
        const wave = (elapsed * 0.9) % 1;
        signalRing.scale.setScalar(1 + wave * 3.0);
        signalRingMat.color.setHex(commsColor);
        signalRingMat.opacity = (1 - wave) * 0.7;
      } else {
        signalRingMat.opacity = 0;
      }

      // Active LangGraph node pulse on reactor ring
      reactorRing.rotation.z = elapsed * (activeNodesRef.current.length > 0 ? 2.4 : 0.4);

      // Repair / telemetry update scan wave
      if (scanPulseRef.current > 0) {
        scanPulseRef.current = Math.max(0, scanPulseRef.current - 0.018);
        const progress = 1 - scanPulseRef.current;
        scanRing.position.x = 2.6 - progress * 5.0;
        scanRingMat.opacity = Math.sin(progress * Math.PI) * 0.85;
      } else {
        scanRingMat.opacity = 0;
      }

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    return () => {
      window.cancelAnimationFrame(frameId);
      resizeObserver.disconnect();
      controls.dispose();
      renderer.dispose();
      if (renderer.domElement.parentNode === container) {
        container.removeChild(renderer.domElement);
      }
    };
  }, []);

  if (webglError) {
    return (
      <div className="rounded border border-slate-800 bg-[#070c17] p-3 text-center text-[11px] font-mono text-slate-400">
        {t('telemetry.viewer3d.webglUnavailable')}
      </div>
    );
  }

  return (
    <div
      className={`relative rounded border border-slate-800 bg-[radial-gradient(ellipse_at_center,_#0f213a_0%,_#060a14_78%)] overflow-hidden ${
        expanded ? 'w-full h-full' : 'w-full h-48'
      }`}
    >
      {/* Top HUD Overlay */}
      <div className="pointer-events-none absolute top-2 left-2.5 right-2.5 z-10 flex items-center justify-between text-[10px] font-mono">
        <div className="flex items-center gap-1.5">
          <span className="text-cyan-300 font-semibold">{t('telemetry.vessel')}</span>
          <span className="px-1.5 py-0.2 rounded bg-cyan-500/15 border border-cyan-500/30 text-cyan-200 text-[9px]">
            {t('telemetry.viewer3d.badge')}
          </span>
        </div>

        <div className="pointer-events-auto flex items-center gap-1">
          <button
            type="button"
            onClick={() => setHologramMode((v) => !v)}
            className="p-1 rounded bg-slate-900/80 border border-slate-700 hover:border-cyan-500/60 text-slate-300 hover:text-cyan-300 transition"
            title={hologramMode ? t('telemetry.viewer3d.solidMode') : t('telemetry.viewer3d.holoMode')}
          >
            {hologramMode ? <Sparkles className="w-3 h-3" /> : <Box className="w-3 h-3" />}
          </button>
          <button
            type="button"
            onClick={() => resetCamRef.current?.()}
            className="p-1 rounded bg-slate-900/80 border border-slate-700 hover:border-cyan-500/60 text-slate-300 hover:text-cyan-300 transition"
            title={t('telemetry.viewer3d.resetCamera')}
          >
            <RotateCw className="w-3 h-3" />
          </button>
          {onToggleExpand && (
            <button
              type="button"
              onClick={onToggleExpand}
              className="p-1 rounded bg-slate-900/80 border border-slate-700 hover:border-cyan-500/60 text-slate-300 hover:text-cyan-300 transition"
              title={expanded ? t('telemetry.viewer3d.collapse') : t('telemetry.viewer3d.expand')}
            >
              {expanded ? <Minimize2 className="w-3 h-3" /> : <Maximize2 className="w-3 h-3" />}
            </button>
          )}
        </div>
      </div>

      {/* Three.js WebGL Mount */}
      <div ref={mountRef} className="w-full h-full cursor-grab active:cursor-grabbing" />

      {/* Bottom Subtle Telemetry Callout Strip */}
      <div className="pointer-events-none absolute bottom-1.5 left-2.5 right-2.5 z-10 flex items-center justify-between text-[9px] font-mono text-slate-400">
        <span>{t('telemetry.viewer3d.dragHint')}</span>
        <div className="flex items-center gap-2">
          <span className={ship.engine_condition < 50 ? 'text-red-400' : 'text-cyan-300'}>
            {t('telemetry.svg.eng')} {ship.engine_condition}%
          </span>
          <span className={ship.energy < 50 ? 'text-amber-400' : 'text-cyan-300'}>
            {t('telemetry.svg.pwr')} {ship.energy}%
          </span>
          <span className={ship.oxygen < 55 ? 'text-red-400' : 'text-cyan-300'}>
            O2 {ship.oxygen}%
          </span>
        </div>
      </div>
    </div>
  );
}
