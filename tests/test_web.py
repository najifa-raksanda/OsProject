import json

from exam_manager.web import create_app


def test_dashboard_and_api(tmp_path):
    policy = tmp_path / "policy.json"
    policy.write_text(json.dumps({"mode": "detect_only"}), encoding="utf-8")
    app = create_app(policy, tmp_path / "events.db")
    app.config.update(TESTING=True)
    client = app.test_client()
    assert client.get("/").status_code == 200
    response = client.get("/api/status")
    assert response.status_code == 200
    assert response.get_json()["mode"] == "detect_only"
    assert client.get("/api/predictions").status_code == 200
