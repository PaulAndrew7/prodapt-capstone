import { createRoot } from "react-dom/client";
import AvatarFigure from "../../src/features/avatar/AvatarFigure";
import { LOOKS, type Expression } from "../../src/features/avatar/expressions";
import "../../src/index.css";

/* Every expression side by side, for the avatar e2e check and visual review. */
function AvatarSheet() {
  const talking = new URLSearchParams(location.search).has("talking");
  return (
    <main className="grid grid-cols-4 gap-x-6 gap-y-10 bg-paper p-10 text-ink">
      {(Object.keys(LOOKS) as Expression[]).map((e) => (
        <figure key={e} data-expression={e} className="border-2 border-ink bg-sheet">
          <div className="mx-auto size-[260px]">
            <AvatarFigure expression={e} talking={talking} />
          </div>
          <figcaption className="border-t-2 border-ink px-3 py-2 font-semibold">{e}</figcaption>
        </figure>
      ))}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<AvatarSheet />);
