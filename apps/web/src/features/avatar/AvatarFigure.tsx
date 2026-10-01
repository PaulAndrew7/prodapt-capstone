/*
  The companion: an anime girl drawn as flat vector parts in the product's own finish
  (ink outlines, flat fills, the mark only as a fill on her hair clips, bow, iris glow and
  the odd emote). An expression (expressions.ts) sets her face, hands, one manga emote and
  how she moves; one frame loop drives breathing, the head spring, gaze, blinks, the talking
  mouth and the emotes by writing SVG attributes directly. Pure SVG, so it needs no WebGL,
  idles offscreen and holds its expression still under reduced motion. The caption, not
  the figure, carries the information.
*/
import { useId, useRef, type ReactNode } from "react";
import { AnimatePresence, motion, useAnimationFrame, useInView, useReducedMotion } from "motion/react";
import { LOOKS, type Brows, type Emote, type Expression, type Eyes, type Hands, type Mouth } from "./expressions";

const OUT = "#1B1E2E";
const HAIR = "#2E3760";
const HAIR_HI = "#6B7DB8";
const SKIN = "#FFE9DE";
const SKIN_SH = "#F5CBBC";
const WHITE = "#FFFFFF";
const MARK = "#DDFF3C";
const MOUTH = "#9C3346";
const TONGUE = "#FF8C9C";
const WATER = "#BDE6FF";

/* Head pivot, where the chin meets the neck. */
const PX = 100;
const PY = 150;
/* Eye centre height, the axis the blink squashes towards. */
const EYE_Y = 114;
const EYE_SHAPE = "M68 110 C68 102 92 101 92 109 C92 121 87 127 80 127 C73 127 68 121 68 110 Z";

type Spring = { x: number; v: number };
const spring = (x = 0): Spring => ({ x, v: 0 });
/* Semi-implicit spring; the default is a little underdamped so poses land with a small bounce. */
function step(s: Spring, target: number, dt: number, k = 90, c = 12) {
  s.v += (k * (target - s.x) - c * s.v) * dt;
  s.x += s.v * dt;
}

const STAR = "M0 -8 C1 -2 2 -1 8 0 C2 1 1 2 0 8 C-1 2 -2 1 -8 0 C-2 -1 -1 -2 0 -8 Z";

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
      <path d={EYE_SHAPE} fill={WHITE} />
      <g clipPath={`url(#${clipId})`}>
        <g ref={gazeRef}>
          {/* A startled eye shrinks the iris towards its centre. */}
          <g transform={kind === "wide" ? "translate(80 115) scale(0.72) translate(-80 -115)" : undefined}>
            <ellipse cx={80} cy={115} rx={9.6} ry={12.2} fill={`url(#${irisId})`} stroke={OUT} strokeWidth={1.1} />
            <ellipse cx={80} cy={115.5} rx={4.25} ry={5.9} fill="#121A05" />
            {kind !== "wide" && <ellipse cx={80} cy={122.5} rx={5.5} ry={2.2} fill={MARK} opacity={0.75} />}
            {kind === "sparkle" ? (
              <>
                <path d={STAR} transform="translate(77 111) scale(0.66)" fill={WHITE} />
                <circle cx={85} cy={120.6} r={1.9} fill={WHITE} />
              </>
            ) : kind === "shine" ? (
              <>
                <circle cx={75.2} cy={109.6} r={5.2} fill={WHITE} />
                <circle cx={84.4} cy={120.2} r={2.7} fill={WHITE} />
                <circle cx={84.2} cy={109.4} r={1.5} fill={WHITE} />
              </>
            ) : (
              <>
                <circle cx={75.8} cy={109.5} r={3.9} fill={WHITE} />
                <circle cx={84.6} cy={120.8} r={1.8} fill={WHITE} />
              </>
            )}
          </g>
        </g>
        {/* Welling up: a wet line along the lower lid. */}
        {kind === "shine" && <path d="M66 121.5 Q80 128 94 121.5 L94 131 L66 131 Z" fill={WATER} opacity={0.75} />}
      </g>
      {/* A squint drops the upper lid over the top of the eye. */}
      {kind === "squint" && (
        <path d="M66 112 L66 106 C67.4 101 76 99.4 82 99.6 C88 99.8 93.4 101.6 94.6 105.2 L94.6 110.6 C90 108.6 71 108.6 66 112 Z" fill={SKIN} />
      )}
      <g fill="none" stroke={OUT} strokeLinecap="round">
        {kind === "squint" ? (
          <>
            <path d="M66 111.6 C72 108.4 88 108.4 94 110.8" strokeWidth={3.4} />
            <path d="M67.2 110.9 L61.8 108.6" strokeWidth={2} />
          </>
        ) : (
          <>
            <path d="M66.5 109.5 C68 102.5 76 100 82 100.3 C87.5 100.6 92 102.5 93.5 106.5" strokeWidth={3.4} />
            <path d="M67.8 106.8 C65.5 105.4 63.6 104.4 61.6 103.6" strokeWidth={2.2} />
            <path d="M68.4 110 L64 109" strokeWidth={1.6} />
          </>
        )}
        <path d="M75 127.6 Q80 129 85 127.6" strokeWidth={1.2} opacity={0.75} />
      </g>
    </g>
  );
}

