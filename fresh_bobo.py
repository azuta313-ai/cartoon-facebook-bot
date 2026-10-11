"""Generate one new Bobo animation using only free ZeroGPU allocation."""
import hashlib, json, math, os, re, shutil, subprocess, wave
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np
from gradio_client import Client, handle_file

SPACE='zerogpu-aoti/wan2-2-fp8da-aoti-faster'
OUT=Path('fresh_output'); OUT.mkdir(exist_ok=True)
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

# Captions describe these visible beats, rather than unrelated fixed intervals.
ACTION_BEATS=[
 ('Bobo holds up the bubble wand and gently blows one bubble. He watches it float and slowly reaches toward it. Keep the bubble intact through this shot.',
  'The floating bubble pops as Bobo reaches it. He jumps in surprise, then laughs and shrugs.'),
 ('Bobo fills and tips his beach bucket onto the sand, pats it carefully, and prepares to lift it. Keep the bucket covering the result.',
  'Bobo lifts the bucket to reveal a tiny sandcastle, looks surprised, then proudly gives a thumbs up.'),
 ('Bobo reaches for the red apple on the picnic blanket. It starts rolling away and he reaches after it, looking surprised.',
  'Bobo catches the rolling apple with both hands and holds it up proudly with a relieved smile.'),
 ('Bobo carefully places one block on his tower. The tower starts wobbling and he freezes with wide eyes.',
  'Bobo gently steadies the wobbling tower, then celebrates with a small shoulder dance.'),
 ('Bobo notices the puddle and cautiously raises one foot over it, smiling mischievously. Keep the foot just above the water.',
  'Bobo taps the puddle and splashes water, reacts with surprise, then does a playful hop and laughs.'),
 ('Bobo studies the glowing spaceship button and slowly brings his finger close to it. Do not press it yet.',
  'Bobo presses the button. The cockpit lights blink and he reacts with delight, then waves and winks.'),
 ('Bobo rolls a tiny snowball and carefully raises it like a trophy, looking very serious.',
  'Bobo beams proudly at the tiny snowball, places it beside the snowman and celebrates.'),
 ('Bobo makes a careful brush stroke on his painting, then glances down toward his hand.',
  'Bobo notices paint on his hand, smiles sheepishly, then proudly points at the painting and bows.'),
]

def caption_cues(captions, first_shot_duration, total=11):
 split=float(first_shot_duration)
 setup=min(2.0,split*.4)
 return [(captions[0],0,setup),(captions[1],setup,split),(captions[2],split,total)]

