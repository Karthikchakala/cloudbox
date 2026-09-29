import os
from app import create_app
from app.config import config

app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("BACKEND_PORT", 5000))
    debug = os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")
    print(f"[*] CloudBox Backend starting on port {port} (debug={debug})...")
    app.run(host="0.0.0.0", port=port, debug=debug)
