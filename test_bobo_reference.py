
import os
import json
import base64
import urllib.request
import urllib.error
import uuid
import time
from pathlib import Path

API_KEY = os.environ["POLLINATIONS_API_KEY"]

REFERENCE_IMAGE = Path("bobo_reference.jpg.jpg")

if not REFERENCE_IMAGE.exists():
    raise FileNotFoundError(
        f"Reference image missing: {REFERENCE_IMAGE}"
    )

# Five connected scenes for one funny cartoon story
STORY = [
    (
        "scene_01",
        "Bobo finds a beautiful red balloon in a colorful "
        "playground. He looks excited and reaches for it."
    ),
    (
        "scene_02",
        "Bobo holds the red balloon proudly and starts "
        "walking through the playground, smiling happily."
    ),
    (
        "scene_03",
        "A gentle breeze pulls the red balloon upward. "
        "Bobo looks surprised and holds its string tightly."
    ),
    (
        "scene_04",
        "Bobo jumps comically while trying to keep hold "
        "of the red balloon. His expression is very funny."
    ),
    (
        "scene_05",
        "Bobo safely catches the red balloon, waves to "
        "the audience, and celebrates with a happy smile."
    ),
]

CHARACTER_PROMPT = """
Keep the same Bobo bear character as the reference image.
Bobo is a cute brown bear with soft brown fur, round ears,
large expressive eyes, rosy cheeks, a black nose,
and blue denim overalls with white buttons.

Keep the same face, clothing, fur color, and body proportions.
High-quality colorful 3D children's cartoon illustration.
Vertical 2:3 composition. Full body visible.
Bright cheerful playground setting.
Consistent character design throughout the story.
No text, no captions, no watermark.
"""

def form_field(boundary, name, value):
    return (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
        f"{value}\r\n"
    ).encode("utf-8")


def generate_scene(scene_name, description):
    boundary = "----BoboBoundary" + uuid.uuid4().hex

    prompt = (
        CHARACTER_PROMPT
        + "\nSCENE ACTION:\n"
        + description
    )

    body = b""
    body += form_field(boundary, "prompt", prompt)
    body += form_field(boundary, "model", "kontext")
    body += form_field(boundary, "size", "1024x1536")

    image_data = REFERENCE_IMAGE.read_bytes()

    body += (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; '
        'name="image"; filename="bobo_reference.jpg"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode("utf-8")

    body += image_data
    body += b"\r\n"
    body += f"--{boundary}--\r\n".encode("utf-8")

    request = urllib.request.Request(
        "https://gen.pollinations.ai/v1/images/edits",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": (
                f"multipart/form-data; boundary={boundary}"
            ),
        },
    )

    print(f"Generating {scene_name}...", flush=True)

    with urllib.request.urlopen(
        request, timeout=300
    ) as response:
        result = json.loads(response.read().decode("utf-8"))

    item = result["data"][0]

    if item.get("b64_json"):
        output = base64.b64decode(item["b64_json"])
    elif item.get("url"):
        with urllib.request.urlopen(
            item["url"], timeout=180
        ) as response:
            output = response.read()
    else:
        raise ValueError(
            f"No image returned for {scene_name}"
        )

    output_path = Path(f"{scene_name}.png")
    output_path.write_bytes(output)

    print(
        f"SUCCESS: {output_path} created",
        flush=True
    )


def main():
    print("Starting Bobo's Balloon Adventure")

    for index, (scene_name, description) in enumerate(STORY):
        for attempt in range(1, 4):
            try:
                generate_scene(scene_name, description)
                break
            except Exception as error:
                print(
                    f"{scene_name}, attempt {attempt}: "
                    f"{type(error).__name__}: {error}",
                    flush=True
                )
                if attempt == 3:
                    raise
                time.sleep(10)

        if index < len(STORY) - 1:
            time.sleep(3)

    print("All five Bobo story scenes generated!")


if __name__ == "__main__":
    main()
