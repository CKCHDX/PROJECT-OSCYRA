"""
CSH Service Launcher — Python replacement for .bat launchers.

Usage:
    python -m CSH.launcher start --all
    python -m CSH.launcher start klar
    python -m CSH.launcher stop klar
    python -m CSH.launcher status
"""

import argparse
import os
import subprocess
import sys
import signal
import time
from pathlib import Path

import yaml

CSH_DIR = Path(__file__).resolve().parent
CONFIG_PATH = CSH_DIR / "config" / "services.yaml"


def load_config():
    with open(CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _wrapper_cmd(svc_key: str, svc_cfg: dict, gateway_cfg: dict) -> list:
    """Build the command list to invoke service_wrapper for a service."""
    keys_dir = CSH_DIR / gateway_cfg.get("keys_dir", "keys")
    gw_host = gateway_cfg.get("host", "127.0.0.1")
    gw_port = gateway_cfg.get("port", 14270)

    launch = svc_cfg.get("launch", {})
    launch_cmd = launch.get("command", "")
    launch_cwd_rel = launch.get("cwd", "")
    launch_cwd = str((CSH_DIR / launch_cwd_rel).resolve()) if launch_cwd_rel else ""

    private_key = str(keys_dir / f"{svc_key}_private.key")
    csh_pub_key = str(keys_dir / "csh_public.key")

    return [
        sys.executable, "-m", "slp.agent.service_wrapper",
        "--service-id", svc_cfg.get("service_id", f"{svc_key}-001"),
        "--service-name", svc_cfg.get("name", svc_key),
        "--version", svc_cfg.get("version", "1.0.0"),
        "--http-port", str(svc_cfg.get("http_port", 0)),
        "--domain", svc_cfg.get("domain", ""),
        "--csh-addr", f"{gw_host}:{gw_port}",
        "--private-key", private_key,
        "--csh-public-key", csh_pub_key,
        "--launch-cmd", launch_cmd,
        "--launch-cwd", launch_cwd,
    ]


# Track running processes by service key.
_PIDFILE_DIR = CSH_DIR / ".pids"


def _pidfile(svc_key: str) -> Path:
    return _PIDFILE_DIR / f"{svc_key}.pid"


def _write_pid(svc_key: str, pid: int):
    _PIDFILE_DIR.mkdir(exist_ok=True)
    _pidfile(svc_key).write_text(str(pid))


def _read_pid(svc_key: str) -> int | None:
    pf = _pidfile(svc_key)
    if not pf.exists():
        return None
    try:
        pid = int(pf.read_text().strip())
        # Check if process is actually running.
        os.kill(pid, 0)
        return pid
    except (ValueError, OSError):
        pf.unlink(missing_ok=True)
        return None


def _remove_pid(svc_key: str):
    _pidfile(svc_key).unlink(missing_ok=True)


def cmd_start(args, config):
    gateway_cfg = config.get("gateway", {})
    services = config.get("services", {})
    targets = list(services.keys()) if args.all else args.services

    for key in targets:
        if key not in services:
            print(f"[!] Unknown service: {key}")
            continue

        existing_pid = _read_pid(key)
        if existing_pid is not None:
            print(f"[~] {key} already running (PID {existing_pid})")
            continue

        svc_cfg = services[key]
        cmd = _wrapper_cmd(key, svc_cfg, gateway_cfg)
        print(f"[+] Starting {svc_cfg.get('name', key)}...")

        proc = subprocess.Popen(
            cmd,
            cwd=str(CSH_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        _write_pid(key, proc.pid)
        print(f"    PID {proc.pid}")


def cmd_stop(args, config):
    services = config.get("services", {})
    targets = list(services.keys()) if args.all else args.services

    for key in targets:
        pid = _read_pid(key)
        if pid is None:
            print(f"[~] {key} is not running")
            continue

        print(f"[-] Stopping {key} (PID {pid})...")
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                os.killpg(os.getpgid(pid), signal.SIGTERM)
                time.sleep(2)
                try:
                    os.killpg(os.getpgid(pid), signal.SIGKILL)
                except OSError:
                    pass
        except OSError as e:
            print(f"    Kill failed: {e}")
        _remove_pid(key)
        print(f"    Stopped.")


def cmd_status(args, config):
    services = config.get("services", {})
    print(f"{'Service':<15} {'PID':<10} {'Status':<10} {'Port':<8}")
    print("-" * 45)
    for key, svc_cfg in services.items():
        pid = _read_pid(key)
        status = "RUNNING" if pid else "STOPPED"
        pid_str = str(pid) if pid else "-"
        port = svc_cfg.get("http_port", "?")
        print(f"{svc_cfg.get('name', key):<15} {pid_str:<10} {status:<10} {port:<8}")


def main():
    parser = argparse.ArgumentParser(
        prog="CSH Launcher",
        description="Manage CSH service processes via SLP service wrappers.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_start = sub.add_parser("start", help="Start one or more services")
    p_start.add_argument("services", nargs="*", default=[])
    p_start.add_argument("--all", action="store_true", help="Start all services")

    p_stop = sub.add_parser("stop", help="Stop one or more services")
    p_stop.add_argument("services", nargs="*", default=[])
    p_stop.add_argument("--all", action="store_true", help="Stop all services")

    p_status = sub.add_parser("status", help="Show status of all services")

    args = parser.parse_args()
    config = load_config()

    if args.command == "start":
        if not args.all and not args.services:
            parser.error("Specify service names or --all")
        cmd_start(args, config)
    elif args.command == "stop":
        if not args.all and not args.services:
            parser.error("Specify service names or --all")
        cmd_stop(args, config)
    elif args.command == "status":
        cmd_status(args, config)


if __name__ == "__main__":
    main()
