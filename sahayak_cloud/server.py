"""SAHAYAK launcher. The original server is backed up under .codex_artifacts."""
import logging
import os
import hashlib
from pathlib import Path
from app import create_app

if __name__ == "__main__":
    # Windows permits multiple Waitress sockets to reuse a port. Keep one process
    # per installation so requests cannot reach an older copy after an update.
    if os.name == 'nt':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
        kernel.CreateMutexW.restype = wintypes.HANDLE
        name = 'Local\\SAHAYAK_backend_' + hashlib.sha256(str(Path(__file__).resolve().parent).encode()).hexdigest()[:16]
        instance_mutex = kernel.CreateMutexW(None, False, name)
        if not instance_mutex:
            raise ctypes.WinError(ctypes.get_last_error())
        if ctypes.get_last_error() == 183:
            print('SAHAYAK backend is already running. Open http://localhost:5000', flush=True)
            raise SystemExit(0)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    app = create_app()
    port=int(os.environ.get('PORT','5000'))
    print(f"SAHAYAK listening on port {port}", flush=True)
    from waitress import serve
    serve(app, host="0.0.0.0", port=port, threads=8)