function MouthShape({ kind }: { kind: Mouth }) {
  switch (kind) {
    case "open":
      return (
        <g stroke={OUT} strokeWidth={1.5} strokeLinejoin="round">
          <path d="M93.5 135 Q100 136 106.5 135 Q105.5 144.5 100 144.5 Q94.5 144.5 93.5 135 Z" fill={MOUTH} />
          <path d="M96.2 141.6 Q100 139.2 103.8 141.6 Q102.4 144.4 100 144.4 Q97.6 144.4 96.2 141.6 Z" fill={TONGUE} stroke="none" />
        </g>
      );
    case "grin":
      return (
        <g stroke={OUT} strokeWidth={1.5} strokeLinejoin="round">
          <path d="M91.5 134.2 Q100 136.6 108.5 134.2 Q107.2 146.6 100 146.6 Q92.8 146.6 91.5 134.2 Z" fill={MOUTH} />
          <path d="M92.4 135.2 Q100 137.4 107.6 135.2 L107.2 137.6 Q100 139.4 92.8 137.6 Z" fill={WHITE} stroke="none" />
          <path d="M95.6 143 Q100 140.2 104.4 143 Q102.8 146.4 100 146.4 Q97.2 146.4 95.6 143 Z" fill={TONGUE} stroke="none" />
        </g>
      );
    case "o":
      return <ellipse cx={100} cy={138.5} rx={2.7} ry={3.3} fill={MOUTH} stroke={OUT} strokeWidth={1.3} />;
    case "pout":
      return <path d="M96.5 138.6 Q100 137.2 103.5 138.6" fill="none" stroke={OUT} strokeWidth={1.6} strokeLinecap="round" />;
    case "smile":
      return <path d="M95 136 Q100 141 105 136" fill="none" stroke={OUT} strokeWidth={1.7} strokeLinecap="round" />;
    case "wavy":
      return (
        <path
          d="M93.5 138.4 Q95.4 135.8 97.2 138.4 Q99 141 100.8 138.4 Q102.6 135.8 104.4 138.4 Q105.4 139.8 106.5 139"
          fill="none"
          stroke={OUT}
          strokeWidth={1.6}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      );
    case "flat":
      return <path d="M95.5 138.4 L104.5 137.8" fill="none" stroke={OUT} strokeWidth={1.9} strokeLinecap="round" />;
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
  worried: "M71.5 97.8 Q79 96.4 86.8 92.6",
  determined: "M71 94 Q79 94.4 87.4 99.4",
};

/* ---------- Hands ---------- */

type Pt = [number, number];
const f1 = (n: number) => n.toFixed(1);

/* A sleeve from off-frame to the wrist, with the sailor cuff near its end. */
function Sleeve({ from, to, w = 16 }: { from: Pt; to: Pt; w?: number }) {
  const [x1, y1] = from;
  const [x2, y2] = to;
  const len = Math.hypot(x2 - x1, y2 - y1);
  const ux = (x2 - x1) / len;
  const uy = (y2 - y1) / len;
  const nx = -uy;
  const ny = ux;
  const a = (w * 1.2) / 2;
  const b = w / 2;
  const at = (back: number, half: number, side: 1 | -1) => `${f1(x2 - ux * back + nx * half * side)} ${f1(y2 - uy * back + ny * half * side)}`;
  const tube = `M${f1(x1 + nx * a)} ${f1(y1 + ny * a)} L${at(0, b, 1)} Q${f1(x2 + ux * b)} ${f1(y2 + uy * b)} ${at(0, b, -1)} L${f1(x1 - nx * a)} ${f1(y1 - ny * a)} Z`;
  const cuff = `M${at(12, b + 0.2, 1)} L${at(4, b, 1)} L${at(4, b, -1)} L${at(12, b + 0.2, -1)} Z`;
  return (
    <g stroke={OUT} strokeLinejoin="round">
      <path d={tube} fill={WHITE} strokeWidth={1.8} />
      <path d={cuff} fill={HAIR} strokeWidth={1.4} />
      <path d={`M${at(8, b - 1.2, 1)} L${at(8, b - 1.2, -1)}`} stroke={WHITE} strokeWidth={1.1} />
    </g>
  );
}

/* A fist in local coordinates: knuckles up (-y), wrist down. */
function Fist({ finger = false }: { finger?: boolean }) {
  return (
    <g stroke={OUT} strokeLinejoin="round" strokeLinecap="round">
      {finger && <path d="M-5.2 -6 L-5.2 -20.5 C-5.2 -24.6 0.2 -24.6 0.2 -20.5 L0.2 -6 Z" fill={SKIN} strokeWidth={1.6} />}
      <path d="M-8.6 0 C-9.2 -6.6 -5.4 -10 0 -10 C5.6 -10 9.2 -6.6 8.8 0 C8.4 6 5 9 0 9 C-5 9 -8.2 5.8 -8.6 0 Z" fill={SKIN} strokeWidth={1.7} />
      {!finger && <path d="M-4 -9.6 L-3.8 -5.8 M0.6 -10 L0.6 -5.8 M5 -9 L4.6 -5.6" fill="none" strokeWidth={1.1} />}
      {finger && <path d="M1.2 -9.8 L1.2 -5.8 M5.2 -8.8 L4.8 -5.6" fill="none" strokeWidth={1.1} />}
      <path d="M-8.4 -0.6 C-4.8 -2.8 0.2 -2.4 3.4 -0.4" fill="none" strokeWidth={1.3} />
    </g>
  );
}

/* A sleeve plus a fist at its end, the fist turned to follow the forearm. */
const HAND = 1.2;

function Arm({ from, to, finger, mirror, w = 18 }: { from: Pt; to: Pt; finger?: boolean; mirror?: boolean; w?: number }) {
  const len = Math.hypot(to[0] - from[0], to[1] - from[1]);
  const ux = (to[0] - from[0]) / len;
  const uy = (to[1] - from[1]) / len;
  const angle = (Math.atan2(ux, -uy) * 180) / Math.PI;
  const cx = to[0] + ux * 6.5 * HAND;
  const cy = to[1] + uy * 6.5 * HAND;
  return (
    <g>
      <Sleeve from={from} to={to} w={w} />
      <g transform={`translate(${f1(cx)} ${f1(cy)}) rotate(${f1(angle)}) scale(${mirror ? -HAND : HAND} ${HAND})`}>
        <Fist finger={finger} />
      </g>
    </g>
  );
}

function HandPose({ kind }: { kind: Hands }) {
  switch (kind) {
    case "fists":
      return (
        <>
          <Arm from={[34, 236]} to={[42, 154]} mirror />
          <Arm from={[166, 236]} to={[158, 154]} />
        </>
      );
    case "point":
      return <Arm from={[180, 236]} to={[166, 134]} finger />;
    case "chin":
      return <Arm from={[144, 236]} to={[119.5, 183]} finger />;
    case "pray":
      // Palms pressed together under the chin, fingertips up.
      return (
        <>
          <Sleeve from={[48, 236]} to={[92, 194]} w={18} />
          <Sleeve from={[152, 236]} to={[108, 194]} w={18} />
          <g stroke={OUT} strokeLinejoin="round" strokeLinecap="round" fill="none">
            <path
              d="M100 154 C93.8 157.2 90 165.4 90 175 C90 184.8 93.4 191.6 100 193 C106.6 191.6 110 184.8 110 175 C110 165.4 106.2 157.2 100 154 Z"
              fill={SKIN}
              strokeWidth={1.8}
            />
            <path d="M100 155.6 L100 191.8" strokeWidth={1.3} />
            <path d="M94.6 160.4 L95.7 166.6 M97.5 157.2 L98.1 164 M105.4 160.4 L104.3 166.6 M102.5 157.2 L101.9 164" strokeWidth={1.1} />
            <path d="M92.8 184 Q96.5 179.6 99 182.6 M107.2 184 Q103.5 179.6 101 182.6" strokeWidth={1.3} />
          </g>
        </>
      );
    case "magnifier":
      return (
        <>
          <Sleeve from={[172, 236]} to={[159, 164]} w={18} />
          <line x1={134.2} y1={123.6} x2={155} y2={151} stroke={OUT} strokeWidth={7.4} strokeLinecap="round" />
          <line x1={134.2} y1={123.6} x2={155} y2={151} stroke={HAIR} strokeWidth={4.2} strokeLinecap="round" />
          <circle cx={124} cy={110} r={16} fill={WATER} fillOpacity={0.34} stroke={OUT} strokeWidth={5} />
          <circle cx={124} cy={110} r={16} fill="none" stroke={HAIR_HI} strokeWidth={2.2} />
          <path d="M113.6 103.6 A12 12 0 0 1 119.4 98.2" fill="none" stroke={WHITE} strokeWidth={2.4} strokeLinecap="round" />
          <path d="M131.8 118.6 A12 12 0 0 1 128.6 121.6" fill="none" stroke={WHITE} strokeWidth={1.6} strokeLinecap="round" />
          <g transform={`translate(156.4 155.4) rotate(-12) scale(${HAND})`}>
            <Fist />
          </g>
        </>
      );
    case "paper":
      return (
        <>
          <Sleeve from={[40, 236]} to={[66, 190]} w={18} />
          <Sleeve from={[160, 236]} to={[134, 188]} w={18} />
          <g transform="rotate(-5 100 176)">
            <rect x={70} y={155} width={60} height={46} fill={WHITE} stroke={OUT} strokeWidth={2} />
            <rect x={76} y={167.4} width={40} height={5.6} fill={MARK} />
            <g stroke="#8B93A0" strokeWidth={1.8} strokeLinecap="round">
              <path d="M77 162 L118 162" />
              <path d="M77 170.2 L113 170.2" stroke={OUT} />
              <path d="M77 178.4 L121 178.4" />
              <path d="M77 186.6 L108 186.6" />
            </g>
          </g>
          <g transform={`translate(70.4 179) rotate(28) scale(${-HAND} ${HAND})`}>
            <Fist />
          </g>
          <g transform={`translate(130.4 175.6) rotate(-30) scale(${HAND})`}>
            <Fist />
          </g>
        </>
      );
    default:
      return null;
  }
}

/* ---------- Emotes ---------- */

function EmoteShape({ kind }: { kind: Emote }): ReactNode {
  switch (kind) {
    case "dots":
      return (
        <g fill="currentColor">
          {[0, 1, 2].map((i) => (
            <circle key={i} data-anim="dot" data-i={i} cx={150 + i * 10} cy={40} r={3.2} />
          ))}
        </g>
      );
    case "question":
      return (
        <text x={150} y={56} fontSize={34} fontWeight={700} fontFamily="'Clash Display', sans-serif" fill="currentColor" transform="rotate(12 158 44)">
          ?
        </text>
      );
    case "exclaim":
      return (
        <g data-anim="wobble">
          <path d="M153.6 20 L164 20 L160.8 45.6 L156.8 45.6 Z" fill="currentColor" />
          <circle cx={158.8} cy={52.4} r={3.6} fill="currentColor" />
          <path d="M146 24 L140.5 18.5 M171.5 24.5 L177.5 19.5 M173.5 37 L180.5 36" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" />
        </g>
      );
    case "sparkles":
      return (
        <g fill={MARK} stroke="currentColor" strokeWidth={1.4} strokeLinejoin="round">
          <path data-anim="twinkle" data-i={0} d={STAR} transform="translate(160 36) scale(1.15)" />
          <path data-anim="twinkle" data-i={1} d={STAR} transform="translate(176 62) scale(0.65)" />
          <path data-anim="twinkle" data-i={2} d={STAR} transform="translate(34 46) scale(0.8)" />
          <path data-anim="twinkle" data-i={3} d={STAR} transform="translate(22 78) scale(0.5)" />
        </g>
      );
    case "heart":
      return (
        <g fill="#FF7A93" stroke="currentColor" strokeWidth={1.4} strokeLinejoin="round">
          <path data-anim="beat" d="M160 58 C150 50 148 42 154 39 C158 37 160 40 160 42 C160 40 162 37 166 39 C172 42 170 50 160 58 Z" />
          <path d="M176 38 C171 34 170 30 173 28.5 C175 27.5 176 29 176 30 C176 29 177 27.5 179 28.5 C182 30 181 34 176 38 Z" />
        </g>
      );
    case "zz":
      return (
        <g fill="currentColor" fontFamily="'Clash Display', sans-serif" fontWeight={700}>
          <text x={148} y={58} fontSize={18}>
            z
          </text>
          <text x={162} y={42} fontSize={13}>
            z
          </text>
        </g>
      );
    case "sweat":
      return (
        <g data-anim="drip">
          <path d="M150 70 C150 70 142.6 80.6 142.6 85 C142.6 89.2 145.9 92.4 150 92.4 C154.1 92.4 157.4 89.2 157.4 85 C157.4 80.6 150 70 150 70 Z" fill={WATER} stroke={OUT} strokeWidth={1.6} strokeLinejoin="round" />
          <ellipse cx={147.4} cy={85.6} rx={1.6} ry={2.8} fill={WHITE} />
        </g>
      );
    case "thought":
      return (
        <g>
          <circle cx={140} cy={56} r={2.6} fill={WHITE} stroke={OUT} strokeWidth={1.4} />
          <circle cx={146} cy={47.6} r={3.8} fill={WHITE} stroke={OUT} strokeWidth={1.4} />
          <path
            d="M152 36 C146 36 144.6 27.4 151 26 C151 18.6 161 16 164.6 21.6 C168.4 15.4 179.2 17 180 24.8 C187.6 25 188.6 35 182 37.2 C183 43.8 173 46.6 169.6 41.8 C165.4 47.4 155.6 45.4 155.6 40.6 C153.4 40.4 152 38.6 152 36 Z"
            fill={WHITE}
            stroke={OUT}
            strokeWidth={1.6}
            strokeLinejoin="round"
          />
          <g fill={OUT}>
            {[0, 1, 2].map((i) => (
              <circle key={i} data-anim="dot" data-i={i} cx={158 + i * 8} cy={32} r={2.3} />
            ))}
          </g>
        </g>
      );
    case "bulb":
      return (
        <g>
          <g data-anim="rays" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round">
            <path d="M162 6 L162 0.5 M147.5 11.5 L143.6 7.6 M176.5 11.5 L180.4 7.6 M142 25 L136.5 25 M182 25 L187.5 25" />
          </g>
          <path
            d="M162 12 C154.6 12 150.4 17.6 150.4 23.4 C150.4 28 153.2 30.6 155.2 33.8 L168.8 33.8 C170.8 30.6 173.6 28 173.6 23.4 C173.6 17.6 169.4 12 162 12 Z"
            fill={MARK}
            stroke={OUT}
            strokeWidth={1.8}
            strokeLinejoin="round"
          />
          <path d="M157.4 25 L159.6 28.4 L162 24 L164.4 28.4 L166.6 25" fill="none" stroke={OUT} strokeWidth={1.2} strokeLinejoin="round" />
          <rect x={155.6} y={34} width={12.8} height={7} fill="#C9CED8" stroke={OUT} strokeWidth={1.5} />
          <path d="M155.8 37.4 L168.2 37.4" stroke={OUT} strokeWidth={1.1} />
        </g>
      );
    case "check":
      return (
        <g>
          <circle cx={165} cy={42} r={11.5} fill={MARK} stroke={OUT} strokeWidth={1.7} />
          <path d="M158.8 42.4 L163 46.6 L171 37.4" fill="none" stroke={OUT} strokeWidth={2.8} strokeLinecap="round" strokeLinejoin="round" />
        </g>
      );
    default:
      return null;
  }
}

export default function AvatarFigure({ expression, talking = false, dim = false }: { expression: Expression; talking?: boolean; dim?: boolean }) {
  const reduce = useReducedMotion();
  const svg = useRef<SVGSVGElement>(null);
  const inView = useInView(svg, { margin: "120px" });
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const clipId = `eye-${uid}`;
  const irisId = `iris-${uid}`;
  const frameId = `frame-${uid}`;

  const root = useRef<SVGGElement>(null);
  const heads = useRef<(SVGGElement | null)[]>([]);
  const features = useRef<SVGGElement>(null);
  const eyes = useRef<(SVGGElement | null)[]>([]);
  const gaze = useRef<(SVGGElement | null)[]>([]);
  const ahoge = useRef<SVGGElement>(null);
  const hands = useRef<SVGGElement>(null);
  const extras = useRef<SVGGElement>(null);
  const mouth = useRef<SVGGElement>(null);
  const talk = useRef<SVGEllipseElement>(null);

  const look = LOOKS[expression];
  const motionState = useRef({
    tilt: spring(),
    lean: spring(),
    turn: spring(),
    gx: spring(),
    gy: spring(),
    expression,
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
    if (s.expression !== expression) {
      s.expression = expression;
      s.since = t;
    }
    const local = t - s.since;
    const still = Boolean(reduce);

    let tilt = look.tilt;
    let lean = look.lean;
    let turn = look.turn;
    let gx = look.gx;
    let hop = 0;
    let shake = 0;
    if (!still) {
      switch (look.move) {
        case "sway":
          tilt += 1.4 * Math.sin(t * 0.7);
          break;
        case "bounce":
          lean += 4 * Math.sin(Math.min(local / 0.8, 1) * Math.PI * 2) * Math.exp(-local * 1.3);
          break;
        case "hop": {
          const ph = local % 2.2;
          if (ph < 0.9) hop = -6.5 * Math.abs(Math.sin((ph / 0.45) * Math.PI)) * (ph < 0.45 ? 1 : 0.55);
          tilt += 2 * Math.sin(t * 2.2);
          break;
        }
        case "tremble":
          shake = 0.6 * Math.sin(t * 43);
          tilt += 1.2 * Math.sin(t * 1.3);
          break;
        case "nod":
          lean += 2.6 * Math.pow(Math.max(0, Math.sin(local * 2.4)), 3);
          break;
        case "scan":
          gx += 3.4 * Math.sin(local * 1.6);
          turn += 1.6 * Math.sin(local * 1.6);
          tilt += 1.2 * Math.sin(local * 1.1);
          break;
      }
    }
    const targets = { tilt, lean, turn, gx, gy: look.gy };
    for (const key of ["tilt", "lean", "turn", "gx", "gy"] as const) {
      if (still) {
        s[key].x = targets[key];
        s[key].v = 0;
      } else if (key === "gx" || key === "gy") step(s[key], targets[key], dt, 160, 22);
      else step(s[key], targets[key], dt);
    }

    const breath = still ? 0 : Math.sin(t * 1.75) * 0.9;
    root.current?.setAttribute("transform", `translate(${shake.toFixed(2)} ${(breath + hop).toFixed(2)})`);
    const head = `translate(${(s.turn.x * 0.4).toFixed(2)} ${s.lean.x.toFixed(2)}) rotate(${s.tilt.x.toFixed(2)} ${PX} ${PY})`;
    heads.current.forEach((g) => g?.setAttribute("transform", head));
    features.current?.setAttribute("transform", `translate(${s.turn.x.toFixed(2)} 0)`);
    gaze.current[0]?.setAttribute("transform", `translate(${s.gx.x.toFixed(2)} ${s.gy.x.toFixed(2)})`);
    // The right eye is mirrored, so its horizontal gaze runs the other way.
    gaze.current[1]?.setAttribute("transform", `translate(${(-s.gx.x).toFixed(2)} ${s.gy.x.toFixed(2)})`);
    // Hands belong to the body but follow the head a little, so a hand at the chin stays there.
    hands.current?.setAttribute("transform", `translate(${(s.turn.x * 0.3).toFixed(2)} ${(s.lean.x * 0.6).toFixed(2)})`);

    let open = 1;
    if (!still && look.eyes !== "happy" && look.eyes !== "sleep") {
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

    // Talking flaps a small open mouth in place of the expression's own.
    const speaking = talking && !still;
    mouth.current?.setAttribute("opacity", speaking ? "0" : "1");
    if (talk.current) {
      talk.current.setAttribute("opacity", speaking ? "1" : "0");
      if (speaking) talk.current.setAttribute("ry", (0.9 + 2.9 * Math.abs(Math.sin(t * 11))).toFixed(2));
    }

    const quick = look.move === "hop" || look.move === "tremble" ? 3.4 : 2.2;
    ahoge.current?.setAttribute("transform", `rotate(${still ? 0 : (6 * Math.sin(t * quick)).toFixed(2)} 101 31)`);
    const ex = extras.current;
    if (ex) {
      ex.setAttribute("transform", `translate(${(s.turn.x * 0.4).toFixed(2)} ${(s.lean.x + (still ? 0 : 1.6 * Math.sin(t * 2.4))).toFixed(2)})`);
      ex.querySelectorAll<SVGElement>("[data-anim]").forEach((el) => {
        const i = Number(el.dataset.i ?? 0);
        switch (el.dataset.anim) {
          case "dot":
            el.setAttribute("opacity", still ? "1" : (0.25 + 0.75 * Math.max(0, Math.sin(t * 4 - i * 0.9))).toFixed(2));
            break;
          case "twinkle":
            el.setAttribute("opacity", still ? "1" : (0.35 + 0.65 * Math.abs(Math.sin(t * 2.6 + i * 1.3))).toFixed(2));
            break;
          case "rays":
            el.setAttribute("opacity", still ? "1" : (0.3 + 0.7 * Math.abs(Math.sin(t * 3))).toFixed(2));
            break;
          case "drip": {
            const p = still ? 0 : (t * 0.7) % 1;
            el.setAttribute("transform", `translate(0 ${(p * 7).toFixed(2)})`);
            el.setAttribute("opacity", (p > 0.8 ? 1 - (p - 0.8) * 5 : 1).toFixed(2));
            break;
          }
          case "wobble":
            el.setAttribute("transform", `rotate(${still ? 0 : (7 * Math.sin(t * 7)).toFixed(2)} 159 50)`);
            break;
          case "beat": {
            const k = still ? 1 : 1 + 0.1 * Math.max(0, Math.sin(t * 7));
            el.setAttribute("transform", `translate(160 48) scale(${k.toFixed(3)}) translate(-160 -48)`);
            break;
          }
        }
      });
    }
    s.painted = true;
  });

  const enter = reduce ? false : { opacity: 0, y: 6, scale: 0.8 };
  return (
    <svg ref={svg} viewBox="0 0 200 200" className="size-full overflow-visible" style={dim ? { filter: "grayscale(1)", opacity: 0.7 } : undefined} aria-hidden>
      <defs>
        <linearGradient id={irisId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#253A06" />
          <stop offset="0.55" stopColor="#5E8A0E" />
          <stop offset="1" stopColor="#C4F03A" />
        </linearGradient>
        <clipPath id={clipId}>
          <path d={EYE_SHAPE} />
        </clipPath>
        {/* The figure is a bust: nothing below the frame's bottom edge, emotes free above it. */}
        <clipPath id={frameId}>
          <rect x={-200} y={-200} width={600} height={400} />
        </clipPath>
      </defs>
      <g ref={root} clipPath={`url(#${frameId})`}>
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
                  <g ref={(el) => void (eyes.current[m > 0 ? 0 : 1] = el)}>
                    <Eye kind={look.eyes} clipId={clipId} irisId={irisId} gazeRef={(el) => void (gaze.current[m > 0 ? 0 : 1] = el)} />
                  </g>
                  <path d={BROWS[look.brows]} fill="none" stroke={OUT} strokeWidth={look.brows === "determined" ? 2.3 : 1.8} strokeLinecap="round" opacity={0.9} />
                </g>
              ))}
              <path d="M100.6 127 L99.6 129.6" stroke="#D38E7B" strokeWidth={1.3} strokeLinecap="round" />
              <g ref={mouth}>
                <MouthShape kind={look.mouth} />
              </g>
              <ellipse ref={talk} cx={100} cy={138.6} rx={3.6} ry={2} fill={MOUTH} stroke={OUT} strokeWidth={1.3} opacity={0} />
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

        {/* Hands come up into frame from below when a pose needs them. */}
        <g ref={hands} data-part="hands">
          <AnimatePresence>
            {look.hands !== "none" && (
              <motion.g
                key={look.hands}
                initial={reduce ? false : { opacity: 0, y: 28 }}
                animate={{ opacity: 1, y: 0 }}
                exit={reduce ? undefined : { opacity: 0, y: 28 }}
                transition={{ duration: 0.34, ease: [0.2, 0.8, 0.2, 1] }}
              >
                <HandPose kind={look.hands} />
              </motion.g>
            )}
          </AnimatePresence>
        </g>

        <g ref={extras} data-part="emote">
          <AnimatePresence>
            {look.emote !== "none" && (
              <motion.g
                key={look.emote}
                style={{ transformBox: "fill-box", transformOrigin: "50% 100%" }}
                initial={enter}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={reduce ? undefined : { opacity: 0, y: -6, scale: 0.9 }}
                transition={{ type: "spring", stiffness: 420, damping: 18 }}
              >
                <EmoteShape kind={look.emote} />
              </motion.g>
            )}
          </AnimatePresence>
        </g>
      </g>
    </svg>
  );
}
