"""Desktop entry point; all connection work begins in the sign-in worker."""

import argparse
import hashlib
import logging
import sys
from pathlib import Path

from PyQt5.QtCore import QLockFile, QStandardPaths
from PyQt5.QtWidgets import QApplication, QMessageBox

from client.controller import worker_pool
from client.gui.login_window import LoginWindow
from client.gui.main_window import MainWindow
from client.network import NetworkClient
from shared.constants import DEFAULT_HOST, DEFAULT_PORT
from shared.tls import client_context


def main() -> int:
    parser = argparse.ArgumentParser(description="SecureTeam Messenger desktop client")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--ca", help="Trusted TLS certificate or CA bundle; enables TLS")
    parser.add_argument(
        "--new-instance", action="store_true", help="Allow another client for demos"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    try:
        context = client_context(args.ca) if args.ca else None
    except OSError as exc:
        parser.error(f"Cannot load TLS trust: {exc}")
    app = QApplication(sys.argv[:1])
    app.setApplicationName("SecureTeam Messenger")
    instance_key = hashlib.sha256(f"{args.host}:{args.port}".encode()).hexdigest()[:12]
    instance_lock = QLockFile(
        str(
            Path(QStandardPaths.writableLocation(QStandardPaths.TempLocation))
            / f"secureteam-{instance_key}.lock"
        )
    )
    if not args.new_instance and not instance_lock.tryLock(0):
        QMessageBox.information(
            None,
            "Already running",
            "A client for this server is already running. Use --new-instance for a second client.",
        )
        return 1
    network = NetworkClient(args.host, args.port, context)
    try:
        login = LoginWindow(network)
        if login.exec_() != login.Accepted or not login.user_info:
            return 0
        window = MainWindow(network, login.user_info)
        window.show()
        return app.exec_()
    finally:
        network.disconnect()
        worker_pool().waitForDone(12000)


if __name__ == "__main__":
    raise SystemExit(main())
