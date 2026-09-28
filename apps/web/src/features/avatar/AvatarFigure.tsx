/*
  The companion: a small anime girl drawn as flat vector parts in the product's own finish
  (ink outlines, flat fills, the mark only as a fill on her hair clips, bow and iris glow).
  Expressions swap per mode; one frame loop drives breathing, the head spring, gaze and
  blinks by writing SVG transforms directly. Pure SVG, so it needs no WebGL, idles offscreen
  and holds its expression still under reduced motion. The caption, not the figure, carries
  the information.
*/
import { useId, useRef } from "react";
import { AnimatePresence, motion, useAnimationFrame, useInView, useReducedMotion } from "motion/react";
import type { AvatarMode } from "./controller";

const OUT = "#1B1E2E";
const HAIR = "#2E3760";
const HAIR_HI = "#6B7DB8";
const SKIN = "#FFE9DE";
const SKIN_SH = "#F5CBBC";
const BLUSH = "#FF8FA6";
const WHITE = "#FFFFFF";
const MARK = "#DDFF3C";
const MOUTH = "#9C3346";
const TONGUE = "#FF8C9C";

type Pose = { tilt: number; lean: number; turn: number; gx: number; gy: number };
const POSE: Record<AvatarMode, Pose> = {
  resting: { tilt: 0, lean: 0, turn: 0, gx: 0, gy: 0 },
  attending: { tilt: 3, lean: 2.5, turn: 0, gx: -0.5, gy: 2.8 },
  acknowledging: { tilt: -2, lean: 0, turn: 0, gx: 0, gy: 0 },
  working: { tilt: 0, lean: 2, turn: 0, gx: 0, gy: 2 },
  waiting_for_user: { tilt: -10, lean: 0, turn: -1.5, gx: 1.5, gy: -2.5 },
  presenting: { tilt: 5, lean: -1, turn: 0, gx: 0, gy: 0 },
  evidence_focus: { tilt: 4, lean: 0.5, turn: 3, gx: 4, gy: 0.5 },
  unavailable: { tilt: -6, lean: 4, turn: 0, gx: 0, gy: 0 },
};

type Eyes = "open" | "happy" | "sleep";
type Mouth = "cat" | "smile" | "open" | "pout" | "o";
type Brows = "neutral" | "raised" | "focused";
type Extra = "none" | "dots" | "question" | "sparkles" | "heart" | "zz";
const FACE: Record<AvatarMode, { eyes: Eyes; mouth: Mouth; brows: Brows; extra: Extra }> = {
  resting: { eyes: "open", mouth: "cat", brows: "neutral", extra: "none" },
  attending: { eyes: "open", mouth: "smile", brows: "raised", extra: "none" },
  acknowledging: { eyes: "happy", mouth: "open", brows: "raised", extra: "heart" },
  working: { eyes: "open", mouth: "pout", brows: "focused", extra: "dots" },
  waiting_for_user: { eyes: "open", mouth: "o", brows: "raised", extra: "question" },
  presenting: { eyes: "open", mouth: "open", brows: "raised", extra: "sparkles" },
  evidence_focus: { eyes: "open", mouth: "smile", brows: "neutral", extra: "none" },
  unavailable: { eyes: "sleep", mouth: "pout", brows: "neutral", extra: "zz" },
};

/* Head pivot, where the chin meets the neck. */
const PX = 100;
const PY = 150;
/* Eye centre height, the axis the blink squashes towards. */
const EYE_Y = 114;

type Spring = { x: number; v: number };
const spring = (x = 0): Spring => ({ x, v: 0 });
/* Semi-implicit spring; the default is a little underdamped so poses land with a small bounce. */
function step(s: Spring, target: number, dt: number, k = 90, c = 12) {
  s.v += (k * (target - s.x) - c * s.v) * dt;
  s.x += s.v * dt;
}

