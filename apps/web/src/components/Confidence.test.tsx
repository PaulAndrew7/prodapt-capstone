import { afterEach, expect, it } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { Confidence } from "@/lib/api/types";
import { ConfidenceSummary } from "./Confidence";

afterEach(cleanup);

const confidence: Confidence = {
  score: 60,
  band: "medium",
  basis: "Decided by finding 1: Data-owner approval",
  factors: [
    { label: "Validation disputed it", points: 0, max_points: 40 },
    { label: "Quote found word for word in the clause", points: 20, max_points: 20 },
    { label: "Deciding facts were stated by the requester", points: 25, max_points: 25 },
    { label: "Search ranked the clause #1", points: 15, max_points: 15 },
  ],
};

it("shows the score with its band and reveals each factor on request", () => {
  render(<ConfidenceSummary confidence={confidence} subject="result" />);
  expect(screen.getByLabelText("Evidence score 60 of 100, Medium")).toBeTruthy();
  expect(screen.queryByText("Validation disputed it")).toBeNull();

  const toggle = screen.getByRole("button", { name: /How it was scored/ });
  fireEvent.click(toggle);
  expect(toggle.getAttribute("aria-expanded")).toBe("true");
  expect(screen.getByText("Decided by finding 1: Data-owner approval")).toBeTruthy();
  expect(screen.getByText("0/40")).toBeTruthy();
  expect(screen.getByText(/not a probability/)).toBeTruthy();
});
