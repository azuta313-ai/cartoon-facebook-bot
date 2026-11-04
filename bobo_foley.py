"""Free CC0 foley sources with immutable URLs and SHA256 verification."""
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

import numpy as np

KENNEY_COMMIT = "9662dc1bed3b06ae753045915f9accfac044c7ce"
KENNEY_BASE = (
    "https://raw.githubusercontent.com/GeorgeQLe/assets-sfx-combat/"
    + KENNEY_COMMIT
    + "/assets/kenney/impact-sounds/Audio/"
)

SOURCES = {
    "water": {
        "url": "https://bigsoundbank.com/UPLOAD/mp3/1530.mp3",
        "page": "https://bigsoundbank.com/splash-small-2-s1530.html",
        "sha256": "3133c863e9881f2ec82e87e8d46d3276023b6209208c4f79b15bd07b3ecd11a7",
        "author": "Joseph SARDIN",
        "license": "CC0",
        "filename": "natural-water-splash-1530.mp3",
    },
    "snow": {
        "url": KENNEY_BASE + "footstep_snow_000.ogg",
        "page": "https://kenney.nl/assets/impact-sounds",
        "sha256": "c05fa4a9dc9a7aabc04996466fb589537e49af76de9998d8f9e6270ec92dcef7",
        "author": "Kenney",
        "license": "CC0",
        "filename": "kenney-footstep-snow-000.ogg",
    },
    "wood": {
        "url": KENNEY_BASE + "impactWood_light_000.ogg",
        "page": "https://kenney.nl/assets/impact-sounds",
        "sha256": "eb45e35b4bed784d3f120de4afec4b0d6ac09d9e143cce8cfcb7d739e1b1f3c3",
        "author": "Kenney",
        "license": "CC0",
        "filename": "kenney-impact-wood-light-000.ogg",
    },
    "tap": {
        "url": KENNEY_BASE + "impactSoft_medium_000.ogg",
        "page": "https://kenney.nl/assets/impact-sounds",
        "sha256": "7d3ba0bb5e60a11b5d3e558c141303dcf494256675fbf753c0d252d2cf0481e3",
        "author": "Kenney",
        "license": "CC0",
        "filename": "kenney-impact-soft-medium-000.ogg",
    },
}

MAP = {
    "splash": "water",
    "snow": "snow",
    "wood": "wood",
    "tap": "tap",
}


def recorded_effect(kind, length, out):
    """Return a softly trimmed mono CC0 source, or None for unmapped effect types."""
    source_key = MAP.get(kind)
    if source_key is None:
        return None
    source = SOURCES[source_key]
    cache = Path(out) / "foley-sources"
    cache.mkdir(exist_ok=True)
    archive = cache / source["filename"]

    if not archive.exists():
        request = urllib.request.Request(
            source["url"], headers={"User-Agent": "Bobo-video-foley/1.0"}
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read(5_000_001)
        if len(data) > 5_000_000:
            raise RuntimeError("Foley download exceeds size limit")
        if hashlib.sha256(data).hexdigest() != source["sha256"]:
            raise RuntimeError("Foley source changed; review required")
        archive.write_bytes(data)

    data = archive.read_bytes()
    if hashlib.sha256(data).hexdigest() != source["sha256"]:
        raise RuntimeError("Foley source hash mismatch")
    raw = subprocess.check_output([
        "ffmpeg", "-v", "error", "-i", str(archive),
        "-ac", "1", "-ar", "48000", "-f", "f32le", "-"
    ])
    samples = np.frombuffer(raw, dtype="<f4").astype(float)
    if not samples.size or not np.isfinite(samples).all():
        raise RuntimeError("Invalid recorded foley")
    active = np.flatnonzero(np.abs(samples) > max(.001, np.max(np.abs(samples)) * .04))
    if not active.size:
        raise RuntimeError("Empty recorded foley")
    start = max(0, int(active[0]) - 240)
    samples = samples[start:start + int(length * 48000)].copy()
    samples = np.pad(samples, (0, max(0, int(length * 48000) - len(samples))))
    fade = min(480, len(samples) // 4)
    if fade:
        samples[:fade] *= np.linspace(0, 1, fade)
        samples[-fade:] *= np.linspace(1, 0, fade)

    path = Path(out) / "foley-provenance.json"
    provenance = json.loads(path.read_text()) if path.exists() else {}
    provenance[kind] = {
        "source_url": source["url"],
        "page": source["page"],
        "author": source["author"],
        "license": source["license"],
        "sha256": source["sha256"],
        "source_onset_seconds": start / 48000,
        "excerpt_seconds": length,
        "listening_verified": False,
    }
    path.write_text(json.dumps(provenance, indent=2))
    return samples
