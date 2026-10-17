"""SAHAYAK launcher. The original server is backed up under .codex_artifacts."""
import logging
from app import create_app

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = create_app()
    print("SAHAYAK dashboard: http://localhost:5000", flush=True)
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000, threads=8)
