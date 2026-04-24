#!/usr/local/bin/python3
"""Download Ring event video (fast, partial) and extract first frame."""
import sys
import subprocess
import os

DOWNLOAD_TIMEOUT = 5  # seconds — enough for first GOP in typical Ring MP4

def download_with_timeout(url, output_path):
    """Download video with a short timeout. Ring MP4s have first frame early."""
    cmd = [
        "curl", "-s", "-L", "-o", output_path,
        "--max-time", str(DOWNLOAD_TIMEOUT),
        "--connect-timeout", "5",
        "-H", "Accept: */*",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=DOWNLOAD_TIMEOUT + 2)
        # curl exits 28 on timeout — that's OK if we got enough data
        if result.returncode not in (0, 28):
            print(f"curl error {result.returncode}: {result.stderr}", file=sys.stderr)
            return False

        size = os.path.getsize(output_path)
        if size == 0:
            print("ERROR: Downloaded 0 bytes", file=sys.stderr)
            return False

        print(f"Downloaded {size} bytes (curl exit: {result.returncode})")
        return True
    except subprocess.TimeoutExpired:
        print("ERROR: curl subprocess timed out", file=sys.stderr)
        return False

def extract_frame(video_path, output_path):
    """Extract first frame with ffmpeg, tolerant of incomplete files."""
    cmd = [
        "ffmpeg", "-y",
        "-fflags", "+genpts+discardcorrupt",
        "-err_detect", "ignore_err",
        "-i", video_path,
        "-ss", "00:00:00",
        "-vframes", "1",
        "-q:v", "2",
        output_path
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print(f"Frame saved to {output_path}")
            return True
        else:
            # Check if file was created anyway (ffmpeg sometimes writes despite errors)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 100:
                print(f"Frame saved despite warnings ({os.path.getsize(output_path)} bytes)")
                return True
            print(f"ffmpeg stderr: {result.stderr[:500]}", file=sys.stderr)
            return False
    except subprocess.TimeoutExpired:
        print("ERROR: ffmpeg timed out", file=sys.stderr)
        return False

def main():
    if len(sys.argv) < 3:
        print("Usage: ring_video_frame.py <video_url> <output_path>", file=sys.stderr)
        sys.exit(1)

    video_url = sys.argv[1]
    output_path = sys.argv[2]
    temp_video = "/tmp/ring_event_tmp.mp4"

    if not download_with_timeout(video_url, temp_video):
        sys.exit(1)

    if not extract_frame(temp_video, output_path):
        sys.exit(1)

    # Cleanup
    try:
        os.remove(temp_video)
    except:
        pass

    sys.exit(0)

if __name__ == "__main__":
    main()
