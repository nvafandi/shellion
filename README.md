# Shellion

Small MCP server for SSH access via Paramiko. Exposes three tools:

- `run_command` - run a shell command
- `upload_file` - upload a file with SFTP
- `download_file` - download a file with SFTP

## Install

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Configure

Credentials can come from a JSON file or environment variables.

### JSON credential file

Copy `ssh_credential.example.json` to a private path and point
`SSH_CREDENTIALS_FILE` at it:

```json
{
  "host": "103.119.237.114",
  "port": 20136,
  "username": "nurvan",
  "password": "change-me"
}
```

```bash
SSH_CREDENTIALS_FILE=C:\Users\nurvan\Documents\ssh_credential.json
```

The file may use `password` or `key_path` / `key_passphrase`, plus optional
`known_hosts` and `timeout`. Keep the real file out of Git and restrict its
permissions (`chmod 600` on Linux/macOS).

Environment variables override values from the file, which is useful for CI.

### Environment variables

```bash
SSH_HOST=103.119.237.114
SSH_PORT=20136
SSH_USER=nurvan
SSH_PASSWORD=...
# or
SSH_KEY_PATH=~/.ssh/id_ed25519
SSH_KEY_PASSPHRASE=...
```

Optional:

```bash
SSH_TIMEOUT=15
SSH_KNOWN_HOSTS=~/.ssh/known_hosts
```

If `SSH_KNOWN_HOSTS` is not set, the server accepts unknown host keys. Set it
in production so changed host keys are rejected.

## Run

```bash
python server.py
```

The server speaks MCP over stdio, which is what most MCP clients expect.

### Example MCP client config

```json
{
  "mcpServers": {
    "shellion": {
      "command": "python",
      "args": ["C:/Users/nurvan/Documents/project/shellion/server.py"],
      "env": {
        "SSH_CREDENTIALS_FILE": "C:/Users/nurvan/Documents/ssh_credential.json"
      }
    }
  }
}
```

## Tools

You can override `host`, `port` and `username` per call. Credentials are read
from the environment or the JSON credential file, so they do not end up in tool
calls.
