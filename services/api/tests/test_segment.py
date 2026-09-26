from app.domain.contracts import ClauseKind
from app.ingestion.pdf import PageText
from app.ingestion.segment import classify, merge_spans, segment

FOOTER = "Acme Policy v1\nPage {n} of 3"


def pages(*bodies: str) -> list[PageText]:
    return [
        PageText(i, None, f"ACME INTERNAL\n{body}\n{FOOTER.format(n=i + 1)}")
        for i, body in enumerate(bodies)
    ]


def test_headers_footers_and_cover_are_not_clause_text() -> None:
    seg = segment(
        pages(
            "Acme Policy\nVersion 1 · Owner: Someone",
            "1 Purpose\nThis policy exists.\n2 Rules\n2.1 Approval\nChanges require approval.",
            "2.2 Records\nKeep a record.",
        )
    )
    assert [c.key for c in seg.clauses] == ["1", "2.1", "2.2"]
    assert seg.clauses[0].text == "This policy exists."
    assert seg.clauses[2].text == "Keep a record."
    assert "page # of #" in seg.running_lines


def test_wrapped_lines_starting_with_numbers_are_not_headings() -> None:
    seg = segment(
        pages(
            "cover",
            "1 Access\n1.1 Temporary access\nTemporary access expires after\n14 days.\n"
            "1.2 Vendors\nA vendor must give notice at least\n30 days before a change.",
            "2 Other\nText.",
        )
    )
    keys = [c.key for c in seg.clauses]
    assert keys == ["1.1", "1.2", "2"]
    assert seg.clauses[0].text == "Temporary access expires after 14 days."
    assert seg.clauses[1].text == "A vendor must give notice at least 30 days before a change."


def test_out_of_sequence_numbers_stay_body_text() -> None:
    seg = segment(pages("cover", "1 Scope\nApplies to all.\n7 Things Happen\nMore.", "2 Next\nX."))
    assert [c.key for c in seg.clauses] == ["1", "2"]
    assert seg.clauses[0].text == "Applies to all. 7 Things Happen More."


def test_clause_spanning_pages_keeps_both_spans() -> None:
    ps = pages("cover", "1 Scope\nFirst half of the clause", "continues here.\n2 Next\nDone.")
    seg = segment(ps)
    clause = seg.clauses[0]
    assert clause.text == "First half of the clause continues here."
    spans = merge_spans(clause.pieces)
    assert [s.page_index for s in spans] == [1, 2]
    for span in spans:
        raw = ps[span.page_index].raw_text[span.char_start : span.char_end]
        assert " ".join(raw.split()) == clause.text[span.text_start : span.text_end]


def test_list_items_keep_line_breaks_and_hyphen_wraps_join() -> None:
    seg = segment(
        pages(
            "cover",
            "1 Rules\nStaff must:\n(a) report within one\nhour; and\n(b) keep data-\nsharing records.",
            "2 End\nX.",
        )
    )
    assert (
        seg.clauses[0].text
        == "Staff must:\n(a) report within one hour; and\n(b) keep data-sharing records."
    )


def test_cross_references_are_collected() -> None:
    seg = segment(
        pages(
            "cover",
            "1 Rules\n1.1 Approval\nNeeds approval.\n1.2 Exception\nLegal approves instead of clause 1.1.",
            "2 End\nX.",
        )
    )
    assert seg.clauses[1].references == ["1.1"]
    assert seg.clauses[1].kind == ClauseKind.EXCEPTION


def test_classify() -> None:
    assert classify("Definition of sharing", "x") == ClauseKind.DEFINITION
    assert classify("Terms", "“Vendor” means a third party.") == ClauseKind.DEFINITION
    assert classify("Approval", "Sharing requires approval.") == ClauseKind.REQUIREMENT
    assert classify("Purpose", "This policy sets rules.") == ClauseKind.GENERAL


def test_document_without_numbered_clauses_warns() -> None:
    seg = segment(pages("cover", "Just some prose.", "More prose."))
    assert seg.clauses == []
    assert any("No numbered clauses" in w for w in seg.warnings)
