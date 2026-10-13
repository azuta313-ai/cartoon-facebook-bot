"""Free CC0 source audio; downloads are hash-pinned, never purchased."""
import hashlib, io, json, subprocess, urllib.request, zipfile
from pathlib import Path
import numpy as np

SOURCES={
 'water':{'page':'https://bigsoundbank.com/splash-small-2-s1530.html','url':'https://bigsoundbank.com/UPLOAD/mp3/1530.mp3','sha256':'3133c863e9881f2ec82e87e8d46d3276023b6209208c4f79b15bd07b3ecd11a7','author':'Joseph SARDIN','license':'CC0'},
 'impacts':{'page':'https://kenney.nl/assets/impact-sounds','url':'https://kenney.nl/media/pages/assets/impact-sounds/87b4ddecda-1677589768/kenney_impact-sounds.zip','sha256':'029d734af1582474edf3a694d1b0cebc97c1c152f2f39fa34d4c2bafc5de77f8','author':'Kenney','license':'CC0'},
}
MAP={'splash':('water',None),'wood':('impacts','Audio/impactWood_light_000.ogg'),'tap':('impacts','Audio/impactSoft_medium_000.ogg'),'snow':('impacts','Audio/footstep_snow_000.ogg')}

def recorded_effect(kind,length,out):
 if kind not in MAP: return None
 family,member=MAP[kind]; source=SOURCES[family]
 cache=Path(out)/'foley-sources'; cache.mkdir(exist_ok=True)
 archive=cache/(family+('.zip' if member else '.mp3'))
 if not archive.exists():
  request=urllib.request.Request(source['url'],headers={'User-Agent':'Bobo-video-foley/1.0'})
  with urllib.request.urlopen(request,timeout=30) as response: data=response.read(5_000_001)
  if len(data)>5_000_000: raise RuntimeError('Foley download exceeds size limit')
  if hashlib.sha256(data).hexdigest()!=source['sha256']: raise RuntimeError('Foley source changed; review required')
  archive.write_bytes(data)
 if hashlib.sha256(archive.read_bytes()).hexdigest()!=source['sha256']: raise RuntimeError('Foley source hash mismatch')
 audio=archive
 if member:
  audio=cache/Path(member).name
  with zipfile.ZipFile(archive) as z: audio.write_bytes(z.read(member))
 raw=subprocess.check_output(['ffmpeg','-v','error','-i',str(audio),'-ac','1','-ar','48000','-f','f32le','-'])
 samples=np.frombuffer(raw,dtype='<f4').astype(float)
 if not samples.size or not np.isfinite(samples).all(): raise RuntimeError('Invalid recorded foley')
 active=np.flatnonzero(np.abs(samples)>max(.001,np.max(np.abs(samples))*.04))
 if not active.size: raise RuntimeError('Empty recorded foley')
 start=max(0,int(active[0])-240)
 samples=samples[start:start+int(length*48000)].copy()
 samples=np.pad(samples,(0,max(0,int(length*48000)-len(samples))))
 fade=min(480,len(samples)//4)
 samples[:fade]*=np.linspace(0,1,fade); samples[-fade:]*=np.linspace(1,0,fade)
 path=Path(out)/'foley-provenance.json'
 provenance=json.loads(path.read_text()) if path.exists() else {}
 provenance[kind]={**source,'member':member,'source_onset_seconds':start/48000,'excerpt_seconds':length,'listening_verified':False}
 path.write_text(json.dumps(provenance,indent=2))
 return samples
