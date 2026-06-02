import pandas as pd

from fedatlas.utils import read_table, write_table


def test_write_table_serializes_nested_parquet_values(tmp_path):
    path = tmp_path / "nested.parquet"
    source = pd.DataFrame([
        {"repo": "a/b", "languages": {}, "topics": ["federated-learning"]},
        {"repo": "c/d", "languages": {"Python": 100}, "topics": []},
    ])
    write_table(source, path)
    out = read_table(path)
    assert len(out) == 2
    assert out.iloc[0]["languages"] == "{}"
    assert out.iloc[0]["topics"] == '["federated-learning"]'
