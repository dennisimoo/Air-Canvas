// Client-side MediaPipe setup
const video = document.getElementById('video');
const processedCanvas = document.getElementById('processedCanvas');
const processedCtx = processedCanvas.getContext('2d');

// Drawing state
let bpoints = [[]];
let blue_index = 0;
const color = [200, 100, 255]; // Pink/purple color - BGR (255,100,200) converted to RGB
let analysis_result = "";
let analysis_confidence = 0;
let last_analysis_time = 0;

// Gesture highlighting
let currentGesture = 'none'; // 'draw', 'clear', 'analyze', 'none'

// MediaPipe Hands
const hands = new Hands({
    locateFile: (file) => {
        return `https://cdn.jsdelivr.net/npm/@mediapipe/hands/${file}`;
    }
});

hands.setOptions({
    maxNumHands: 1,
    modelComplexity: 1,
    minDetectionConfidence: 0.7,
    minTrackingConfidence: 0.5
});

hands.onResults(onResults);

function onResults(results) {
    // Clear canvas and draw mirrored video
    processedCtx.clearRect(0, 0, processedCanvas.width, processedCanvas.height);
    processedCtx.save();
    processedCtx.scale(-1, 1);
    processedCtx.drawImage(video, -processedCanvas.width, 0, processedCanvas.width, processedCanvas.height);
    processedCtx.restore();
    
    // Check if hand is in frame
    if (results.multiHandLandmarks && results.multiHandLandmarks.length > 0) {
        for (const landmarks of results.multiHandLandmarks) {
            // Mirror landmarks for display
            const mirroredLandmarks = landmarks.map(landmark => ({
                x: 1 - landmark.x,
                y: landmark.y,
                z: landmark.z
            }));
            
            // Draw hand landmarks
            drawConnectors(processedCtx, mirroredLandmarks, HAND_CONNECTIONS, {color: '#00FF00', lineWidth: 3});
            drawLandmarks(processedCtx, mirroredLandmarks, {color: '#FF0000', lineWidth: 2, radius: 3});
            
            // Get key landmarks (use mirrored for display)
            const fore_finger = mirroredLandmarks[8];
            const middle_finger = mirroredLandmarks[12];
            const ring_finger = mirroredLandmarks[16];
            const pinky = mirroredLandmarks[20];
            const thumb = mirroredLandmarks[4];
            
            // Convert to pixel coordinates
            const width = processedCanvas.width;
            const height = processedCanvas.height;
            
            const center = {
                x: fore_finger.x * width,
                y: fore_finger.y * height
            };
            
            // Draw green circle at fingertip
            processedCtx.fillStyle = '#00FF00';
            processedCtx.beginPath();
            processedCtx.arc(center.x, center.y, 5, 0, 2 * Math.PI);
            processedCtx.fill();
            
            // Check finger positions with stricter thresholds
            const index_up = fore_finger.y < landmarks[6].y - 0.04;
            const middle_up = middle_finger.y < landmarks[10].y - 0.04;
            const ring_up = ring_finger.y < landmarks[14].y - 0.04;
            const pinky_up = pinky.y < landmarks[18].y - 0.04;
            const thumb_up = thumb.x > landmarks[3].x + 0.05;
            
            // More strict fist detection - all fingertips must be well below their knuckles
            const index_really_down = fore_finger.y > landmarks[5].y + 0.02;
            const middle_really_down = middle_finger.y > landmarks[9].y + 0.02;
            const ring_really_down = ring_finger.y > landmarks[13].y + 0.02;
            const pinky_really_down = pinky.y > landmarks[17].y + 0.02;
            
            const is_fist = (!index_up && !middle_up && !ring_up && !pinky_up) && 
                           (index_really_down && middle_really_down && ring_really_down && pinky_really_down);
            const pointer_middle_distance = Math.sqrt(
                Math.pow((fore_finger.x - middle_finger.x) * width, 2) + 
                Math.pow((fore_finger.y - middle_finger.y) * height, 2)
            );
            const fingers_together = pointer_middle_distance < 30;
            const all_fingers_up = [index_up, middle_up, ring_up, pinky_up, thumb_up].filter(Boolean).length >= 4;
            
            // Update gesture highlighting
            let newGesture = 'none';
            
            if (is_fist) {
                // Clear canvas
                bpoints = [[]];
                blue_index = 0;
                analysis_result = "";
                analysis_confidence = 0;
                last_analysis_time = Date.now() - 6000;
                newGesture = 'clear';
            } else if (fingers_together) {
                // Pen up
                bpoints.push([]);
                blue_index++;
            } else if (all_fingers_up) {
                // Analyze drawing
                const current_time = Date.now();
                const has_drawing = bpoints.some(points => points.length > 1);
                
                if (has_drawing && (current_time - last_analysis_time) > 2000) {
                    console.log("FIVE FINGERS DETECTED! Analyzing drawing...");
                    analyzeDrawing();
                    last_analysis_time = current_time;
                }
                bpoints.push([]);
                blue_index++;
                newGesture = 'analyze';
            } else if (index_up && !middle_up && !ring_up && !pinky_up) {
                // Draw (use mirrored coordinates)
                if (!bpoints[blue_index]) bpoints[blue_index] = [];
                bpoints[blue_index].unshift(center);
                newGesture = 'draw';
            } else {
                // Other gestures
                bpoints.push([]);
                blue_index++;
            }
            
            // Update gesture highlighting if changed
            if (newGesture !== currentGesture) {
                updateGestureHighlight(newGesture);
                currentGesture = newGesture;
            }
        }
    } else {
        // No hand in frame - remove all highlights
        bpoints.push([]);
        blue_index++;
        updateGestureHighlight('none');
        currentGesture = 'none';
    }
    
    // Draw pink lines - same as training data
    processedCtx.strokeStyle = `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
    processedCtx.lineWidth = 8;
    processedCtx.lineCap = 'round';
    processedCtx.lineJoin = 'round';
    
    for (const points of bpoints) {
        if (points.length > 1) {
            processedCtx.beginPath();
            processedCtx.moveTo(points[0].x, points[0].y);
            for (let i = 1; i < points.length; i++) {
                processedCtx.lineTo(points[i].x, points[i].y);
            }
            processedCtx.stroke();
        }
    }
}

function analyzeDrawing() {
    // Send drawing to server for heart detection using trained model
    const canvas = document.createElement('canvas');
    canvas.width = 600;
    canvas.height = 400;
    const ctx = canvas.getContext('2d');
    
    // White background like training data
    ctx.fillStyle = 'white';
    ctx.fillRect(0, 0, 600, 400);
    
    // Draw paths in pink like training data
    ctx.strokeStyle = 'rgb(255, 100, 200)';
    ctx.lineWidth = 8;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
    
    for (const points of bpoints) {
        if (points.length > 1) {
            ctx.beginPath();
            // Scale from camera coordinates to analysis coordinates
            const scaleX = 600 / processedCanvas.width;
            const scaleY = 400 / processedCanvas.height;
            
            ctx.moveTo(points[0].x * scaleX, points[0].y * scaleY);
            for (let i = 1; i < points.length; i++) {
                ctx.lineTo(points[i].x * scaleX, points[i].y * scaleY);
            }
            ctx.stroke();
        }
    }
    
    // Send to server for analysis
    canvas.toBlob(blob => {
        const formData = new FormData();
        formData.append('drawing', blob);
        
        fetch('/analyze_drawing', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.confidence > 50) {
                analysis_result = "Heart detected!";
                analysis_confidence = data.confidence;
                console.log(`Heart detected with ${data.confidence}% confidence!`);
            } else {
                console.log(`Not a heart - ${data.confidence}% confidence`);
            }
        })
        .catch(err => console.error('Analysis error:', err));
    }, 'image/jpeg', 0.8);
}

async function setupCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { width: 640, height: 480 } 
        });
        video.srcObject = stream;
        
        video.addEventListener('loadedmetadata', () => {
            const width = video.videoWidth || 640;
            const height = video.videoHeight || 480;
            
            processedCanvas.width = width;
            processedCanvas.height = height;
            
            console.log('Video dimensions:', width, 'x', height);
            document.querySelector('.status-overlay span').textContent = 'Ready to draw';
        });
        
        // Setup MediaPipe camera
        const camera = new Camera(video, {
            onFrame: async () => {
                await hands.send({image: video});
            },
            width: 640,
            height: 480
        });
        camera.start();
        
    } catch (err) {
        console.error('Camera access denied:', err);
        document.querySelector('.status-overlay span').textContent = 'Camera access denied';
    }
}

// Gesture highlighting function
function updateGestureHighlight(gesture) {
    // Remove all highlight classes
    const gestureIcons = document.querySelectorAll('.gesture-icon');
    gestureIcons.forEach(icon => {
        icon.classList.remove('gesture-active');
    });
    
    // Add highlight class based on current gesture
    if (gesture === 'draw') {
        const drawIcon = document.querySelector('.gesture-icon[data-gesture="draw"]');
        if (drawIcon) drawIcon.classList.add('gesture-active');
    } else if (gesture === 'clear') {
        const clearIcon = document.querySelector('.gesture-icon[data-gesture="clear"]');
        if (clearIcon) clearIcon.classList.add('gesture-active');
    } else if (gesture === 'analyze') {
        const analyzeIcon = document.querySelector('.gesture-icon[data-gesture="analyze"]');
        if (analyzeIcon) analyzeIcon.classList.add('gesture-active');
    }
}

// Initialize everything
setupCamera();
setInterval(checkForAnalysis, 1000);
setInterval(checkDebugMessages, 500);