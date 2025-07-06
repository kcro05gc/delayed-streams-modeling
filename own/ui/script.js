// Tab switching
function showTab(tabName, targetButton = null) {
    // Hide all tabs
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.classList.remove('active'));
    
    // Remove active class from all buttons
    const buttons = document.querySelectorAll('.tab-button');
    buttons.forEach(btn => btn.classList.remove('active'));
    
    // Show selected tab
    document.getElementById(`${tabName}-tab`).classList.add('active');
    
    // Activate the corresponding button
    if (targetButton) {
        targetButton.classList.add('active');
    } else if (event && event.target) {
        event.target.classList.add('active');
    } else {
        // Fallback: find button by text content
        const button = Array.from(buttons).find(btn => 
            btn.textContent.toLowerCase().includes(tabName.toLowerCase())
        );
        if (button) button.classList.add('active');
    }
}

// Load test file content
async function loadTestFile() {
    const selector = document.getElementById('test-file-selector');
    const textarea = document.getElementById('tts-input');
    
    if (!selector.value) {
        textarea.value = '';
        return;
    }
    
    try {
        const response = await fetch(`/api/test-file/${selector.value}`);
        const data = await response.json();
        
        if (response.ok) {
            textarea.value = data.content;
        } else {
            console.error('Failed to load test file:', data.error);
            // Fallback to predefined content
            const testContent = {
                'test1_greeting.txt': "Hello! How are you today? I hope you're having a wonderful day. The weather is quite nice, isn't it?",
                'test2_story.txt': "Once upon a time, in a small village nestled between rolling hills, there lived a curious young girl named Luna. She loved exploring the mysterious forest near her home, always searching for new adventures and magical creatures.",
                'test3_french.txt': "Bonjour! Comment allez-vous aujourd'hui? J'espère que vous passez une excellente journée. Le temps est magnifique, n'est-ce pas? J'aimerais vous inviter à prendre un café avec moi cet après-midi.",
                'test4_technical.txt': "The delayed streams modeling technique enables real-time speech-to-text conversion with impressive accuracy. By processing audio in chunks of 500 milliseconds, the system achieves a balance between latency and recognition quality.",
                'test5_numbers.txt': "The company reported revenues of $2.5 billion in Q3 2024, representing a 15% increase year-over-year. With 3,500 employees across 12 offices worldwide, they serve over 1 million customers daily.",
                'test6_questions.txt': "What time is the meeting tomorrow? Can you confirm if everyone received the agenda? I'm wondering whether we should reschedule given the weather forecast. Would you prefer a virtual or in-person format?",
                'test7_poetry.txt': "Beneath the starlit sky so bright,\nThe ocean waves dance through the night.\nWhispers of wind through ancient trees,\nCarry stories on the breeze.\nIn this moment, time stands still,\nPeace and wonder, hearts to fill.",
                'test8_mixed_lang.txt': "Hello, je m'appelle Marie. I work at a startup in Paris, mais I originally come from New York. C'est vraiment interesting to experience both cultures. My favorite café is near the Eiffel Tower, where I often meet mes amis for lunch.",
                'test9_instructions.txt': "First, preheat your oven to 180 degrees Celsius. Next, mix the flour, sugar, and baking powder in a large bowl. Then, add the eggs and milk, stirring until smooth. Pour the batter into a greased pan. Finally, bake for 25 minutes or until golden brown.",
                'test10_dialogue.txt': '"Good morning, Doctor Smith," said the patient nervously.\n"Good morning! How can I help you today?" replied the doctor with a warm smile.\n"I\'ve been having headaches for the past week."\n"I see. Let me ask you a few questions about your symptoms."'
            };
            textarea.value = testContent[selector.value] || '';
        }
    } catch (error) {
        console.error('Error loading test file:', error);
    }
}

