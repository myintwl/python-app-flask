import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from pythonflask import app


def test_details():
    response = app.test_client().get("/api/v1/details")
    assert response.status_code == 200
    assert response.get_json() == {"message": "Hello World"}


def test_healths():
    response = app.test_client().get("/api/v1/healths")
    assert response.status_code == 200
    assert response.get_json() == {"message": "Healths endpoint"}
