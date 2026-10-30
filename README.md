<p align="center">
  <img src="assets/icon.jpg" alt="Shellion icon" width="120" align="middle" />
  &nbsp;&nbsp;
  <img src="assets/title.svg" alt="Shellion" width="360" align="middle" />
</p>

<p align="center"><strong>SSH access for AI agents over MCP</strong></p>

A small [Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server
that gives AI agents SSH access through [Paramiko](https://www.paramiko.org/).
It runs over stdio and works with any MCP-compatible client.

## Features

- Run shell commands and get stdout, stderr, and the exit code.
- Upload and download files over SFTP.
- Load credentials from a JSON file or environment variables.
- Override the target host, port, or username per tool call.
- Optional known-hosts verification for production use.

## Requirements

- Python 3.10 or newer
- SSH access to the target server (password or private key)
- `pip`

## Installation

```bash
git clone https://github.com/nvafandi/shellion.git
cd shellion

python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/macOS
source .venv/bin/activate

pip install -r requirements.txt
```

## Configuration

Credentials can come from a JSON file, environment variables, or both.
For any value, the order of precedence is:

1. Tool-call argument (`host`, `port`, `username`)
2. Environment variable
3. JSON credential file
4. Operating-system user (`USER`), only as the last fallback for `username`

### Option 1: JSON credential file

Copy the example file to a private location:

```bash
cp ssh_credential.example.json ~/.ssh/shellion.json
chmod 600 ~/.ssh/shellion.json
```

```json
{
  "host": "203.0.113.10",
  "port": 22,
  "username": "deploy",
  "password": "change-me"
}
```

Then point the server at it:

```bash
SSH_CREDENTIALS_FILE=~/.ssh/shellion.json
```

Use a private key instead of a password:

```json
{
  "host": "203.0.113.10",
  "port": 22,
  "username": "deploy",
  "key_path": "~/.ssh/id_ed25519",
  "key_passphrase": "optional-passphrase"
}
```

Supported fields:

| Field            | Type   | Required | Description                                      |
| ---------------- | ------ | -------- | ------------------------------------------------ |
| `host`           | string | yes      | SSH server hostname or IP                        |
| `port`           | number | no       | SSH port, default `22`                           |
| `username`       | string | yes      | SSH username (`user` is accepted as an alias)    |
| `password`       | string | no       | Password authentication                          |
| `key_path`       | string | no       | Path to a private key; takes priority over password |
| `key_passphrase` | string | no       | Passphrase for the private key                   |
| `known_hosts`    | string | no       | Path to a known-hosts file                       |
| `timeout`        | number | no       | Connection timeout in seconds, default `15`      |

`password` and `key_path` are mutually exclusive in practice: if `key_path` is
set, the server authenticates with the key.

### Option 2: Environment variables

```bash
SSH_HOST=203.0.113.10
SSH_PORT=22
SSH_USER=deploy

# password authentication
SSH_PASSWORD=change-me

# or key authentication
SSH_KEY_PATH=~/.ssh/id_ed25519
SSH_KEY_PASSPHRASE=optional-passphrase
```

Optional variables:

```bash
SSH_TIMEOUT=15
SSH_KNOWN_HOSTS=~/.ssh/known_hosts
```

| Variable                | Description                                      |
| ----------------------- | ------------------------------------------------ |
| `SSH_HOST`              | Target hostname or IP                            |
| `SSH_PORT`              | Target port, default `22`                        |
| `SSH_USER`              | Target username                                  |
| `SSH_PASSWORD`          | Password for password authentication             |
| `SSH_KEY_PATH`          | Path to a private key                            |
| `SSH_KEY_PASSPHRASE`    | Private-key passphrase                           |
| `SSH_KNOWN_HOSTS`       | Path to a known-hosts file                       |
| `SSH_TIMEOUT`           | Connection timeout in seconds, default `15`      |
| `SSH_CREDENTIALS_FILE`  | Path to a JSON credential file                   |

If `SSH_KNOWN_HOSTS` is unset, the server accepts unknown host keys. Set it in
production so changed host keys are rejected.

## Running the server

```bash
python server.py
```

The server communicates over stdio. MCP clients normally start it for you.

### MCP client configuration

Example for an MCP client that reads `mcpServers` JSON:

```json
{
  "mcpServers": {
    "shellion": {
      "command": "C:/Users/nurvan/Documents/project/shellion/.venv/Scripts/python.exe",
      "args": ["C:/Users/nurvan/Documents/project/shellion/server.py"],
      "env": {
        "SSH_CREDENTIALS_FILE": "C:/Users/nurvan/Documents/ssh_credential.json"
      }
    }
  }
}
```

On Linux or macOS, use the venv Python path instead:

```json
"command": "/home/nurvan/Documents/project/shellion/.venv/bin/python"
```

## Tools

### `run_command`

Run a shell command on the remote server.

| Parameter  | Type   | Required | Description                          |
| ---------- | ------ | -------- | ------------------------------------ |
| `command`  | string | yes      | Shell command to execute             |
| `host`     | string | no       | Override the configured host         |
| `port`     | number | no       | Override the configured port         |
| `username` | string | no       | Override the configured username     |
| `timeout`  | number | no       | Command timeout in seconds, default `60` |

Returns stdout, stderr, and the exit code.

### `upload_file`

Upload a local file to the remote server over SFTP.

| Parameter     | Type   | Required | Description                     |
| ------------- | ------ | -------- | ------------------------------- |
| `local_path`  | string | yes      | Local file to upload            |
| `remote_path` | string | yes      | Destination path on the server  |
| `host`        | string | no       | Override the configured host    |
| `port`        | number | no       | Override the configured port    |
| `username`    | string | no       | Override the configured username |

### `download_file`

Download a remote file over SFTP.

| Parameter     | Type   | Required | Description                     |
| ------------- | ------ | -------- | ------------------------------- |
| `remote_path` | string | yes      | File to download from the server |
| `local_path`  | string | yes      | Destination path on the local machine |
| `host`        | string | no       | Override the configured host    |
| `port`        | number | no       | Override the configured port    |
| `username`    | string | no       | Override the configured username |

## Security notes

- Credential files contain plaintext secrets. Keep them outside the repository,
  restrict permissions (`chmod 600`), and never commit them.
- Use a dedicated SSH account with only the permissions the agent needs.
- Prefer key authentication over passwords where possible.
- Set `SSH_KNOWN_HOSTS` in production. The default `AutoAddPolicy` accepts new
  host keys and cannot detect a changed key.
- `run_command` grants a full shell as the configured SSH user. Treat that
  account as compromised if the MCP server or its credentials are exposed.

## Development

Install the dependencies, then run the tests:

```bash
pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Project layout:

```text
server.py                  MCP server and SSH tools
ssh_credential.example.json  Example credential file
assets/icon.jpg            README icon
assets/title.svg           README wordmark
tests/test_server.py       Unit tests
requirements.txt           Runtime dependencies
LICENSE                    MIT license
```

## License

Released under the [MIT License](LICENSE).
