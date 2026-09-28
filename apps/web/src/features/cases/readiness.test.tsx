import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import type { ReactNode } from "react";
import { api } from "@/lib/api";
import type { Citation, LookupAnswer } from "@/lib/api/types";
import { policyVersions } from "@/fixtures/policies";
import { EvidenceDrawer } from "./EvidenceDrawer";
import { Composer } from "./Conversation";
import { ScenarioComposer } from "./ScenarioComposer";
import { LookupAnswerView, PolicyAsk } from "@/features/policies/PolicyAsk";

vi.mock("@/lib/api", () => ({ api: { mode: "http", getPolicyVersion: vi.fn(), lookup: vi.fn(), createCase: vi.fn() } }));

const version = policyVersions.ds_v1;
const clause = version.clauses[0];
const citation: Citation = { id: "citation", policy_version_id: version.id, clause_id: clause.id,
  section_path: clause.section_path, page_index: clause.page_index, quote: clause.text, source_url: "/source" };
const answer: LookupAnswer = { question: "Who approves?", answer: "Saved answer", citations: [citation], support: "validated", snapshot_id: "snapshot" };
const clients: QueryClient[] = [];

it("blocks oversized scenarios and revalidates edited text on Retry", async () => {
  vi.mocked(api.createCase).mockRejectedValue(new Error("Unavailable"));
  show(<ScenarioComposer />);
  const input = screen.getByRole("textbox", { name: "Scenario" });
  expect(input.getAttribute("maxlength")).toBe("4000");
  fireEvent.change(input, { target: { value: "x".repeat(4001) } });
  fireEvent.submit(input.closest("form")!);
  expect(api.createCase).not.toHaveBeenCalled();
  expect(screen.getByText(/Keep the scenario within/)).toBeTruthy();
  fireEvent.change(input, { target: { value: "A sufficiently detailed scenario for a policy assessment." } });
  fireEvent.submit(input.closest("form")!);
  await screen.findByRole("alert");
  fireEvent.change(input, { target: { value: "short" } });
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  expect(api.createCase).toHaveBeenCalledTimes(1);
});

it("requires a date before creating a case", () => {
  show(<ScenarioComposer />);
  const input = screen.getByRole("textbox", { name: "Scenario" });
  fireEvent.change(input, { target: { value: "A sufficiently detailed scenario for a policy assessment." } });
  fireEvent.change(screen.getByLabelText("Assess as of"), { target: { value: "" } });
  fireEvent.submit(input.closest("form")!);
  expect(api.createCase).not.toHaveBeenCalled();
  expect(screen.getByText("Choose a valid assessment date.")).toBeTruthy();
});

it("prevents duplicate case submissions and allows retry after failure", async () => {
  let reject!: (error: Error) => void;
  vi.mocked(api.createCase).mockImplementation(() => new Promise((_resolve, fail) => { reject = fail; }));
  show(<ScenarioComposer />);
  const input = screen.getByRole("textbox", { name: "Scenario" });
  fireEvent.change(input, { target: { value: "A sufficiently detailed scenario for a policy assessment." } });
  fireEvent.submit(input.closest("form")!);
  fireEvent.submit(input.closest("form")!);
  await waitFor(() => expect(api.createCase).toHaveBeenCalledTimes(1));
  await act(async () => { reject(new Error("Unavailable")); });
  await screen.findByRole("alert");
  expect((input as HTMLTextAreaElement).value).toContain("sufficiently detailed");
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(api.createCase).toHaveBeenCalledTimes(2));
  await act(async () => { reject(new Error("Unavailable")); });
});

function show(content: ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  clients.push(client);
  return render(<QueryClientProvider client={client}><MemoryRouter>{content}</MemoryRouter></QueryClientProvider>);
}

beforeEach(() => { vi.resetAllMocks(); });
afterEach(() => { cleanup(); clients.splice(0).forEach((client) => client.clear()); });

it("retries a failed evidence source without replacing the saved finding", async () => {
  vi.mocked(api.getPolicyVersion).mockRejectedValueOnce(new Error("Unavailable")).mockResolvedValue(version);
  show(<EvidenceDrawer title="Saved finding" citations={[citation]} focusCitationId={citation.id} onClose={() => {}} />);
  expect((await screen.findByRole("alert")).textContent).toContain("This evidence could not be loaded");
  expect(screen.getByRole("heading", { name: "Saved finding" })).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText(version.policy_title);
  expect(api.getPolicyVersion).toHaveBeenCalledTimes(2);
  expect(screen.queryByRole("alert")).toBeNull();
});

