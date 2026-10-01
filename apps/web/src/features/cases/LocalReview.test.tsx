import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { localReviewCase, localReviewQuestions } from "@/fixtures/localReviewCase";
import { ClarificationBlock } from "./Conversation";
import { PrintReport } from "./PrintReport";

vi.mock("@/lib/api", () => ({ api: { getClause: vi.fn(async () => undefined) } }));
afterEach(cleanup);

it("allows early local completion without forcing a confirmation", () => {
  const finish = vi.fn();
  const submit = vi.fn();
  render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <ClarificationBlock questions={localReviewQuestions} localReview onSubmit={submit} onFinishLocal={finish} submitting={false} onOpenClause={vi.fn()} />
  </QueryClientProvider>);
  expect(screen.getByRole("button", { name: "Save confirmations" }).hasAttribute("disabled")).toBe(true);
  fireEvent.click(screen.getByRole("button", { name: "Finish with remaining checks unknown" }));
  expect(finish).toHaveBeenCalledOnce();
  expect(submit).not.toHaveBeenCalled();
});
it("exports the local engine and missing semantic validation in print", () => {
  render(<PrintReport detail={localReviewCase} />);
  expect(screen.getByText("local review")).toBeTruthy();
  expect(screen.getByText("local-review-v1")).toBeTruthy();
  expect(screen.getByText(/No language model semantically validated this result/)).toBeTruthy();
});
