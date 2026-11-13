from app.catalog import load_catalog


def test_catalog_is_synthetic_and_has_unique_ids() -> None:
    catalog = load_catalog()

    assert "Synthetic" in catalog.note
    assert len(catalog.conditions) >= 30
    assert len(catalog.ids()) == len(catalog.conditions)
