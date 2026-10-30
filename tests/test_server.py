import json
import os
import tempfile
import unittest
from unittest.mock import patch

import server


class ConnectionTests(unittest.TestCase):
    def test_requires_host(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(ValueError, "SSH_HOST"):
                server._connection()

    def test_uses_env_credentials(self) -> None:
        env = {
            "SSH_HOST": "example.com",
            "SSH_PORT": "2222",
            "SSH_USER": "deploy",
            "SSH_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.object(server.paramiko, "SSHClient") as client_cls:
                client = client_cls.return_value
                result = server._connection()

        self.assertIs(result, client)
        client.set_missing_host_key_policy.assert_called_once()
        client.connect.assert_called_once_with(
            hostname="example.com",
            port=2222,
            username="deploy",
            timeout=server.DEFAULT_TIMEOUT,
            password="secret",
        )

    def test_uses_key_when_configured(self) -> None:
        env = {
            "SSH_HOST": "example.com",
            "SSH_USER": "deploy",
            "SSH_KEY_PATH": "~/.ssh/id_ed25519",
            "SSH_KEY_PASSPHRASE": "secret",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch.object(server.paramiko, "SSHClient") as client_cls:
                server._connection()

        kwargs = client_cls.return_value.connect.call_args.kwargs
        self.assertTrue(kwargs["key_filename"].endswith(".ssh/id_ed25519"))
        self.assertEqual(kwargs["passphrase"], "secret")
        self.assertNotIn("password", kwargs)

    def test_reads_credentials_from_json_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump(
                {
                    "host": "file.example.com",
                    "port": 2200,
                    "username": "fileuser",
                    "password": "filepass",
                    "timeout": 30,
                },
                handle,
            )
            path = handle.name
        try:
            with patch.dict(os.environ, {"SSH_CREDENTIALS_FILE": path}, clear=True):
                with patch.object(server.paramiko, "SSHClient") as client_cls:
                    server._connection()
        finally:
            os.unlink(path)

        client_cls.return_value.connect.assert_called_once_with(
            hostname="file.example.com",
            port=2200,
            username="fileuser",
            timeout=30.0,
            password="filepass",
        )

    def test_env_overrides_json_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as handle:
            json.dump({"host": "file.example.com", "username": "fileuser"}, handle)
            path = handle.name
        try:
            env = {
                "SSH_CREDENTIALS_FILE": path,
                "SSH_HOST": "env.example.com",
            }
            with patch.dict(os.environ, env, clear=True):
                with patch.object(server.paramiko, "SSHClient") as client_cls:
                    server._connection()
        finally:
            os.unlink(path)

        kwargs = client_cls.return_value.connect.call_args.kwargs
        self.assertEqual(kwargs["hostname"], "env.example.com")
        self.assertEqual(kwargs["username"], "fileuser")


if __name__ == "__main__":
    unittest.main()
