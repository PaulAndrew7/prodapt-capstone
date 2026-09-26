/*
  The companion figure: a restrained geometric bust in the product's own flat material.
  Unlit sheet-white parts with an ink outline (inverted hull), ink eyes and one mark-filled
  collar, matching the paper, ink and highlighter world. No shading, no shadows.
  Procedural geometry, so there is no third-party asset to license. Renders on demand once
  settled; the text caption, not the figure, carries the information.
*/
import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { easing } from "maath";
import * as THREE from "three";
import type { AvatarMode } from "./controller";

const POSE: Record<AvatarMode, { pitch: number; yaw: number; roll: number; gx: number; gy: number }> = {
  resting: { pitch: 0, yaw: 0, roll: 0, gx: 0, gy: 0 },
  attending: { pitch: 0.24, yaw: -0.08, roll: 0, gx: -0.01, gy: -0.03 },
  acknowledging: { pitch: 0.05, yaw: 0, roll: 0, gx: 0, gy: 0 },
  working: { pitch: 0.16, yaw: 0, roll: 0, gx: 0, gy: -0.02 },
  waiting_for_user: { pitch: 0.06, yaw: -0.3, roll: -0.09, gx: -0.03, gy: 0 },
  presenting: { pitch: 0.02, yaw: 0.42, roll: 0.04, gx: 0.03, gy: 0 },
  evidence_focus: { pitch: 0.1, yaw: 0.6, roll: 0, gx: 0.035, gy: -0.01 },
  unavailable: { pitch: 0, yaw: 0, roll: 0, gx: 0, gy: 0 },
};

const SHEET = "#FBFCFB";
const INK = "#111413";
const MARK = "#DDFF3C";
const MUTED = "#8A938E";

/* One flat part with an ink outline drawn as a slightly larger back-facing hull. */
function Part({
  geometry,
  color,
  outline = 0.05,
  position,
  rotation,
}: {
  geometry: THREE.BufferGeometry;
  color: string;
  outline?: number;
  position?: [number, number, number];
  rotation?: [number, number, number];
}) {
  return (
    <group position={position} rotation={rotation}>
      <mesh geometry={geometry}>
        <meshBasicMaterial color={color} toneMapped={false} />
      </mesh>
      <mesh geometry={geometry} scale={1 + outline}>
        <meshBasicMaterial color={INK} side={THREE.BackSide} toneMapped={false} />
      </mesh>
    </group>
  );
}

function Bust({ mode }: { mode: AvatarMode }) {
  const head = useRef<THREE.Group>(null);
  const eyes = useRef<THREE.Group>(null);
  const since = useRef(0);
  const last = useRef<AvatarMode>(mode);
  const geo = useMemo(
    () => ({
      shoulders: new THREE.BoxGeometry(1.7, 0.62, 0.72),
      collar: new THREE.TorusGeometry(0.3, 0.07, 12, 40),
      neck: new THREE.CylinderGeometry(0.19, 0.22, 0.34, 24),
      head: new THREE.CapsuleGeometry(0.5, 0.36, 8, 24),
      eye: new THREE.CapsuleGeometry(0.05, 0.12, 4, 12),
    }),
    [],
  );
  useEffect(() => () => Object.values(geo).forEach((g) => g.dispose()), [geo]);

  useFrame((state, delta) => {
    const t = state.clock.elapsedTime;
    if (last.current !== mode) {
      last.current = mode;
      since.current = t;
    }
    const local = t - since.current;
    const p = POSE[mode];
    let pitch = p.pitch;
    let yaw = p.yaw;
    if (mode === "acknowledging") pitch += 0.2 * Math.sin(Math.min(local / 0.9, 1) * Math.PI * 2) * Math.exp(-local * 1.2);
    if (mode === "working") yaw += 0.16 * Math.sin(local * 1.1);
    if (head.current) easing.dampE(head.current.rotation, [pitch, yaw, p.roll], 0.22, delta);
    if (eyes.current) easing.damp3(eyes.current.position, [p.gx, p.gy, 0], 0.18, delta);
  });

  return (
    <group position={[0, -0.25, 0]}>
      <Part geometry={geo.shoulders} color={SHEET} outline={0.035} position={[0, -1.02, 0]} />
      <Part geometry={geo.collar} color={MARK} outline={0.12} position={[0, -0.68, 0]} rotation={[Math.PI / 2, 0, 0]} />
      <Part geometry={geo.neck} color={SHEET} outline={0.1} position={[0, -0.52, 0]} />
      <group ref={head} position={[0, -0.36, 0]}>
        <Part geometry={geo.head} color={SHEET} outline={0.045} position={[0, 0.62, 0]} />
        <group ref={eyes}>
          {[-0.18, 0.18].map((x) => (
            <mesh key={x} geometry={geo.eye} position={[x, 0.7, 0.47]}>
              <meshBasicMaterial color={mode === "unavailable" ? MUTED : INK} toneMapped={false} />
            </mesh>
          ))}
        </group>
      </group>
    </group>
  );
}

export default function AvatarFigure({ mode, onFailure }: { mode: AvatarMode; onFailure?: () => void }) {
  // Animate while a pose changes or work is live; afterwards render only on demand.
  const [live, setLive] = useState(true);
  useEffect(() => {
    setLive(true);
    if (mode === "working" || mode === "acknowledging") return;
    const t = window.setTimeout(() => setLive(false), 1600);
    return () => window.clearTimeout(t);
  }, [mode]);

  return (
    <Canvas
      dpr={[1, 1.5]}
      frameloop={live ? "always" : "demand"}
      camera={{ position: [0, 0.05, 4.2], fov: 30 }}
      gl={{ antialias: true, alpha: true, powerPreference: "low-power" }}
      onCreated={({ gl }) => {
        gl.domElement.addEventListener("webglcontextlost", () => onFailure?.(), { once: true });
      }}
      aria-hidden
    >
      <Bust mode={mode} />
    </Canvas>
  );
}
