"""
Service Wrapper — launches a service process alongside its SLP agent.

Usage (from CSH):
    python -m slp.agent.service_wrapper \\
        --service-id klar-001 \\
        --service-name Klar \\
        --version 3.1.0 \\
        --http-port 4271 \\
        --domain klar.oscyra.solutions \\
        --csh-addr 127.0.0.1:14270 \\
        --slp-port 14271 \\
        --private-key keys/klar_private.key \\
        --csh-public-key keys/csh_public.key \\
        --launch-cmd "python api_server.py" \\
        --launch-cwd csh/services/klar
"""

import argparse
import asyncio
import logging
import os
import subprocess
import sys
from pathlib import Path

# Ensure the CSH root is on sys.path so relative imports work.
_CSH_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _CSH_ROOT not in sys.path:
    sys.path.insert(0, _CSH_ROOT)

from slp.agent.slp_agent import SLPAgent
from slp.keygen import load_private_key, load_public_key_bytes

logger = logging.getLogger(__name__)


async def _run(args):
    private_key = None
    csh_pub = None
    if args.private_key and os.path.exists(args.private_key):
        private_key = load_private_key(args.private_key)
    if args.csh_public_key and os.path.exists(args.csh_public_key):
        csh_pub = load_public_key_bytes(args.csh_public_key)

    csh_host, csh_port = args.csh_addr.split(":")
    csh_addr = (csh_host, int(csh_port))

    agent = SLPAgent(
        service_id=args.service_id,
        service_name=args.service_name,
        version=args.version,
        http_port=args.http_port,
        domain=args.domain,
        csh_addr=csh_addr,
        bind_port=args.slp_port,
        private_key=private_key,
        csh_public_key=csh_pub,
    )

    # Start SLP agent.
    await agent.start()

    # Start the actual service process.
    launch_cmd = args.launch_cmd.split()
    launch_cwd = args.launch_cwd or "."
    logger.info("Launching service: %s (cwd=%s)", args.launch_cmd, launch_cwd)

    proc = subprocess.Popen(
        launch_cmd,
        cwd=launch_cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    async def on_command(msg):
        cmd = msg.get("command", "")
        if cmd == "GRACEFUL_STOP":
            logger.info("Graceful stop requested")
            proc.terminate()

    agent._on_command = on_command

    # Forward stdout/stderr as LOG_ENTRY.
    async def stream_logs():
        loop = asyncio.get_event_loop()
        while proc.poll() is None:
            line = await loop.run_in_executor(None, proc.stdout.readline)
            if line:
                level = "ERROR" if "error" in line.lower() else "INFO"
                await agent.send_log(level, line.rstrip(), source=args.service_id)
        for line in proc.stdout:
            await agent.send_log("INFO", line.rstrip(), source=args.service_id)

    asyncio.create_task(stream_logs())

    while proc.poll() is None:
        await asyncio.sleep(1)

    logger.info("Service process exited with code %d", proc.returncode)
    agent.stop()


def main():
    parser = argparse.ArgumentParser(description="SLP Service Wrapper")
    parser.add_argument("--service-id", required=True)
    parser.add_argument("--service-name", required=True)
    parser.add_argument("--version", default="1.0.0")
    parser.add_argument("--http-port", type=int, required=True)
    parser.add_argument("--domain", default="")
    parser.add_argument("--csh-addr", default="127.0.0.1:14270")
    parser.add_argument("--slp-port", type=int, default=0)
    parser.add_argument("--private-key", default="")
    parser.add_argument("--csh-public-key", default="")
    parser.add_argument("--launch-cmd", required=True)
    parser.add_argument("--launch-cwd", default="")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
