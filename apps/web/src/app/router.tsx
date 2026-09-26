import { createBrowserRouter, Outlet } from "react-router";
import { Providers } from "./providers";
import { AppShell } from "./AppShell";
import { NotFound } from "./NotFound";

function Root() {
  return (
    <Providers>
      <Outlet />
    </Providers>
  );
}

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
          {
            path: "policies/:policyId/versions/:versionId",
            lazy: async () => ({ Component: (await import("@/features/policies/PolicyDetail")).PolicyDetail }),
          },
          { path: "reviews", lazy: async () => ({ Component: (await import("@/features/review/ReviewQueue")).ReviewQueue }) },
          { path: "reports", lazy: async () => ({ Component: (await import("@/features/admin/AdminPages")).Reports }) },
          { path: "evaluation", lazy: async () => ({ Component: (await import("@/features/admin/AdminPages")).Evaluation }) },
          { path: "settings", lazy: async () => ({ Component: (await import("@/features/admin/AdminPages")).Settings }) },
          { path: "*", element: <NotFound inApp /> },
        ],
      },
      { path: "*", element: <NotFound /> },
    ],
  },
]);
