# AP golden corpus

Production documents and labels must not be committed to Git. Store encrypted source documents and labels in the approved restricted corpus store. Export only a de-identified JSONL manifest for evaluation jobs.

Each manifest row follows:

```json
{"case_id":"opaque-id","document_sha256":"64-lowercase-hex","document_type":"invoice","language":"fr","quality":"scan","supplier_bucket":"supplier-017","tax_treatment":"vat-standard","page_count":2,"label_status":"adjudicated","label_file":"labels/opaque-id.json"}
```

Readiness requires at least 300 adjudicated cases, six document types, two languages and four quality levels. The corpus must also include third-language, handwritten, rotated, multi-document and adversarial cases even though those are not minimum-count dimensions.

Before admission, scan extracted text and labels with `detect_direct_identifiers`; identifiers must be tokenised consistently, with the reversible mapping held outside the evaluation environment. Never tokenise amounts, dates, document layout, tax treatment or error characteristics needed for evaluation.

Qualified-accountant labels require two-person adjudication for disagreements. Record label author, reviewer, adjudicator, timestamps and the applicable tenant accounting/tax policy versions in the restricted label object.
