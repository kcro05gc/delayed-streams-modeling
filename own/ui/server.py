# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "flask",
#     "flask-cors",
# ]
# ///

import os
import json
import subprocess
import tempfile
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, send_file, send_from_directory, Response
from flask_cors import CORS
import time
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Console output
        logging.FileHandler('stt_debug.log')  # File output
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='.')
CORS(app)

# Directory to store generated audio files
AUDIO_OUTPUT_DIR = Path("generated_audio")
AUDIO_OUTPUT_DIR.mkdir(exist_ok=True)

# Global storage for active transcription sessions
active_sessions = {}

def process_long_audio_file(upload_path, model, duration, session_id):
    """Process long audio files by segmenting them into smaller chunks with progress updates."""
    logger.info(f"=== STARTING LONG AUDIO PROCESSING ===")
    logger.info(f"Session ID: {session_id}")
    logger.info(f"Upload path: {upload_path}")
    logger.info(f"Model: {model}")
    logger.info(f"Duration: {duration} seconds ({duration/60:.1f} minutes)")
    
    try:
        # Verify file exists
        if not upload_path.exists():
            logger.error(f"Upload file does not exist: {upload_path}")
            if session_id in active_sessions:
                active_sessions[session_id]['status'] = 'error'
                active_sessions[session_id]['error'] = f'Upload file not found: {upload_path}'
            return
        
        # Log file details
        file_size = upload_path.stat().st_size
        logger.info(f"File size: {file_size} bytes ({file_size/1024/1024:.1f} MB)")
        logger.info(f"File exists and is accessible: {upload_path}")
            
        segment_duration = 300  # 5 minutes per segment
        num_segments = int(duration / segment_duration) + 1
        segments = []
        transcriptions = []
        
        # Calculate estimated processing time (roughly 1:3 ratio - 1 min audio = 3 min processing)
        estimated_minutes = int(duration / 60 * 3)  # Rough estimation
        
        # Initialize session
        active_sessions[session_id] = {
            'status': 'creating_segments',
            'progress': 0,
            'current_segment': 0,
            'total_segments': num_segments,
            'transcriptions': [],
            'estimated_duration_minutes': estimated_minutes,
            'start_time': time.time()
        }
        
        logger.info(f"Creating {num_segments} segments of {segment_duration} seconds each...")
        
        # Create segments
        for i in range(num_segments):
            if session_id not in active_sessions:  # Check if cancelled
                logger.warning(f"Session {session_id} was cancelled during segmentation")
                break
                
            start_time = i * segment_duration
            segment_id = str(uuid.uuid4())
            segment_path = AUDIO_OUTPUT_DIR / f"segment_{segment_id}.wav"
            
            logger.debug(f"Creating segment {i+1}/{num_segments}: {start_time}s-{start_time+segment_duration}s -> {segment_path}")
            
            segment_cmd = [
                "ffmpeg", "-i", str(upload_path),
                "-ss", str(start_time),
                "-t", str(segment_duration),
                "-acodec", "pcm_s16le",
                "-ar", "16000",
                str(segment_path)
            ]
            
            logger.debug(f"Running ffmpeg command: {' '.join(segment_cmd)}")
            result = subprocess.run(segment_cmd, capture_output=True, text=True)
            
            if result.returncode == 0 and segment_path.exists():
                segments.append(segment_path)
                segment_size = segment_path.stat().st_size
                logger.info(f"✅ Created segment {i+1}/{num_segments}: {segment_size} bytes")
            else:
                logger.error(f"❌ Failed to create segment {i+1}/{num_segments}")
                logger.error(f"FFmpeg return code: {result.returncode}")
                logger.error(f"FFmpeg stderr: {result.stderr}")
                logger.error(f"FFmpeg stdout: {result.stdout}")
            
            # Update progress
            if session_id in active_sessions:
                active_sessions[session_id]['progress'] = (i + 1) / num_segments * 30  # 30% for segmentation
        
        # Update status to transcribing
        if session_id in active_sessions:
            active_sessions[session_id]['status'] = 'transcribing'
        
        logger.info(f"Starting transcription of {len(segments)} segments...")
        
        # Transcribe each segment
        for i, segment_path in enumerate(segments):
            if session_id not in active_sessions:  # Check if cancelled
                logger.warning(f"Session {session_id} was cancelled during transcription")
                break
                
            logger.info(f"=== TRANSCRIBING SEGMENT {i+1}/{len(segments)} ===")
            logger.info(f"Segment path: {segment_path}")
            
            # Verify segment file exists and has content
            if not segment_path.exists():
                logger.error(f"Segment file does not exist: {segment_path}")
                continue
                
            segment_size = segment_path.stat().st_size
            logger.info(f"Segment file size: {segment_size} bytes")
            
            if segment_size == 0:
                logger.error(f"Segment file is empty: {segment_path}")
                continue
            
            active_sessions[session_id]['current_segment'] = i + 1
            
            # Try transcription with timeout and retry logic
            max_retries = 2
            segment_success = False
            start_minutes = (i * segment_duration) // 60
            start_seconds = (i * segment_duration) % 60
            
            for retry in range(max_retries):
                try:
                    # Calculate the time offset for this segment (in seconds)
                    segment_offset_seconds = i * segment_duration
                    
                    cmd = [
                        "uv", "run",
                        "../../scripts/stt_from_file_pytorch.py",
                        "--hf-repo", model,
                        "--offset-seconds", str(segment_offset_seconds),
                        str(segment_path)
                    ]
                    
                    logger.info(f"🔄 Attempt {retry + 1}/{max_retries} for segment {i+1}")
                    logger.debug(f"STT command: {' '.join(cmd)}")
                    logger.debug(f"Working directory: {os.path.dirname(__file__)}")
                    
                    # Check if script exists
                    script_path = Path("../../scripts/stt_from_file_pytorch.py")
                    logger.debug(f"Script exists: {script_path.exists()}")
                    
                    # Add timeout to prevent hanging
                    start_time_transcription = time.time()
                    result = subprocess.run(
                        cmd, 
                        capture_output=True, 
                        text=True, 
                        cwd=os.path.dirname(__file__),
                        timeout=300  # 5 minutes timeout per segment
                    )
                    end_time_transcription = time.time()
                    
                    logger.info(f"STT command completed in {end_time_transcription - start_time_transcription:.1f} seconds")
                    logger.info(f"Return code: {result.returncode}")
                    
                    if result.returncode == 0:
                        segment_text = result.stdout.strip()
                        logger.info(f"✅ Segment {i+1} transcribed successfully: {len(segment_text)} characters")
                        logger.debug(f"Transcription preview: {segment_text[:100]}...")
                        
                        transcription_part = f"[{start_minutes:02d}:{start_seconds:02d}] {segment_text}"
                        transcriptions.append(transcription_part)
                        
                        # Add to live transcriptions
                        if session_id in active_sessions:
                            active_sessions[session_id]['transcriptions'].append(transcription_part)
                        
                        segment_success = True
                        
                        # Update progress immediately after successful segment
                        if session_id in active_sessions:
                            segments_completed = i + 1
                            progress = 30 + (segments_completed / len(segments) * 70)
                            active_sessions[session_id]['progress'] = progress
                            logger.info(f"✅ Updated progress to {progress:.1f}% after segment {segments_completed}")
                        
                        break  # Success, exit retry loop
                        
                    else:
                        logger.error(f"❌ Segment {i+1} failed on attempt {retry + 1}")
                        logger.error(f"Return code: {result.returncode}")
                        logger.error(f"STDERR ({len(result.stderr)} chars): {result.stderr}")
                        logger.error(f"STDOUT ({len(result.stdout)} chars): {result.stdout}")
                        
                        if retry == max_retries - 1:  # Last retry failed
                            error_part = f"[{start_minutes:02d}:{start_seconds:02d}] SEGMENT {i+1} FAILED AFTER {max_retries} ATTEMPTS"
                            transcriptions.append(error_part)
                            if session_id in active_sessions:
                                active_sessions[session_id]['transcriptions'].append(error_part)
                                # Update progress even for failed segments
                                segments_processed = i + 1
                                progress = 30 + (segments_processed / len(segments) * 70)
                                active_sessions[session_id]['progress'] = progress
                
                except subprocess.TimeoutExpired:
                    logger.error(f"⏱️ Segment {i+1} TIMED OUT on attempt {retry + 1} (>5min)")
                    if retry == max_retries - 1:  # Last retry timed out
                        timeout_part = f"[{start_minutes:02d}:{start_seconds:02d}] SEGMENT {i+1} TIMED OUT (>5min)"
                        transcriptions.append(timeout_part)
                        if session_id in active_sessions:
                            active_sessions[session_id]['transcriptions'].append(timeout_part)
                            # Update progress even for timed out segments
                            segments_processed = i + 1
                            progress = 30 + (segments_processed / len(segments) * 70)
                            active_sessions[session_id]['progress'] = progress
                
                except Exception as e:
                    logger.error(f"💥 Unexpected error for segment {i+1} on attempt {retry + 1}: {e}")
                    logger.exception("Full exception details:")
                    if retry == max_retries - 1:  # Last retry had error
                        error_part = f"[{start_minutes:02d}:{start_seconds:02d}] SEGMENT {i+1} ERROR: {str(e)[:100]}"
                        transcriptions.append(error_part)
                        if session_id in active_sessions:
                            active_sessions[session_id]['transcriptions'].append(error_part)
                            # Update progress even for error segments
                            segments_processed = i + 1
                            progress = 30 + (segments_processed / len(segments) * 70)
                            active_sessions[session_id]['progress'] = progress
            
            # Progress is now updated immediately after each successful segment
            
            # Clean up segment file
            try:
                segment_path.unlink()
            except:
                pass
        
        # Calculate success statistics
        successful_segments = sum(1 for t in transcriptions if not ('FAILED' in t or 'TIMED OUT' in t or 'ERROR' in t))
        total_segments = len(transcriptions)
        success_rate = (successful_segments / total_segments * 100) if total_segments > 0 else 0
        
        # Mark as completed
        if session_id in active_sessions:
            active_sessions[session_id]['status'] = 'completed'
            active_sessions[session_id]['progress'] = 100
            active_sessions[session_id]['success_rate'] = success_rate
            active_sessions[session_id]['successful_segments'] = successful_segments
        
        # Combine all transcriptions
        full_transcription = "\n\n".join(transcriptions)
        
        # Don't return jsonify from thread - just update session
        if session_id in active_sessions:
            active_sessions[session_id]['final_transcription'] = full_transcription
            active_sessions[session_id]['segments_processed'] = len(segments)
            active_sessions[session_id]['total_duration_minutes'] = duration/60
        
        # Clean up the permanent processing file
        try:
            upload_path.unlink()
        except:
            pass
        
    except Exception as e:
        print(f"Error in process_long_audio_file: {e}")
        if session_id in active_sessions:
            active_sessions[session_id]['status'] = 'error'
            active_sessions[session_id]['error'] = str(e)

