import { afterEach, expect, it } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { ExecutionNotice } from "./ExecutionNotice";
import { localReviewAssessment } from "@/fixtures/localReviewCase";

afterEach(cleanup);

it("identifies fallback and the failed model stage", () => {
  render(<ExecutionNotice execution={localReviewAssessment.execution} />);
  expect(screen.getByLabelText("Local review mode")).toBeTruthy();
  expect(screen.getByText(/failed during analysis/)).toBeTruthy();
  expect(screen.getByText(/explicit confirmations/)).toBeTruthy();
});
it("identifies exact source excerpts and forced offline selection", () => {
  render(<ExecutionNotice lookup execution={{ ...localReviewAssessment.execution!, reason: "forced_offline" }} />);
  expect(screen.getByText(/No language model is used/)).toBeTruthy();
  expect(screen.getByLabelText("Local source mode")).toBeTruthy();
});
it("does not invent a mode for historical or model results", () => {
  const { container, rerender } = render(<ExecutionNotice />);
  expect(container.textContent).toBe("");
  rerender(<ExecutionNotice execution={{ ...localReviewAssessment.execution!, mode: "llm", reason: "configured_model" }} />);
  expect(container.textContent).toBe("");
});