// TTS Functions
async function runTTS() {
    const text = document.getElementById('tts-input').value.trim();
    const commandEl = document.getElementById('tts-command');
    const audioEl = document.getElementById('tts-audio');
    
    if (!text) {
        showMessage('Error: Please enter some text to convert to speech.', 'error');
        return;
    }
    
    // Show loading state
    commandEl.textContent = 'Processing... This may take a few seconds...';
    commandEl.className = '';
    audioEl.style.display = 'none';
    
    try {
        const response = await fetch('/api/tts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ text })
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Display the audio player
            audioEl.src = data.audio_url;
            audioEl.style.display = 'block';
            
            // Show the command that was executed
            const command = `# Generated audio: ${data.audio_url}\n# Command executed:\nuv run scripts/tts_pytorch.py [input] [output]`;
            commandEl.textContent = command;
            
            showMessage('Audio generated successfully! Click play to listen.', 'success');
        } else {
            commandEl.textContent = `Error: ${data.error}`;
            commandEl.className = 'error';
        }
    } catch (error) {
        commandEl.textContent = `Error: ${error.message}`;
        commandEl.className = 'error';
    }
}

function showMessage(message, type) {
    const existingMsg = document.querySelector('.message');
    if (existingMsg) existingMsg.remove();
    
    const msgEl = document.createElement('div');
    msgEl.className = `message ${type}`;
    msgEl.textContent = message;
    document.querySelector('.output-section').insertBefore(msgEl, document.querySelector('.output-section').firstChild);
    setTimeout(() => msgEl.remove(), 5000);
}

function clearTTS() {
    document.getElementById('tts-input').value = '';
    document.getElementById('tts-command').textContent = '';
    document.getElementById('tts-audio').style.display = 'none';
    document.getElementById('test-file-selector').value = '';
}

// STT Functions
async function runSTT() {
    const model = document.getElementById('stt-model').value;
    const commandEl = document.getElementById('stt-command');
    const outputEl = document.getElementById('stt-output');
    
    // Check which source is active
    const isRecording = document.getElementById('record-source').classList.contains('active');
    const isUpload = document.getElementById('upload-source').classList.contains('active');
    
    if (isUpload) {
        // Handle uploaded file
        if (!uploadedFile) {
            showMessage('Please upload an audio file first before transcribing.', 'error');
            return;
        }
        
        // Show loading state
        commandEl.textContent = 'Uploading and processing audio file...';
        commandEl.className = '';
        outputEl.textContent = 'Transcribing audio...';
        
        try {
            // Create FormData to send the audio file
            const formData = new FormData();
            formData.append('audio', uploadedFile);
            formData.append('model', model);
            
            const response = await fetch('/api/stt-upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                if (data.use_streaming) {
                    // Long file - use streaming progress
                    commandEl.textContent = `# Processing long file: ${uploadedFile.name}\n# Audio duration: ${data.audio_duration_minutes.toFixed(1)} minutes\n# Estimated processing time: ~${data.estimated_processing_minutes} minutes\n# Will be processed in ${data.num_segments} segments\n# Note: Some segments may fail due to STT model limitations, but processing will continue`;
                    startProgressTracking(data.session_id);
                } else {
                    // Regular file processing
                    outputEl.textContent = data.transcription;
                    
                    if (data.segments_processed) {
                        commandEl.textContent = `# Transcribed uploaded file: ${uploadedFile.name} using model: ${model}\n# Processed in ${data.segments_processed} segments (${data.total_duration_minutes.toFixed(1)} minutes total)`;
                        showMessage(`Long file processed successfully in ${data.segments_processed} segments!`, 'success');
                    } else {
                        commandEl.textContent = `# Transcribed uploaded file: ${uploadedFile.name} using model: ${model}`;
                        showMessage('Transcription completed successfully!', 'success');
                    }
                    
                    // Show transcript actions for completed transcriptions
                    if (data.transcription) {
                        document.querySelector('.transcript-actions').style.display = 'flex';
                    }
                }
            } else {
                commandEl.textContent = `Error: ${data.error}`;
                commandEl.className = 'error';
                outputEl.textContent = 'Transcription failed.';
            }
        } catch (error) {
            commandEl.textContent = `Error: ${error.message}`;
            commandEl.className = 'error';
            outputEl.textContent = 'Failed to transcribe audio.';
        }
    } else if (isRecording) {
        // Handle recorded audio
        if (!recordedBlob) {
            showMessage('Please record audio first before transcribing.', 'error');
            return;
        }
        
        // Show loading state
        commandEl.textContent = 'Uploading and processing recorded audio...';
        commandEl.className = '';
        outputEl.textContent = 'Transcribing audio...';
        
        try {
            // Create FormData to send the audio blob
            const formData = new FormData();
            formData.append('audio', recordedBlob, 'recording.webm');
            formData.append('model', model);
            
            const response = await fetch('/api/stt-upload', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                outputEl.textContent = data.transcription;
                commandEl.textContent = `# Transcribed recorded audio using model: ${model}`;
                showMessage('Transcription completed successfully!', 'success');
            } else {
                commandEl.textContent = `Error: ${data.error}`;
                commandEl.className = 'error';
                outputEl.textContent = 'Transcription failed.';
            }
        } catch (error) {
            commandEl.textContent = `Error: ${error.message}`;
            commandEl.className = 'error';
            outputEl.textContent = 'Failed to transcribe audio.';
        }
    } else {
        // Handle file selection
        const audioFile = document.getElementById('audio-file-selector').value;
        
        // Show loading state
        commandEl.textContent = 'Processing... This may take a few seconds...';
        commandEl.className = '';
        outputEl.textContent = 'Transcribing audio...';
        
        try {
            const response = await fetch('/api/stt', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ 
                    audio_file: audioFile,
                    model: model
                })
            });
            
            const data = await response.json();
            
            if (response.ok && data.success) {
                outputEl.textContent = data.transcription;
                const command = `# Command executed:\nuv run scripts/stt_from_file_pytorch.py --hf-repo ${model} ${audioFile}`;
                commandEl.textContent = command;
                showMessage('Transcription completed successfully!', 'success');
            } else {
                commandEl.textContent = `Error: ${data.error}`;
                commandEl.className = 'error';
                outputEl.textContent = 'Transcription failed.';
            }
        } catch (error) {
            commandEl.textContent = `Error: ${error.message}`;
            commandEl.className = 'error';
            outputEl.textContent = 'Failed to transcribe audio.';
        }
    }
}

