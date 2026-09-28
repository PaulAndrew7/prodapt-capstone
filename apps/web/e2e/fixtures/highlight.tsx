import { useState } from "react";
import { createRoot } from "react-dom/client";
import { HighlightMark } from "../../src/components/HighlightMark";
import "../../src/index.css";

function HighlightFixture() {
  const [play, setPlay] = useState(false);
  return (
    <main style={{ padding: 24 }}>
      <button onClick={() => setPlay((value) => !value)}>Toggle highlight</button>
      <div style={{ transform: "translate3d(0, 0, 0)", opacity: 0.99, marginTop: 32 }}>
        <h1 className="font-display" style={{ fontSize: 48, lineHeight: 1.02, maxWidth: 600 }}>
          Your next move, <HighlightMark play={play} delay={0.3} duration={0.8}>backed by policy.</HighlightMark>
        </h1>
        <p style={{ maxWidth: 260, marginTop: 32 }}>
          <HighlightMark play={play} delay={0.3} duration={0.8}>
            External sharing of customer data requires written approval from the data owner before any transfer takes place.
          </HighlightMark>
        </p>
      </div>
      <span className="mark-span">Static policy version</span>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<HighlightFixture />);
