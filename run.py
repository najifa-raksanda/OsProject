import os
from pathlib import Path

from exam_manager.web import PROJECT_ROOT, create_app


policy_path = Path(os.environ.get("EXAM_POLICY", PROJECT_ROOT / "config" / "policy.json"))
app = create_app(policy_path=policy_path)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

