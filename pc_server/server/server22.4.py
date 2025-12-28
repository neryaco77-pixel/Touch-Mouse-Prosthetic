


import socket
import threading
from pynput.mouse import Controller, Button
from collections import deque

HOST = '0.0.0.0'
COMMAND_PORT = 5000
DISCOVERY_PORT = 5001

mouse = Controller()
scale_value = 1.6667
recent_deltas = deque(maxlen=5)

def handle_command(cmd: str):
    global scale_value
    parts = cmd.strip().split(':')
    action = parts[0]

    if action == "MOVE_DELTA":
        dx, dy = map(float, parts[1].split(','))
        sx, sy = dx * scale_value, dy * scale_value
        if abs(sx) < 0.5 and abs(sy) < 0.5:
            return
        recent_deltas.append((sx, sy))
        avg_x = sum(d[0] for d in recent_deltas) / len(recent_deltas)
        avg_y = sum(d[1] for d in recent_deltas) / len(recent_deltas)
        mouse.move(avg_x, avg_y)
        print(f"MOVE => ({avg_x:.2f},{avg_y:.2f})")

    elif action == "SET_SCALE":
        scale_value = float(parts[1])
        print(f"Scale set to {scale_value}")

    elif action == "SCROLL_UP":
        mouse.scroll(0, 0.2); print("Scroll up")
    elif action == "SCROLL_DOWN":
        mouse.scroll(0, -0.2); print("Scroll down")
    elif action == "LEFT_CLICK":
        mouse.click(Button.left, 1); print("Left click")
    elif action == "RIGHT_CLICK":
        mouse.click(Button.right, 1); print("Right click")
    else:
        print("Unknown command:", action)

def discovery_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((HOST, DISCOVERY_PORT))
    print(f"Discovery listener on port {DISCOVERY_PORT}")
    while True:
        data, addr = sock.recvfrom(1024)
        if data.decode().strip() == "DISCOVER":
            sock.sendto("MOUSE_SERVER".encode(), addr)
            print(f"Replied to discovery from {addr}")

def command_listener():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((HOST, COMMAND_PORT))
    print(f"Command listener on port {COMMAND_PORT}")
    while True:
        data, addr = sock.recvfrom(1024)
        cmd = data.decode()
        print(f"[{addr}] {cmd.strip()}")
        handle_command(cmd)

def main():
    # מריצים שני מאזינים במקביל
    threading.Thread(target=discovery_listener, daemon=True).start()
    command_listener()

if __name__ == "__main__":
    main()




