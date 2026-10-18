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
 ('Beach bucket surprise','a colorful sandy beach beside a little sandcastle','a small beach bucket','He tips his bucket to make a sandcastle, lifts it proudly, and looks surprised at the tiny result.','He admires his tiny sandcastle and gives a proud thumbs up.',['Big castle coming!','Careful... careful...','Tiny but mighty!'],['BeachComedy','Sandcastle']),
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
 ('The red apple is already rolling within the first half second. Bobo immediately reaches after it with lively natural movement and nearly catches it before it escapes again.',
  'Bobo catches the rolling apple with both hands within the first 1.5 seconds, then keeps the remaining shot active by showing it proudly, doing a relieved little bounce and sharing a playful look with the camera.'),
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


SERIES=['Bobo vs Everyday Things','Bobo Helps... Almost!','Bobo\'s Silly Inventions']
SERIES_LINES=[
 ['Too big for me!','Tiny castle, big dreams!','My snack is running!','One block too many!','My feet are wet!','Captain needs instructions!','Small ball, big champion!','I painted myself!'],
 ['Where did it go?','A tiny surprise!','Snack rescued!','Stay there, tower!','That tickles!','Oh, shiny lights!','Meet your little friend!','That is my masterpiece!'],
]

def comedy_series(slot,scene_id,episode):
 return {
  'name':SERIES[(episode//2)%len(SERIES)],
  'format':'Bobo\'s Mischief' if slot==0 else 'Bobo\'s Surprise',
  'voice_line':SERIES_LINES[slot%2][scene_id],
  'direction':(
   'Comedy structure: Bobo confidently attempts this simple task, makes a small believable mistake with the existing prop, then gives a sheepish funny reaction. Keep the gag readable and tied to the supplied scene.'
   if slot==0 else
   'Comedy structure: the existing object produces an unexpected small result, Bobo reacts with surprise, then treats the result with playful pride. Show a visible twist using only the existing props.'
  ),
  'follow_invitation':[
   'Follow for Bobo\'s next little adventure. 🌳🐒',
   'More tiny adventures with Bobo—follow along! 🐒✨',
   'Join Bobo Giggle Grove for the next giggle. 🌳😄',
  ][episode%3],
  'cost':0,
 }

MUSIC_STYLES=['soft marimba bounce','warm plucked strings','airy flute dance','muted piano shuffle','gentle bell waltz','round synth adventure','mellow electric keys','light pizzicato swing']

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
 tune=np.zeros(len(t)); v=variant%len(melodies); cycle=variant//len(melodies)
 beat=[.28,.34,.31,.25,.38,.27,.36,.30][v]*(1+0.025*(cycle%5))
 for n,start in enumerate(np.arange(0,seconds,beat)):
  note=melodies[v][(n+cycle)%len(melodies[v])]; freq=[220,196,330,247,294,165,262,233][v]*2**((note+cycle%5)/12)
  u=t-start; active=(u>=0)&(u<beat*.9); local=np.maximum(u,0)
  envelope=np.minimum(local/[.012,.008,.04,.014,.02,.03,.02,.008][v],1)*np.exp(-local*[11,14,5,9,7,6,8,16][v])
  phase=2*np.pi*freq*local
  partials=[(0.15,0,0),(0.28,0.12,0.06),(0.04,0,0),(0.22,0.08,0),(0,0.24,0.12),(0.35,0,0),(0.12,0.15,0),(0.32,0.16,0.08)][v]
  tone=np.sin(phase)+partials[0]*np.sin(2*phase)+partials[1]*np.sin(3*phase)+partials[2]*np.sin(4*phase)
  if v==4: tone=np.sin(phase)+.22*np.sin(2.76*phase)
  if v==5: tone=np.sin(phase+.8*np.sin(phase*.5))
  accent=[1,.6,.85,.55][n%4]
  tune+=active*envelope*tone*.19*accent
  if n%4==0:
   bass=np.sin(2*np.pi*(freq/2)*local)*np.minimum(local/.025,1)*np.exp(-local*9)
   tune+=active*bass*.045
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
  [('sand',2.4,.4),('sand',split+.25,.3)],
  [('roll',2.5,.6),('tap',split+.3,.12)],
  [('wood',2.3,.1),('wood_creak',3.3,.6),('wood',split+.35,.12)],
  [('splash',split+.3,.45),('splash',split+1.5,.3)],
  [('beep',split+.2,.15),('beep',split+.6,.15),('chime',split+1,.35)],
  [('snow',2.3,.4),('snow',split+.7,.3)],
  [('brush',2.2,.5),('brush',split+.2,.3)],
 ]
 observed_plan=OUT/'observed-effects.json'
 selected=json.loads(observed_plan.read_text()) if observed_plan.exists() else plans[variant%8]
 for kind,start,length in selected:
  t=np.arange(int(length*rate))/rate; noise=rng.normal(0,1,len(t))
  smooth=np.convolve(noise,np.ones(12)/12,mode='same')
  env=np.sin(np.pi*t/length)**2
  if kind=='pop': signal=smooth*(1-np.exp(-t/0.002))*np.exp(-t*65)
  elif kind=='beep': signal=np.sin(2*np.pi*850*t)*env*.55
  elif kind=='chime': signal=(np.sin(2*np.pi*1047*t)+.4*np.sin(2*np.pi*1568*t))*np.exp(-t*9)*env
  elif kind=='wood' or kind=='tap':
   attack=1-np.exp(-t/0.002)
   signal=(smooth*.7+np.sin(2*np.pi*190*t)*.12+np.sin(2*np.pi*430*t)*.05)*attack*np.exp(-t*55)
  elif kind=='wood_creak': signal=smooth*env*(.45+.15*np.sin(2*np.pi*9*t))
  elif kind=='roll': signal=smooth*env*(.4+.6*np.sin(2*np.pi*12*t)**2)
  elif kind=='splash':
   # Soft water wash and scattered droplets; no loud descending cartoon tone.
   water=np.convolve(noise,np.ones(48)/48,mode='same')
   water_env=(1-np.exp(-t/0.025))*np.exp(-t/0.13)*np.minimum((length-t)/0.06,1)
   signal=water*water_env
   for delay in (.055,.11,.18):
    u=np.maximum(t-delay,0)
    drop=np.sin(2*np.pi*(1100*u-900*u*u))*np.exp(-u*70)
    signal+=(t>=delay)*drop*.025
  else: signal=smooth*env*.6
  from bobo_foley import recorded_effect
  recorded=recorded_effect(kind,length,OUT)
  if recorded is not None: signal=recorded
  signal=signal/max(1,float(np.max(np.abs(signal))))
  a=int(start*rate); z=min(len(audio),a+len(signal))
  gain={'splash':.22,'pop':.28,'wood':.30,'tap':.24,'wood_creak':.28,'roll':.30,'sand':.28,'snow':.30,'brush':.24,'air':.25,'beep':.20,'chime':.18}.get(kind,.25)
  gain=min(gain,(.06 if kind=='splash' else .14)/max(float(np.max(np.abs(signal))),1e-9))
  if a<z: audio[a:z]+=signal[:z-a]*gain
 path=OUT/'scene_effects.wav'
 with wave.open(str(path),'wb') as wav:
  wav.setnchannels(2); wav.setsampwidth(2); wav.setframerate(rate)
  wav.writeframes((np.column_stack((audio,audio))*32767).astype('<i2').tobytes())
 return str(path)

def soundtrack(seconds, variant, first_shot_duration=5.0625, music_variant=None):
 music=original_music(seconds,variant if music_variant is None else music_variant)
 effects=scene_effects(seconds,variant,first_shot_duration)
 mix=f'[0:a]loudnorm=I=-18:TP=-2:LRA=7,aresample=48000,afade=t=in:st=0:d=0.15,afade=t=out:st={seconds-.6}:d=0.6,volume=0.80[m];[1:a]aformat=channel_layouts=stereo,asplit=2[fx][key];[m][key]sidechaincompress=threshold=0.035:ratio=3:attack=10:release=180[duck];[duck][fx]amix=inputs=2:duration=first:normalize=0,atrim=duration={seconds}[audio]'
 run(['ffmpeg','-loglevel','error','-y','-i',music,'-i',effects,'-filter_complex',mix,'-map','[audio]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(OUT/'audio.wav')])

def music_level(video):
 result=subprocess.run(['ffmpeg','-v','error','-ss','2','-t','1','-i',str(video),'-vn','-ac','1','-ar','48000','-f','f32le','-'],capture_output=True)
 samples=np.frombuffer(result.stdout,dtype='<f4') if result.returncode==0 else np.array([])
 if not samples.size: return -180.0
 return float(20*np.log10(max(float(np.sqrt(np.mean(samples**2))),1e-9)))

def ensure_audible_music(video, variant, music_variant=None):
 level=music_level(video)
 if not np.isfinite(level) or level < -24:
  print('Automatically rebuilding quiet or missing soundtrack.')
  soundtrack(11,variant,music_variant=music_variant)
  if (OUT/'dialogue-timing.json').exists() and (OUT/'voice-track.wav').exists():
   from bobo_voice import mix_voice
   mix_voice(OUT)
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
 from bobo_pipeline import approvals,next_episode
 reserve=approvals()
 if Path('bobo_review_pending.json').exists():
  pending=json.loads(Path('bobo_review_pending.json').read_text())
  if int(pending['episode']) not in reserve:
   print('Unreviewed draft exists: repair/review this artifact before spending more quota.'); return
 token=os.getenv('HF_TOKEN','').strip()
 if not token: raise RuntimeError('HF_TOKEN is missing; a free Hugging Face account token is required.')
 now=datetime.now(ZoneInfo('Asia/Karachi'))
 quota_path=Path('bobo_quota.json')
 if quota_path.exists():
  pause=json.loads(quota_path.read_text())
  if now<datetime.fromisoformat(pause['retry_after']):
   print('Free generation quota unavailable until '+pause['retry_after']+'; no GPU request or Facebook upload attempted.'); return
 ledger_path=Path('published_bobo.json')
 ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
 episode=next_episode(now,ledger,reserve)
 if episode is None:
  print('Four reviewed reserve entries ready; conserving free quota.'); return
 # Approved stories are selected in strict order, never by scene rotation.
 queue=json.loads(Path('bobo_ten_day_story_queue.json').read_text())
 published_serials={int(v['story_serial']) for v in ledger.values() if v.get('story_serial') and v.get('facebook_reel_id') and v.get('facebook_reel_verified') is True and v.get('instagram',{}).get('media_id') and v.get('instagram',{}).get('permalink')}
 serial=next((i for i in range(1,11) if i not in published_serials),None)
 if serial is None:
  print('All ten approved stories published.'); return
 story=next(s for s in queue['stories'] if int(s['serial'])==serial)
 slot=episode%2
 episode_key=f'long-v2-{episode}'
 if episode_key in ledger:
  print('This episode was already published; skipping generation and upload.'); return
 recent=[v.get('scene_id') for v in list(ledger.values())[-3:]]
 review_path=Path('bobo_review_approval.json')
 if review_path.exists():
  previous_review=json.loads(review_path.read_text())
  if previous_review.get('status')=='rejected' and previous_review.get('episode')==episode:
   recent.extend(previous_review.get('rejected_scene_ids',[previous_review.get('scene_id')]))
 scene_id=(now.toordinal()*2+slot)%len(SCENES)
 eligible=[n for n in (5,6,4,3,7,0,1,2) if n not in recent]
 if not eligible:
  print('All scenes exhausted for this episode; hold for repair rather than loop.'); return
 scene_id=eligible[0]
 board_path=Path('bobo_storyboard_pilot.json')
 board=json.loads(board_path.read_text()) if board_path.exists() else {}
 if board.get('episode')==episode and int(board.get('scene_id',-1)) not in recent:
  assert board.get('cost')==0 and len(board['shots'])==3
  scene_id=int(board['scene_id'])
 else: board={}
 title,setting,prop,action,ending,captions,scene_tags=SCENES[scene_id]
 simple=[
  ('Bobo gently moves the existing bubble wand left and right and follows it with his eyes.', 'Bobo lowers the wand, then playfully tries to balance it in his hand.'),
  ('Bobo pats sand in the existing bucket with his hand.', 'Bobo adjusts the bucket handle and gives it a playful little wobble without pouring or revealing anything.'),
  ('Bobo holds the existing apple and turns it slowly in his hands.', 'Bobo lifts the apple, then lowers it and gives a playful shoulder wiggle. No rolling, catching or eating.'),
  ('Bobo gently taps the existing wooden block with one finger.', 'Bobo moves his hand around the block and gives a little shoulder wiggle. No tower collapse or rescue.'),
  ('Bobo makes one small foot tap in the existing shallow puddle.', 'Bobo makes another small foot tap then steps beside the puddle. No large splash.'),
  ('Bobo immediately presses the existing toy button once and watches the existing lights.', 'Bobo points between the existing button and lights, then moves his hand away. No new objects.'),
  ('Bobo gently pats the existing snowball with both hands.', 'Bobo turns the snowball in his hands then carefully lowers it beside himself.'),
  ('Bobo moves his brush gently across the existing painting.', 'Bobo lifts the brush and examines its tip, then lowers it toward the palette. No new paint accident or reveal.'),
 ]
 action,ending=simple[scene_id]
 series=comedy_series(slot,scene_id,episode)
 series['direction']='One simple prop interaction; final joke and dialogue chosen after observing rendered action.'
 series['voice_line']=['Look at that!','Let us try!','My apple!','Careful now!','A puddle!','What is this?','My snowball!','Time to paint!'][scene_id]
 if board:
  title=board['title']; series['voice_line']=board['voice_line']
  action=board['shots'][0]['action']
  (OUT/'storyboard.json').write_text(json.dumps(board,indent=2))
 # Never substitute an unrelated scene for an approved serial story.
 if serial==2:
  scene_id=0
  setting='a colorful autumn garden path beneath a leafy tree'
  prop='a small yellow fabric umbrella and falling autumn leaves'
 if serial==1:
  scene_id=4
  setting='a cheerful garden path after rain with a tiny puddle'
  prop='a tiny puddle and bright yellow rain boots'
 title=story['title']
 action=' '.join(b['action'] for b in story['beats'][:2])
 ending=story['beats'][2]['action']
 series['voice_line']=(ending.split('Bobo says: ')[-1].split('Bobo whispers: ')[-1].strip() if ('Bobo says: ' in ending or 'Bobo whispers: ' in ending) else 'Oh wow!')
 scene_reference=(Path('assets/scenes/scene4.jpg') if serial==1 else Path('assets/story_queue')/f'story{serial:02d}.jpg' if serial==2 else Path('assets/story_queue')/f'story{serial:02d}.png')
 if not scene_reference.is_file():
  raise RuntimeError(f'Story {serial} missing matching Bobo reference at {scene_reference}; do not waste free quota on unrelated footage.')
 if not scene_reference.is_file(): raise RuntimeError('Missing verified scene image; refusing to reuse the cake reference.')
 shutil.copyfile(scene_reference,OUT/'reference.png')
 from bobo_voice import prepare_voice,mix_voice
 voice_record=prepare_voice(OUT,scene_id,start=8.15 if serial==1 else .35,text=series['voice_line'])
 voice_end=voice_record['cues'][0]['end']
 if serial==1:
  action=('Bobo bends his knees, JUMPS clearly into the air, and lands in his bright yellow boots beside the tiny puddle. Exactly ONE little droplet rises; NO large splash.')
  ending=('The ONE tiny droplet visibly arcs and lands on the TIP OF Bobo\'s NOSE. He looks cross-eyed at the droplet and smiles with comic pride.')
 prompt=('High quality 3D animated family comedy. Animate this exact supplied scene in '+setting+'. Preserve the Bobo monkey and red shirt and the main prop '+prop+'. '+action+' Timing: begin visible purposeful movement in the first half second; keep lively normal-speed movement throughout all four seconds, with a quick clear setup and no long pose or anticipatory pause. No slow motion. Clear natural hand movement and expressive face, smooth motion, fixed camera. Preserve clothing details exactly; do not add or change lettering on the shirt. Bobo says the brief English reaction "'+series['voice_line']+'" near the start: a brief natural speaking mouth movement during seconds 0.35 to '+str(voice_end)+', then keep lips closed for all remaining frames. No repeated open-close jaw motions outside this measured speech window. Use expressive gestures for the remaining physical comedy. No prolonged talking. No cake, no kitchen, no extra characters, no text overlays. Complete the action within four seconds.')
 client=Client(SPACE, token=token, httpx_kwargs={'timeout':90})
 # Provider caps each request at five seconds. Three four-second shots supply
 # active footage beyond eleven seconds without freeze padding or speed changes.
 clips=[]; shot_durations=[]
 for shot in range(3):
  shot_prompt=prompt if shot==0 else ('Continue this exact 3D cartoon scene from the supplied last frame. Same Bobo monkey and red shirt, same '+setting+' and '+prop+'. '+ending+' Preserve clothing details exactly; no added shirt lettering. Silent physical comedy with closed-lip smiles throughout. Keep lips closed in every frame; show surprise using eyebrows, eyes and body gestures. No jaw flapping, no open-mouth laughing, no talking or lip-sync mouth motions. Lively normal-speed action begins immediately and continues through the final frame, with a quick reaction and playful moving celebration; no slow motion or long frozen pose. Smooth clear movements, fixed camera, no sudden scene changes. Complete in four seconds.')
  if board:
   shot_prompt=('Original 3D Bobo family comedy. Preserve the supplied Bobo, red shirt, room and existing props. '+board['shots'][shot]['action']+' Required ending pose: '+board['shots'][shot]['end_pose']+' Fixed camera. Normal-speed purposeful action starts immediately. No added objects, no melting, no text, no prolonged pose. '+('Only one brief speaking window from 0.35 to '+str(voice_end)+' seconds; lips closed afterward.' if shot==0 else 'Lips closed throughout; express emotion with eyes, arms and shoulders. No talking or open-mouth laughter.'))
  if serial==1:
   if shot==0:
    shot_prompt=('High-quality 3D Bobo, red shirt and yellow rain boots, same sunny puddle garden. '
                 'He visibly bends knees and JUMPS into the air, landing by the tiny puddle. '
                 'Exactly ONE tiny drop starts to rise. NO talking, no big splash, no scene change.')
   elif shot==1:
    shot_prompt=('Continue same 3D Bobo, red shirt, yellow boots, same garden and puddle. '
                 'The SINGLE tiny droplet rises from the puddle, travels visibly toward his nose. '
                 'Bobo tracks it with his eyes. No big spray, no talking, natural motion.')
   else:
    shot_prompt=('Continue same 3D Bobo and same garden. Show the ONE tiny droplet visibly LAND '
                 'on the TIP of his NOSE. He looks cross-eyed at it and gives a delighted comic smile. '
                 'Keep the droplet visible. No scene change, smooth motion.')
    
    shot_prompt += (
        " MANDATORY ANIMATION QUALITY RULES: "
        "Show every requested physical action clearly on screen. "
        "Do not skip, replace, or merely imply an action. "
        "Show preparation, movement, physical contact, "
        "and the resulting reaction in the correct sequence. "
        "Keep Bobo's face, golden-brown fur, red shirt, "
        "body proportions, and scene consistent. "
        "Use smooth natural 3D animation and expressive eyes. "
        "Do not freeze, teleport props, repeat movements, "
        "or introduce unrelated objects. "
        "Complete the required action before the shot ends. "
        "Preserve continuity with the next shot."
  )
  reference=OUT/('reference.png' if shot==0 else 'continuation.png')
  try:
   result=client.predict(input_image=handle_file(str(reference)),prompt=shot_prompt,steps=4,negative_prompt='blur, distorted hands, extra limbs, melting face, flicker, frozen frame, camera shake, repeated talking, jaw flapping, open mouth laughter',duration_seconds=4,guidance_scale=1,guidance_scale_2=1,seed=(episode*2+shot)%2147483647,randomize_seed=False,api_name='/generate_video')
  except Exception as exc:
   message=str(exc)
   if 'quota' in message.lower() or 'zerogpu runs limit' in message.lower():
    wait=re.search(r'Try again in (\d+):(\d+):(\d+)',message)
    if wait:
     hours,minutes,seconds=map(int,wait.groups())
     retry=now+timedelta(hours=hours,minutes=minutes,seconds=seconds+120)
     quota_path.write_text(json.dumps({'retry_after':retry.isoformat(),'reason':'Free ZeroGPU quota exhausted'},indent=2))
     print('Free quota exhausted; pausing requests until '+retry.isoformat())
    else:
     retry=datetime.now(ZoneInfo('Asia/Karachi'))+timedelta(hours=1)
     quota_path.write_text(json.dumps({'retry_after':retry.isoformat(),'reason':'Provider ZeroGPU quota/runs limit; reset time not supplied','retry_is_backoff_not_reset':True},indent=2))
     print('Provider limit confirmed; one-hour retry backoff, not a promised quota reset.')
   raise
  source=result[0]
  if isinstance(source,dict): source=source.get('video',source.get('path'))
  if not isinstance(source,str) or not Path(source).is_file(): raise RuntimeError('Generator did not return a video file.')
  clip=OUT/f'shot{shot}.mp4'; shutil.copyfile(source,clip); clips.append(clip)
  shot_info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','json',str(clip)]))
  shot_durations.append(float(shot_info['format']['duration']))
  if not 3.8<=float(shot_info['format']['duration'])<=4.5: raise RuntimeError('Invalid generated shot duration; no freeze padding allowed.')
  shot_raw=subprocess.check_output(['ffmpeg','-loglevel','error','-i',str(clip),'-vf','fps=1,scale=64:64,format=gray','-f','rawvideo','-'])
  sampled=np.frombuffer(shot_raw,dtype=np.uint8).reshape(-1,64,64).astype(float)
  if len(sampled)<4 or np.abs(np.diff(sampled,axis=0)).mean()<.5: raise RuntimeError('Static generated shot; skipping publication.')
  if shot<2: run(['ffmpeg','-loglevel','error','-y','-sseof','-0.1','-i',str(clip),'-frames:v','1',str(OUT/'continuation.png')])
 (OUT/'shots.txt').write_text(''.join(f"file '{p.name}'\n" for p in clips))
 run(['ffmpeg','-loglevel','error','-y','-f','concat','-safe','0','-i',str(OUT/'shots.txt'),'-an','-c:v','libx264','-preset','medium','-crf','16',str(OUT/'generated.mp4')])
 info=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=width,height','-of','json',str(OUT/'generated.mp4')]))
 duration=float(info['format']['duration'])
 if duration<11: raise RuntimeError('Insufficient active footage for eleven seconds; no freeze padding allowed.')
 # Reject static output using differences among four sampled frames.
 raw=subprocess.check_output(['ffmpeg','-loglevel','error','-i',str(OUT/'generated.mp4'),'-vf','fps=1,scale=64:64,format=gray','-f','rawvideo','-'])
 frames=np.frombuffer(raw,dtype=np.uint8).reshape(-1,64,64).astype(float)
 if len(frames)<4 or np.abs(np.diff(frames,axis=0)).mean()<.5: raise RuntimeError('Generated clip is static; skipping publication.')
 # Separate music choice from the scene; avoid the last three published arrangements.
 recent_music={v.get('music_variant',v.get('audio_mix_variant')) for v in list(ledger.values())[-3:]}
 music_variant=(episode*5+scene_id)%64
 while music_variant in recent_music or music_variant%8 in {v%8 for v in recent_music if isinstance(v,int)}:
  music_variant=(music_variant+1)%64
 soundtrack(11,scene_id,shot_durations[0],music_variant=music_variant)
 from bobo_voice import prepare_voice,mix_voice
 if not voice_record.get('enabled'):
  raise RuntimeError('Bobo voice is required for every video; holding silent draft.')
 mix_voice(OUT)
 font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
 filters=['hqdn3d=1.0:0.8:1.5:1.2','fps=30','scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos','crop=720:1280']
 # No invented action captions. Add only after observing source footage.
 cues=[]
 if voice_record['enabled']:
  from bobo_voice import subtitle_cues
  cues=subtitle_cues(cues,voice_record)
 (OUT/'captions-timing.json').write_text(json.dumps([{'text':t,'start':a,'end':z} for t,a,z in cues],indent=2))
 (OUT/'captions.srt').write_text(''.join(str(i+1)+'\n'+'00:00:'+f'{a:06.3f}'.replace('.',',')+' --> 00:00:'+f'{z:06.3f}'.replace('.',',')+'\n'+t+'\n\n' for i,(t,a,z) in enumerate(cues)))
 # Textfiles avoid shell/filter escaping for captions.
 for i,(text,start,end,y,size) in enumerate([(title,0,1.5,150,36)]+[(t,a,z,1160,34) for t,a,z in cues]):
  path=OUT/f'text{i}.txt';path.write_text(text)
  filters.append(f"drawtext=fontfile={font}:textfile={path}:fontsize={size}:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=8:x=(w-text_w)/2:y={y}:enable='gte(t,{start})*lt(t,{end})'")
 run(['ffmpeg','-loglevel','error','-y','-i',str(OUT/'generated.mp4'),'-i',str(OUT/'audio.wav'),'-vf',','.join(filters),'-af','loudnorm=I=-16:TP=-1.5:LRA=7','-map','0:v:0','-map','1:a:0','-c:v','libx264','-preset','medium','-crf','16','-c:a','aac','-b:a','192k','-ar','48000','-pix_fmt','yuv420p','-t','11','-movflags','+faststart',str(OUT/'bobo_fresh.mp4')])
 run(['ffmpeg','-v','error','-i',str(OUT/'bobo_fresh.mp4'),'-f','null','-'])
 music_db=ensure_audible_music(OUT/'bobo_fresh.mp4',scene_id,music_variant=music_variant)
 metadata={'episode':episode,'title':title,'space':SPACE,'generated_sha256':hashlib.sha256((OUT/'generated.mp4').read_bytes()).hexdigest(),'duration':11,'generated_at':now.isoformat(),'quality_reference':str(scene_reference),'music_check_dbfs':round(music_db,2),'export_fps':30,'effects':'original scene-specific effects; no bite sample','voice':voice_record,'voice_review_required':voice_record['enabled'],'caption_kind':'spoken subtitle plus separate action captions' if voice_record['enabled'] else 'action captions; no spoken dialogue','caption_review_required':True,'caption_timing':[{'text':t,'start':a,'end':z} for t,a,z in cues],'audio_mix_variant':scene_id,'scene_id':scene_id,'setting':setting,'music':'original procedural composition '+str(scene_id)}
 metadata.update(music_variant=music_variant,music_style=MUSIC_STYLES[music_variant%8],music='original procedural arrangement '+str(music_variant),sound_design_version=3,pacing_review_required=True)
 metadata['story_serial']=serial
 metadata['approved_story_beats']=story['beats']
 metadata.update(production_strategy='observe-repair-reserve-v1',finishing_required=True,planned_effects_unverified=True,reserve_target=4)
 hook,teaser,question=PROMOTION[scene_id]
 follow_line=series['follow_invitation']
 teaser=series['format']+' • '+series['name']+'\n'+teaser
 metadata['comedy_series']=series
 social_caption=f"{hook}\n\n{teaser}\n{question}\n{follow_line}\n\n"+' '.join('#'+tag for tag in ['Bobo','3DAnimation']+scene_tags+[['FunnyCartoon'],['CartoonComedy'],['AnimatedShorts'],['FunnyAnimation']][scene_id%4])
 social_caption=f"{title} 🐒✨\\n{ending}\\nFollow Bobo Giggle Grove for the next adventure. 🌳🐒\\n#Bobo #3DAnimation #AnimatedShorts"
 # Legacy storyboard captions must not override approved serial stories.
 if False and board:
  social_caption=board['social_caption']
  metadata['storyboard_version']=board['version']
  metadata['planned_shot_evidence']=[s['required_evidence'] for s in board['shots']]
 metadata['social_caption']=social_caption
 metadata['growth_experiment']={'version':'tiny-comedy-series-v2','evidence_snapshot':'2026-10-13T23:43:42+05:00','content_change':'Morning mischief and evening surprise formats with rotating series identity and short scene-specific reaction dialogue; evaluate at comparable ages without causal claims','promotion_change':'one concise follow invitation after the scene-specific question','primary_metrics':['post_video_retention_graph','blue_reels_play_count','fb_reels_total_plays','followers_count'],'cost':0}
 (OUT/'facebook-caption.txt').write_text(social_caption)
 (OUT/'episode.json').write_text(json.dumps(metadata,indent=2))
 print(f'New episode created: {title}. No paid API used.')
 # Automated zero-cost technical finishing review. Visual story actions remain human-review gated.
 technical_report={'status':'technical_review_pending','repairs':[],'checks':{}}
 final_video=OUT/'bobo_fresh.mp4'
 final_probe=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_type,width,height','-of','json',str(final_video)]))
 final_duration=float(final_probe['format']['duration'])
 streams=final_probe.get('streams',[])
 video_stream=next((s for s in streams if s.get('codec_type')=='video'),None)
 audio_stream=next((s for s in streams if s.get('codec_type')=='audio'),None)
 technical_report['checks'].update(duration_seconds=final_duration,has_video=bool(video_stream),has_audio=bool(audio_stream))
 if not (10.9<=final_duration<=11.1) or not video_stream or not audio_stream:
  raise RuntimeError('Technical review failed: video must contain 11 seconds of picture and sound.')
 if (video_stream.get('width'),video_stream.get('height'))!=(720,1280):
  fixed=OUT/'reframed.mp4'
  run(['ffmpeg','-loglevel','error','-y','-i',str(final_video),'-vf','scale=720:1280:force_original_aspect_ratio=increase,crop=720:1280','-c:v','libx264','-preset','medium','-crf','16','-c:a','copy',str(fixed)])
  fixed.replace(final_video)
  technical_report['repairs'].append('normalized vertical framing to 720x1280')
 for cue in json.loads((OUT/'captions-timing.json').read_text()):
  if not (0<=float(cue['start'])<float(cue['end'])<=11):
   raise RuntimeError('Subtitle timing invalid: hold for repair, do not publish.')
 technical_report['checks']['subtitle_timing_valid']=True
 run(['ffmpeg','-v','error','-i',str(final_video),'-f','null','-'])
 technical_report['checks']['decodes_without_errors']=True
 technical_report['final_sha256']=hashlib.sha256(final_video.read_bytes()).hexdigest()
 technical_report['status']='technical_pass_visual_review_required'
 (OUT/'automatic-review.json').write_text(json.dumps(technical_report,indent=2))
 print('Automatic technical review passed; visual action review still required.')
 # All generated videos require a separate publication review.
 Path('bobo_review_pending.json').write_text(json.dumps({'episode':episode,'title':title,'generated_sha256':metadata['generated_sha256'],'status':'awaiting_visual_audio_review','artifact_run_id':os.getenv('GITHUB_RUN_ID'),'created_at':now.isoformat()},indent=2))
 print('REVIEW REQUIRED: saved draft; no Facebook upload attempted.')
 return
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
