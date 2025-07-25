from collections import deque
import cv2 
import numpy as np
import mediapipe as mp
from flask import Flask, render_template, Response, jsonify, request
import time
import torch
from ultralytics import YOLO
import io
from PIL import Image
import os

app = Flask(__name__)

# Disable template caching for development
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.auto_reload = True

# Giving different arrays to handle colour points of different colour
bpoints = [deque(maxlen=1024)]

# Blue index for drawing
blue_index = 0

# Pink color like in screenshot
color = (255, 100, 200)

# Here is code for Canvas setup
paintWindow = np.zeros((471,636,3)) + 255

# Initialize MediaPipe
mpHands = mp.solutions.hands
hands = mpHands.Hands(max_num_hands=1, min_detection_confidence=0.7)
mpDraw = mp.solutions.drawing_utils

# No webcam needed for WebRTC - frames come from browser

# Analysis result
analysis_result = ""
analysis_confidence = 0
last_analysis_time = 0

# Load the trained heart detection model
try:
    heart_model = YOLO('heart_detect.pt')
    print("Heart detection model loaded successfully!")
except Exception as e:
    print(f"Failed to load heart model: {e}")
    heart_model = None

# Debug messages for browser console
debug_messages = []

def analyze_drawing():
    global analysis_result, analysis_confidence, debug_messages
    
    if heart_model is None:
        analysis_result = "Model not loaded"
        analysis_confidence = 0
        debug_messages.append("ALERT SENT: Heart detection model not loaded")
        return
    
    # Create a white image to draw the path (same as training data)
    analysis_img = np.ones((400, 600, 3), dtype=np.uint8) * 255
    
    # Draw all the points as pink lines (same as training data)
    for j in range(len(bpoints)):
        for k in range(1, len(bpoints[j])):
            if bpoints[j][k - 1] is None or bpoints[j][k] is None:
                continue
            cv2.line(analysis_img, 
                    (int(bpoints[j][k - 1][0] * 600/640), int(bpoints[j][k - 1][1] * 400/480)), 
                    (int(bpoints[j][k][0] * 600/640), int(bpoints[j][k][1] * 400/480)), 
                    (255, 100, 200), 8)  # Same color and thickness as training
    
    try:
        # Use the trained model to predict
        results = heart_model.predict(analysis_img, verbose=False)
        
        if len(results) > 0 and len(results[0].probs) > 0:
            # Get the predicted class probabilities
            probs = results[0].probs.data.cpu().numpy()
            
            # Assuming class 0 is 'hearts' and class 1 is 'not_hearts'
            heart_confidence = int(probs[0] * 100) if len(probs) > 0 else 0
            
            if heart_confidence > 50:  # 50% threshold
                analysis_result = "Heart detected!"
                analysis_confidence = heart_confidence
                debug_messages.append(f"ALERT SENT: Heart detected with {heart_confidence}% confidence!")
            else:
                analysis_result = ""
                analysis_confidence = 0
                debug_messages.append(f"Not detected - {heart_confidence}% confidence")
        else:
            analysis_result = ""
            analysis_confidence = 0
            debug_messages.append("No prediction from model")
            
    except Exception as e:
        analysis_result = ""
        analysis_confidence = 0
        debug_messages.append(f"Model error - {str(e)}")

