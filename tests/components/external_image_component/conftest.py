import pytest


@pytest.fixture
def image_component(tmp_path, monkeypatch):
    """An ExternalImageComponent whose image store (config.data_dir) points at a temp dir."""
    from config import config
    from components.external_image_component import ExternalImageComponent
    monkeypatch.setattr(config, "data_dir", str(tmp_path))
    return ExternalImageComponent()
