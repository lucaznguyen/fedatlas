from __future__ import annotations

import re
from typing import Any


TOPIC_RULES: list[tuple[str, list[str]]] = [
    ("Foundation Models / LLMs", ["large language model", "llm", "foundation model", "transformer", "prompt", "federated foundation"]),
    ("Graph / GNN FL", ["graph neural", "gnn", "graph federated", "federated graph"]),
    ("Vertical / Split / Transfer FL", ["vertical federated", "split learning", "federated transfer", "horizontal federated", "federated multi-task"]),
    ("Fairness & Ethics", ["fairness", "bias", "ethical", "equity", "trustworthy"]),
    ("Data Heterogeneity / Non-IID", ["non iid", "non-iid", "heterogeneity", "heterogeneous", "statistical heterogeneity"]),
    ("Wireless & Networking", ["wireless", "6g", "5g", "network", "vehicular", "mobile edge"]),
    ("Healthcare & Biomedical", ["healthcare", "medical", "biomedical", "clinical", "hospital", "radiology", "disease", "patient"]),
    ("Systems & Edge/IoT", ["internet of things", "iot", "edge computing", "edge intelligence", "device", "mobile", "system", "resource allocation"]),
    ("Communication Efficiency", ["communication efficient", "compression", "quantization", "sparsification", "bandwidth", "communication cost"]),
    ("Security & Robustness", ["attack", "poisoning", "backdoor", "byzantine", "robust", "adversarial", "secure aggregation", "gradient leakage"]),
    ("Privacy", ["privacy", "differential privacy", "private", "secure multi-party", "homomorphic", "confidential"]),
    ("Personalization", ["personalized", "personalisation", "meta-learning", "personalization", "client adaptation"]),
    ("Core FL Algorithms", ["federated averaging", "fedavg", "federated optimization", "aggregation", "convergence", "algorithm"]),
]


def classify_topic(title: Any, abstract: Any = None, openalex_topics: list[dict[str, Any]] | None = None) -> tuple[str, str]:
    text_parts = [str(title or ""), str(abstract or "")]
    if openalex_topics:
        for topic in openalex_topics:
            text_parts.append(str(topic.get("display_name") or topic.get("name") or ""))
    text = re.sub(r"\s+", " ", " ".join(text_parts).lower())
    for group, keywords in TOPIC_RULES:
        for keyword in keywords:
            if keyword in text:
                return group, f"keyword:{keyword}"
    if "federated learning" in text or "federated machine learning" in text:
        return "Core FL Algorithms", "keyword:federated learning"
    return "Other", "fallback"
