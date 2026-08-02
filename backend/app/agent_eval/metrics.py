from __future__ import annotations

from collections.abc import Iterable, Mapping


def extraction_scores(expected: Iterable[Mapping], predicted: Iterable[Mapping], criticality: Mapping[str, float]) -> dict:
    expected = list(expected); predicted = list(predicted)
    if len(expected) != len(predicted): raise ValueError("Expected and predicted case counts differ")
    true_weight = predicted_weight = expected_weight = 0.0
    for gold, output in zip(expected, predicted, strict=True):
        fields = set(gold) | set(output)
        for field in fields:
            weight = float(criticality.get(field, 1.0))
            if field in gold: expected_weight += weight
            if field in output: predicted_weight += weight
            if field in gold and field in output and output[field] == gold[field]: true_weight += weight
    precision = true_weight / predicted_weight if predicted_weight else 0.0
    recall = true_weight / expected_weight if expected_weight else 0.0
    return {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0}


def classification_accuracy(expected: Iterable[str], predicted: Iterable[str]) -> float:
    expected = list(expected); predicted = list(predicted)
    if len(expected) != len(predicted): raise ValueError("Expected and predicted case counts differ")
    return sum(a == b for a, b in zip(expected, predicted, strict=True)) / len(expected) if expected else 0.0


def calibration_error(confidences: Iterable[float], correct: Iterable[bool], bins: int = 10) -> float:
    pairs = list(zip(confidences, correct, strict=True))
    if not pairs: return 0.0
    error = 0.0
    for index in range(bins):
        low, high = index / bins, (index + 1) / bins
        bucket = [(confidence, result) for confidence, result in pairs if low <= confidence <= high and (confidence < high or index == bins - 1)]
        if bucket:
            mean_confidence = sum(item[0] for item in bucket) / len(bucket)
            accuracy = sum(item[1] for item in bucket) / len(bucket)
            error += len(bucket) / len(pairs) * abs(mean_confidence - accuracy)
    return error


def refusal_scores(should_refuse: Iterable[bool], did_refuse: Iterable[bool]) -> dict:
    pairs = list(zip(should_refuse, did_refuse, strict=True))
    tp = sum(expected and actual for expected, actual in pairs)
    fp = sum(not expected and actual for expected, actual in pairs)
    fn = sum(expected and not actual for expected, actual in pairs)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": precision, "recall": recall, "false_accepts": fn, "unnecessary_refusals": fp}


def regression_gate(current: Mapping[str, float], baseline: Mapping[str, float], tolerances: Mapping[str, float]) -> list[str]:
    failures = []
    for metric, baseline_value in baseline.items():
        if metric not in current: failures.append(f"Missing metric: {metric}"); continue
        tolerance = float(tolerances.get(metric, 0.0))
        if current[metric] < baseline_value - tolerance: failures.append(f"{metric} regressed from {baseline_value:.4f} to {current[metric]:.4f}")
    return failures
