"""Production WSGI entrypoint for Gunicorn or another WSGI server."""

from exam_manager.web import create_app


app = create_app()