function clearSTT() {
    document.getElementById('stt-command').textContent = '';
    document.getElementById('stt-output').textContent = '';
    document.getElementById('audio-file-selector').selectedIndex = 0;
    document.getElementById('stt-model').selectedIndex = 0;
    
    // Clear recording
    const recordedAudio = document.getElementById('recorded-audio');
    const timer = document.getElementById('recording-timer');
    const status = document.getElementById('recording-status');
    const recordBtn = document.getElementById('record-btn');
    
    recordedAudio.style.display = 'none';
    recordedAudio.src = '';
    timer.style.display = 'none';
    timer.textContent = '00:00';
    status.textContent = '';
    recordBtn.classList.remove('recording');
    recordBtn.innerHTML = '<span class="record-icon">🎤</span> Start Recording';
    recordedBlob = null;
    
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
    }
    
    // Clear upload
    const uploadedAudio = document.getElementById('uploaded-audio');
    const uploadStatus = document.getElementById('upload-status');
    const uploadZone = document.querySelector('.upload-zone');
    const fileInput = document.getElementById('mp3-file-input');
    
    uploadedAudio.style.display = 'none';
    uploadedAudio.src = '';
    uploadStatus.textContent = '';
    uploadStatus.className = 'upload-status';
    fileInput.value = '';
    uploadedFile = null;
    
    uploadZone.innerHTML = `
        <div class="upload-icon">📁</div>
        <div class="upload-text">
            <strong>Click to select an audio file</strong><br>
            <small>Supports MP3, WAV, OGG formats<br>
            Max size: 500MB, Files >5min auto-segmented</small>
        </div>
    `;
}

// Audio recording variables
let mediaRecorder;
let audioChunks = [];
let recordingStartTime;
let timerInterval;
let recordedBlob;
let uploadedFile;
let currentSessionId = null;
let progressInterval = null;

// Switch between file and recording audio sources
function switchAudioSource(source) {
    const sources = document.querySelectorAll('.audio-source');
    const tabs = document.querySelectorAll('.source-tab');
    
    sources.forEach(s => s.classList.remove('active'));
    tabs.forEach(t => t.classList.remove('active'));
    
    document.getElementById(`${source}-source`).classList.add('active');
    
    // Find and activate the correct button
    if (event && event.target) {
        event.target.classList.add('active');
    } else {
        // Fallback: find button by onclick attribute
        const button = Array.from(tabs).find(tab => 
            tab.getAttribute('onclick') && tab.getAttribute('onclick').includes(`'${source}'`)
        );
        if (button) button.classList.add('active');
    }
}