it("labels a missing evidence clause and preserves its saved quote", async () => {
  vi.mocked(api.getPolicyVersion).mockResolvedValue({ ...version, clauses: [] });
  show(<EvidenceDrawer title="Saved finding" citations={[citation]} focusCitationId={citation.id} onClose={() => {}} />);
  expect((await screen.findByRole("status")).textContent).toContain("This clause is missing");
  expect(screen.getByText(clause.text)).toBeTruthy();
  expect(screen.queryByText(/match the stored clause text exactly/)).toBeNull();
});

it("recovers failed lookup citation loading", async () => {
  vi.mocked(api.getPolicyVersion).mockRejectedValueOnce(new Error("Unavailable")).mockResolvedValue(version);
  show(<LookupAnswerView answer={answer} play={false} />);
  expect((await screen.findByRole("alert")).textContent).toContain("This citation could not be loaded");
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await screen.findByText(version.policy_title);
  expect(screen.getByText("Saved answer")).toBeTruthy();
  expect(screen.queryByRole("alert")).toBeNull();
});

it("explains missing lookup clauses instead of showing a permanent skeleton", async () => {
  vi.mocked(api.getPolicyVersion).mockResolvedValue({ ...version, clauses: [] });
  show(<LookupAnswerView answer={answer} play={false} />);
  expect((await screen.findByRole("status")).textContent).toContain("This clause is missing");
  expect(screen.getByRole("link", { name: "Open policy version" }).getAttribute("href")).toContain(version.id);
});

it("retries the submitted lookup question even after the input changes", async () => {
  vi.mocked(api.lookup).mockRejectedValue(new Error("Unavailable"));
  show(<PolicyAsk />);
  const input = screen.getByRole("textbox", { name: "Policy question" });
  expect(input.getAttribute("maxlength")).toBe("2000");
  fireEvent.change(input, { target: { value: "  Who approves?  " } });
  fireEvent.click(screen.getByRole("button", { name: "Ask" }));
  await screen.findByRole("alert");
  fireEvent.change(input, { target: { value: "A different question" } });
  fireEvent.click(screen.getByRole("button", { name: "Retry" }));
  await waitFor(() => expect(api.lookup).toHaveBeenCalledTimes(2));
  expect(vi.mocked(api.lookup).mock.calls.map(([q]) => q)).toEqual(["Who approves?", "Who approves?"]);
});

it("does not send oversized lookup input via programmatic submission", () => {
  show(<PolicyAsk />);
  const input = screen.getByRole("textbox", { name: "Policy question" });
  fireEvent.change(input, { target: { value: "x".repeat(2001) } });
  fireEvent.submit(input.closest("form")!);
  expect(api.lookup).not.toHaveBeenCalled();
});

it("blocks duplicate follow-ups until the first submission finishes", async () => {
  let finish!: () => void;
  const send = vi.fn(() => new Promise<void>((resolve) => { finish = resolve; }));
  show(<Composer disabled={false} sending={false} hint="Ready" onSend={send} />);
  const input = screen.getByRole("textbox");
  expect(input.getAttribute("maxlength")).toBe("4000");
  fireEvent.change(input, { target: { value: "New detail" } });
  fireEvent.submit(input.closest("form")!);
  fireEvent.submit(input.closest("form")!);
  expect(send).toHaveBeenCalledTimes(1);
  await act(async () => { finish(); });
  expect((input as HTMLTextAreaElement).value).toBe("");
});

it("retains a rejected follow-up and permits a retry", async () => {
  const send = vi.fn().mockRejectedValueOnce(new Error("Unavailable")).mockResolvedValue(undefined);
  show(<Composer disabled={false} sending={false} hint="Ready" onSend={send} />);
  const input = screen.getByRole("textbox");
  fireEvent.change(input, { target: { value: "Keep this detail" } });
  fireEvent.submit(input.closest("form")!);
  await screen.findByText(/Your text is still here/);
  expect((input as HTMLTextAreaElement).value).toBe("Keep this detail");
  fireEvent.submit(input.closest("form")!);
  await waitFor(() => expect((input as HTMLTextAreaElement).value).toBe(""));
  expect(send).toHaveBeenCalledTimes(2);
});

it("refuses disabled and oversized follow-up submissions", () => {
  const send = vi.fn();
  const view = show(<Composer disabled={true} sending={false} hint="Wait" onSend={send} />);
  let input = screen.getByRole("textbox");
  fireEvent.change(input, { target: { value: "A detail" } });
  fireEvent.submit(input.closest("form")!);
  expect(send).not.toHaveBeenCalled();
  view.unmount();
  show(<Composer disabled={false} sending={false} hint="Ready" onSend={send} />);
  input = screen.getByRole("textbox");
  fireEvent.change(input, { target: { value: "x".repeat(4001) } });
  fireEvent.submit(input.closest("form")!);
  expect(send).not.toHaveBeenCalled();
});
