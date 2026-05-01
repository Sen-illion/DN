import argparse
import base64
import os
import shlex
import sys

import paramiko


def run_remote_script(host: str, port: int, username: str, password: str, script: str) -> int:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        hostname=host,
        port=port,
        username=username,
        password=password,
        look_for_keys=False,
        allow_agent=False,
        timeout=20,
    )

    # Pass through token envs only for this process and only when set locally.
    remote_prefix = []
    for key in ("HF_TOKEN", "HUGGINGFACE_HUB_TOKEN"):
        value = os.environ.get(key)
        if value:
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            remote_prefix.append(f'export {key}="{escaped}"')

    wrapped = "set -euo pipefail\n"
    if remote_prefix:
        wrapped += "\n".join(remote_prefix) + "\n"
    wrapped += script

    encoded = base64.b64encode(wrapped.encode("utf-8")).decode("ascii")
    command = f'bash -lc "$(printf %s {shlex.quote(encoded)} | base64 -d)"'
    stdin, stdout, stderr = client.exec_command(command, get_pty=True)

    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    status = stdout.channel.recv_exit_status()

    if out:
        sys.stdout.buffer.write(out.encode("utf-8", errors="replace"))
    if err:
        sys.stderr.buffer.write(err.encode("utf-8", errors="replace"))

    client.close()
    return status


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", required=True, type=int)
    parser.add_argument("--username", required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--script-file", required=True)
    args = parser.parse_args()

    with open(args.script_file, "r", encoding="utf-8") as handle:
        script = handle.read()

    return run_remote_script(args.host, args.port, args.username, args.password, script)


if __name__ == "__main__":
    raise SystemExit(main())
