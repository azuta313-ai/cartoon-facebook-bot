import os
import json
import base64
import urllib.request
import uuid

API_KEY = os.environ["POLLINATIONS_API_KEY"]

boundary = "----BoboBoundary" + uuid.uuid4().hex

prompt = """
Keep the exact same Bobo bear character from the reference image:
same brown fur, same face, same large expressive eyes,
same blue denim overalls, same body proportions and same
high-quality 3D children's cartoon style.

Create a NEW scene where Bobo is happily holding a large
red balloon in a colorful playground. Full body visible.
Vertical composition. Bright cheerful lighting.
No text, no watermark.
"""

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

with open("bobo_reference.jpg", "rb") as f:
    image_data = f.read()

body += (
    f"--{boundary}\r\n"
    'Content-Disposition: form-data; name="image"; filename="bobo_reference.jpg"\r\n'
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

print("Generating new Bobo scene from reference image...")

with urllib.request.urlopen(request, timeout=300) as response:
    result = json.loads(response.read().decode())

item = result["data"][0]

if "b64_json" in item:
    output = base64.b64decode(item["b64_json"])
else:
    image_url = item["url"]
    with urllib.request.urlopen(image_url, timeout=180) as response:
        output = response.read()

with open("bobo_reference_test.png", "wb") as f:
    f.write(output)

print("SUCCESS: bobo_reference_test.png created")
