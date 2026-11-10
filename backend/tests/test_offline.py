import os
import socket

import pytest
from pytest_socket import SocketBlockedError


def test_api_key_is_not_set():
    assert "ANTHROPIC_API_KEY" not in os.environ


def test_network_sockets_are_blocked():
    with pytest.raises(SocketBlockedError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