/* The left eye in its own coordinates; the right eye is the same group mirrored about x = 100. */
function Eye({ kind, clipId, irisId, gazeRef }: { kind: Eyes; clipId: string; irisId: string; gazeRef: (el: SVGGElement | null) => void }) {
  if (kind === "happy") {
    return (
      <g fill="none" stroke={OUT} strokeLinecap="round">
        <path d="M68 118 Q80 103 92 118" strokeWidth={3.6} />
        <path d="M68.5 115 L63.5 112.5" strokeWidth={2} />
      </g>
    );
  }
  if (kind === "sleep") {
    return (
      <g fill="none" stroke={OUT} strokeLinecap="round">
        <path d="M68 113 Q80 122 92 113" strokeWidth={3.2} />
        <path d="M72 118.5 L70.5 121.5 M77 120.5 L76.5 123.5" strokeWidth={1.4} />
      </g>
    );
  }
  return (
    <g>
      <path d="M68 110 C68 102 92 101 92 109 C92 121 87 127 80 127 C73 127 68 121 68 110 Z" fill={WHITE} />
      <g clipPath={`url(#${clipId})`}>
        <g ref={gazeRef}>
          <ellipse cx={80} cy={115} rx={9.6} ry={12.2} fill={`url(#${irisId})`} stroke={OUT} strokeWidth={1.1} />
          <ellipse cx={80} cy={115.5} rx={4.6} ry={6.4} fill="#121A05" />
          <ellipse cx={80} cy={122.5} rx={5.5} ry={2.2} fill={MARK} opacity={0.75} />
          <circle cx={75.8} cy={109.5} r={3.9} fill={WHITE} />
          <circle cx={84.6} cy={120.8} r={1.8} fill={WHITE} />
        </g>
      </g>
      <g fill="none" stroke={OUT} strokeLinecap="round">
        <path d="M66.5 109.5 C68 102.5 76 100 82 100.3 C87.5 100.6 92 102.5 93.5 106.5" strokeWidth={3.4} />
        <path d="M67.8 106.8 C65.5 105.4 63.6 104.4 61.6 103.6" strokeWidth={2.2} />
        <path d="M68.4 110 L64 109" strokeWidth={1.6} />
        <path d="M75 127.6 Q80 129 85 127.6" strokeWidth={1.2} opacity={0.75} />
      </g>
    </g>
  );
}

function Mouth({ kind }: { kind: Mouth }) {
  switch (kind) {
    case "open":
      return (
        <g stroke={OUT} strokeWidth={1.5} strokeLinejoin="round">
          <path d="M93.5 135 Q100 136 106.5 135 Q105.5 144.5 100 144.5 Q94.5 144.5 93.5 135 Z" fill={MOUTH} />
          <path d="M96.2 141.6 Q100 139.2 103.8 141.6 Q102.4 144.4 100 144.4 Q97.6 144.4 96.2 141.6 Z" fill={TONGUE} stroke="none" />
        </g>
      );
    case "o":
      return <ellipse cx={100} cy={138.5} rx={2.7} ry={3.3} fill={MOUTH} stroke={OUT} strokeWidth={1.3} />;
    case "pout":
      return <path d="M96.5 138.6 Q100 137.2 103.5 138.6" fill="none" stroke={OUT} strokeWidth={1.6} strokeLinecap="round" />;
    case "smile":
      return <path d="M95 136 Q100 141 105 136" fill="none" stroke={OUT} strokeWidth={1.7} strokeLinecap="round" />;
    default:
      return (
        <path d="M94 136 Q97 139.6 100 136.6 Q103 139.6 106 136" fill="none" stroke={OUT} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round" />
      );
  }
}

const BROWS: Record<Brows, string> = {
  neutral: "M71.5 97 Q79 94.8 86.5 96.2",
  raised: "M71.5 95.2 Q79 92.2 86.5 94",
  focused: "M71.5 95.6 Q79 95 87 98.2",
};

const STAR = "M0 -8 C1 -2 2 -1 8 0 C2 1 1 2 0 8 C-1 2 -2 1 -8 0 C-2 -1 -1 -2 0 -8 Z";

