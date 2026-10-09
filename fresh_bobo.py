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

# Rotate complete settings and stories; preserve Bobo, not the old kitchen.
SCENES=[
 ('Garden bubble trouble','a sunny flower garden beside a bubble wand','a floating soap bubble','He blows a bubble, follows it with his finger, and jumps in surprise when it pops.','He laughs at the popped bubble and gives a playful shrug.',['One perfect bubble!','Wait for it...','POP!'],['GardenFun','BubbleTrouble']),
 ('Beach bucket surprise','a colorful sandy beach beside a little sandcastle','a small beach bucket','He tips his bucket to make a sandcastle, lifts it proudly, and looks surprised at the tiny result.','He admires his tiny sandcastle and gives a proud thumbs up.',['Big castle coming!','Is that all?','Tiny but mighty!'],['BeachComedy','Sandcastle']),
 ('Picnic apple escape','a leafy park with a picnic blanket and fruit basket','a rolling red apple','He reaches for an apple, watches it roll away, and quickly catches it with both hands.','He holds up the rescued apple and smiles proudly.',['Snack time!','Come back!','Got you!'],['PicnicFun','AppleAdventure']),
 ('Toy room tower wobble','a bright playroom with colorful wooden blocks','a wobbly block tower','He places a block on a tower, sees it wobble, and freezes with a funny wide eyed expression.','He steadies the tower gently and celebrates with a little shoulder dance.',['One more block!','Easy... easy...','Tower saved!'],['ToyRoom','BlockTower']),
 ('Rainy puddle splash','a cheerful garden path after rain with a shallow puddle','a shallow puddle','He cautiously taps a puddle with his foot, makes a small splash, then grins at the camera.','He does a playful little hop beside the puddle and laughs.',['Just a little splash!','Oops!','Worth it!'],['PuddleFun','RainyDay']),
 ('Space button surprise','a playful colorful toy spaceship cockpit','a large glowing button','He studies a glowing button, presses it carefully, and reacts with delighted surprise as lights blink.','He waves happily at the blinking lights and gives a cheeky wink.',['What does this do?','Beep beep!','Captain Bobo!'],['SpaceComedy','CaptainBobo']),
 ('Snowball tiny champion','a bright snowy playground beside a small snowman','a tiny snowball','He rolls a little snowball, holds it up like a trophy, and gives an exaggerated proud smile.','He gently places the snowball beside the snowman and celebrates.',['Snow champion!','My tiny trophy!','Coolest prize!'],['SnowDay','SnowmanFun']),
 ('Art room paint surprise','a sunny art room with a small easel and paint palette','a colorful paintbrush','He makes a careful brush stroke, notices a little paint on his hand, and smiles sheepishly.','He proudly points at his colorful painting and bows playfully.',['Masterpiece coming!','Paint everywhere!','Artist Bobo!'],['ArtComedy','LittleArtist']),
]

def original_music(seconds, variant):
 # Original procedural tunes avoid paid downloads and repeated sections of one song.
 melodies=[
  [0,4,7,12,7,4,2,7,11,14,11,7],
  [0,7,5,9,4,7,2,5,0,4,7,4],
  [0,2,4,7,9,7,4,2,5,9,7,2],
  [0,5,9,12,9,5,7,11,14,11,7,2],
  [0,3,7,10,7,3,5,8,12,8,5,2],
  [0,12,7,2,9,4,11,7,5,2,7,12],
  [0,4,9,7,2,5,11,9,7,4,2,0],
  [0,7,12,4,9,2,7,5,11,4,7,0],
 ]
 rate=48000; t=np.arange(int(seconds*rate))/rate
 tune=np.zeros(len(t)); v=variant%len(melodies); beat=[.28,.34,.31,.25,.38,.27,.36,.30][v]
 for n,start in enumerate(np.arange(0,seconds,beat)):
  note=melodies[v][n%len(melodies[v])]; freq=220*2**((note+v%3)/12)
  u=t-start; active=(u>=0)&(u<beat*.9); local=np.maximum(u,0)
  envelope=np.minimum(local/.008,1)*np.exp(-local*(9+v))
  tone=np.sin(2*np.pi*freq*local)+(.15+v*.025)*np.sin(4*np.pi*freq*local)
  tune+=active*envelope*tone*.22
 tune=np.clip(tune,-.8,.8)
 stereo=np.column_stack((tune,tune))
 path=OUT/'original_music.wav'
 with wave.open(str(path),'wb') as wav:
  wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(rate); wav.writeframes((stereo*32767).astype('<i2').tobytes())
 return str(path)

def run(args): subprocess.run(args, check=True)

