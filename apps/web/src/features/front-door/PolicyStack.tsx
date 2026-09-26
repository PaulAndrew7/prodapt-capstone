/*
  Hero 3D: a loose stack of real (fictional-corpus) policy pages. Scrolling the hero
  brings the page holding clause 4.2 forward and sweeps a highlighter across it,
  dramatizing retrieval: many policies narrow to one clause.
  Isolated canvas leaf; it only reads a scroll MotionValue, Motion never animates inside it.
*/
import { useEffect, useMemo, useRef, useState } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import type { MotionValue } from "motion/react";
import * as THREE from "three";
import { easing } from "maath";
import { policyVersions } from "@/fixtures/policies";
import { vendorCitations } from "@/fixtures/vendorCase";
import type { Clause } from "@/lib/api/types";

const PAPER = "#FBFCFB";
const INK = "#111413";
const INK2 = "#4A524E";
const MARK = "#DDFF3C";

const BASE_W = 1024;
const BASE_H = 1325;
const SHEET_W = 1.9;
const SHEET_H = SHEET_W * (BASE_H / BASE_W);

type Page = { title: string; label: string; page: number; clauses: Clause[]; target: boolean };
type LineRect = { x: number; y: number; w: number; h: number };

function corpusPages(): Page[] {
  const order = ["ds_v1", "vd_v1", "ac_v1", "ds_v2", "rd_v1", "md_v1"];
  const pages: Page[] = [];
  for (const id of order) {
    const v = policyVersions[id];
    const byPage = new Map<number, Clause[]>();
    v.clauses.forEach((c) => byPage.set(c.page_index, [...(byPage.get(c.page_index) ?? []), c]));
    for (const [page, clauses] of byPage) {
      pages.push({
        title: v.policy_title,
        label: v.label,
        page: page + 1,
        clauses,
        target: id === "ds_v1" && clauses.some((c) => c.section_path.includes("4.2")),
      });
    }
  }
  const target = pages.find((p) => p.target)!;
  const rest = pages.filter((p) => !p.target).slice(0, 8);
  rest.splice(4, 0, target);
  return rest;
}

function wrap(ctx: CanvasRenderingContext2D, text: string, width: number) {
  const words = text.split(" ");
  const lines: string[] = [];
  let line = "";
  for (const w of words) {
    const next = line ? `${line} ${w}` : w;
    if (ctx.measureText(next).width > width && line) {
      lines.push(line);
      line = w;
    } else line = next;
  }
  if (line) lines.push(line);
  return lines;
}

/* Draws one page; returns the texture and, for the target page, the line boxes of clause 4.2. */
function drawPage(p: Page, scale: number) {
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(BASE_W * scale);
  canvas.height = Math.round(BASE_H * scale);
  const ctx = canvas.getContext("2d")!;
  ctx.scale(scale, scale);
  ctx.fillStyle = PAPER;
  ctx.fillRect(0, 0, BASE_W, BASE_H);
  const m = 84;
  ctx.fillStyle = INK;
  ctx.textBaseline = "alphabetic";
  ctx.font = "600 27px Switzer";
  ctx.fillText(p.title, m, m + 20);
  ctx.fillStyle = INK2;
  ctx.font = "500 22px Switzer";
  const meta = `${p.label}   Page ${p.page}`;
  ctx.fillText(meta, BASE_W - m - ctx.measureText(meta).width, m + 20);
  ctx.fillStyle = INK;
  ctx.fillRect(m, m + 44, BASE_W - 2 * m, 4);

  let y = m + 130;
  const textX = m + 150;
  const textW = BASE_W - textX - m;
  const lineH = 40;
  const rects: LineRect[] = [];
  for (const c of p.clauses) {
    ctx.fillStyle = INK;
    ctx.font = "700 64px 'Clash Display'";
    ctx.fillText(c.section_path[c.section_path.length - 1], m, y + 20);
    ctx.font = "600 29px Switzer";
    ctx.fillText(c.heading, textX, y);
    y += 50;
    ctx.font = "400 27px Switzer";
    const lines = wrap(ctx, c.text, textW);
    const qStart = p.target && c.section_path.includes("4.2") ? c.text.indexOf(CITED) : -1;
    const qEnd = qStart + CITED.length;
    let offset = 0;
    for (const l of lines) {
      ctx.fillStyle = INK;
      ctx.fillText(l, textX, y);
      if (qStart >= 0) {
        // Intersect this wrapped line with the cited character range; wrap() joins words with single spaces.
        const from = Math.max(offset, qStart);
        const to = Math.min(offset + l.length, qEnd);
        if (to > from) {
          const x0 = ctx.measureText(l.slice(0, from - offset)).width;
          const w = ctx.measureText(l.slice(from - offset, to - offset)).width;
          rects.push({ x: textX + x0 - 4, y: y - 30, w: w + 8, h: 40 });
        }
      }
      offset += l.length + 1;
      y += lineH;
    }
    y += 54;
  }
  ctx.fillStyle = INK2;
  ctx.font = "500 20px Switzer";
  ctx.fillText(`Kestrel Mutual (fictional demo policy)`, m, BASE_H - m);

  const tex = new THREE.CanvasTexture(canvas);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.anisotropy = 4;
  return { tex, rects };
}

/* The exact words finding 1 cites. The hero marks these and nothing else, same as the evidence drawer. */
const CITED = vendorCitations.find((c) => c.id === "cite_1")!.quote;

const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
const smooth = (v: number) => v * v * (3 - 2 * v);

