from fedatlas.topic_classifier import classify_topic


def test_topic_classifier_security():
    group, method = classify_topic("Backdoor attacks in federated learning", "robust aggregation against poisoning")
    assert group == "Security & Robustness"
    assert method.startswith("keyword:")


def test_topic_classifier_llm():
    group, _ = classify_topic("Federated learning for large language models")
    assert group == "Foundation Models / LLMs"
