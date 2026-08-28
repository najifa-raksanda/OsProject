from __future__ import annotations

from pathlib import Path

from flask import Flask, jsonify, redirect, render_template, url_for

from .service import ExamService


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def create_app(
    policy_path: str | Path = PROJECT_ROOT / "config" / "policy.json",
    database_path: str | Path = PROJECT_ROOT / "data" / "events.db",
) -> Flask:
    app = Flask(__name__)
    service = ExamService(policy_path, database_path)
    app.extensions["exam_service"] = service

    @app.get("/")
    def dashboard():
        return render_template(
            "dashboard.html",
            status=service.status(),
            processes=service.processes(),
            events=service.logger.recent(30),
        )

    @app.post("/exam/start")
    def start_exam():
        service.start()
        return redirect(url_for("dashboard"))

    @app.post("/exam/stop")
    def stop_exam():
        service.stop()
        return redirect(url_for("dashboard"))

    @app.get("/api/status")
    def api_status():
        return jsonify(service.status())

    @app.get("/api/processes")
    def api_processes():
        return jsonify(service.processes())

    @app.get("/api/events")
    def api_events():
        return jsonify(service.logger.recent(100))

    return app

