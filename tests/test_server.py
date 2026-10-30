import os
import unittest
from unittest.mock import MagicMock, patch

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


if __name__ == "__main__":
    unittest.main()
