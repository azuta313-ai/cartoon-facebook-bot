"""Exact-artifact timing repair. Visual mouth defect remains held for review."""
import hashlib,json,subprocess
from pathlib import Path
import sys
root=Path(sys.argv[1] if len(sys.argv)>1 else 'source')
assert hashlib.sha256((root/'bobo_fresh.mp4').read_bytes()).hexdigest()=='7f69807e92f48a4ab4c384ccc16c022ed46297d817830b979191eba9b44df5de'
caption=root/'repaired-speech.txt';caption.write_text('Careful now!')
graph=("[0:v]split=2[a][b];[a]trim=start_frame=0:end_frame=46,setpts=PTS-STARTPTS[a1];"
       "[b]trim=start_frame=65:end_frame=195,setpts=PTS-STARTPTS[b1];"
       "[a1][b1]concat=n=2:v=1:a=0,fps=30,scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280,"
       f"drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:textfile={caption}:fontsize=34:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=8:x=(w-text_w)/2:y=1160:enable='gte(t,0.65)*lt(t,1.3671)'[v];"
       "[1:a]atrim=duration=11,loudnorm=I=-20:TP=-3:LRA=7,volume=enable='between(t,0.55,1.53)':volume=0.22,volume=enable='between(t,3.02,3.42)':volume=0.45[m];"
       "[2:a]adelay=300|300,atrim=duration=11,volume=2[voc];"
       "[3:a]atrim=start=2.3:end=2.42,asetpts=PTS-STARTPTS,afade=t=in:d=0.01,afade=t=out:st=0.07:d=0.05,volume=0.5,adelay=3125|3125,apad=whole_dur=11,atrim=duration=11[fx];"
       "[m][voc][fx]amix=inputs=3:normalize=0:duration=first,alimiter=limit=0.84:level=false:latency=true[aout]")
subprocess.run(['ffmpeg','-v','error','-y','-i',str(root/'generated.mp4'),'-i',str(root/'original_music.wav'),'-i',str(root/'voice-track.wav'),'-i',str(root/'scene_effects.wav'),'-filter_complex',graph,'-map','[v]','-map','[aout]','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','11','-movflags','+faststart',str(root/'bobo_code_repaired.mp4')],check=True)
record={'source_sha256':'7f69807e92f48a4ab4c384ccc16c022ed46297d817830b979191eba9b44df5de','repaired_sha256':hashlib.sha256((root/'bobo_code_repaired.mp4').read_bytes()).hexdigest(),'removed_source_interval':[2.875,4.0625],'duration_target':11,'speech':{'text':'Careful now!','start':.65,'end':1.3671,'listening_verified':False,'mouth_sync_verified':False},'effects':[{'type':'wood','source':'existing scene_effects.wav 2.30-2.42; perceptual realism not verified','start':3.125,'gain':.5,'observed_contact':[3.0625,3.9375]}],'music_variant':json.loads((root/'episode.json').read_text())['music_variant'],'status':'held','remaining_defect':'Repeated unvoiced mouth animation; no reliable tracking correction. This file has not passed final quality review.'}
(root/'code-repair-review.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record))
