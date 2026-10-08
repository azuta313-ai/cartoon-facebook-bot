"""Read-only video model discovery. NEVER generates media or spends Pollen."""
import json
import urllib.request

url = "https://gen.pollinations.ai/video/models"
req = urllib.request.Request(url, headers={"User-Agent": "bobo-free-only-discovery/1.0"})
with urllib.request.urlopen(req, timeout=35) as resp:
    payload = json.load(resp)
models = payload.get("data", payload.get("models", payload)) if isinstance(payload, dict) else payload
if not isinstance(models, list):
    raise RuntimeError("Unexpected video model catalog response; no generation attempted")
print("Discovered", len(models), "video models")
for m in models:
    if not isinstance(m, dict):
        continue
    name = m.get("id") or m.get("name") or m.get("model")
    print(json.dumps({"id":name,"pricing":m.get("pricing"),"cost":m.get("cost"),"capabilities":m.get("capabilities"),"input_modalities":m.get("input_modalities"),"output_modalities":m.get("output_modalities")},default=str)[:1500])
print("READ_ONLY_COMPLETE: no API key used; no Pollen spent")
