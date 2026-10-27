"""Small reproducible localhost workload using synthetic temporary data only."""

import json
import statistics
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from client.network import NetworkClient
from server.auth import hash_password
from server.database import Database
from server.server import MessengerServer


def measure() -> dict:
    with tempfile.TemporaryDirectory(prefix="secureteam-benchmark-") as directory:
        start = time.perf_counter()
        db = Database(str(Path(directory) / "benchmark.db"))
        hashed = hash_password("synthetic benchmark password")
        for index in range(8):
            db.create_user(f"user{index}", hashed, "employee")
        cid = db.admin_create_chat("Benchmark", 1, list(range(1, 9)))
        server = MessengerServer(port=0, database_path=db.path)
        startup = time.perf_counter()
        thread = threading.Thread(target=server.start)
        thread.start()
        assert server.ready.wait(5)
        startup_ms = (time.perf_counter() - startup) * 1000
        clients = []
        latencies = []
        login_times = []
        try:
            for index in range(8):
                client = NetworkClient(port=server.port)
                clients.append(client)
                before = time.perf_counter()
                assert client.connect()
                assert client.login(f"user{index}", "synthetic benchmark password")["success"]
                login_times.append((time.perf_counter() - before) * 1000)

            def send(client):
                values = []
                for index in range(10):
                    before = time.perf_counter()
                    assert client.send_text_message(cid, f"Concurrent sample {index}")["success"]
                    values.append((time.perf_counter() - before) * 1000)
                return values

            with ThreadPoolExecutor(max_workers=8) as pool:
                for values in pool.map(send, clients):
                    latencies.extend(values)
            before = time.perf_counter()
            response = clients[0].get_chat_history(cid)
            history_ms = (time.perf_counter() - before) * 1000
            assert response["success"] and len(response["messages"]) == 20
            with db.transaction() as conn:
                assert conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0] == 80
                plan = [
                    row[3]
                    for row in conn.execute(
                        "EXPLAIN QUERY PLAN SELECT * FROM messages WHERE chat_id=? AND id<? ORDER BY id DESC LIMIT 20",
                        (cid, 2**63 - 1),
                    )
                ]
        finally:
            for client in clients:
                client.disconnect()
            before = time.perf_counter()
            server.stop()
            thread.join(5)
            shutdown_ms = (time.perf_counter() - before) * 1000
        assert not thread.is_alive() and not server.threads and not server.connections
        return {
            "clients": 8,
            "messages": len(latencies),
            "listener_start_ms": round(startup_ms, 2),
            "connect_and_argon2_login_median_ms": round(statistics.median(login_times), 2),
            "send_ack_median_ms": round(statistics.median(latencies), 2),
            "send_ack_p95_ms": round(sorted(latencies)[int(len(latencies) * 0.95) - 1], 2),
            "history_page_ms": round(history_ms, 2),
            "shutdown_ms": round(shutdown_ms, 2),
            "query_plan": plan,
            "remaining_worker_threads": len(server.threads),
            "remaining_connections": len(server.connections),
            "total_seconds": round(time.perf_counter() - start, 2),
        }


if __name__ == "__main__":
    print(json.dumps(measure(), indent=2))
