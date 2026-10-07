import os
import json
import base64
import urllib.request
import uuid
import time

API_KEY = os.environ["POLLINATIONS_API_KEY"]
REFERENCE = "bobo_reference.jpg"

scenes = [
    """
    Keep the exact same Bobo bear character from the reference image:
    same brown fur, face, large reddish eyes, pink cheeks, black nose,
    blue denim overalls and body proportions.

    Bobo is walking happily through a colorful playground.
    He suddenly notices a beautiful red balloon nearby.
    Bobo looks curious and excited.
    Full body visible, high-quality 3D children's cartoon,
    vertical composition, bright cheerful daylight.
    No text, no watermark.
    """,

    """
    Keep the exact same Bobo bear character from the reference image:
    same brown fur, face, large reddish eyes, pink cheeks, black nose,
    blue denim overalls and body proportions.

    Bobo is happily holding a bright red balloon by its string
    in the colorful playground. He has a big joyful smile.
    Full body visible, high-quality 3D children's cartoon,
    vertical composition, bright cheerful daylight.
    No text, no watermark.
    """,

    """
    Keep the exact same Bobo bear character from the reference image:
    same brown fur, face, large reddish eyes, pink cheeks, black nose,
    blue denim overalls and body proportions.

    A strong playful gust of wind pulls the red balloon away
    from Bobo. Bobo reaches toward it with a surprised funny expression.
    The balloon is floating upward and away.
    Colorful playground, full body visible,
    high-quality 3D children's cartoon, vertical composition.
    No text, no watermark.
    """,

    """
    Keep the exact same Bobo bear character from the reference image:
    same brown fur, face, large reddish eyes, pink cheeks, black nose,
    blue denim overalls and body proportions.

    Bobo runs through the colorful playground chasing his red balloon.
    His arms and legs show energetic running movement.
    The red balloon floats ahead of him.
    Bobo looks determined but funny.
    Full body visible, high-quality 3D children's cartoon,
    vertical composition, bright daylight.
    No text, no watermark.
    """,

    """
    Keep the exact same Bobo bear character from the reference image:
    same brown fur, face, large reddish eyes, pink cheeks, black nose,
    blue denim overalls and body proportions.

    Bobo has successfully caught the red balloon.
    He holds it proudly and jumps happily in celebration
    in the colorful playground.
    Big joyful smile, happy ending.
    Full body visible, high-quality 3D children's cartoon,
    vertical composition, bright cheerful daylight.
    No text, no watermark.
    """
]


def generate_scene(prompt, output_file):

    boundary = "----BoboBoundary" + uuid.uuid4().hex

    def field(name, value):
        return (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n"
        ).encode()

    body = b""
    body += field("prompt", prompt)
    body += field("model", "kontext")
    body += field("size", "1024x1536")

    with open(REFERENCE, "rb") as f:
        image_data = f.read()

    body += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; '
        f'filename="{REFERENCE}"\r\n'
        "Content-Type: image/jpeg\r\n\r\n"
    ).encode()

    body += image_data
    body += b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    request = urllib.request.Request(
        "https://gen.pollinations.ai/v1/images/edits",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )

    with urllib.request.urlopen(request, timeout=300) as response:
        result = json.loads(response.read().decode())

    item = result["data"][0]

    if "b64_json" in item:
        image = base64.b64decode(item["b64_json"])
    else:
        with urllib.request.urlopen(item["url"], timeout=180) as response:
            image = response.read()

    with open(output_file, "wb") as f:
        f.write(image)


print("Starting Bobo AI story generation...")

for number, prompt in enumerate(scenes, start=1):

    filename = f"bobo_scene_{number}.png"

    print(f"Generating scene {number}/5...")

    generate_scene(prompt, filename)

    print(f"Scene {number} created: {filename}")

    if number < len(scenes):
        time.sleep(3)

print("================================")
print("BOBO STORY COMPLETE")
print("5 AI scenes successfully created")
print("================================")
