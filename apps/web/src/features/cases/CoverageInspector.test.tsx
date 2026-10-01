import { afterEach, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { coverageGapAssessment, coverageGapCase } from "@/fixtures/coverageCase";
import { vendorAssessment } from "@/fixtures/vendorCase";
import { CoverageInspector } from "./CoverageInspector";
import { PrintReport } from "./PrintReport";

afterEach(cleanup);

it("shows an omitted requirement and its actual source independently of findings", () => {
  const open = vi.fn();
  render(<CoverageInspector assessment={coverageGapAssessment} onOpenEvidence={open} />);
  expect(screen.getByText("Review needed")).toBeTruthy();
  expect(screen.getByText(/A compliant result is withheld/)).toBeTruthy();
  fireEvent.click(screen.getByText("Inspect 2 retrieved candidates"));
  expect(screen.getByText("Unassessed")).toBeTruthy();
  fireEvent.click(screen.getByText("§4.5 · Retention period"));
  expect(screen.getByText(/Each external share must record a retention period/)).toBeTruthy();
  const source = screen.getByRole("link", { name: "Open original PDF for §4.5 Retention period · page 2" });
  expect(source.getAttribute("href")).toBe("/api/v1/policy-versions/ds_v2/source?page=2");
  fireEvent.click(screen.getByText("§4.2 · Data-owner approval"));
  fireEvent.click(screen.getByRole("button", { name: "Open finding evidence" }));
  expect(open).toHaveBeenCalledWith("finding_1", "cite_coverage_approval");
});

it("keeps missing coverage on legacy results distinct from complete coverage", () => {
  render(<CoverageInspector assessment={vendorAssessment} onOpenEvidence={vi.fn()} />);
  expect(screen.getByText(/Coverage was not recorded/)).toBeTruthy();
  expect(screen.queryByText("Retrieved candidates accounted for")).toBeNull();
});

it("does not describe a confirmed violation as withheld because of other gaps", () => {
  render(<CoverageInspector assessment={{ ...coverageGapAssessment, status: "non_compliant" }} onOpenEvidence={vi.fn()} />);
  expect(screen.getByText(/The established findings decide this result/)).toBeTruthy();
  expect(screen.queryByText(/A compliant result is withheld/)).toBeNull();
});

it("prints coverage candidates even when their disclosures were never opened", () => {
  render(<PrintReport detail={coverageGapCase} />);
  expect(screen.getByRole("heading", { name: /Retention period — unassessed/ })).toBeTruthy();
  expect(screen.getByText(/Retrieved candidates: 2. Accounted for: 1. Unresolved: 1/)).toBeTruthy();
  expect(screen.getAllByText(/Source: .*ds_v2\/source\?page=2/)).toHaveLength(3);
});

it("explains unconfirmed findings separately from omitted findings", () => {
  const coverage = coverageGapAssessment.coverage!;
  render(<CoverageInspector assessment={{
    ...coverageGapAssessment,
    coverage: { ...coverage, rows: coverage.rows.map((row) => row.state === "unassessed" ? {
      ...row, state: "unconfirmed", finding_ids: ["unconfirmed_finding"],
      note: "Validation did not confirm every finding for this candidate.",
    } : row) },
  }} onOpenEvidence={vi.fn()} />);
  fireEvent.click(screen.getByText("Inspect 2 retrieved candidates"));
  fireEvent.click(screen.getByText("§4.5 · Retention period"));
  expect(screen.getByText("Unconfirmed")).toBeTruthy();
  expect(screen.getByText(/Validation did not confirm every finding/)).toBeTruthy();
});
