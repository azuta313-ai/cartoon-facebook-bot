import subprocess
from pathlib import Path

print("======================================")
print("   BOBO FINAL VISUAL TEST")
print("======================================")

clips = [
    "Bobo 1.mp4",
    "new bobo clip 2.mp4",
    "new bobo clip 3.mp4",
    "new bobo clip 4.mp4"
]

# Check files
for clip in clips:
    if not Path(clip).exists():
        raise FileNotFoundError(f"Missing video: {clip}")

# Normalize clips
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
        "format=yuv420p",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        output
    ], check=True)

    normalized.append(output)

print("Clips normalized.")

# Create list for direct joining
with open("clips.txt", "w") as f:
    for clip in normalized:
        f.write(f"file '{clip}'\n")

# Join clips directly
subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", "clips.txt",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "20",
    "-pix_fmt", "yuv420p",
    "joined.mp4"
], check=True)

print("Clips joined.")

# Smooth motion to 60 FPS
subprocess.run([
    "ffmpeg", "-y",
    "-i", "joined.mp4",
    "-vf",
    "minterpolate=fps=60:"
    "mi_mode=mci:"
    "mc_mode=aobmc:"
    "me_mode=bilat:"
    "me=epzs:"
    "vsbmc=1:"
    "scd=fdiff",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "20",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "bobo_cake_reel.mp4"
], check=True)
# Add timed funny captions
caption_filter = (
    "drawtext=text='OOOH... CAKE!':"
    "fontsize=36:fontcolor=white:"
    "box=1:boxcolor=black@0.55:boxborderw=8:"
    "x=(w-text_w)/2:y=h-text_h-120:"
    "enable='between(t,0.5,2.8)',"

    "drawtext=text='JUST ONE TASTE...':"
    "fontsize=34:fontcolor=white:"
    "box=1:boxcolor=black@0.55:boxborderw=8:"
    "x=(w-text_w)/2:y=h-text_h-120:"
    "enable='between(t,3.8,6.2)',"

    "drawtext=text='YUMMY!':"
    "fontsize=36:fontcolor=white:"
    "box=1:boxcolor=black@0.55:boxborderw=8:"
    "x=(w-text_w)/2:y=h-text_h-120:"
    "enable='between(t,6.8,8.8)',"

    "drawtext=text='UH-OH!':"
    "fontsize=38:fontcolor=white:"
    "box=1:boxcolor=black@0.55:boxborderw=8:"
    "x=(w-text_w)/2:y=h-text_h-120:"
    "enable='between(t,9.0,10.8)',"

    "drawtext=text='NO ONE SAW THAT!':"
    "fontsize=34:fontcolor=white:"
    "box=1:boxcolor=black@0.55:boxborderw=8:"
    "x=(w-text_w)/2:y=h-text_h-120:"
    "enable='between(t,11.0,13.5)'"
)

subprocess.run([
    "ffmpeg", "-y",
    "-i", "bobo_cake_reel.mp4",
    "-vf", caption_filter,
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "20",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "bobo_captioned.mp4"
], check=True)

# Replace the non-captioned output with the captioned version
Path("bobo_cake_reel.mp4").unlink()
Path("bobo_captioned.mp4").rename("bobo_cake_reel.mp4")

print("Funny captions added!")
print("======================================")
print("FINAL VISUAL TEST CREATED")
print("60 FPS")
print("NO CROSSFADE")
print("NO SPEED-UP")
print("Output: bobo_cake_reel.mp4")
print("======================================")
