import subprocess
from pathlib import Path

print("======================================")
print("   BOBO 60 FPS SMOOTH CARTOON BOT")
print("======================================")

clips = [
    "Bobo 1.mp4",
    "new bobo clip 2.mp4",
    "new bobo clip 3.mp4",
    "new bobo clip 4.mp4"
]

for clip in clips:
    if not Path(clip).exists():
        raise FileNotFoundError(f"Missing video: {clip}")

normalized = []

# Normalize clips WITHOUT artificially forcing 30 FPS first
for i, clip in enumerate(clips, start=1):
    output = f"normalized_{i}.mp4"

    subprocess.run([
        "ffmpeg", "-y",
        "-i", clip,
        "-an",
        "-vf",
        "scale=720:1280:force_original_aspect_ratio=decrease,"
        "pad=720:1280:(ow-iw)/2:(oh-ih)/2,"
        "format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        output
    ], check=True)

    normalized.append(output)

print("Clips normalized.")

# Join the continuous clips
with open("clips.txt", "w") as f:
    for clip in normalized:
        f.write(f"file '{clip}'\n")

subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", "clips.txt",

    # Create new intermediate motion frames
    "-vf",
    "minterpolate=fps=60:"
    "mi_mode=mci:"
    "mc_mode=aobmc:"
    "me_mode=bilat:"
    "me=epzs:"
    "scd=fdiff",

    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "20",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "bobo_cake_reel.mp4"
], check=True)

print("======================================")
print("60 FPS MOTION-INTERPOLATED VIDEO READY")
print("Output: bobo_cake_reel.mp4")
print("======================================")
