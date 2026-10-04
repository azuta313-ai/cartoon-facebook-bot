import subprocess
from pathlib import Path

print("======================================")
print("   BOBO SMOOTH CARTOON VIDEO BOT")
print("======================================")

clips = [
    "Bobo 1.mp4",
    "Bobo 2.mp4",
    "Bobo 3.mp4",
    "Bobo 4.mp4"
]

# Check files
for clip in clips:
    if not Path(clip).exists():
        raise FileNotFoundError(f"Missing video: {clip}")

# Normalize every clip first.
# This gives all clips the same resolution, FPS and pixel format.
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
        output
    ], check=True)

print("All clips normalized.")

# Each source clip is approximately 3.5 seconds.
# Blend neighboring clips for 0.4 seconds.
transition = 0.4

filter_complex = (
    "[0:v][1:v]"
    "xfade=transition=fade:duration=0.4:offset=3.1[v01];"
    
    "[v01][2:v]"
    "xfade=transition=fade:duration=0.4:offset=6.2[v012];"
    
    "[v012][3:v]"
    "xfade=transition=fade:duration=0.4:offset=9.3[vout]"
)

subprocess.run([
    "ffmpeg", "-y",
    "-i", "normalized_1.mp4",
    "-i", "normalized_2.mp4",
    "-i", "normalized_3.mp4",
    "-i", "normalized_4.mp4",
    "-filter_complex", filter_complex,
    "-map", "[vout]",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "bobo_cake_reel.mp4"
], check=True)

print("======================================")
print("SMOOTH VIDEO CREATED SUCCESSFULLY!")
print("Output: bobo_cake_reel.mp4")
print("======================================")
