#!/usr/bin/env python3
# server.py – גרסה מעודכנת: גלילה דינמית + ניהול מצלמה מרחוק (Remote AI Control)

import socket, threading, sys, subprocess
from pynput.mouse import Controller as MouseController, Button
import keyboard as kb
import pyautogui
from collections import deque
from thefuzz import process, fuzz 

HOST = '0.0.0.0'
COMMAND_PORT = 5000
DISCOVERY_PORT = 5001

mouse = MouseController()
scale_value = 1.6667
running = True
is_dragging = False 
head_track_process = None  # משתנה לאחסון תהליך המצלמה

COMMAND_MAPPINGS = {
    "RIGHT_CLICK": ["right click", "right", "רייט קליק", "רייט", "ימין"],
    "LEFT_CLICK": ["left click", "left", "לפט קליק", "לפט", "שמאל", "קליק"],
    "HOTKEY_CTRL_C": ["copy", "העתק", "קופי", "תעתיק"],
    "HOTKEY_CTRL_V": ["paste", "הדבק", "פייסט", "תדביק"],
    "HOTKEY_CTRL_X": ["cut", "גזור", "קאט", "תגזור"],
    "HOTKEY_CTRL_Z": ["undo", "בטל", "אנדו", "חזור אחורה"],
    "HOTKEY_CTRL_S": ["save", "שמור", "סייב", "תשמור"],
    "HOTKEY_CTRL_F": ["find", "search", "חפש", "חיפוש", "תמצא"],
    "HOTKEY_ENTER": ["enter", "אנטר", "כנס", "שורה חדשה"],
    "TOGGLE_SELECTION": ["select", "mark", "סמן", "בחירה", "סלקט", "תסמן"]
}

def parse_hotkey(name: str):
    parts = name.strip().upper().split('_')
    return [p.lower() for p in parts if p]

def press_combo(keys):
    try:
        combo = '+'.join(keys)
        if combo == 'ctrl+c' or combo == 'ctrl+f': 
            pyautogui.hotkey(*keys)
        else:
            kb.send(combo, do_press=True, do_release=True)
        print(f"✔ Executed Combo: {combo}")
    except Exception as e:
        print(f"❌ Error: {e}")

def handle_internal_command(action):
    global is_dragging
    if action == "LEFT_CLICK":
        mouse.click(Button.left)
    elif action == "RIGHT_CLICK":
        mouse.click(Button.right)
    elif action == "TOGGLE_SELECTION":
        if not is_dragging:
            mouse.press(Button.left)
            is_dragging = True
            print("🔹 Selection Mode: ON")
        else:
            mouse.release(Button.left)
            is_dragging = False
            print("🔸 Selection Mode: OFF")
    elif action.startswith("HOTKEY_"):
        key_string = action.replace("HOTKEY_", "")
        keys = parse_hotkey(key_string)
        if keys: press_combo(keys)

def handle_smart_voice(text):
    text = text.lower().strip()
    print(f"🔍 Analyzing voice: '{text}'")
    best_score = 0
    best_action = None
    for action, keywords in COMMAND_MAPPINGS.items():
        if text in keywords:
            handle_internal_command(action)
            return 
    for action, keywords in COMMAND_MAPPINGS.items():
        match, score = process.extractOne(text, keywords, scorer=fuzz.ratio)
        if score > best_score:
            best_score = score
            best_action = action
    if best_score >= 60:
        print(f"🤖 Fuzzy Match: '{text}' -> {best_action} ({best_score}%)")
        handle_internal_command(best_action)
    else:
        print(f"🤷‍♂️ Not understood: '{text}'")

def handle_command(cmd: str):
    global scale_value, head_track_process
    try:
        parts = cmd.strip().split(':')
        action = parts[0].strip()

        # --- פקודות שליטה במצלמה (App Control) ---
        if action == "START_CAMERA":
            if head_track_process is None:
                try:
                    # הפעלת ה-AI כתהליך נפרד ברקע
                    head_track_process = subprocess.Popen([sys.executable, 'head_track_poc.py'])
                    print("📷 Camera AI Started via App")
                except Exception as e:
                    print(f"❌ Failed to start camera: {e}")
            return

        if action == "STOP_CAMERA":
            if head_track_process is not None:
                head_track_process.terminate()
                head_track_process = None
                print("🛑 Camera AI Stopped via App")
            return

        # --- פקודות גלילה מה-AI ---
        if action == "SCROLL_DOWN":
            mouse.scroll(0, -2) 
            print("🎢 Action: GENTLE SCROLL DOWN")
            return
        
        if action == "SCROLL_UP":
            mouse.scroll(0, 2)
            print("🚀 Action: GENTLE SCROLL UP")
            return

        if action == "SCROLL_RAW":
            try:
                velocity = float(parts[1])
                # הכפלת המהירות כדי שהגלילה תהיה מורגשת יותר ב-PC
                scroll_amount = -(velocity * 3) 
                # הדפסה לטרמינל כדי שתראה שזה עובד
                print(f"☝️ Touch Scroll: {scroll_amount:.1f}") 
                mouse.scroll(0, scroll_amount)
            except Exception as e:
                print(f"❌ Scroll Error: {e}")
            return

        if action == "VOICE_RAW":
            raw_text = parts[1] if len(parts) > 1 else ""
            print(f"🎤 Voice Command Received: '{raw_text}'")
            handle_smart_voice(raw_text)
            return

        if action == "MOVE_DELTA":
            dx, dy = map(float, parts[1].split(','))
            mouse.move(dx * scale_value, dy * scale_value)

        elif action == "SET_SCALE":
            scale_value = float(parts[1])
            print(f"• Scale set to {scale_value}")
        else:
            handle_internal_command(action)

    except Exception as e:
        print(f"❌ Error: {e}")

def discovery_listener(sock):
    while running:
        try:
            data, addr = sock.recvfrom(1024)
            if data.decode().strip() == "DISCOVER":
                sock.sendto(b"MOUSE_SERVER", addr)
        except: pass

def command_listener(sock):
    while running:
        try:
            data, addr = sock.recvfrom(1024)
            if not data: continue
            handle_command(data.decode())
        except: continue

def main():
    global running
    disc_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    disc_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    disc_sock.bind((HOST, DISCOVERY_PORT))
    
    cmd_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    cmd_sock.bind((HOST, COMMAND_PORT))
    
    threading.Thread(target=discovery_listener, args=(disc_sock,), daemon=True).start()

    print(f"✅ Server Running - App Camera Control Enabled 🚀")
    
    try:
        command_listener(cmd_sock)
    except KeyboardInterrupt:
        running = False
        if head_track_process: head_track_process.terminate()
        disc_sock.close()
        cmd_sock.close()

if __name__ == "__main__":
    main()