// Toggle recording
async function toggleRecording() {
    const recordBtn = document.getElementById('record-btn');
    const recordedAudio = document.getElementById('recorded-audio');
    const timer = document.getElementById('recording-timer');
    const status = document.getElementById('recording-status');
    
    if (!mediaRecorder || mediaRecorder.state === 'inactive') {
        // Start recording
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];
            
            mediaRecorder.ondataavailable = event => {
                audioChunks.push(event.data);
            };
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                recordedBlob = audioBlob;
                const audioUrl = URL.createObjectURL(audioBlob);
                
                recordedAudio.src = audioUrl;
                recordedAudio.style.display = 'block';
                
                // Stop all tracks
                stream.getTracks().forEach(track => track.stop());
                
                status.textContent = 'Recording complete. You can now transcribe the audio.';
            };
            
            mediaRecorder.start();
            recordingStartTime = Date.now();
            
            // Update UI
            recordBtn.classList.add('recording');
            recordBtn.innerHTML = '<span class="record-icon">⏹</span> Stop Recording';
            status.textContent = 'Recording...';
            timer.style.display = 'block';
            
            // Start timer
            timerInterval = setInterval(updateTimer, 100);
            
        } catch (error) {
            console.error('Error accessing microphone:', error);
            status.textContent = 'Error: Could not access microphone. Please check permissions.';
            status.style.color = '#e74c3c';
        }
    } else {
        // Stop recording
        mediaRecorder.stop();
        clearInterval(timerInterval);
        
        recordBtn.classList.remove('recording');
        recordBtn.innerHTML = '<span class="record-icon">🎤</span> Start Recording';
    }
}

// Update recording timer
function updateTimer() {
    const elapsed = Date.now() - recordingStartTime;
    const seconds = Math.floor(elapsed / 1000);
    const minutes = Math.floor(seconds / 60);
    const displaySeconds = seconds % 60;
    
    document.getElementById('recording-timer').textContent = 
        `${minutes.toString().padStart(2, '0')}:${displaySeconds.toString().padStart(2, '0')}`;
}

// Handle file upload
function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const uploadStatus = document.getElementById('upload-status');
    const uploadedAudio = document.getElementById('uploaded-audio');
    
    // Validate file type
    const validTypes = ['audio/mp3', 'audio/mpeg', 'audio/wav', 'audio/ogg'];
    if (!validTypes.includes(file.type)) {
        uploadStatus.textContent = 'Please select a valid audio file (MP3, WAV, OGG)';
        uploadStatus.className = 'upload-status error';
        return;
    }
    
    // Validate file size (max 500MB)
    if (file.size > 500 * 1024 * 1024) {
        uploadStatus.textContent = 'File too large. Please select a file smaller than 500MB.';
        uploadStatus.className = 'upload-status error';
        return;
    }
    
    uploadedFile = file;
    
    // Create audio URL for preview
    const audioUrl = URL.createObjectURL(file);
    uploadedAudio.src = audioUrl;
    uploadedAudio.style.display = 'block';
    
    uploadStatus.textContent = `File loaded: ${file.name} (${(file.size / 1024 / 1024).toFixed(2)} MB)`;
    uploadStatus.className = 'upload-status success';
    
    // Update upload zone
    const uploadZone = document.querySelector('.upload-zone');
    uploadZone.innerHTML = `
        <div class="upload-icon">✅</div>
        <div class="upload-text">
            <strong>${file.name}</strong><br>
            <small>Click to select a different file</small>
        </div>
    `;
}