def process_frame_data(frame):
    global bpoints, blue_index
    global paintWindow, analysis_result, analysis_confidence, last_analysis_time
    
    if frame is None:
        return frame
    
    x, y, c = frame.shape
    framergb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    # Get hand landmark prediction
    result = hands.process(framergb)

    # post process the result
    if result.multi_hand_landmarks:
        landmarks = []
        for handslms in result.multi_hand_landmarks:
            for lm in handslms.landmark:
                lmx = int(lm.x * frame.shape[1])
                lmy = int(lm.y * frame.shape[0])
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
        
        # Check finger positions - proper detection
        index_up = fore_finger[1] < landmarks[6][1] - 10
        middle_up = middle_finger[1] < landmarks[10][1] - 10
        ring_up = ring_finger[1] < landmarks[14][1] - 10
        pinky_up = pinky[1] < landmarks[18][1] - 10
        thumb_up = thumb[0] > landmarks[3][0] + 20  # thumb extended
        
        # Check for fist (clear) - all fingertips close to palm
        is_fist = (not index_up and not middle_up and not ring_up and not pinky_up)
        
        # Check if pointer and middle are together (no drawing) - distance between fingertips
        pointer_middle_distance = ((fore_finger[0] - middle_finger[0])**2 + (fore_finger[1] - middle_finger[1])**2)**0.5
        fingers_together = pointer_middle_distance < 30
        
        # Check if all 5 fingers are up - high five position
        fingers_extended = [index_up, middle_up, ring_up, pinky_up, thumb_up]
        all_fingers_up = sum(fingers_extended) >= 4  # At least 4 out of 5 fingers
        
        if is_fist:  # Fist - clear canvas
            bpoints = [deque(maxlen=512)]
            blue_index = 0
            paintWindow[67:,:,:] = 255
            # Clear analysis result when clearing canvas
            analysis_result = ""
            analysis_confidence = 0
            # Reset cooldown properly when clearing
            last_analysis_time = time.time() - 6  # Allow immediate analysis after clearing
        elif fingers_together:  # Pointer and middle together - no drawing
            bpoints.append(deque(maxlen=512))
            blue_index += 1
        elif all_fingers_up:  # All 5 fingers up - analyze drawing
            # Only send debug messages once per gesture to reduce spam
            current_time = time.time()
            has_drawing = any(len(points) > 1 for points in bpoints if points)
            
            # Only analyze if cooldown has passed
            if has_drawing and (current_time - last_analysis_time) > 5:
                debug_messages.append("FIVE FINGERS DETECTED! Analyzing drawing...")
                analyze_drawing()
                last_analysis_time = current_time
            bpoints.append(deque(maxlen=512))
            blue_index += 1
        elif index_up and not middle_up and not ring_up and not pinky_up:  # Only index finger up - draw
            bpoints[blue_index].appendleft(center)
        else:  # Other gestures - no drawing
            bpoints.append(deque(maxlen=512))
            blue_index += 1
    # Append the next deques when nothing is detected to avoid messing up
    else:
        bpoints.append(deque(maxlen=512))
        blue_index += 1

    # Draw pink lines on the frame
    for j in range(len(bpoints)):
        for k in range(1, len(bpoints[j])):
            if bpoints[j][k - 1] is None or bpoints[j][k] is None:
                continue
            cv2.line(frame, bpoints[j][k - 1], bpoints[j][k], color, 8)

    return frame

@app.route('/process_frame', methods=['POST'])
def process_frame():
    if 'frame' not in request.files:
        return 'No frame', 400
    
    file = request.files['frame']
    if file.filename == '':
        return 'No frame', 400
    
    try:
        # Read image from browser
        image = Image.open(io.BytesIO(file.read()))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Process the frame (add hand landmarks and drawings)
        processed_frame = process_frame_data(frame)
        
        # Encode processed frame as JPEG
        ret, buffer = cv2.imencode('.jpg', processed_frame)
        if ret:
            return Response(buffer.tobytes(), mimetype='image/jpeg')
        else:
            return 'Processing failed', 500
            
    except Exception as e:
        print(f"Error processing frame: {e}")
        return 'Error', 500

@app.route('/')
def index():
    # Add cache busting headers
    response = app.make_response(render_template('index.html'))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response


@app.route('/analyze_drawing', methods=['POST'])
def analyze_drawing():
    if 'drawing' not in request.files:
        return jsonify({'confidence': 0})
    
    file = request.files['drawing']
    if file.filename == '':
        return jsonify({'confidence': 0})
    
    try:
        # Read image from browser
        image = Image.open(io.BytesIO(file.read()))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Use the trained model to predict
        if heart_model is not None:
            results = heart_model.predict(frame, verbose=False)
            
            if len(results) > 0 and len(results[0].probs) > 0:
                probs = results[0].probs.data.cpu().numpy()
                heart_confidence = int(probs[0] * 100) if len(probs) > 0 else 0
                return jsonify({'confidence': heart_confidence})
        
        return jsonify({'confidence': 0})
        
    except Exception as e:
        print(f"Error analyzing drawing: {e}")
        return jsonify({'confidence': 0})

@app.route('/get_analysis')
def get_analysis():
    return {'result': analysis_result, 'confidence': analysis_confidence}

@app.route('/get_debug')
def get_debug():
    global debug_messages
    messages = debug_messages.copy()
    debug_messages = []  # Clear after sending
    return {'messages': messages}

@app.route('/check_template_modified')
def check_template_modified():
    """Check if the HTML template has been modified for live reload"""
    try:
        template_path = os.path.join(app.template_folder, 'index.html')
        if os.path.exists(template_path):
            modified_time = os.path.getmtime(template_path)
            return jsonify({'modified': modified_time})
        else:
            return jsonify({'modified': 0})
    except Exception as e:
        return jsonify({'modified': 0})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)