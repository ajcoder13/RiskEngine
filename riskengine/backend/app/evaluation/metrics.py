"""Evaluation helpers. Only computes metrics from real labelled data supplied by the caller."""
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, precision_recall_fscore_support


def sentiment_report(y_true: list[str], y_pred: list[str]) -> dict:
    labels = ["positive", "negative", "neutral"]
    p, r, f, s = precision_recall_fscore_support(y_true, y_pred, labels=labels, zero_division=0)
    return {"n": len(y_true), "accuracy": float(accuracy_score(y_true, y_pred)),
            "macro_f1": float(f.mean()),
            "per_class": {l: {"precision": float(p[i]), "recall": float(r[i]), "f1": float(f[i]), "support": int(s[i])}
                          for i, l in enumerate(labels)}}


def event_report(y_true: list[str], y_pred: list[str]) -> dict:
    labels = sorted(set(y_true) | set(y_pred))
    rep = classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)
    return {"n": len(y_true), "accuracy": float(accuracy_score(y_true, y_pred)),
            "macro_f1": float(rep["macro avg"]["f1-score"]), "labels": labels,
            "confusion_matrix": confusion_matrix(y_true, y_pred, labels=labels).tolist(),
            "per_class": {l: rep[l] for l in labels}}
