# Air Canvas - Hand Gesture Drawing

Real-time hand gesture recognition for air drawing with AI-powered heart detection.

## Quick Start

Open terminal and run this command:

```bash
git clone https://github.com/dennisimoo/Air-Canvas.git && cd Air-Canvas && pip install -r requirements.txt && python app.py
```

Then open: http://localhost:5001

## Manual Setup

1. Clone the repository:
```bash
git clone https://github.com/dennisimoo/Air-Canvas.git
cd Air-Canvas
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
python app.py
```

4. Open your browser to: http://localhost:5001

## How to Use

- **Index finger**: Draw in the air
- **Fist**: Clear the canvas
- **Two fingers together**: Pen up (stop drawing)
- **High five (4+ fingers)**: Analyze drawing for hearts

## Requirements

- Python 3.8+
- Webcam access
- Modern browser (Chrome, Firefox, Safari)

## Features

- Real-time hand tracking with MediaPipe
- Air drawing with gesture controls
- AI heart detection using trained YOLOv8 model
- Dark/light mode toggle
- Works on desktop and mobile

## Deployment

For cloud deployment, the app uses browser camera access via WebRTC. Deploy to any platform that supports Flask:

- Railway
- Render
- Heroku
- DigitalOcean

Make sure to enable HTTPS for camera access in production.

## Technical Stack

- **Frontend**: HTML5 Canvas, MediaPipe JavaScript
- **Backend**: Flask, OpenCV, MediaPipe Python
- **AI Model**: YOLOv8 for heart detection
- **Deployment**: Docker ready

## Troubleshooting

**Camera not working?**
- Ensure HTTPS in production
- Allow camera permissions in browser
- Check if webcam is being used by another app

**Model not detecting hearts?**
- Make sure `heart_detect.pt` file exists
- Try drawing clearer heart shapes
- Check console for error messages

Made by Dennis Khylkouski