
import subprocess
from pathlib import Path

OUTPUT = "bobo_story_video.mp4"
SCENE_DURATION = 3
FPS = 30
WIDTH = 720
HEIGHT = 1280

scenes = [Path(f"bobo_scene_{i}.png") for i in range(1, 6)]

for scene in scenes:
    if not scene.is_file():
        raise FileNotFoundError(f"Missing image: {scene}")

clips = []

for i, scene in enumerate(scenes, start=1):
    clip = f"bobo_clip_{i}.mp4"

    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},"
        f"zoompan=z='min(zoom+0.0005,1.05)':"
        f"d={SCENE_DURATION * FPS}:"
        f"s={WIDTH}x{HEIGHT}:fps={FPS},"
        "format=yuv420p"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-loop", "1",
        "-i", str(scene),
        "-vf", vf,
        "-frames:v", str(SCENE_DURATION * FPS),
        "-an",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-pix_fmt", "yuv420p",
        clip
    ], check=True)

    clips.append(clip)
    print(f"Created clip {i}/5")

with open("bobo_clips.txt", "w") as f:
    for clip in clips:
        f.write(f"file '{clip}'\n")

subprocess.run([
    "ffmpeg", "-y",
    "-f", "concat",
    "-safe", "0",
    "-i", "bobo_clips.txt",
    "-c", "copy",
    "-movflags", "+faststart",
    OUTPUT
], check=True)

print(f"SUCCESS: {OUTPUT} created")
