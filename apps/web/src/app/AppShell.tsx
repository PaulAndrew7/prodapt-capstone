import { Link, NavLink, Outlet, useLocation } from "react-router";
import * as Dropdown from "@radix-ui/react-dropdown-menu";
import { CaretDown, List, Plus } from "@phosphor-icons/react";
import clsx from "clsx";
import { Wordmark } from "@/components/Wordmark";
import { ButtonLink } from "@/components/Button";
import { api } from "@/lib/api";

/* The live app has three areas (plan §12); fixture mode also shows the prototype screens. */
const primary = [
  { to: "/app/cases", label: "Cases" },
  { to: "/app/policies", label: "Policies" },
  { to: "/app/ask", label: "Ask a question" },
  ...(api.mode === "fixture" ? [{ to: "/app/reviews", label: "Reviews" }] : []),
];

const secondary =
  api.mode === "fixture"
    ? [
        { to: "/app/reports", label: "Reports" },
        { to: "/app/evaluation", label: "Evaluation" },
        { to: "/app/settings", label: "Settings" },
      ]
    : [];

function NavItem({ to, label, forceActive }: { to: string; label: string; forceActive?: boolean }) {
  return (
    <NavLink
      to={to}
      className={({ isActive }) =>
        clsx(
          "relative flex h-16 items-center px-3 font-semibold transition-colors",
          isActive || forceActive ? "text-ink" : "text-ink-2 hover:text-ink",
        )
      }
    >
      {({ isActive }) => (
        <>
          {label}
          {(isActive || forceActive) && <span aria-hidden className="absolute inset-x-3 bottom-0 h-1 bg-mark" />}
        </>
      )}
    </NavLink>
  );
}

const menuItem =
  "flex h-10 cursor-pointer items-center px-4 font-medium outline-none data-[highlighted]:bg-mark data-[highlighted]:text-on-mark";

export function AppHeader({ sticky = true, activePath }: { sticky?: boolean; activePath?: string }) {
  const { pathname } = useLocation();
  return (
  <header className={clsx("z-10 border-b-2 border-ink bg-paper", sticky && "sticky top-0")}>
    <div className="mx-auto flex h-16 max-w-[1600px] items-center gap-2 px-4 md:px-8">
      <Link to="/" className="mr-4 shrink-0" aria-label="Paul.ez home">
        <Wordmark />
      </Link>

      <nav aria-label="Primary" className="hidden items-center lg:flex">
        {primary.map((n) => (
          <NavItem key={n.to} {...n} forceActive={activePath === n.to} />
        ))}
        {secondary.length > 0 && (
          <Dropdown.Root>
            <Dropdown.Trigger className="flex h-16 items-center gap-1 px-3 font-semibold text-ink-2 outline-none hover:text-ink data-[state=open]:text-ink">
              More <CaretDown size={14} aria-hidden />
            </Dropdown.Trigger>
            <Dropdown.Portal>
              <Dropdown.Content
                align="start"
                sideOffset={0}
                className="z-30 min-w-48 border-2 border-ink bg-sheet py-1"
              >
                {secondary.map((n) => (
                  <Dropdown.Item key={n.to} asChild className={menuItem}>
                    <Link to={n.to}>{n.label}</Link>
                  </Dropdown.Item>
                ))}
              </Dropdown.Content>
            </Dropdown.Portal>
          </Dropdown.Root>
        )}
      </nav>

      <div className="ml-auto flex items-center gap-3">
        <span className="hidden border border-ink/30 px-2 py-1 text-xs font-semibold text-ink-2 xl:inline">
          Demo corpus: fictional policies
        </span>
        {api.mode === "fixture" && (
          <span className="hidden border border-dashed border-ink/40 px-2 py-1 text-xs font-semibold text-ink-2 md:inline">
            Fixture data
          </span>
        )}
        {pathname !== "/app/cases/new" && (
          <ButtonLink to="/app/cases/new" size="sm" icon={<Plus size={16} aria-hidden />}>
            New case
          </ButtonLink>
        )}
        <Dropdown.Root>
          <Dropdown.Trigger
            className="flex size-10 items-center justify-center border-2 border-ink lg:hidden"
            aria-label="Menu"
          >
            <List aria-hidden />
          </Dropdown.Trigger>
          <Dropdown.Portal>
            <Dropdown.Content align="end" sideOffset={8} className="z-30 min-w-56 border-2 border-ink bg-sheet py-1">
              {[...primary, ...secondary].map((n) => (
                <Dropdown.Item key={n.to} asChild className={menuItem}>
                  <Link to={n.to}>{n.label}</Link>
                </Dropdown.Item>
              ))}
              <p className="border-t border-rule px-4 pt-2 pb-1 text-xs text-ink-2">
                Demo corpus: fictional policies
              </p>
            </Dropdown.Content>
          </Dropdown.Portal>
        </Dropdown.Root>
      </div>
    </div>
  </header>
  );
}

export function AppShell() {
  return (
    <div className="min-h-dvh bg-paper">
      <a
        href="#main"
        className="sr-only z-50 bg-mark px-4 py-2 font-semibold text-on-mark focus:not-sr-only focus:fixed focus:left-4 focus:top-4"
      >
        Skip to content
      </a>
      <AppHeader />
      <main id="main" tabIndex={-1} className="outline-none">
        <Outlet />
      </main>
    </div>
  );
}
