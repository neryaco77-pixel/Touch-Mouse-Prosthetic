import cv2
import mediapipe as mp
import numpy as np
import math
import socket
import time

# הגדרות שרת
SERVER_IP = "127.0.0.1"
PORT = 5000
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send_to_server(command):
    try:
        sock.sendto(command.encode(), (SERVER_IP, PORT))
    except: pass

# --- הגדרות רגישות (Thresholds) ---
PITCH_THRESHOLD = 12  # לגלילה (למעלה/למטה)
YAW_THRESHOLD = 15    # לקליקים (ימינה/שמאלה) - דורש תנועה ברורה הצידה

# השהיות למניעת כפילויות
last_scroll_time = 0
scroll_delay = 0.1

last_click_time = 0
click_delay = 1.0 # השהיה של שנייה שלמה לקליק כדי למנוע "דאבל קליק" בטעות

# אתחול MediaPipe
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(max_num_faces=1, refine_landmarks=True, min_detection_confidence=0.5)
mp_drawing = mp.solutions.drawing_utils

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

# מודל 3D של פנים
face_3d_model = np.array([
    (0.0, 0.0, 0.0), (0.0, -330.0, -65.0), (-225.0, 170.0, -135.0),
    (225.0, 170.0, -135.0), (-150.0, -150.0, -125.0), (150.0, -150.0, -125.0)
], dtype=np.float64)

print(f">>> DEBUG MODE: Pitch={PITCH_THRESHOLD}, Yaw={YAW_THRESHOLD}. Watching for head movement...")

while cap.isOpened():
    success, image = cap.read()
    if not success: continue

    img_h, img_w, _ = image.shape
    results = face_mesh.process(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))

    if results.multi_face_landmarks:
        for face_landmarks in results.multi_face_landmarks:
            mp_drawing.draw_landmarks(
                image=image,
                landmark_list=face_landmarks,
                connections=mp_face_mesh.FACEMESH_CONTOURS,
                landmark_drawing_spec=None,
                connection_drawing_spec=mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1)
            )

            face_2d = []
            for idx in [1, 199, 33, 263, 61, 291]:
                lm = face_landmarks.landmark[idx]
                face_2d.append([lm.x * img_w, lm.y * img_h])
            
            face_2d = np.array(face_2d, dtype=np.float64)
            focal_length = img_w
            cam_matrix = np.array([[focal_length, 0, img_w / 2], [0, focal_length, img_h / 2], [0, 0, 1]])
            
            _, rot_vec, _ = cv2.solvePnP(face_3d_model, face_2d, cam_matrix, np.zeros((4,1)))
            rmat, _ = cv2.Rodrigues(rot_vec)
            
            # --- 1. חישוב זווית Pitch (למעלה/למטה לגלילה) ---
            pitch = math.degrees(math.atan2(rmat[2, 1], rmat[2, 2]))
            if pitch > 90: pitch -= 180
            if pitch < -90: pitch += 180
            pitch = pitch - 0 

            # --- 2. חישוב זווית Yaw (ימינה/שמאלה לקליקים) ---
            yaw = math.degrees(math.atan2(-rmat[2, 0], math.sqrt(rmat[2, 1]**2 + rmat[2, 2]**2)))

            current_time = time.time()
            
            # 1. שליחת פקודות גלילה
            if pitch > PITCH_THRESHOLD:
                if current_time - last_scroll_time > scroll_delay:
                    send_to_server("SCROLL_DOWN")
                    last_scroll_time = current_time
            elif pitch < -PITCH_THRESHOLD:
                if current_time - last_scroll_time > scroll_delay:
                    send_to_server("SCROLL_UP")
                    last_scroll_time = current_time

            # 2. שליחת פקודות קליק
            # שים לב: הכיוונים (ימינה/שמאלה) תלויים בהשתקפות המצלמה. אם זה הפוך, פשוט תחליף בין ה-RIGHT ל-LEFT למטה.
            if yaw > YAW_THRESHOLD:
                if current_time - last_click_time > click_delay:
                    send_to_server("RIGHT_CLICK")
                    last_click_time = current_time
                    print("\n🖱️ COMMAND SENT: RIGHT_CLICK")
            elif yaw < -YAW_THRESHOLD:
                if current_time - last_click_time > click_delay:
                    send_to_server("LEFT_CLICK")
                    last_click_time = current_time
                    print("\n🖱️ COMMAND SENT: LEFT_CLICK")

            # תצוגת נתונים על המסך
            cv2.putText(image, f"Pitch: {int(pitch)} | Yaw: {int(yaw)}", (20, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

    cv2.imshow('ProsthetiClick Debug', image)
    if cv2.waitKey(1) & 0xFF == ord('q'): break

cap.release()
cv2.destroyAllWindows()