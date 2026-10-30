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

Set credentials as environment variables. Use either a password or a key.

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
        "SSH_HOST": "example.com",
        "SSH_PORT": "22",
        "SSH_USER": "root",
        "SSH_PASSWORD": "change-me"
      }
    }
  }
}
```

## Tools

You can override `host`, `port` and `username` per call. Credentials are read
from the environment only, so they do not end up in tool calls.
