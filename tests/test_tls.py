import pytest

from client.network import NetworkClient
from scripts.dev_certificate import generate
from shared.tls import client_context, server_context
from tests.conftest import PASSWORD


def test_verified_tls_round_trip(server_factory, tmp_path):
    cert, key = generate(tmp_path / "tls")
    server = server_factory(ssl_context=server_context(str(cert), str(key)))
    client = NetworkClient(port=server.port, ssl_context=client_context(str(cert)))
    try:
        assert client.connect()
        assert client.socket.version() in {"TLSv1.2", "TLSv1.3"}
        assert client.login("alice", PASSWORD)["success"]
        cid = client.create_chat("TLS chat")["chat_id"]
        assert client.send_text_message(cid, "TLS protected")["success"]
        assert client.get_chat_history(cid)["messages"][0]["content"] == "TLS protected"
    finally:
        client.disconnect()


def test_untrusted_certificate_rejected(server_factory, tmp_path):
    cert, key = generate(tmp_path / "server")
    other_cert, _ = generate(tmp_path / "unrelated")
    server = server_factory(ssl_context=server_context(str(cert), str(key)))
    client = NetworkClient(port=server.port, ssl_context=client_context(str(other_cert)))
    try:
        assert not client.connect()
        assert client.socket is None
    finally:
        client.disconnect()


def test_wrong_hostname_rejected(server_factory, tmp_path):
    # The certificate is for localhost; explicitly using a different peer name must fail.
    import socket
    import ssl

    cert, key = generate(tmp_path / "tls")
    server = server_factory(ssl_context=server_context(str(cert), str(key)))
    with socket.create_connection(("127.0.0.1", server.port), timeout=2) as raw:
        with pytest.raises(ssl.SSLCertVerificationError):
            client_context(str(cert)).wrap_socket(raw, server_hostname="wrong.example")


def test_certificate_generator_refuses_overwrite(tmp_path):
    generate(tmp_path)
    with pytest.raises(FileExistsError):
        generate(tmp_path)
