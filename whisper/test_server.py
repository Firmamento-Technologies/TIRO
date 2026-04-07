"""Basic test for Whisper server import and endpoint definition."""
from server import app


def test_app_exists() -> None:
    assert app.title == "TIRO Whisper"


def test_routes() -> None:
    routes = [r.path for r in app.routes]
    assert "/v1/audio/transcriptions" in routes
    assert "/salute" in routes
