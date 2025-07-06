#!/usr/bin/env python3
# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "flask",
#     "flask-cors",
# ]
# ///

import subprocess
import tempfile
import os
from pathlib import Path

def segment_audio_file(input_path, segment_duration=300):  # 5 minutes segments
    """
    Segment a long audio file into smaller chunks for processing.
    Returns list of segment file paths.
    """
    segments = []
    
    # Get total duration
    duration_cmd = [
        "ffprobe", "-v", "quiet", 
        "-show_entries", "format=duration", 
        "-of", "csv=p=0", 
        str(input_path)
    ]
    
    duration_result = subprocess.run(duration_cmd, capture_output=True, text=True)
    
    if duration_result.returncode != 0:
        raise Exception("Could not determine audio duration")
    
    total_duration = float(duration_result.stdout.strip())
    num_segments = int(total_duration / segment_duration) + 1
    
    base_name = Path(input_path).stem
    output_dir = Path(input_path).parent
    
    for i in range(num_segments):
        start_time = i * segment_duration
        segment_path = output_dir / f"{base_name}_segment_{i:03d}.wav"
        
        segment_cmd = [
            "ffmpeg", "-i", str(input_path),
            "-ss", str(start_time),
            "-t", str(segment_duration),
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            str(segment_path)
        ]
        
        result = subprocess.run(segment_cmd, capture_output=True, text=True)
        
        if result.returncode == 0 and segment_path.exists():
            segments.append(str(segment_path))
        else:
            print(f"Failed to create segment {i}: {result.stderr}")
    
    return segments

def transcribe_segments(segments, model="kyutai/stt-2.6b-en"):
    """
    Transcribe each segment and combine results.
    """
    full_transcription = []
    
    for i, segment_path in enumerate(segments):
        print(f"Processing segment {i+1}/{len(segments)}...")
        
        cmd = [
            "uv", "run",
            "../../scripts/stt_from_file_pytorch.py",
            "--hf-repo", model,
            segment_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            segment_text = result.stdout.strip()
            full_transcription.append(f"[Segment {i+1}] {segment_text}")
        else:
            full_transcription.append(f"[Segment {i+1}] ERROR: {result.stderr}")
        
        # Clean up segment file
        try:
            os.unlink(segment_path)
        except:
            pass
    
    return "\n\n".join(full_transcription)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python segment_long_audio.py <audio_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    print(f"Processing long audio file: {input_file}")
    
    try:
        segments = segment_audio_file(input_file)
        print(f"Created {len(segments)} segments")
        
        transcription = transcribe_segments(segments)
        print("\n=== FULL TRANSCRIPTION ===")
        print(transcription)
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)