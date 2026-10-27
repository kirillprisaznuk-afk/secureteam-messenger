"""Start the server or explicitly bootstrap the first owner without default credentials."""

import argparse
import getpass
import logging
import sqlite3

from server import config
from server.auth import hash_password
from server.database import Database
from server.server import MessengerServer
from shared import validation
from shared.tls import server_context


def main() -> int:
    parser = argparse.ArgumentParser(description="SecureTeam Messenger server")
    parser.add_argument(
        "--host", default=config.HOST, help="Numeric bind IP; remote binds require TLS"
    )
    parser.add_argument("--port", type=int, default=config.PORT)
    parser.add_argument("--database", default=config.DATABASE_PATH)
    parser.add_argument("--cert")
    parser.add_argument("--key")
    parser.add_argument("--init-admin", action="store_true", help="Create first owner and exit")
    parser.add_argument(
        "--reset-password", metavar="USERNAME", help="Local recovery; stop server first"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s"
    )
    if bool(args.cert) != bool(args.key):
        parser.error("--cert and --key must be supplied together")
    if args.init_admin and args.reset_password:
        parser.error("Choose one account setup action")
    try:
        if args.init_admin or args.reset_password:
            db = Database(args.database)
            if args.init_admin and db.user_count():
                raise ValueError(
                    "Database already has users; bootstrap will not overwrite accounts"
                )
            username = (
                validation.username(input("Owner username: ").strip())
                if args.init_admin
                else args.reset_password
            )
            password = validation.password(getpass.getpass("New password (12–128 characters): "))
            if password != getpass.getpass("Confirm password: "):
                raise ValueError("Passwords do not match")
            hashed = hash_password(password)
            with db.transaction() as conn:
                if args.init_admin:
                    if db.user_count():
                        raise ValueError("Database already has users")
                    db.create_user(username, hashed, "owner")
                else:
                    user = db.get_user_by_username(username)
                    if not user:
                        raise ValueError("User not found")
                    conn.execute(
                        "UPDATE users SET password_hash=? WHERE id=?", (hashed, user["id"])
                    )
            print("Account saved. Start the server to sign in.")
            return 0
        context = server_context(args.cert, args.key) if args.cert else None
        server = MessengerServer(args.host, args.port, args.database, ssl_context=context)
        if not server.db.user_count():
            raise ValueError("No accounts. Run python run_server.py --init-admin first")
        try:
            server.start()
        except KeyboardInterrupt:
            server.stop()
        return 0
    except (OSError, ValueError, sqlite3.Error) as exc:
        logging.error("Server could not start: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
