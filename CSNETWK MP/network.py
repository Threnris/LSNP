# network.py
import socket
from config import BROADCAST_IP, PORT, BUFFER_SIZE
from logger import log

def send_broadcast(message: str):
    """Send UDP broadcast message."""
    log(f"SEND >\n{message}")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.sendto(message.encode("utf-8"), (BROADCAST_IP, PORT))

def listen(callback):
    """Listen for UDP messages and pass them to a callback."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("", PORT))
        while True:
            data, addr = s.recvfrom(BUFFER_SIZE)
            log(f"RECV < {addr}\n{data.decode(errors='ignore')}")
            callback(data.decode("utf-8", errors="ignore"), addr)