PROMOTION=[
 ("Bobo vs. one tiny bubble... who wins? 🫧😂","One little puff starts a very big reaction.","Would you chase it or let it pop?"),
 ("Big sandcastle dreams. Tiny bucket problems. 🏖️🐒","Bobo has a plan—and a bucket full of surprises.","What should he build next?"),
 ("Bobo's snack has an escape plan! 🍎😂","A peaceful picnic turns into a tiny apple chase.","Which picnic snack would Bobo love most?"),
 ("One more block... what could possibly happen? 🧱😆","Bobo's serious builder face deserves its own award.","Would you add another block?"),
 ("Bobo found a puddle. You know what's coming! 💦🐒","That innocent little step has splashy consequences.","Are you team splash or team stay dry?"),
 ("Someone gave Bobo a spaceship button... 🚀😂","Curiosity just got promoted to captain.","What would you name Bobo's spaceship?"),
 ("The tiniest snowball. The proudest monkey. ❄️🏆","Bobo takes his winter championship very seriously.","Does this little champion deserve a medal?"),
 ("Bobo's masterpiece comes with a messy surprise! 🎨😆","A little paint and a lot of confidence.","What should our little artist paint next?"),
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

def scene_effects(seconds, variant, first_shot_duration=5.0625):
 # Original scene-specific effects; never reuse eating sounds for other actions.
 rate=48000; audio=np.zeros(int(seconds*rate))
 split=float(first_shot_duration); rng=np.random.default_rng(variant+31)
 plans=[
  [('air',1.1,.3),('pop',split+.25,.12)],
  [('sand',2.4,.4),('sand',split+.25,.3),('chime',split+1,.35)],
  [('roll',2.5,.6),('tap',split+.3,.12),('chime',split+1,.3)],
  [('wood',2.3,.1),('wobble',3.3,.6),('wood',split+.35,.12)],
  [('splash',split+.3,.45),('splash',split+1.5,.3)],
  [('beep',split+.2,.15),('beep',split+.6,.15),('chime',split+1,.35)],
  [('snow',2.3,.4),('snow',split+.7,.3),('chime',split+1.4,.3)],
  [('brush',2.2,.5),('brush',split+.2,.3),('chime',split+1.5,.35)],
 ]
 for kind,start,length in plans[variant%8]:
  t=np.arange(int(length*rate))/rate; noise=rng.normal(0,1,len(t))
  smooth=np.convolve(noise,np.ones(12)/12,mode='same')
  env=np.sin(np.pi*t/length)**2
  if kind=='pop': signal=np.sin(2*np.pi*(750*t-1800*t*t))*np.exp(-t*45)+smooth*np.exp(-t*60)
  elif kind=='beep': signal=np.sin(2*np.pi*850*t)*env*.55
  elif kind=='chime': signal=(np.sin(2*np.pi*1047*t)+.4*np.sin(2*np.pi*1568*t))*np.exp(-t*9)*env
  elif kind=='wood' or kind=='tap': signal=(np.sin(2*np.pi*360*t)+smooth)*np.exp(-t*55)
  elif kind=='wobble': signal=np.sin(2*np.pi*(270*t+12*np.sin(2*np.pi*6*t)))*env*.4
  elif kind=='roll': signal=smooth*env*(.4+.6*np.sin(2*np.pi*12*t)**2)
  elif kind=='splash': signal=smooth*env+np.sin(2*np.pi*(600*t-350*t*t))*env*.15
  else: signal=smooth*env*.6
  signal=signal/max(1,float(np.max(np.abs(signal))))
  a=int(start*rate); z=min(len(audio),a+len(signal))
  if a<z: audio[a:z]+=signal[:z-a]*.35
 path=OUT/'scene_effects.wav'
 with wave.open(str(path),'wb') as wav:
  wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(rate)
  wav.writeframes((np.column_stack((audio,audio))*32767).astype('<i2').tobytes())
 return str(path)

def soundtrack(seconds, variant, first_shot_duration=5.0625):
 music=original_music(seconds,variant)
 effects=scene_effects(seconds,variant,first_shot_duration)
 mix=f'[0:a]loudnorm=I=-18:TP=-2:LRA=7,aresample=48000,afade=t=in:st=0:d=0.15,afade=t=out:st={seconds-.6}:d=0.6[m];[1:a]aformat=channel_layouts=stereo[fx];[m][fx]amix=inputs=2:duration=first:normalize=0,atrim=duration={seconds}[audio]'
 run(['ffmpeg','-loglevel','error','-y','-i',music,'-i',effects,'-filter_complex',mix,'-map','[audio]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(OUT/'audio.wav')])

def music_level(video):
 result=subprocess.run(['ffmpeg','-v','error','-ss','2','-t','1','-i',str(video),'-vn','-ac','1','-ar','48000','-f','f32le','-'],capture_output=True)
 samples=np.frombuffer(result.stdout,dtype='<f4') if result.returncode==0 else np.array([])
 if not samples.size: return -180.0
 return float(20*np.log10(max(float(np.sqrt(np.mean(samples**2))),1e-9)))

def ensure_audible_music(video, variant):
 level=music_level(video)
 if not np.isfinite(level) or level < -24:
  print('Automatically rebuilding quiet or missing soundtrack.')
  soundtrack(11,variant)
  repaired=video.with_name(video.stem+'-audio-repaired.mp4')
  run(['ffmpeg','-v','error','-y','-i',str(video),'-i',str(OUT/'audio.wav'),'-map','0:v:0','-map','1:a:0','-c:v','copy','-af','loudnorm=I=-16:TP=-1.5:LRA=7','-c:a','aac','-b:a','192k','-ar','48000','-t','11','-movflags','+faststart',str(repaired)])
  repaired.replace(video)
  level=music_level(video)
  if not np.isfinite(level) or level < -24:
   # Correct a remaining low level with bounded gain and a peak limiter.
   gain=min(24,max(0,-18-level))
   run(['ffmpeg','-v','error','-y','-i',str(video),'-map','0:v:0','-map','0:a:0','-c:v','copy','-af',f'volume={gain}dB,alimiter=limit=0.84:level=false','-c:a','aac','-b:a','192k','-t','11','-movflags','+faststart',str(repaired)])
   repaired.replace(video)
   level=music_level(video)
  if not np.isfinite(level) or level < -30:
   raise RuntimeError('Soundtrack repair failed: audio is missing or unreadable.')
 print(f'Exported music loudness between effects: {level:.1f} dBFS')
 return level

def main():
 token=os.getenv('HF_TOKEN','').strip()
 if not token: raise RuntimeError('HF_TOKEN is missing; a free Hugging Face account token is required.')
 now=datetime.now(ZoneInfo('Asia/Karachi'))
 quota_path=Path('bobo_quota.json')
 if quota_path.exists():
  pause=json.loads(quota_path.read_text())
  if now<datetime.fromisoformat(pause['retry_after']):
   print('Free generation quota unavailable until '+pause['retry_after']+'; no GPU request or Facebook upload attempted.'); return
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
 action,ending=ACTION_BEATS[scene_id]
 scene_reference=Path('assets/scenes')/f'scene{scene_id}.jpg'
 if not scene_reference.is_file(): raise RuntimeError('Missing verified scene image; refusing to reuse the cake reference.')
 shutil.copyfile(scene_reference,OUT/'reference.png')
 prompt=('High quality 3D animated family comedy. Animate this exact supplied scene in '+setting+'. Preserve the Bobo monkey and red shirt and the main prop '+prop+'. '+action+' Timing: establish the setup during seconds 0 to 2; show the main movement during seconds 2 to 5. Clear natural hand movement and expressive face, smooth motion, fixed camera. No cake, no kitchen, no extra characters, no text overlays. Complete the action within five seconds.')
 client=Client(SPACE, token=token, httpx_kwargs={'timeout':90})
 # Exactly two free-GPU requests per episode, with no paid fallback.
 clips=[]; shot_durations=[]
 for shot in range(2):
  shot_prompt=prompt if shot==0 else ('Continue this exact 3D cartoon scene from the supplied last frame. Same Bobo monkey and red shirt, same '+setting+' and '+prop+'. '+ending+' Smooth clear movements, fixed camera, no sudden scene changes. Complete in five seconds.')
  reference=OUT/('reference.png' if shot==0 else 'continuation.png')
  try:
   result=client.predict(input_image=handle_file(str(reference)),prompt=shot_prompt,steps=4,negative_prompt='blur, distorted hands, extra limbs, melting face, flicker, frozen frame, camera shake',duration_seconds=5,guidance_scale=1,guidance_scale_2=1,seed=(episode*2+shot)%2147483647,randomize_seed=False,api_name='/generate_video')
  except Exception as exc:
   message=str(exc)
   if 'quota' in message.lower():
    wait=re.search(r'Try again in (\d+):(\d+):(\d+)',message)
    if wait:
     hours,minutes,seconds=map(int,wait.groups())
     retry=now+timedelta(hours=hours,minutes=minutes,seconds=seconds+120)
     quota_path.write_text(json.dumps({'retry_after':retry.isoformat(),'reason':'Free ZeroGPU quota exhausted'},indent=2))
     print('Free quota exhausted; pausing requests until '+retry.isoformat())
   raise
  source=result[0]
  if isinstance(source,dict): source=source.get('video',source.get('path'))
  if not isinstance(source,str) or not Path(source).is_file(): raise RuntimeError('Generator did not return a video file.')
  clip=OUT/f'shot{shot}.mp4'; shutil.copyfile(source,clip); clips.append(clip)
  shot_info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(clip)]))
  shot_durations.append(float(shot_info['format']['duration']))
  if not 4.8<=float(shot_info['format']['duration'])<=5.5: raise RuntimeError('Invalid generated shot duration.')
  shot_raw=subprocess.check_output(['ffmpeg','-loglevel','error','-i',str(clip),'-vf','fps=1,scale=64:64,format=gray','-f','rawvideo','-'])
  sampled=np.frombuffer(shot_raw,dtype=np.uint8).reshape(-1,64,64).astype(float)
  if len(sampled)<4 or np.abs(np.diff(sampled,axis=0)).mean()<.5: raise RuntimeError('Static generated shot; skipping publication.')
  if shot==0: run(['ffmpeg','-loglevel','error','-y','-sseof','-0.1','-i',str(clip),'-frames:v','1',str(OUT/'continuation.png')])
 (OUT/'shots.txt').write_text(''.join(f"file '{p.name}'\n" for p in clips))
 run(['ffmpeg','-loglevel','error','-y','-f','concat','-safe','0','-i',str(OUT/'shots.txt'),'-an','-c:v','libx264','-preset','medium','-crf','16',str(OUT/'generated.mp4')])
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=width,height','-of','json',str(OUT/'generated.mp4')]))
 duration=float(info['format']['duration'])
 if not 9.5<=duration<=11: raise RuntimeError('Generated video duration is invalid.')
 # Reject static output using differences among four sampled frames.
 raw=subprocess.check_output(['ffmpeg','-loglevel','error','-i',str(OUT/'generated.mp4'),'-vf','fps=1,scale=64:64,format=gray','-f','rawvideo','-'])
 frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,64,64).astype(float)
 if len(frames)<4 or np.abs(np.diff(frames,axis=0)).mean()<.5: raise RuntimeError('Generated clip is static; skipping publication.')
 soundtrack(11,scene_id,shot_durations[0])
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
 filters=['hqdn3d=1.0:0.8:1.5:1.2','fps=30','scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos','crop=720:1280','tpad=stop_mode=clone:stop_duration=1.5']
 cues=caption_cues(captions,shot_durations[0])
 (OUT/'captions-timing.json').write_text(json.dumps([{'text':t,'start':a,'end':z} for t,a,z in cues],indent=2))
 (OUT/'captions.srt').write_text(''.join(str(i+1)+'\n'+'00:00:'+f'{a:06.3f}'.replace('.',',')+' --> 00:00:'+f'{z:06.3f}'.replace('.',',')+'\n'+t+'\n\n' for i,(t,a,z) in enumerate(cues)))
 # Textfiles avoid shell/filter escaping for captions.
 for i,(text,start,end,y,size) in enumerate([(title,0,1.5,150,36)]+[(t,a,z,1160,34) for t,a,z in cues]):
  path=OUT/f'text{i}.txt';path.write_text(text)
  filters.append(f"drawtext=fontfile={font}:textfile={path}:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=8:x=(w-text_w)/2:y={y}:enable='gte(t,{start})*lt(t,{end})'")
 run(['ffmpeg','-loglevel','error','-y','-i',str(OUT/'generated.mp4'),'-i',str(OUT/'audio.wav'),'-vf',','.join(filters),'-af','loudnorm=I=-16:TP=-1.5:LRA=7','-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','16','-c:a','aac','-b:a','192k','-ar','48000','-pix_fmt','yuv420p','-t','11','-movflags','+faststart',str(OUT/'bobo_fresh.mp4')])
 run(['ffmpeg','-v','error','-i',str(OUT/'bobo_fresh.mp4'),'-f','null','-'])
 music_db=ensure_audible_music(OUT/'bobo_fresh.mp4',scene_id)
 metadata={'episode':episode,'title':title,'space':SPACE,'generated_sha256':hashlib.sha256((OUT/'generated.mp4').read_bytes()).hexdigest(),'duration':11,'generated_at':now.isoformat(),'quality_reference':str(scene_reference),'music_check_dbfs':round(music_db,2),'export_fps':30,'effects':'original scene-specific effects; no bite sample','caption_timing':[{'text':t,'start':a,'end':z} for t,a,z in cues],'audio_mix_variant':scene_id,'scene_id':scene_id,'setting':setting,'music':'original procedural composition '+str(scene_id)}
 hook,teaser,question=PROMOTION[scene_id]
 social_caption=f"{hook}\n\n{teaser}\n{question}\n\n"+' '.join('#'+tag for tag in ['Bobo','3DAnimation']+scene_tags+[['FunnyCartoon'],['CartoonComedy'],['AnimatedShorts'],['FunnyAnimation']][scene_id%4])
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