function Extras({ kind, dotRefs }: { kind: Extra; dotRefs: (i: number) => (el: SVGCircleElement | null) => void }) {
  switch (kind) {
    case "dots":
      return (
        <g fill="currentColor">
          {[0, 1, 2].map((i) => (
            <circle key={i} ref={dotRefs(i)} cx={150 + i * 10} cy={40} r={3.2} />
          ))}
        </g>
      );
    case "question":
      return (
        <text x={150} y={56} fontSize={34} fontWeight={700} fontFamily="'Clash Display', sans-serif" fill="currentColor" transform="rotate(12 158 44)">
          ?
        </text>
      );
    case "sparkles":
      return (
        <g fill={MARK} stroke="currentColor" strokeWidth={1.4} strokeLinejoin="round">
          <path d={STAR} transform="translate(160 36) scale(1.15)" />
          <path d={STAR} transform="translate(176 62) scale(0.65)" />
          <path d={STAR} transform="translate(34 46) scale(0.8)" />
        </g>
      );
    case "heart":
      return (
        <path
          d="M160 58 C150 50 148 42 154 39 C158 37 160 40 160 42 C160 40 162 37 166 39 C172 42 170 50 160 58 Z"
          fill="#FF7A93"
          stroke="currentColor"
          strokeWidth={1.4}
          strokeLinejoin="round"
        />
      );
    case "zz":
      return (
        <g fill="currentColor" fontFamily="'Clash Display', sans-serif" fontWeight={700}>
          <text x={148} y={58} fontSize={18}>z</text>
          <text x={162} y={42} fontSize={13}>z</text>
        </g>
      );
    default:
      return null;
  }
}

