import subprocess
from pathlib import Path

print("======================================")
print("       BOBO CARTOON VIDEO BOT")
print("======================================")

clips = [
    "bobo_01.mp4",
    "bobo_02.mp4",
    "bobo_03.mp4",
    "bobo_04.mp4"
]

# Check that all clips exist
for clip in clips:
    if not Path(clip).exists():
        raise FileNotFoundError(f"Missing video: {clip}")

# Create FFmpeg concat file
with open("clips.txt", "w") as f:
    for clip in clips:
        f.write(f"file '{clip}'\n")

# Combine the clips
subprocess.run([
    "ffmpeg",
    "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", "clips.txt",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "bobo_cake_reel.mp4"
], check=True)

print()
print("VIDEO CREATED SUCCESSFULLY!")
print("Output: bobo_cake_reel.mp4")
