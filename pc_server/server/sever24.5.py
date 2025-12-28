#!/usr/bin/env python3
# שילוב: עכבר עם pynput, קיצורים עם keyboard (עובד גם עם CTRL+C)

import socket, threading, sys, time
from pynput.mouse import Controller as MouseController, Button
import keyboard as kb  # ספריית keyboard שולחת ממש ברמת מערכת
from collections import deque

HOST = '0.0.0.0'
COMMAND_PORT = 5000
DISCOVERY_PORT = 5001
SCROLL_STEP = 0.2

mouse = MouseController()
scale_value = 1.6667
recent_deltas = deque(maxlen=5)
running = True

def parse_hotkey(name: str):
    parts = name.strip().upper().split('_')
    return [p.lower() for p in parts if p]  # ['ctrl', 'c']

def press_combo(keys):
    try:
        combo = '+'.join(keys)
        print(f"✔ Sending keyboard hotkey: {combo}")
        kb.send(combo, do_press=True, do_release=True)
    except Exception as e:
        print("❌ Error sending combo:", e, file=sys.stderr)

def handle_command(cmd: str):
    global scale_value
    parts = cmd.strip().split(':')
    action = parts[0].strip()

    if action == "MOVE_DELTA":
        dx, dy = map(float, parts[1].split(','))
        sx, sy = dx * scale_value, dy * scale_value
        if abs(sx) >= 0.5 or abs(sy) >= 0.5:
            mouse.move(sx, sy)

    elif action == "SET_SCALE":
        scale_value = float(parts[1])
        print(f"• scale set to {scale_value}")

    elif action == "SCROLL_UP":
        mouse.scroll(0, SCROLL_STEP)
    elif action == "SCROLL_DOWN":
        mouse.scroll(0, -SCROLL_STEP)

    elif action == "LEFT_CLICK":
        mouse.click(Button.left)
    elif action == "RIGHT_CLICK":
        mouse.click(Button.right)
    elif action == "LEFT_DOWN":
        mouse.press(Button.left)
    elif action == "LEFT_UP":
        mouse.release(Button.left)

    elif action.startswith("HOTKEY_"):
        key_string = action.replace("HOTKEY_", "")
        keys = parse_hotkey(key_string)
        if keys:
            press_combo(keys)
        else:
            print(f"❌ Invalid hotkey: {key_string}", file=sys.stderr)

def discovery_listener(sock):
    while running:
        try:
            data, addr = sock.recvfrom(1024)
            if data.decode().strip() == "DISCOVER":
                sock.sendto(b"MOUSE_SERVER", addr)
        except socket.timeout:
            continue

def command_listener(sock):
    while running:
        try:
            data, addr = sock.recvfrom(1024)
            handle_command(data.decode())
        except socket.timeout:
            continue
        except Exception as e:
            print("Err:", e, file=sys.stderr)

def main():
    global running
    disc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    disc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    disc_sock.bind((HOST, DISCOVERY_PORT))
    disc_sock.settimeout(1.0)

    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cmd_sock.bind((HOST, COMMAND_PORT))
    cmd_sock.settimeout(1.0)

    t_disc = threading.Thread(target=discovery_listener, args=(disc_sock,), daemon=True)
    t_disc.start()

    print(f"✅ Server ready on UDP {COMMAND_PORT}/{DISCOVERY_PORT} using keyboard module")
    try:
        command_listener(cmd_sock)
    except KeyboardInterrupt:
        print("\nStopping…")
        running = False
        disc_sock.close()
        cmd_sock.close()
        t_disc.join()
    print("🔻 Shutdown complete.")

if __name__ == "__main__":
    main()
    # python C:\dev\server\server.py
    # python C:\dev\server\sever_old.py
    # python C:\dev\server\server22.4.py
