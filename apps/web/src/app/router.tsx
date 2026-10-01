import { createBrowserRouter, Outlet } from "react-router";
import { Providers } from "./providers";
import { AppShell } from "./AppShell";
import { NotFound } from "./NotFound";
import { Prototype } from "./Prototype";
import { api } from "@/lib/api";

function Root() {
  return (
    <Providers>
      <Outlet />
    </Providers>
  );
}

/* Screens that only exist as fixture prototypes; the live app labels them instead (plan §12). */
const live = api.mode === "http";

/* Route-level code splitting: the front door and each app page load on demand. */
export const router = createBrowserRouter([
  {
    element: <Root />,
    errorElement: <NotFound />,
    children: [
      { path: "/", lazy: async () => ({ Component: (await import("@/features/front-door/FrontDoor")).FrontDoor }) },
      {
        path: "/app",
        element: <AppShell />,
        children: [
          { index: true, lazy: async () => ({ Component: (await import("@/features/overview/Overview")).Overview }) },
          { path: "cases", lazy: async () => ({ Component: (await import("@/features/cases/CaseIndex")).CaseIndex }) },
          { path: "cases/new", lazy: async () => ({ Component: (await import("@/features/cases/ScenarioComposer")).NewCase }) },
          { path: "cases/:caseId", lazy: async () => ({ Component: (await import("@/features/cases/CaseWorkspace")).CaseWorkspace }) },
          { path: "policies", lazy: async () => ({ Component: (await import("@/features/policies/PolicyLibrary")).PolicyLibrary }) },
          { path: "policies/manage", lazy: async () => ({ Component: (await import("@/features/policies/PolicyManagement")).PolicyManagement }) },
          { path: "policies/manage/:versionId", lazy: async () => ({ Component: (await import("@/features/policies/PolicyManagement")).DraftPolicyReview }) },
          { path: "ask", lazy: async () => ({ Component: (await import("@/features/policies/AskPage")).AskPage }) },
          {
            path: "policies/:policyId/versions/:versionId",
            lazy: async () => ({ Component: (await import("@/features/policies/PolicyDetail")).PolicyDetail }),
          },
          ...(live
            ? ["reviews", "reports", "evaluation", "settings"].map((path) => ({ path, element: <Prototype /> }))
            : [
                { path: "reviews", lazy: async () => ({ Component: (await import("@/features/review/ReviewQueue")).ReviewQueue }) },
                { path: "reports", lazy: async () => ({ Component: (await import("@/features/admin/AdminPages")).Reports }) },
                { path: "evaluation", lazy: async () => ({ Component: (await import("@/features/admin/AdminPages")).Evaluation }) },
                { path: "settings", lazy: async () => ({ Component: (await import("@/features/admin/AdminPages")).Settings }) },
              ]),
          { path: "*", element: <NotFound inApp /> },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
