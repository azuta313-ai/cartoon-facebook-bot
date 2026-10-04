import subprocess
from pathlib import Path

print("======================================")
print("   BOBO CONTINUOUS CARTOON BOT")
print("======================================")

clips = [
    "Bobo 1.mp4",
    "Bobo 2.mp4",
    "Bobo 3.mp4",
    "Bobo 4.mp4"
]

# Check that every clip exists
for clip in clips:
    if not Path(clip).exists():
        raise FileNotFoundError(f"Missing video: {clip}")

# Normalize all clips so FFmpeg receives identical video properties
normalized = []

for i, clip in enumerate(clips, start=1):
    output = f"normalized_{i}.mp4"

    subprocess.run([
        "ffmpeg", "-y",
        "-i", clip,
        "-an",
        "-vf",
        "scale=720:1280:force_original_aspect_ratio=decrease,"
        "pad=720:1280:(ow-iw)/2:(oh-ih)/2,"
        "fps=30,format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-r", "30",
        output
    ], check=True)

    normalized.append(output)

print("All clips normalized.")

# Create concat list
with open("clips.txt", "w") as f:
    for clip in normalized:
        f.write(f"file '{clip}'\n")

# Join clips directly — NO fade or transition
subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", "clips.txt",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-pix_fmt", "yuv420p",
    "-r", "30",
    "-movflags", "+faststart",
    "bobo_cake_reel.mp4"
], check=True)

print("======================================")
print("CONTINUOUS VIDEO CREATED!")
print("NO CROSSFADE TRANSITIONS")
print("Output: bobo_cake_reel.mp4")
print("======================================")
