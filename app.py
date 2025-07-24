from flask import Flask, render_template, Response
import cv2
import numpy as np
import mediapipe as mp
from collections import deque
import time

app = Flask(__name__)

# Only blue drawing points
bpoints = [deque(maxlen=1024)]

# Blue index for drawing
blue_index = 0

# Pink color like in screenshot
color = (255, 100, 200)

# Here is code for Canvas setup
paintWindow = np.zeros((471,636,3)) + 255

# initialize mediapipe
mpHands = mp.solutions.hands
hands = mpHands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mpDraw = mp.solutions.drawing_utils

# Initialize the webcam
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

def generate_frames():
    global bpoints, blue_index
    global paintWindow
    
    while True:
        # Read each frame from the webcam
        ret, frame = cap.read()
        if not ret:
            continue

        x, y, c = frame.shape

        # Flip the frame vertically
        frame = cv2.flip(frame, 1)
        framergb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        # Get hand landmark prediction
        result = hands.process(framergb)

        # post process the result
        if result.multi_hand_landmarks:
            landmarks = []
            for handslms in result.multi_hand_landmarks:
                for lm in handslms.landmark:
                    lmx = int(lm.x * 640)
                    lmy = int(lm.y * 480)
                    landmarks.append([lmx, lmy])

                # Drawing landmarks on frames
                mpDraw.draw_landmarks(frame, handslms, mpHands.HAND_CONNECTIONS)
            
            # Get key landmarks
            fore_finger = (landmarks[8][0], landmarks[8][1])
            middle_finger = (landmarks[12][0], landmarks[12][1])
            ring_finger = (landmarks[16][0], landmarks[16][1])
            pinky = (landmarks[20][0], landmarks[20][1])
            thumb = (landmarks[4][0], landmarks[4][1])
            
            center = fore_finger
            cv2.circle(frame, center, 3, (0,255,0), -1)
            
            # Check if all 5 fingers are visible (open hand) - no drawing
            fingers_up = 0
            if thumb[0] > landmarks[3][0]:  # thumb
                fingers_up += 1
            if fore_finger[1] < landmarks[6][1]:  # index
                fingers_up += 1
            if middle_finger[1] < landmarks[10][1]:  # middle
                fingers_up += 1
            if ring_finger[1] < landmarks[14][1]:  # ring
                fingers_up += 1
            if pinky[1] < landmarks[18][1]:  # pinky
                fingers_up += 1
            
            # Check for fist (clear) - all fingertips close to palm
            is_fist = (fore_finger[1] > landmarks[6][1] and 
                      middle_finger[1] > landmarks[10][1] and 
                      ring_finger[1] > landmarks[14][1] and 
                      pinky[1] > landmarks[18][1])
            
            if is_fist:  # Fist - clear canvas
                bpoints = [deque(maxlen=512)]
                blue_index = 0
                paintWindow[67:,:,:] = 255
            elif fingers_up >= 5:  # Open hand - pen up, no drawing
                bpoints.append(deque(maxlen=512))
                blue_index += 1
            else:  # Normal drawing with index finger
                bpoints[blue_index].appendleft(center)
        # Append the next deques when nothing is detected to avoid messing up
        else:
            bpoints.append(deque(maxlen=512))
            blue_index += 1

        # Draw blue lines on the frame
        for j in range(len(bpoints)):
            for k in range(1, len(bpoints[j])):
                if bpoints[j][k - 1] is None or bpoints[j][k] is None:
                    continue
                cv2.line(frame, bpoints[j][k - 1], bpoints[j][k], color, 8)

        # Encode frame
        ret, buffer = cv2.imencode('.jpg', frame)
        frame = buffer.tobytes()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)