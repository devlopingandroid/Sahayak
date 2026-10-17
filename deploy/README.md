# Optional hosted frontend

The backend, models and primary storage run on the laptop. Vercel hosts only the built frontend. Cloudflare Quick Tunnel connects the Vercel API rewrite to the laptop. Keep the laptop and tunnel running.

## Configure another laptop

1. Complete the local installation in the root README and create a caretaker password locally.
2. Install the official Cloudflare tunnel client. Put `cloudflared.exe` in `.codex_artifacts/tools/` on Windows.
3. Install the Vercel CLI from npm and sign in to your own Vercel account.
4. Create `.codex_artifacts/vercel-frontend/` and copy the contents of `Web Interface/dist/` into it. Link that folder to your Vercel project using the Vercel CLI.
5. Copy `deploy/remote-access.example.json` to `.codex_artifacts/remote-access.json`. Set the real production frontend URL and the absolute path to the installed Vercel CLI JavaScript entry point. `vercel_command` is an argument array, not a shell command.
6. Run `python start-remote-sahayak.py` from the project root. It starts the backend when needed, creates a temporary tunnel, updates the permitted origins and deploys the frontend API rewrite. Wait until deployment completes.

The temporary tunnel URL changes after restart, so each launch updates Vercel. Use `http://localhost:5000/` for laptop microphone and speaker controls. Remote visitors cannot operate them. Remote photos and API responses pass through Cloudflare and Vercel, while primary storage remains on the laptop.

Keep tokens, CLI sign-in state, generated `.vercel` metadata and `.codex_artifacts` files out of Git. Create a private `firmware/SahayakCamera/config.h` from `firmware/config.example.h` for camera provisioning. Do not copy another installation's device token or database.
