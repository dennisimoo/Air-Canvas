// Initialize Lucide icons
lucide.createIcons();

// Tutorial functionality
function closeTutorial() {
    document.getElementById('tutorialOverlay').style.display = 'none';
    localStorage.setItem('tutorialShown', 'true');
}

// Close tutorial when clicking outside
document.getElementById('tutorialOverlay').addEventListener('click', function(e) {
    if (e.target === this) {
        closeTutorial();
    }
});

// Check if tutorial has been shown before
if (!localStorage.getItem('tutorialShown')) {
    document.getElementById('tutorialOverlay').style.display = 'flex';
} else {
    document.getElementById('tutorialOverlay').style.display = 'none';
}

// Dark mode toggle
const themeToggle = document.getElementById('themeToggle');
const lightIcon = document.getElementById('lightIcon');
const darkIcon = document.getElementById('darkIcon');
const body = document.body;

themeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-mode');
    
    if (body.classList.contains('dark-mode')) {
        lightIcon.style.display = 'none';
        darkIcon.style.display = 'inline';
    } else {
        lightIcon.style.display = 'inline';
        darkIcon.style.display = 'none';
    }
});

function checkForAnalysis() {
    if (analysis_result) {
        const analysisDiv = document.getElementById('analysisResult');
        const resultText = document.getElementById('resultText');
        const confidenceText = document.getElementById('confidenceText');
        
        console.log(`Analysis: ${analysis_result} with ${analysis_confidence}% confidence`);
        
        resultText.textContent = analysis_result;
        confidenceText.textContent = `${analysis_confidence}% confidence`;
        analysisDiv.style.display = 'flex';
        
        // Clear result after showing
        analysis_result = "";
        analysis_confidence = 0;
        
        setTimeout(() => {
            analysisDiv.style.display = 'none';
        }, 3000);
    }
}

function checkDebugMessages() {
    // No server calls needed - all client-side now
}

// Auto-refresh for development - checks if HTML file changed
console.log('Setting up auto-reload for hostname:', window.location.hostname);
if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' || window.location.hostname === '0.0.0.0') {
    let lastModified = null;
    setInterval(async () => {
        try {
            const response = await fetch('/check_template_modified?t=' + Date.now()); // Cache bust
            const data = await response.json();
            console.log('Template modified check:', data.modified, 'vs', lastModified);
            if (lastModified && data.modified !== lastModified) {
                console.log('Template changed, reloading...');
                // Force hard reload to bypass all caches
                window.location.href = window.location.href.split('?')[0] + '?t=' + Date.now();
            }
            lastModified = data.modified;
        } catch (e) {
            console.log('Auto-reload check failed:', e);
        }
    }, 500); // Check more frequently
} else {
    console.log('Auto-reload disabled for hostname:', window.location.hostname);
}