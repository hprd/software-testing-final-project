#!/usr/bin/env python3
"""Start the local model if needed, then ask a question or chat."""
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.error
import urllib.request

root = Path(__file__).resolve().parent
url = "http://127.0.0.1:" + os.environ.get("PORT", "8080") + "/health"
opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

def status():
    try:
        with opener.open(url, timeout=2) as response:
            return response.status
    except urllib.error.HTTPError as error:
        return error.code
    except (urllib.error.URLError, TimeoutError, OSError):
        return None

server = None
try:
    if "--help" not in sys.argv[1:] and "-h" not in sys.argv[1:]:
        health = status()
        if health != 200:
            if health is None:
                log_path = root / "logs" / "run-server.log"
                with log_path.open("a") as log:
                    server = subprocess.Popen([str(root / "serve.sh")], stdout=log, stderr=subprocess.STDOUT)
            elif health != 503:
                sys.exit("Unexpected service on " + url + "; choose another PORT.")
            print("Loading model; the first start may take a minute...", file=sys.stderr)
            deadline = time.monotonic() + 300
            while status() != 200:
                if server is not None and server.poll() is not None:
                    sys.exit("Model server failed. See " + str(root / "logs" / "run-server.log"))
                if time.monotonic() >= deadline:
                    sys.exit("Model startup timed out. See logs in " + str(root / "logs"))
                time.sleep(1)
        if not sys.argv[1:]:
            print("Ask your question at You>. Type /quit to exit.", file=sys.stderr)
    result = subprocess.call([sys.executable, str(root / "chat.py"), *sys.argv[1:]])
    sys.exit(result)
except KeyboardInterrupt:
    print(file=sys.stderr)
    sys.exit(130)
finally:
    if server is not None and server.poll() is None:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
