import subprocess
import os
import random
from pathlib import Path

# ==========================================
# WORKFLOW SETTINGS
# ==========================================

STORY_NAME = os.getenv("STORY_NAME", "Bobo Cartoon")

ADD_CAPTIONS = os.getenv(
    "ADD_CAPTIONS", "true"
).lower() == "true"

ADD_MUSIC = os.getenv(
    "ADD_MUSIC", "true"
).lower() == "true"

ADD_SFX = os.getenv(
    "ADD_SFX", "true"
).lower() == "true"

print("Story:", STORY_NAME)
print("Captions:", ADD_CAPTIONS)
print("Music:", ADD_MUSIC)
print("Sound effects:", ADD_SFX)

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

# ======================================
# ADD FUNNY CAPTIONS
# ======================================

if ADD_CAPTIONS:
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

    Path("bobo_cake_reel.mp4").unlink()
    Path("bobo_captioned.mp4").rename("bobo_cake_reel.mp4")

    print("Funny captions added!")
else:
    print("Funny captions skipped.")

# ======================================
# ADD CARTOON SOUND EFFECTS
# ======================================

if ADD_SFX:
    audio_filter = (
        # Pop when Bobo notices the cake - 1.0 sec
        "[1:a]volume=1.20,adelay=1000|1000[pop];"

        # Bite/taste sound - 7.15 sec
        "[2:a]volume=2.00,adelay=7150|7150[bite];"

        # Boing for surprised reaction - 9.4 sec
        "[3:a]volume=1.30,adelay=9400|9400[boing];"

        # Mix the three effects
        "[pop][bite][boing]"
        "amix=inputs=3:duration=longest:dropout_transition=0,"
        "apad=whole_dur=14.13[sfx]"
    )

    subprocess.run([
        "ffmpeg", "-y",

        "-i", "bobo_cake_reel.mp4",
        "-i", "soundreality-pop-sound-423716.mp3",
        "-i", "freesound_community-cartoon-bite-39234.mp3",
        "-i", "universfield-cartoon-spring-boing-140378.mp3",

        "-filter_complex", audio_filter,

        "-map", "0:v",
        "-map", "[sfx]",

        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",

        "-shortest",
        "-movflags", "+faststart",

        "bobo_with_sound.mp4"
    ], check=True)

    Path("bobo_cake_reel.mp4").unlink()
    Path("bobo_with_sound.mp4").rename("bobo_cake_reel.mp4")

    print("Cartoon sound effects added!")
else:
    print("Cartoon sound effects skipped.")


# ======================================
# ADD BACKGROUND MUSIC
# ======================================

if ADD_MUSIC:
    music_filter = (
        "[1:a]atrim=start=0:end=14.13,"
        "asetpts=PTS-STARTPTS,"
        "volume=0.16,"
        "afade=t=in:st=0:d=0.6,"
        "afade=t=out:st=12.6:d=1.53[music];"
        "[0:a][music]"
        "amix=inputs=2:duration=first:"
        "dropout_transition=0:"
        "weights='1 1':normalize=0[audio]"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-i", "bobo_cake_reel.mp4",
        "-i", "alex-morgan-cartoon-bouncy-chase-antics-578472.mp3",
        "-filter_complex", music_filter,
        "-map", "0:v",
        "-map", "[audio]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-t", "14.13",
        "-movflags", "+faststart",
        "bobo_with_music.mp4"
    ], check=True)

    Path("bobo_cake_reel.mp4").unlink()
    Path("bobo_with_music.mp4").rename("bobo_cake_reel.mp4")

    print("Background music added!")
else:
    print("Background music skipped.")
print("======================================")
print("FINAL VISUAL TEST CREATED")
print("60 FPS")
print("NO CROSSFADE")
print("NO SPEED-UP")
print("Output: bobo_cake_reel.mp4")
print("======================================")
