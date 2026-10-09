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

def soundtrack(seconds, variant):
 # Use the same musical/cartoon asset family as the uploaded reference.
 music='alex-morgan-cartoon-bouncy-chase-antics-578472.mp3'
 effects=['soundreality-pop-sound-423716.mp3','freesound_community-cartoon-bite-39234.mp3','universfield-cartoon-spring-boing-140378.mp3']
 orders=[(0,1,2),(2,0,1),(0,2,0),(1,0,2)]
 order=orders[variant%4]; offset=[0,16,32,48][variant%4]
 args=['ffmpeg','-loglevel','error','-y','-ss',str(offset),'-i',music]
 for index in order: args+=['-i',effects[index]]
 times=[900,4800,8500]
 mix=[f'[0:a]atrim=duration={seconds},asetpts=PTS-STARTPTS,volume=0.16,afade=t=in:st=0:d=0.3,afade=t=out:st={seconds-.6}:d=0.6[music]']
 for i,delay in enumerate(times,1):
  level=[.65,.8,.7][(i+variant)%3]
  mix.append(f'[{i}:a]aresample=48000,aformat=channel_layouts=stereo,volume={level},adelay={delay}|{delay}[fx{i}]')
 mix.append(f'[music][fx1][fx2][fx3]amix=inputs=4:duration=first:normalize=0,atrim=duration={seconds}[audio]')
 args+=['-filter_complex',';'.join(mix),'-map','[audio]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(OUT/'audio.wav')]
 run(args)

def main():
 token=os.getenv('HF_TOKEN','').strip()
 if not token: raise RuntimeError('HF_TOKEN is missing; a free Hugging Face account token is required.')
 now=datetime.now(ZoneInfo('Asia/Karachi'))
 slot=int(os.getenv('EPISODE_SLOT',str(0 if now.hour<21 else 1)))
 episode=int(now.strftime('%Y%m%d'))*2+slot
 episode_key=f'long-v2-{episode}'
 ledger_path=Path('published_bobo.json')
 ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
 if os.getenv('PUBLISH_FACEBOOK')=='true' and episode_key in ledger:
  print('This episode was already published; skipping generation and upload.'); return
 title,action,captions=STORIES[(now.toordinal()*2+slot)%len(STORIES)]
 run(['ffmpeg','-loglevel','error','-y','-i',os.getenv('BOBO_REFERENCE_VIDEO','Bobo reel base.mp4'),'-frames:v','1',str(OUT/'reference.png')])
 prompt=('High quality 3D animated family comedy. Keep the exact little brown monkey in the red Bobo shirt and the detailed colorful kitchen from the reference. '+action+' Clear natural hand movement and expressive face, smooth motion, fixed camera. No extra characters, no text overlays. Complete the action within five seconds.')
 client=Client(SPACE, token=token, httpx_kwargs={'timeout':90})
 # Exactly two free-GPU requests per episode, with no paid fallback.
 clips=[]
 endings=['He shrugs with a cheeky smile and laughs at his mistake.','He looks embarrassed after sneezing and giggles.','He hides his hand and smiles innocently at the camera.','He finishes his dance with a proud bow and wink.','He peeks back at the cake, then shrugs and grins.','He shows his cherry proudly and laughs.','He pretends to write a detective note, then smiles knowingly.','He makes a smaller imaginary bite gesture and giggles.']
 for shot in range(2):
  shot_prompt=prompt if shot==0 else ('Continue this exact 3D cartoon scene from the supplied last frame. Same Bobo monkey, outfit, cake and kitchen. '+endings[(now.toordinal()*2+slot)%8]+' Smooth clear movements, fixed camera, no sudden scene changes. Complete in five seconds.')
  reference=OUT/('reference.png' if shot==0 else 'continuation.png')
  result=client.predict(input_image=handle_file(str(reference)),prompt=shot_prompt,steps=4,negative_prompt='blur, distorted hands, extra limbs, melting face, flicker, frozen frame, camera shake',duration_seconds=5,guidance_scale=1,guidance_scale_2=1,seed=(episode*2+shot)%2147483647,randomize_seed=False,api_name='/generate_video')
  source=result[0]
  if isinstance(source,dict): source=source.get('video',source.get('path'))
  if not isinstance(source,str) or not Path(source).is_file(): raise RuntimeError('Generator did not return a video file.')
  clip=OUT/f'shot{shot}.mp4'; shutil.copyfile(source,clip); clips.append(clip)
  shot_info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(clip)]))
  if not 4.8<=float(shot_info['format']['duration'])<=5.5: raise RuntimeError('Invalid generated shot duration.')
  shot_raw=subprocess.check_output(['ffmpeg','-loglevel','error','-i',str(clip),'-vf','fps=1,scale=64:64,format=gray','-f','rawvideo','-'])
  sampled=np.frombuffer(shot_raw,dtype=np.uint8).reshape(-1,64,64).astype(float)
  if len(sampled)<4 or np.abs(np.diff(sampled,axis=0)).mean()<.5: raise RuntimeError('Static generated shot; skipping publication.')
  if shot==0: run(['ffmpeg','-loglevel','error','-y','-sseof','-0.1','-i',str(clip),'-frames:v','1',str(OUT/'continuation.png')])
 (OUT/'shots.txt').write_text(''.join(f"file '{p.name}'\n" for p in clips))
 run(['ffmpeg','-loglevel','error','-y','-f','concat','-safe','0','-i',str(OUT/'shots.txt'),'-an','-c:v','libx264','-preset','fast','-crf','18',str(OUT/'generated.mp4')])
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=width,height','-of','json',str(OUT/'generated.mp4')]))
 duration=float(info['format']['duration'])
 if not 9.5<=duration<=11: raise RuntimeError('Generated video duration is invalid.')
 # Reject static output using differences among four sampled frames.
 raw=subprocess.check_output(['ffmpeg','-loglevel','error','-i',str(OUT/'generated.mp4'),'-vf','fps=1,scale=64:64,format=gray','-f','rawvideo','-'])
 frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,64,64).astype(float)
 if len(frames)<4 or np.abs(np.diff(frames,axis=0)).mean()<.5: raise RuntimeError('Generated clip is static; skipping publication.')
 soundtrack(11,episode)
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
 filters=['minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bilat:vsbmc=1:scd=fdiff','scale=720:1280:force_original_aspect_ratio=increase','crop=720:1280','tpad=stop_mode=clone:stop_duration=1']
 # Textfiles avoid shell/filter escaping for captions.
 for i,(text,start,end,y,size) in enumerate([(title,0,1.5,150,36)]+[(captions[0],0,4,1160,34),(captions[1],4,8,1160,34),(captions[2],8,11,1160,34)]):
  path=OUT/f'text{i}.txt';path.write_text(text)
  filters.append(f"drawtext=fontfile={font}:textfile={path}:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=8:x=(w-text_w)/2:y={y}:enable='between(t,{start},{end})'")
 run(['ffmpeg','-loglevel','error','-y','-i',str(OUT/'generated.mp4'),'-i',str(OUT/'audio.wav'),'-vf',','.join(filters),'-af','loudnorm=I=-20:TP=-1.5:LRA=9','-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-b:a','192k','-ar','48000','-pix_fmt','yuv420p','-t','11','-movflags','+faststart',str(OUT/'bobo_fresh.mp4')])
 run(['ffmpeg','-v','error','-i',str(OUT/'bobo_fresh.mp4'),'-f','null','-'])
 metadata={'episode':episode,'title':title,'space':SPACE,'generated_sha256':hashlib.sha256((OUT/'generated.mp4').read_bytes()).hexdigest(),'duration':11,'generated_at':now.isoformat(),'quality_reference':'Bobo reel base.mp4','export_fps':60,'audio_mix_variant':episode%4}
 (OUT/'episode.json').write_text(json.dumps(metadata,indent=2))
 print(f'New episode created: {title}. No paid API used.')
 if os.getenv('PUBLISH_FACEBOOK')=='true':
  page=os.environ['FB_PAGE_ID']; fb_token=os.environ['FB_PAGE_ACCESS_TOKEN']
  if not page or not fb_token: raise RuntimeError('Facebook credentials are missing.')
  if any(v.get('generated_sha256')==metadata['generated_sha256'] for v in ledger.values()): raise RuntimeError('Duplicate generated video; skipping upload.')
  social_caption=f"{title} 😂\n{captions[0]} Watch Bobo's reaction! Which moment made you smile?\n#Bobo #FunnyCartoon #3DAnimation #CartoonComedy #AnimatedShorts"
  metadata['social_caption']=social_caption
  (OUT/'facebook-caption.txt').write_text(social_caption)
  response=subprocess.check_output(['curl','--silent','--show-error','--fail-with-body','--max-time','180','-X','POST',f'https://graph-video.facebook.com/v26.0/{page}/videos','-F',f'access_token={fb_token}','-F',f'source=@{OUT}/bobo_fresh.mp4','-F',f'description={social_caption}'])
  result=json.loads(response)
  if not result.get('id'): raise RuntimeError('Facebook did not accept the video.')
  metadata['facebook_video_id']=result['id']; ledger[episode_key]=metadata
  ledger_path.write_text(json.dumps(ledger,indent=2))
  (OUT/'episode.json').write_text(json.dumps(metadata,indent=2))
  print('Facebook accepted new video:',result['id'])
if __name__=='__main__': main()
