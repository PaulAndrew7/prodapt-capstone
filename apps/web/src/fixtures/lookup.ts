import type { LookupAnswer } from "@/lib/api/types";
import { cite } from "./cite";
import { SNAPSHOT_ID } from "./policies";

export const LOOKUP_QUESTION = "What approvals are required before sharing customer information with a third party?";

export const lookupAnswer: LookupAnswer = {
  question: LOOKUP_QUESTION,
  answer:
    "Two approvals. The data owner must approve the share in writing and record it in the data-sharing register. The receiving vendor must also hold Approved status in the vendor register before any customer data reaches it.",
  citations: [
    cite("lk_1", "ds_v1_4_4.2", "requires written approval from the data owner, recorded in the data-sharing register before any transfer takes place"),
    cite("lk_2", "vd_v1_3_3.1", "hold Approved status in the vendor register, before receiving customer data"),
  ],
  support: "validated",
  snapshot_id: SNAPSHOT_ID,
};
