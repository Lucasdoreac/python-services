import importlib

import configmodule


def test_config_prefers_explicit_mongo_uri(monkeypatch):
    monkeypatch.setenv("MONGO_URI", "mongodb://mongo:27017")
    monkeypatch.setenv("MONGO_DATABASE", "reservas_local")
    monkeypatch.setenv("MONGO_HOST", "atlas.example.mongodb.net")
    monkeypatch.setenv("MONGO_USERNAME", "atlas-user")
    monkeypatch.setenv("MONGO_PASSWORD", "atlas-password")

    config = importlib.reload(configmodule).Config

    assert config.MONGO_URI == "mongodb://mongo:27017"
    assert config.MONGO_DATABASE == "reservas_local"


def test_config_keeps_atlas_uri_fallback(monkeypatch):
    monkeypatch.delenv("MONGO_URI", raising=False)
    monkeypatch.setenv("MONGO_DATABASE", "reservas")
    monkeypatch.setenv("MONGO_HOST", "cluster.example.mongodb.net")
    monkeypatch.setenv("MONGO_USERNAME", "atlas-user")
    monkeypatch.setenv("MONGO_PASSWORD", "atlas-password")

    config = importlib.reload(configmodule).Config

    assert config.MONGO_URI == (
        "mongodb+srv://atlas-user:atlas-password@cluster.example.mongodb.net/"
    )