def soundtrack(seconds, variant):
 # Use the same musical/cartoon asset family as the uploaded reference.
 music=original_music(seconds,variant)
 effects=['soundreality-pop-sound-423716.mp3','freesound_community-cartoon-bite-39234.mp3','universfield-cartoon-spring-boing-140378.mp3']
 orders=[(0,1,2),(2,0,1),(0,2,0),(1,0,2)]
 order=orders[variant%4]; offset=0
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
 recent=[v.get('scene_id') for v in list(ledger.values())[-3:]]
 scene_id=(now.toordinal()*2+slot)%len(SCENES)
 while scene_id in recent: scene_id=(scene_id+1)%len(SCENES)
 title,setting,prop,action,ending,captions,scene_tags=SCENES[scene_id]
 run(['ffmpeg','-loglevel','error','-y','-i',os.getenv('BOBO_REFERENCE_VIDEO','Bobo reel base.mp4'),'-frames:v','1',str(OUT/'reference.png')])
 prompt=('High quality 3D animated family comedy. Use the reference only for the exact little brown monkey character and red Bobo shirt. Start a NEW scene in '+setting+'. Replace the reference kitchen and cake completely; the main prop is '+prop+'. '+action+' Clear natural hand movement and expressive face, smooth motion, fixed camera. No extra characters, no text overlays. Complete the action within five seconds.')
 client=Client(SPACE, token=token, httpx_kwargs={'timeout':90})
 # Exactly two free-GPU requests per episode, with no paid fallback.
 clips=[]
 endings=['He shrugs with a cheeky smile and laughs at his mistake.','He looks embarrassed after sneezing and giggles.','He hides his hand and smiles innocently at the camera.','He finishes his dance with a proud bow and wink.','He peeks back at the cake, then shrugs and grins.','He shows his cherry proudly and laughs.','He pretends to write a detective note, then smiles knowingly.','He makes a smaller imaginary bite gesture and giggles.']
 for shot in range(2):
  shot_prompt=prompt if shot==0 else ('Continue this exact 3D cartoon scene from the supplied last frame. Same Bobo monkey and red shirt, same '+setting+' and '+prop+'. '+ending+' Smooth clear movements, fixed camera, no sudden scene changes. Complete in five seconds.')
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
 soundtrack(11,scene_id)
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
 filters=['minterpolate=fps=60:mi_mode=mci:mc_mode=aobmc:me_mode=bilat:vsbmc=1:scd=fdiff','scale=720:1280:force_original_aspect_ratio=increase','crop=720:1280','tpad=stop_mode=clone:stop_duration=1.5']
 # Textfiles avoid shell/filter escaping for captions.
 for i,(text,start,end,y,size) in enumerate([(title,0,1.5,150,36)]+[(captions[0],0,4,1160,34),(captions[1],4,8,1160,34),(captions[2],8,11,1160,34)]):
  path=OUT/f'text{i}.txt';path.write_text(text)
  filters.append(f"drawtext=fontfile={font}:textfile={path}:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=8:x=(w-text_w)/2:y={y}:enable='between(t,{start},{end})'")
 run(['ffmpeg','-loglevel','error','-y','-i',str(OUT/'generated.mp4'),'-i',str(OUT/'audio.wav'),'-vf',','.join(filters),'-af','loudnorm=I=-20:TP=-1.5:LRA=9','-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','fast','-crf','18','-c:a','aac','-b:a','192k','-ar','48000','-pix_fmt','yuv420p','-t','11','-movflags','+faststart',str(OUT/'bobo_fresh.mp4')])
 run(['ffmpeg','-v','error','-i',str(OUT/'bobo_fresh.mp4'),'-f','null','-'])
 metadata={'episode':episode,'title':title,'space':SPACE,'generated_sha256':hashlib.sha256((OUT/'generated.mp4').read_bytes()).hexdigest(),'duration':11,'generated_at':now.isoformat(),'quality_reference':'Bobo reel base.mp4','export_fps':60,'audio_mix_variant':scene_id,'scene_id':scene_id,'setting':setting,'music':'original procedural composition '+str(scene_id)}
 social_caption=f"{title} 😂\n{captions[0]} {captions[-1]}\n"+['Which moment made you smile?','What should Bobo try next?','Would you try this too?','Who else loves Bobo?'][scene_id%4]+"\n"+' '.join('#'+tag for tag in ['Bobo','3DAnimation']+scene_tags+[['FunnyCartoon'],['CartoonComedy'],['AnimatedShorts'],['FunnyAnimation']][scene_id%4])
 metadata['social_caption']=social_caption
 (OUT/'facebook-caption.txt').write_text(social_caption)
 (OUT/'episode.json').write_text(json.dumps(metadata,indent=2))
 print(f'New episode created: {title}. No paid API used.')
 if os.getenv('PUBLISH_FACEBOOK')=='true':
  page=os.environ['FB_PAGE_ID']; fb_token=os.environ['FB_PAGE_ACCESS_TOKEN']
  if not page or not fb_token: raise RuntimeError('Facebook credentials are missing.')
  if any(v.get('generated_sha256')==metadata['generated_sha256'] for v in ledger.values()): raise RuntimeError('Duplicate generated video; skipping upload.')
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
