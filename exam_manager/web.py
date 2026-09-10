from __future__ import annotations

import csv
import io
from pathlib import Path

from flask import Flask, Response, jsonify, redirect, render_template, url_for

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
            events=service.logger.recent(30, service.session_id),
            predictions=service.predictions()[:12],
            samples=list(reversed(service.samples(60))),
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
        return jsonify(service.logger.recent(100, service.session_id))

    @app.get("/api/predictions")
    def api_predictions():
        return jsonify(service.predictions())

    @app.get("/api/evaluation")
    def api_evaluation():
        return jsonify(service.logger.summary(service.session_id))

    def csv_response(rows: list[dict], filename: str) -> Response:
        output = io.StringIO()
        if rows:
            writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()), extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    @app.get("/export/events.csv")
    def export_events():
        return csv_response(service.logger.session_events(service.session_id), f"events-{service.session_id}.csv")

    @app.get("/export/samples.csv")
    def export_samples():
        rows = list(reversed(service.logger.recent_samples(service.session_id, 2000)))
        return csv_response(rows, f"samples-{service.session_id}.csv")

    @app.get("/export/report.json")
    def export_report():
        report = {
            "session_id": service.session_id,
            "exam_name": service.policy.exam_name,
            "mode": service.policy.mode,
            "summary": service.logger.summary(service.session_id),
        }
        response = jsonify(report)
        response.headers["Content-Disposition"] = f'attachment; filename="report-{service.session_id}.json"'
        return response

    return app