# Serve the main UI
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# Serve static files
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

# TTS endpoint
@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    try:
        data = request.json
        text = data.get('text', '').strip()
        
        if not text:
            return jsonify({'error': 'No text provided'}), 400
        
        # Generate unique filename
        audio_id = str(uuid.uuid4())
        output_filename = f"tts_{audio_id}.wav"
        output_path = AUDIO_OUTPUT_DIR / output_filename
        
        # Create temporary input file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as tmp_file:
            tmp_file.write(text)
            tmp_file_path = tmp_file.name
        
        try:
            # Run TTS command
            cmd = [
                "uv", "run", 
                "../../scripts/tts_pytorch.py", 
                tmp_file_path, 
                str(output_path)
            ]
            
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                return jsonify({'error': f'TTS failed: {error_msg}'}), 500
            
            # Check if file was created
            if not output_path.exists():
                return jsonify({'error': 'Audio file was not generated'}), 500
            
            return jsonify({
                'success': True,
                'audio_url': f'/audio/{output_filename}',
                'audio_id': audio_id
            })
            
        finally:
            # Clean up temp file
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# STT endpoint for uploaded audio files
@app.route('/api/stt-upload', methods=['POST'])
def speech_to_text_upload():
    try:
        if 'audio' not in request.files:
            return jsonify({'error': 'No audio file provided'}), 400
        
        audio_file = request.files['audio']
        model = request.form.get('model', 'kyutai/stt-2.6b-en')
        
        # Save uploaded file temporarily
        upload_id = str(uuid.uuid4())
        file_extension = audio_file.filename.split('.')[-1].lower() if '.' in audio_file.filename else 'audio'
        upload_filename = f"upload_{upload_id}.{file_extension}"
        upload_path = AUDIO_OUTPUT_DIR / upload_filename
        
        audio_file.save(str(upload_path))
        
        wav_path = None  # Initialize to avoid UnboundLocalError
        try:
            # Check audio duration first
            duration_cmd = [
                "ffprobe", "-v", "quiet", 
                "-show_entries", "format=duration", 
                "-of", "csv=p=0", 
                str(upload_path)
            ]
            
            duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
            
            if duration_result.returncode == 0:
                try:
                    duration = float(duration_result.stdout.strip())
                    print(f"Audio duration: {duration:.2f} seconds")
                    
                    # Always use segmentation for files longer than 5 minutes to avoid memory issues
                    if duration > 300:
                        session_id = str(uuid.uuid4())
                        print(f"File detected ({duration/60:.1f} minutes), processing in segments...")
                        
                        # Copy the uploaded file to a permanent location for background processing
                        permanent_path = AUDIO_OUTPUT_DIR / f"processing_{session_id}_{upload_filename}"
                        import shutil
                        shutil.copy2(upload_path, permanent_path)
                        
                        # Start background processing
                        import threading
                        thread = threading.Thread(
                            target=process_long_audio_file,
                            args=(permanent_path, model, duration, session_id)
                        )
                        thread.start()
                        
                        return jsonify({
                            'success': True,
                            'use_streaming': True,
                            'session_id': session_id,
                            'audio_duration_minutes': duration/60,
                            'estimated_processing_minutes': int(duration / 60 * 3),
                            'num_segments': int(duration / 300) + 1
                        })
                        
                except ValueError:
                    print("Could not determine audio duration, proceeding anyway")
            
            # Convert to wav using ffmpeg with duration limit
            wav_filename = f"upload_{upload_id}.wav"
            wav_path = AUDIO_OUTPUT_DIR / wav_filename
            
            convert_cmd = [
                "ffmpeg", "-i", str(upload_path), 
                "-acodec", "pcm_s16le", 
                "-ar", "16000",
                str(wav_path)
            ]
            
            convert_result = subprocess.run(convert_cmd, capture_output=True, text=True)
            
            if convert_result.returncode != 0:
                return jsonify({'error': f'Audio conversion failed: {convert_result.stderr}'}), 500
            
            # Run STT command
            cmd = [
                "uv", "run",
                "../../scripts/stt_from_file_pytorch.py",
                "--hf-repo", model,
                str(wav_path)
            ]
            
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__))
            
            if result.returncode != 0:
                error_msg = result.stderr if result.stderr else result.stdout
                return jsonify({'error': f'STT failed: {error_msg}'}), 500
            
            # Parse the output to extract transcription
            output_lines = result.stdout.strip().split('\n')
            transcription = '\n'.join(output_lines)
            
            return jsonify({
                'success': True,
                'transcription': transcription
            })
            
        finally:
            # Clean up temporary files
            if upload_path.exists():
                upload_path.unlink()
            if wav_path and wav_path.exists():
                wav_path.unlink()
                
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# STT endpoint
@app.route('/api/stt', methods=['POST'])
def speech_to_text():
    try:
        data = request.json
        audio_file = data.get('audio_file', '')
        model = data.get('model', 'kyutai/stt-2.6b-en')
        
        if not audio_file:
            return jsonify({'error': 'No audio file specified'}), 400
        
        # Construct full path to audio file
        audio_path = f"../../{audio_file}"
        
        # Run STT command
        cmd = [
            "uv", "run",
            "../../scripts/stt_from_file_pytorch.py",
            "--hf-repo", model,
            audio_path
        ]
        
        print(f"Running command: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout
            return jsonify({'error': f'STT failed: {error_msg}'}), 500
        
        # Parse the output to extract transcription
        output_lines = result.stdout.strip().split('\n')
        transcription = '\n'.join(output_lines)
        
        return jsonify({
            'success': True,
            'transcription': transcription
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Serve generated audio files
@app.route('/audio/<filename>')
def serve_audio(filename):
    try:
        return send_file(
            AUDIO_OUTPUT_DIR / filename,
            mimetype='audio/wav',
            as_attachment=False
        )
    except FileNotFoundError:
        return jsonify({'error': 'Audio file not found'}), 404

# Load test file content
@app.route('/api/test-file/<filename>')
def get_test_file(filename):
    try:
        test_file_path = Path("../text_test") / filename
        if not test_file_path.exists():
            return jsonify({'error': 'Test file not found'}), 404
        
        with open(test_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        return jsonify({'content': content})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Clean up old audio files (optional)
@app.route('/api/cleanup', methods=['POST'])
def cleanup_audio():
    try:
        files_deleted = 0
        for audio_file in AUDIO_OUTPUT_DIR.glob("*.wav"):
            audio_file.unlink()
            files_deleted += 1
        
        return jsonify({
            'success': True,
            'files_deleted': files_deleted
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Progress endpoint
@app.route('/api/progress/<session_id>')
def get_progress(session_id):
    if session_id not in active_sessions:
        return jsonify({'error': 'Session not found'}), 404
    
    session = active_sessions[session_id]
    return jsonify(session)

# Cancel transcription
@app.route('/api/cancel/<session_id>', methods=['POST'])
def cancel_transcription(session_id):
    if session_id in active_sessions:
        del active_sessions[session_id]
        return jsonify({'success': True, 'message': 'Transcription cancelled'})
    return jsonify({'error': 'Session not found'}), 404

if __name__ == '__main__':
    print("Starting DSM UI Server...")
    print(f"Audio files will be saved to: {AUDIO_OUTPUT_DIR.absolute()}")
    print("Access the UI at: http://localhost:8888")
    app.run(host='0.0.0.0', port=8888, debug=True)