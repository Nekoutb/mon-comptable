from app.agent_eval.corpus import CorpusCase, corpus_readiness, detect_direct_identifiers
from app.agent_eval.metrics import calibration_error, classification_accuracy, extraction_scores, refusal_scores, regression_gate


def case(index: int, status="adjudicated"):
    return CorpusCase(f"case-{index}", f"{index:064x}", ["invoice","credit_note","proforma","statement","receipt","noise"][index % 6], ["en","fr"][index % 2], ["clean","scan","photo","faded"][index % 4], f"supplier-{index % 30}", f"tax-{index % 5}", 1, status, f"labels/case-{index}.json")


def test_corpus_requires_300_adjudicated_stratified_cases():
    assert corpus_readiness([case(i) for i in range(299)])["ready"] is False
    report = corpus_readiness([case(i) for i in range(300)])
    assert report["ready"] is True
    assert report["dimensions"]["document_types"] == 6


def test_identifier_detection_blocks_direct_contact_and_bank_data():
    findings = detect_direct_identifiers("Send to ap@example.com, +237 699 12 34 56, CM2110003001000500000605306")
    assert set(findings) == {"email", "phone", "bank_account"}


def test_extraction_metrics_weight_critical_fields():
    score = extraction_scores([{"invoice_number":"A1","amount":"100"}], [{"invoice_number":"A1","amount":"90"}], {"amount":10,"invoice_number":2})
    assert score["precision"] == score["recall"]
    assert 0 < score["f1"] < .2


def test_classification_calibration_and_refusal_metrics():
    assert classification_accuracy(["invoice","noise"],["invoice","noise"]) == 1
    assert calibration_error([.9,.1],[True,False]) <= .11
    refusal = refusal_scores([True,False,True],[True,True,False])
    assert refusal["false_accepts"] == 1
    assert refusal["unnecessary_refusals"] == 1


def test_regression_gate_reports_material_drop():
    failures = regression_gate({"precision":.93,"recall":.91},{"precision":.96,"recall":.91},{"precision":.01,"recall":.01})
    assert failures == ["precision regressed from 0.9600 to 0.9300"]
