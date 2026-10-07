import os
import urllib.parse
import urllib.request

api_key = os.environ["POLLINATIONS_API_KEY"]

prompt = """
cute friendly 3D cartoon bear named Bobo,
round brown bear, big expressive eyes,
blue overalls, cheerful funny expression,
standing in a colorful playground,
bright children's animated movie style,
soft lighting, vibrant colors,
vertical composition, full body,
no text, no watermark
"""

encoded_prompt = urllib.parse.quote(prompt.strip())

url = (
    "https://gen.pollinations.ai/image/"
    + encoded_prompt
    + "?model=flux&width=768&height=1024"
)

request = urllib.request.Request(
    url,
    headers={
        "Authorization": f"Bearer {api_key}"
    }
)

print("Generating Bobo test image...")

with urllib.request.urlopen(request, timeout=180) as response:
    image_data = response.read()

with open("bobo_ai_test.jpg", "wb") as f:
    f.write(image_data)

print("SUCCESS: bobo_ai_test.jpg created")
