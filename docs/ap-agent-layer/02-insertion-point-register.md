# AP insertion-point register

Production event volumes and handling times are not accessible from this workspace. Values below are explicit planning estimates, not measured facts. They must be replaced by a 30-day production query and AP-user time study before build order is final.

Scoring uses `monthly volume × median minutes ÷ blast-radius factor`, where 1 is low/reversible and 10 is severe/irreversible.

| Rank | Human action | Estimated monthly volume | Estimated median minutes | Judgement | Reversible | Blast factor | Provisional score | Evidence status |
|---:|---|---:|---:|---|---|---:|---:|---|
| 1 | Extract invoice fields and correct OCR | 1,000 | 4 | Medium | Yes | 2 | 2,000 | Estimate |
| 2 | Classify/split incoming document packs | 1,000 | 2 | Low | Yes | 1 | 2,000 | Estimate |
| 3 | Match PO, GRN and invoice; explain breaks | 700 | 8 | High | Yes before posting | 4 | 1,400 | Estimate |
| 4 | Resolve supplier | 800 | 3 | Medium/high | Yes | 3 | 800 | Estimate |
| 5 | Code GL, dimensions and tax | 700 | 6 | High | Yes before posting | 6 | 700 | Estimate |
| 6 | Triage validation/duplicate exceptions | 250 | 7 | High | Usually | 4 | 438 | Estimate |
| 7 | Read and link supplier email | 400 | 3 | Medium | Yes | 2 | 600 | Estimate |
| 8 | Build payment-run proposal | 2 | 120 | High | Yes before release | 8 | 30 | Estimate |
| 9 | Reconcile supplier statements | 25 | 45 | High | Yes | 5 | 225 | Estimate |
| 10 | AP close checklist/accrual schedule | 1 | 480 | High | Yes before posting | 8 | 60 | Estimate |

The equal provisional scores for extraction and classification are resolved by dependency: classification/splitting must precede extraction. Therefore the provisional order is Classifier, Extractor, Matcher, Vendor Resolver, Coder, Correspondent, Validator/Exception Triage, Reconciler, Payment Planner, Close Assistant.

## Required measurement query

For the latest 30 complete days, measure by tenant and entity:

- invoice count by source, document type, page count, language and final status;
- timestamps between receipt, extraction completion, first human edit, supplier resolution, proposal, submission, approval and ERP draft;
- human edit counts and fields changed;
- exception and rejection reason codes;
- false-match and duplicate-overturn rates;
- number of supplier emails and attachments;
- ERP draft failures and retries.

The current schema lacks several timestamps and structured reason codes needed for this query. Those are prerequisite tickets in the gap report.