function Sheet({
  page,
  index,
  targetIndex,
  progress,
}: {
  page: Page;
  index: number;
  targetIndex: number;
  progress: MotionValue<number>;
}) {
  const group = useRef<THREE.Group>(null);
  const marks = useRef<(THREE.Mesh | null)[]>([]);
  const { tex, rects } = useMemo(() => drawPage(page, page.target ? 1 : 0.5), [page]);
  useEffect(() => () => tex.dispose(), [tex]);

  const offset = index - targetIndex;
  const rest = useMemo(
    () => ({
      pos: new THREE.Vector3(2.75 + offset * 0.16, 0.05 - offset * 0.08, -Math.abs(offset) * 0.45 - (offset > 0 ? 0.12 : 0)),
      rot: new THREE.Euler(-0.16, -0.58 + offset * 0.03, 0.09 - offset * 0.02),
    }),
    [offset],
  );

  useFrame((state, delta) => {
    const g = group.current;
    if (!g) return;
    const p = progress.get();
    const t = state.clock.elapsedTime;
    const drift = Math.sin(t * 0.5 + index * 0.9) * 0.025;
    if (page.target) {
      const k = smooth(clamp01((p - 0.16) / 0.4));
      easing.damp3(g.position, [rest.pos.x * (1 - k), rest.pos.y * (1 - k) + drift * (1 - k), rest.pos.z * (1 - k) + 1.75 * k], 0.12, delta);
      easing.dampE(g.rotation, [rest.rot.x * (1 - k), rest.rot.y * (1 - k), rest.rot.z * (1 - k)], 0.14, delta);
      marks.current.forEach((m, i) => {
        if (!m) return;
        const s = smooth(clamp01((p - 0.6 - i * 0.07) / 0.12));
        m.scale.x = Math.max(0.0001, s);
        m.visible = s > 0.001;
      });
    } else {
      const spread = smooth(clamp01((p - 0.14) / 0.45));
      easing.damp3(
        g.position,
        [rest.pos.x + offset * 0.75 * spread, rest.pos.y + drift - Math.sign(offset) * 0.45 * spread, rest.pos.z - 2.2 * spread],
        0.15,
        delta,
      );
      easing.dampE(g.rotation, [rest.rot.x, rest.rot.y - 0.25 * spread * Math.sign(offset || 1), rest.rot.z], 0.18, delta);
    }
  });

  const px = (x: number) => (x / BASE_W) * SHEET_W - SHEET_W / 2;
  const py = (y: number) => SHEET_H / 2 - (y / BASE_H) * SHEET_H;

  return (
    <group ref={group} position={rest.pos} rotation={rest.rot}>
      <mesh position={[0, 0, -0.004]}>
        <planeGeometry args={[SHEET_W + 0.016, SHEET_H + 0.016]} />
        <meshBasicMaterial color={INK} side={THREE.DoubleSide} />
      </mesh>
      <mesh>
        <planeGeometry args={[SHEET_W, SHEET_H]} />
        <meshBasicMaterial map={tex} color={page.target ? "#FFFFFF" : "#EEF1EF"} side={THREE.DoubleSide} toneMapped={false} />
      </mesh>
      {rects.map((r, i) => (
        <MarkLine
          key={i}
          rect={r}
          x={px(r.x)}
          y={py(r.y + r.h / 2)}
          meshRef={(el) => {
            marks.current[i] = el;
          }}
        />
      ))}
    </group>
  );
}

/* One highlighter stroke over a text line, anchored at its left edge so scale.x sweeps rightwards. */
function MarkLine({
  rect,
  x,
  y,
  meshRef,
}: {
  rect: LineRect;
  x: number;
  y: number;
  meshRef: (el: THREE.Mesh | null) => void;
}) {
  const geometry = useMemo(() => {
    const w = (rect.w / BASE_W) * SHEET_W;
    const h = (rect.h / BASE_H) * SHEET_H;
    const g = new THREE.PlaneGeometry(w, h);
    g.translate(w / 2, 0, 0);
    return g;
  }, [rect]);
  useEffect(() => () => geometry.dispose(), [geometry]);
  return (
    <mesh ref={meshRef} geometry={geometry} position={[x, y, 0.002]} scale={[0.0001, 1, 1]} visible={false}>
      <meshBasicMaterial color={MARK} blending={THREE.MultiplyBlending} premultipliedAlpha transparent depthWrite={false} toneMapped={false} />
    </mesh>
  );
}

function Rig({ children }: { children: React.ReactNode }) {
  const g = useRef<THREE.Group>(null);
  const { pointer } = useThree();
  useFrame((_, delta) => {
    if (!g.current) return;
    easing.dampE(g.current.rotation, [pointer.y * 0.06, pointer.x * 0.1, 0], 0.4, delta);
  });
  return <group ref={g}>{children}</group>;
}

export default function PolicyStack({ progress, active }: { progress: MotionValue<number>; active: boolean }) {
  const [ready, setReady] = useState(false);
  const pages = useMemo(() => (ready ? corpusPages() : []), [ready]);
  const targetIndex = pages.findIndex((p) => p.target);

  useEffect(() => {
    let alive = true;
    Promise.all([
      document.fonts.load("700 64px 'Clash Display'"),
      document.fonts.load("400 27px Switzer"),
      document.fonts.load("600 27px Switzer"),
    ]).finally(() => alive && setReady(true));
    return () => {
      alive = false;
    };
  }, []);

  return (
    <Canvas
      dpr={[1, 1.5]}
      frameloop={active ? "always" : "never"}
      camera={{ position: [0, 0, 7], fov: 30 }}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      aria-hidden
    >
      <Rig>
        {pages.map((p, i) => (
          <Sheet key={`${p.title}-${p.label}-${p.page}`} page={p} index={i} targetIndex={targetIndex} progress={progress} />
        ))}
      </Rig>
    </Canvas>
  );
}
