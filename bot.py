import subprocess
from pathlib import Path

print("======================================")
print("   BOBO IMPROVED PACING BOT")
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

# STEP 1: Normalize and join the four continuous clips
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
        output
    ], check=True)

    normalized.append(output)

with open("clips.txt", "w") as f:
    for clip in normalized:
        f.write(f"file '{clip}'\n")

subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", "clips.txt",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-pix_fmt", "yuv420p",
    "joined.mp4"
], check=True)

# STEP 2:
# 0–7 sec       = normal
# 7–13 sec      = 25% faster
# 13 sec–end    = normal
#
# This targets the repetitive cake-eating section.

filter_graph = (
    "[0:v]split=3[a][b][c];"
    "[a]trim=start=0:end=7,setpts=PTS-STARTPTS[first];"
    "[b]trim=start=7:end=13,setpts=(PTS-STARTPTS)/1.25[middle];"
    "[c]trim=start=13,setpts=PTS-STARTPTS[last];"
    "[first][middle][last]concat=n=3:v=1:a=0[paced];"
    "[paced]minterpolate=fps=60:"
    "mi_mode=mci:"
    "mc_mode=aobmc:"
    "me_mode=bilat:"
    "me=epzs:"
    "scd=fdiff[out]"
)

subprocess.run([
    "ffmpeg", "-y",
    "-i", "joined.mp4",
    "-filter_complex", filter_graph,
    "-map", "[out]",
    "-c:v", "libx264",
    "-preset", "veryfast",
    "-crf", "20",
    "-pix_fmt", "yuv420p",
    "-movflags", "+faststart",
    "bobo_cake_reel.mp4"
], check=True)

print("======================================")
print("IMPROVED-PACING VIDEO CREATED")
print("Cake section accelerated by 25%")
print("Output: bobo_cake_reel.mp4")
print("======================================")
