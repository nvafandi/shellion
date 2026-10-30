"""Shellion - a small MCP server for SSH access over Paramiko."""

from __future__ import annotations

import os
import threading
from typing import Any

import paramiko
from mcp.server.mcpserver import MCPServer

mcp = MCPServer("shellion")

DEFAULT_TIMEOUT = float(os.getenv("SSH_TIMEOUT", "15"))


def _connection(
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
) -> paramiko.SSHClient:
    """Open an SSH connection using env defaults plus optional overrides.

    Credentials come from the environment only, so they never appear in a
    tool call or the model transcript.
    """
    resolved_host = host or os.getenv("SSH_HOST")
    resolved_port = int(port or os.getenv("SSH_PORT", "22"))
    resolved_user = username or os.getenv("SSH_USER") or os.getenv("USER")

    if not resolved_host:
        raise ValueError("SSH_HOST is not set")
    if not resolved_user:
        raise ValueError("SSH_USER is not set")

    client = paramiko.SSHClient()
    known_hosts = os.getenv("SSH_KNOWN_HOSTS")
    if known_hosts:
        client.load_host_keys(os.path.expanduser(known_hosts))
    else:
        # shortcut: accept unknown host keys; install SSH_KNOWN_HOSTS for
        # production use so the tool can detect changed host keys.
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    kwargs: dict[str, Any] = {
        "hostname": resolved_host,
        "port": resolved_port,
        "username": resolved_user,
        "timeout": DEFAULT_TIMEOUT,
    }
    key_path = os.getenv("SSH_KEY_PATH")
    if key_path:
        kwargs["key_filename"] = os.path.expanduser(key_path)
        passphrase = os.getenv("SSH_KEY_PASSPHRASE")
        if passphrase:
            kwargs["passphrase"] = passphrase
    else:
        kwargs["password"] = os.getenv("SSH_PASSWORD")

    client.connect(**kwargs)
    return client


@mcp.tool()
def run_command(
    command: str,
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
    timeout: float = 60.0,
) -> str:
    """Run a shell command over SSH and return stdout, stderr and exit code."""
    client = _connection(host, port, username)
    try:
        _, stdout, stderr = client.exec_command(command, timeout=timeout)
        # Read both streams concurrently; a full stderr pipe can otherwise
        # block the remote command while stdout is being drained.
        chunks: dict[str, list[bytes]] = {"out": [], "err": []}

        def drain(name: str, stream: Any) -> None:
            chunks[name].append(stream.read())

        readers = [
            threading.Thread(target=drain, args=("out", stdout), daemon=True),
            threading.Thread(target=drain, args=("err", stderr), daemon=True),
        ]
        for thread in readers:
            thread.start()
        for thread in readers:
            thread.join(timeout)
        exit_code = stdout.channel.recv_exit_status()
        out = b"".join(chunks["out"]).decode("utf-8", "replace")
        err = b"".join(chunks["err"]).decode("utf-8", "replace")
        return f"exit_code: {exit_code}\n--- stdout ---\n{out}\n--- stderr ---\n{err}"
    finally:
        client.close()


@mcp.tool()
def upload_file(
    local_path: str,
    remote_path: str,
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
) -> str:
    """Upload a local file to the remote host with SFTP."""
    client = _connection(host, port, username)
    try:
        sftp = client.open_sftp()
        sftp.put(os.path.expanduser(local_path), remote_path)
        sftp.close()
        return f"uploaded {local_path} -> {remote_path}"
    finally:
        client.close()


@mcp.tool()
def download_file(
    remote_path: str,
    local_path: str,
    host: str | None = None,
    port: int | None = None,
    username: str | None = None,
) -> str:
    """Download a remote file to the local machine with SFTP."""
    client = _connection(host, port, username)
    try:
        sftp = client.open_sftp()
        sftp.get(remote_path, os.path.expanduser(local_path))
        sftp.close()
        return f"downloaded {remote_path} -> {local_path}"
    finally:
        client.close()


if __name__ == "__main__":
    mcp.run()
