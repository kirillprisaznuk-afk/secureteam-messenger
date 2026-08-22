import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.server import MessengerServer

if __name__ == "__main__":
    server = MessengerServer()
    try:
        server.start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
        server.stop()
