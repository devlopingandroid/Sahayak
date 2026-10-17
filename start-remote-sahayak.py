"""Run the laptop backend and a temporary tunnel; refresh its Vercel proxy."""
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import requests

ROOT=Path(__file__).resolve().parent
ARTIFACTS=ROOT/'.codex_artifacts'
DEPLOY=ARTIFACTS/'vercel-frontend'
CONFIG=ARTIFACTS/'remote-access.json'


def healthy():
    try:
        r=requests.get('http://127.0.0.1:5000/api/health',timeout=2)
        return r.ok and r.json().get('service')=='SAHAYAK'
    except (requests.RequestException,ValueError):
        return False


def main():
    config=json.loads(CONFIG.read_text())
    backend=None
    tunnel=None
    hidden={'creationflags':subprocess.CREATE_NO_WINDOW} if os.name=='nt' else {}
    try:
        if not healthy():
            log=(ARTIFACTS/'remote-backend.log').open('a',encoding='utf-8')
            backend=subprocess.Popen([sys.executable,str(ROOT/'sahayak_cloud/server.py')],cwd=ROOT,
                stdout=log,stderr=subprocess.STDOUT,**hidden)
            for _ in range(40):
                if healthy():break
                if backend.poll() is not None:raise RuntimeError('Backend failed. Check .codex_artifacts/remote-backend.log.')
                time.sleep(1)
            else:raise RuntimeError('Backend did not become ready.')
        print('Laptop backend is running.',flush=True)
        tunnel_log=ARTIFACTS/'remote-tunnel.log'
        with tunnel_log.open('w',encoding='utf-8') as output:
            tunnel=subprocess.Popen([str(ARTIFACTS/'tools/cloudflared.exe'),'tunnel','--url',
                'http://127.0.0.1:5000','--http-host-header','localhost:5000','--no-autoupdate'],
                stdout=output,stderr=subprocess.STDOUT,cwd=ROOT,**hidden)
        address=None
        for _ in range(60):
            matches=re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com',tunnel_log.read_text(errors='replace'))
            if matches:
                address=matches[0];break
            if tunnel.poll() is not None:raise RuntimeError('Tunnel stopped. Check .codex_artifacts/remote-tunnel.log.')
            time.sleep(1)
        if not address:raise RuntimeError('No tunnel address received.')
        config['tunnel_url']=address
        config['allowed_origins']=list(dict.fromkeys([config['frontend_url'],address]))
        CONFIG.write_text(json.dumps(config,indent=2))
        (DEPLOY/'vercel.json').write_text(json.dumps({
            'version':2,'rewrites':[{'source':'/api/:path*','destination':address+'/api/:path*'}],
            'headers':[{'source':'/api/:path*','headers':[{'key':'Cache-Control','value':'no-store'}]}]
        },indent=2))
        print('Refreshing the Vercel frontend connection. This may take a minute.',flush=True)
        result=subprocess.run(config['vercel_command']+['deploy','--prod','--yes'],cwd=DEPLOY)
        if result.returncode:raise RuntimeError('Frontend deployment failed. Sign in with the Vercel CLI and try again.')
        print('\nSAHAYAK frontend: '+config['frontend_url'],flush=True)
        print('Keep this window open. Press Ctrl+C to close the tunnel.',flush=True)
        while tunnel.poll() is None:time.sleep(1)
        raise RuntimeError('The tunnel stopped. Restart this launcher to reconnect.')
    finally:
        for process in (tunnel,backend):
            if process is not None and process.poll() is None:
                process.terminate()
                try:process.wait(timeout=8)
                except subprocess.TimeoutExpired:process.kill()


if __name__=='__main__':
    try:main()
    except KeyboardInterrupt:print('\nRemote access stopped.')
    except Exception as exc:
        print('Could not start remote access: '+str(exc))
        sys.exit(1)