// Progress tracking functions
function startProgressTracking(sessionId) {
    currentSessionId = sessionId;
    const progressContainer = document.getElementById('progress-container');
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressContainer.style.display = 'block';
    progressFill.style.width = '0%';
    progressText.textContent = 'Starting transcription...';
    
    progressInterval = setInterval(async () => {
        try {
            const response = await fetch(`/api/progress/${sessionId}`);
            const data = await response.json();
            
            if (response.ok) {
                progressFill.style.width = `${data.progress}%`;
                
                if (data.status === 'creating_segments') {
                    progressText.textContent = `Creating segments... ${Math.round(data.progress)}%`;
                } else if (data.status === 'transcribing') {
                    // Calculate estimated time remaining
                    let timeText = '';
                    if (data.start_time && data.estimated_duration_minutes) {
                        const elapsed = (Date.now() / 1000) - data.start_time;
                        const totalEstimated = data.estimated_duration_minutes * 60;
                        const remaining = Math.max(0, totalEstimated - elapsed);
                        const remainingMinutes = Math.round(remaining / 60);
                        timeText = remainingMinutes > 0 ? ` (~${remainingMinutes}min left)` : '';
                    }
                    
                    progressText.textContent = `Transcribing segment ${data.current_segment}/${data.total_segments}... ${Math.round(data.progress)}%${timeText}`;
                    
                    // Update live transcription
                    if (data.transcriptions && data.transcriptions.length > 0) {
                        document.getElementById('stt-output').textContent = data.transcriptions.join('\n\n');
                    }
                } else if (data.status === 'completed') {
                    progressText.textContent = 'Transcription completed!';
                    progressContainer.style.display = 'none';
                    clearInterval(progressInterval);
                    currentSessionId = null;
                    
                    // Show final transcription and actions
                    const finalTranscription = data.final_transcription || data.transcriptions.join('\n\n');
                    document.getElementById('stt-output').textContent = finalTranscription;
                    document.querySelector('.transcript-actions').style.display = 'flex';
                    
                    // Update command with final stats
                    if (data.segments_processed) {
                        const successRate = data.success_rate || 0;
                        const successfulSegs = data.successful_segments || 0;
                        document.getElementById('stt-command').textContent += `\n# Processing completed: ${successfulSegs}/${data.segments_processed} segments successful (${successRate.toFixed(1)}%)`;
                    }
                    
                    const successRate = data.success_rate || 0;
                    if (successRate >= 80) {
                        showMessage('Long file transcribed successfully!', 'success');
                    } else if (successRate >= 50) {
                        showMessage(`Transcription completed with ${successRate.toFixed(1)}% success rate. Some segments failed.`, 'success');
                    } else {
                        showMessage(`Transcription completed but many segments failed (${successRate.toFixed(1)}% success). Check the results.`, 'error');
                    }
                } else if (data.status === 'error') {
                    progressText.textContent = 'Error occurred during transcription';
                    progressContainer.style.display = 'none';
                    clearInterval(progressInterval);
                    currentSessionId = null;
                    showMessage(`Error: ${data.error}`, 'error');
                }
            }
        } catch (error) {
            console.error('Progress tracking error:', error);
        }
    }, 1000); // Update every second
}

function cancelTranscription() {
    if (currentSessionId) {
        fetch(`/api/cancel/${currentSessionId}`, { method: 'POST' });
        clearInterval(progressInterval);
        document.getElementById('progress-container').style.display = 'none';
        showMessage('Transcription cancelled', 'error');
        currentSessionId = null;
    }
}

function downloadTranscription() {
    const transcription = document.getElementById('stt-output').textContent;
    if (!transcription) return;
    
    const blob = new Blob([transcription], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `transcription_${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function copyTranscription() {
    const transcription = document.getElementById('stt-output').textContent;
    if (!transcription) return;
    
    navigator.clipboard.writeText(transcription).then(() => {
        showMessage('Transcription copied to clipboard!', 'success');
    }).catch(() => {
        showMessage('Failed to copy to clipboard', 'error');
    });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Set default tab
    const defaultTab = document.querySelector('.tab-button.active') || document.querySelector('.tab-button');
    if (defaultTab) {
        showTab('tts', defaultTab);
    }
    
    // Add drag and drop functionality
    const uploadZone = document.querySelector('.upload-zone');
    
    if (uploadZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, preventDefaults, false);
        });
        
        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }
        
        ['dragenter', 'dragover'].forEach(eventName => {
            uploadZone.addEventListener(eventName, () => uploadZone.classList.add('dragover'), false);
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, () => uploadZone.classList.remove('dragover'), false);
        });
        
        uploadZone.addEventListener('drop', handleDrop, false);
        
        function handleDrop(e) {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                document.getElementById('mp3-file-input').files = files;
                handleFileUpload({ target: { files: files } });
            }
        }
    }
});