export default function AvatarFigure({ mode }: { mode: AvatarMode }) {
  const reduce = useReducedMotion();
  const svg = useRef<SVGSVGElement>(null);
  const inView = useInView(svg, { margin: "120px" });
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const clipId = `eye-${uid}`;
  const irisId = `iris-${uid}`;

  const root = useRef<SVGGElement>(null);
  const heads = useRef<(SVGGElement | null)[]>([]);
  const features = useRef<SVGGElement>(null);
  const eyes = useRef<(SVGGElement | null)[]>([]);
  const gaze = useRef<(SVGGElement | null)[]>([]);
  const ahoge = useRef<SVGGElement>(null);
  const extras = useRef<SVGGElement>(null);
  const dots = useRef<(SVGCircleElement | null)[]>([]);

  const face = FACE[mode];
  const motionState = useRef({
    tilt: spring(),
    lean: spring(),
    turn: spring(),
    gx: spring(),
    gy: spring(),
    mode,
    since: 0,
    nextBlink: 1.8,
    blinkAt: -1,
    painted: false,
  });

  useAnimationFrame((ms, deltaMs) => {
    const s = motionState.current;
    if (!inView && s.painted) return;
    const t = ms / 1000;
    const dt = Math.min(deltaMs / 1000, 1 / 30);
    if (s.mode !== mode) {
      s.mode = mode;
      s.since = t;
    }
    const local = t - s.since;
    const p = POSE[mode];
    const still = Boolean(reduce);

    let tilt = p.tilt;
    let lean = p.lean;
    let gx = p.gx;
    if (!still) {
      if (mode === "acknowledging") lean += 4 * Math.sin(Math.min(local / 0.8, 1) * Math.PI * 2) * Math.exp(-local * 1.3);
      if (mode === "presenting") lean -= 3 * Math.abs(Math.sin(local * 5)) * Math.exp(-local * 1.4);
      if (mode === "working") {
        gx = 3.2 * Math.sin(local * 1.7);
        tilt += 1.5 * Math.sin(local * 1.1);
      }
      if (mode === "resting") tilt += 1.2 * Math.sin(t * 0.6);
    }
    const targets = { tilt, lean, turn: p.turn, gx, gy: p.gy };
    for (const key of ["tilt", "lean", "turn", "gx", "gy"] as const) {
      if (still) {
        s[key].x = targets[key];
        s[key].v = 0;
      } else if (key === "gx" || key === "gy") step(s[key], targets[key], dt, 160, 22);
      else step(s[key], targets[key], dt);
    }

    const breath = still ? 0 : Math.sin(t * 1.75) * 0.9;
    root.current?.setAttribute("transform", `translate(0 ${breath.toFixed(2)})`);
    const head = `translate(${(s.turn.x * 0.4).toFixed(2)} ${s.lean.x.toFixed(2)}) rotate(${s.tilt.x.toFixed(2)} ${PX} ${PY})`;
    heads.current.forEach((g) => g?.setAttribute("transform", head));
    features.current?.setAttribute("transform", `translate(${s.turn.x.toFixed(2)} 0)`);
    gaze.current[0]?.setAttribute("transform", `translate(${s.gx.x.toFixed(2)} ${s.gy.x.toFixed(2)})`);
    // The right eye is mirrored, so its horizontal gaze runs the other way.
    gaze.current[1]?.setAttribute("transform", `translate(${(-s.gx.x).toFixed(2)} ${s.gy.x.toFixed(2)})`);

    let open = 1;
    if (!still && face.eyes === "open") {
      if (t > s.nextBlink) {
        s.blinkAt = t;
        s.nextBlink = t + 2.4 + Math.random() * 3.2;
        if (Math.random() < 0.2) s.nextBlink = t + 0.28;
      }
      const b = (t - s.blinkAt) / 0.16;
      if (b >= 0 && b <= 1) open = 1 - 0.92 * Math.sin(b * Math.PI);
    }
    const blink = `translate(0 ${(EYE_Y * (1 - open)).toFixed(2)}) scale(1 ${open.toFixed(3)})`;
    eyes.current.forEach((g) => g?.setAttribute("transform", blink));

    ahoge.current?.setAttribute("transform", `rotate(${still ? 0 : (6 * Math.sin(t * 2.2)).toFixed(2)} 101 31)`);
    extras.current?.setAttribute("transform", `translate(0 ${still ? 0 : (1.6 * Math.sin(t * 2.4)).toFixed(2)})`);
    dots.current.forEach((d, i) => d?.setAttribute("opacity", still ? "1" : (0.25 + 0.75 * Math.max(0, Math.sin(t * 4 - i * 0.9))).toFixed(2)));
    s.painted = true;
  });

  return (
    <svg
      ref={svg}
      viewBox="0 0 200 200"
      className="size-full overflow-visible"
      style={mode === "unavailable" ? { filter: "grayscale(1)", opacity: 0.7 } : undefined}
      aria-hidden
    >
      <defs>
        <linearGradient id={irisId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#253A06" />
          <stop offset="0.55" stopColor="#5E8A0E" />
          <stop offset="1" stopColor="#C4F03A" />
        </linearGradient>
        <clipPath id={clipId}>
          <path d="M68 110 C68 102 92 101 92 109 C92 121 87 127 80 127 C73 127 68 121 68 110 Z" />
        </clipPath>
      </defs>
      <g ref={root}>
        {/* Hair behind the head and shoulders. */}
        <g ref={(el) => void (heads.current[0] = el)}>
          <path
            d="M100 27 C60 27 38 55 38 97 C38 129 35 158 29 184 C35 182 40 184 44 190 C48 184 53 182 59 184 C61 160 63 130 65 112 L135 112 C137 130 139 160 141 184 C147 182 152 184 156 190 C160 184 165 182 171 184 C165 158 162 129 162 97 C162 55 140 27 100 27 Z"
            fill={HAIR}
            stroke={OUT}
            strokeWidth={2}
            strokeLinejoin="round"
          />
        </g>

        {/* Neck, sailor top and the mark bow. */}
        <path d="M89 136 L89 173 C94 176 106 176 111 173 L111 136 Z" fill={SKIN} stroke={OUT} strokeWidth={1.8} />
        <path d="M89 143 C95 152 105 152 111 143 L111 151 C105 158 95 158 89 151 Z" fill={SKIN_SH} />
        <path d="M30 200 C32 186 46 176 76 171 L124 171 C154 176 168 186 170 200 Z" fill={WHITE} stroke={OUT} strokeWidth={2} strokeLinejoin="round" />
        {[1, -1].map((m) => (
          <g key={m} transform={m < 0 ? "translate(200 0) scale(-1 1)" : undefined}>
            <path d="M76 171 C84 170 88 171 90 172 L100 196 L92 200 L36 200 C40 186 55 176 76 171 Z" fill={HAIR} stroke={OUT} strokeWidth={1.8} strokeLinejoin="round" />
            <path d="M83 176.5 L96.5 197" stroke={WHITE} strokeWidth={1.6} strokeLinecap="round" />
          </g>
        ))}
        <g fill={MARK} stroke={OUT} strokeWidth={1.4} strokeLinejoin="round">
          <path d="M98 184 L94 196 L98.5 194 L100.5 185 Z" />
          <path d="M102 184 L106 196 L101.5 194 L99.5 185 Z" />
          <path d="M100 180 C94 173.5 85.5 173 84.5 178.5 C83.5 184.5 92 186 100 182 Z" />
          <path d="M100 180 C106 173.5 114.5 173 115.5 178.5 C116.5 184.5 108 186 100 182 Z" />
          <rect x={96.5} y={177} width={7} height={6.5} rx={2} />
        </g>

        <g ref={(el) => void (heads.current[1] = el)}>
          {/* Face */}
          <path d="M56 78 L56 104 C57 128 80 147 100 151 C120 147 143 128 144 104 L144 78 Z" fill={SKIN} stroke={OUT} strokeWidth={2} strokeLinejoin="round" />

          {/* Fringe, swept to her right, and the side locks that frame the face. */}
          <path
            d="M53 106 C46 60 68 30 100 30 C132 30 154 60 147 106 C144 97 142 89 141 81 C138 89 134 94 128 97 C126 90 123 84 119 78 C116 87 112 93 106 96 C105 89 103 83 99 77 C96 86 91 91 85 96 C84 89 82 84 79 79 C76 87 72 92 66 95 C65 91 64 87 64 83 C61 91 57 99 53 106 Z"
            fill={HAIR}
            stroke={OUT}
            strokeWidth={2}
            strokeLinejoin="round"
          />
          {[1, -1].map((m) => (
            <path
              key={m}
              transform={m < 0 ? "translate(200 0) scale(-1 1)" : undefined}
              d="M59 82 C51 104 49 134 54 164 C57 156 60 147 62 137 C63.5 125 64.5 109 66.5 96 Z"
              fill={HAIR}
              stroke={OUT}
              strokeWidth={1.8}
              strokeLinejoin="round"
            />
          ))}
          <path d="M63 64 C75 45 125 45 137 64 L133 61.5 L130 65 L125.5 57.5 L120 61 L114.5 54.5 L108 58 L101.5 53.5 L95 57.5 L89 54 L83.5 59.5 L78 56.5 L73.5 62.5 L68.5 59.5 Z" fill={HAIR_HI} opacity={0.85} />

          {/* Features sit low on the face, under a big fringe: the usual moe proportion. */}
          <g ref={features}>
            <g transform="translate(0 3)">
            {[1, -1].map((m) => (
              <g key={m} transform={m < 0 ? "translate(200 0) scale(-1 1)" : undefined}>
                <ellipse cx={71} cy={128} rx={7.5} ry={3.6} fill={BLUSH} opacity={0.45} />
                <path d="M67 129.5 L69 126.5 M70.5 129.5 L72.5 126.5 M74 129.5 L76 126.5" stroke="#F2708C" strokeWidth={1.1} strokeLinecap="round" opacity={0.8} />
                <g ref={(el) => void (eyes.current[m > 0 ? 0 : 1] = el)}>
                  <Eye kind={face.eyes} clipId={clipId} irisId={irisId} gazeRef={(el) => void (gaze.current[m > 0 ? 0 : 1] = el)} />
                </g>
                <path d={BROWS[face.brows]} fill="none" stroke={OUT} strokeWidth={1.8} strokeLinecap="round" opacity={0.9} />
              </g>
            ))}
            <path d="M100.6 127 L99.6 129.6" stroke="#D38E7B" strokeWidth={1.3} strokeLinecap="round" />
            <Mouth kind={face.mouth} />
            </g>
          </g>

          {/* Ahoge and a pair of mark hair clips. */}
          <g ref={ahoge}>
            <path d="M98 31 C94 20 99 11 110 9 C104 14 102 21 104 31 Z" fill={HAIR} stroke={OUT} strokeWidth={1.8} strokeLinejoin="round" />
          </g>
          <g transform="rotate(-32 131 71)" fill={MARK} stroke={OUT} strokeWidth={1.5}>
            <rect x={122} y={64} width={19} height={5.5} rx={2} />
            <rect x={122} y={72} width={19} height={5.5} rx={2} />
          </g>
        </g>

        <g ref={extras}>
          <AnimatePresence>
            {face.extra !== "none" && (
              <motion.g
                key={face.extra}
                initial={reduce ? false : { opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduce ? undefined : { opacity: 0, y: -4 }}
                transition={{ duration: 0.25, ease: [0.2, 0.8, 0.2, 1] }}
              >
                <Extras kind={face.extra} dotRefs={(i) => (el) => void (dots.current[i] = el)} />
              </motion.g>
            )}
          </AnimatePresence>
        </g>
      </g>
    </svg>
  );
}
