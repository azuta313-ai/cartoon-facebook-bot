"""Generate one new Bobo animation using only free ZeroGPU allocation."""
import hashlib, json, math, os, shutil, subprocess, wave
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from gradio_client import Client, handle_file

SPACE='zerogpu-aoti/wan2-2-fp8da-aoti-faster'
OUT=Path('fresh_output'); OUT.mkdir(exist_ok=True)
STORIES=[
 ('The cherry trick', 'He carefully picks up a cherry from the cake, proudly raises it, accidentally drops it back onto the cake, then laughs at his mistake.', ['One tiny cherry...', 'Oops!', 'Still counts!']),
 ('Cake smells amazing', 'He leans forward to smell the cake, closes his eyes with a delighted smile, then suddenly sneezes and looks surprised before laughing.', ['Smells amazing!', 'Ah... ah...', 'ACHOO!']),
 ('Caught looking', 'He looks left and right suspiciously, reaches slowly toward the cake, suddenly freezes with wide eyes as if caught, then hides his hand and smiles innocently.', ['Nobody is watching...', 'Wait...', 'Who, me?']),
 ('The cake dance', 'He points excitedly at the cake, performs a small joyful shoulder dance with both hands raised, then proudly bows toward the cake and giggles.', ['Cake spotted!', 'Happy dance!', 'Thank you, cake!']),
 ('Too tempting', 'He shakes his head firmly while pushing his hand away from the cake, tries to look away, then immediately turns back with a huge delighted smile.', ['I can resist!', 'Definitely...', 'Maybe tomorrow!']),
 ('Cherry champion', 'He carefully takes one cherry from the cake, holds it like a tiny trophy, beams proudly, then celebrates with a little fist pump and laughs.', ['My tiny trophy!', 'Champion!', 'Best prize ever!']),
 ('Cake detective', 'He studies the cake very seriously, points at a cherry, tilts his head thoughtfully, then looks directly at the camera with a cheeky knowing grin.', ['A serious mystery...', 'Found a clue!', 'It looks delicious!']),
 ('The tiny bite plan', 'He measures a tiny imaginary bite between thumb and finger, looks at the large cake, opens his mouth exaggeratedly, then laughs and shrugs.', ['Just a tiny bite...', 'This tiny?', 'Oops... too big!']),
]

def run(args): subprocess.run(args, check=True)

def soundtrack(seconds):
 sr=48000; audio=np.zeros(int(sr*seconds)); notes=[523.25,659.25,783.99,659.25,587.33,698.46,783.99,523.25]
 for i,start in enumerate(np.arange(0,seconds,.375)):
  n=min(int(.35*sr),len(audio)-int(start*sr)); t=np.arange(n)/sr
  audio[int(start*sr):int(start*sr)+n]+=.14*np.sin(2*np.pi*notes[i%8]*t)*np.exp(-t*12)*np.minimum(t/.008,1)
 for start,freq in [(1,900),(3,250),(5,1100)]:
  n=int(.3*sr);t=np.arange(n)/sr; k=int(start*sr)
  audio[k:k+n]+=.2*np.sin(2*np.pi*(freq*t-200*t*t))*np.exp(-t*12)
 audio*=np.minimum(np.arange(len(audio))/sr/.1,1)*np.minimum((seconds-np.arange(len(audio))/sr)/.3,1)
 with wave.open(str(OUT/'audio.wav'),'wb') as w:
  w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes((np.repeat(audio[:,None],2,1)*32767).astype('<i2').tobytes())

def main():
 token=os.getenv('HF_TOKEN','').strip()
 if not token: raise RuntimeError('HF_TOKEN is missing; a free Hugging Face account token is required.')
 now=datetime.now(ZoneInfo('Asia/Karachi'))
 slot=int(os.getenv('EPISODE_SLOT',str(max(0,min(3,(now.hour-9)//4)))))
 episode=int(now.strftime('%Y%m%d'))*4+slot
 title,action,captions=STORIES[episode%len(STORIES)]
 run(['ffmpeg','-loglevel','error','-y','-i','Bobo 1.mp4','-frames:v','1',str(OUT/'reference.png')])
 prompt=('High quality 3D animated family comedy. Keep the exact little brown monkey in the red Bobo shirt and the detailed colorful kitchen from the reference. '+action+' Clear natural hand movement and expressive face, smooth motion, fixed camera. No extra characters, no text overlays. Complete the action within six seconds.')
 client=Client(SPACE, token=token, httpx_kwargs={'timeout':90})
 # One request only. Never buy credits, retry against paid providers, or reuse old clips.
 result=client.predict(input_image=handle_file(str(OUT/'reference.png')),prompt=prompt,steps=4,negative_prompt='blur, distorted hands, extra limbs, melting face, flicker, frozen frame, camera shake',duration_seconds=6,guidance_scale=1,guidance_scale_2=1,seed=episode%2147483647,randomize_seed=False,api_name='/generate_video')
 source=result[0]
 if isinstance(source,dict): source=source.get('video',source.get('path'))
 if not isinstance(source,str) or not Path(source).is_file(): raise RuntimeError('Generator did not return a video file.')
 shutil.copyfile(source,OUT/'generated.mp4')
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=width,height','-of','json',str(OUT/'generated.mp4')]))
 duration=float(info['format']['duration'])
 if not 5.5<=duration<=7: raise RuntimeError('Generated video duration is invalid.')
 # Reject static output using differences among four sampled frames.
 raw=subprocess.check_output(['ffmpeg','-loglevel','error','-i',str(OUT/'generated.mp4'),'-vf','fps=1,scale=64:64,format=gray','-f','rawvideo','-'])
 frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,64,64).astype(float)
 if len(frames)<4 or np.abs(np.diff(frames,axis=0)).mean()<.5: raise RuntimeError('Generated clip is static; skipping publication.')
 soundtrack(6)
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
 filters=['scale=720:1280:force_original_aspect_ratio=increase','crop=720:1280','fps=30']
 # Textfiles avoid shell/filter escaping for captions.
 for i,(text,start,end,y,size) in enumerate([(title,0,1.5,150,40)]+[(c,i*2,(i+1)*2,1040,40) for i,c in enumerate(captions)]):
  path=OUT/f'text{i}.txt';path.write_text(text)
  filters.append(f"drawtext=fontfile={font}:textfile={path}:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=14:x=(w-text_w)/2:y={y}:enable='between(t,{start},{end})'")
 run(['ffmpeg','-loglevel','error','-y','-i',str(OUT/'generated.mp4'),'-i',str(OUT/'audio.wav'),'-vf',','.join(filters),'-af','loudnorm=I=-16:TP=-1.5:LRA=7','-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-b:a','192k','-ar','48000','-pix_fmt','yuv420p','-t','6','-movflags','+faststart',str(OUT/'bobo_fresh.mp4')])
 run(['ffmpeg','-v','error','-i',str(OUT/'bobo_fresh.mp4'),'-f','null','-'])
 metadata={'episode':episode,'title':title,'space':SPACE,'generated_sha256':hashlib.sha256((OUT/'generated.mp4').read_bytes()).hexdigest(),'duration':6,'generated_at':now.isoformat()}
 (OUT/'episode.json').write_text(json.dumps(metadata,indent=2))
 print(f'New episode created: {title}. No paid API used.')
if __name__=='__main__': main()
