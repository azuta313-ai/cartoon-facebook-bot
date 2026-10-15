"""CPU-only finishing of an observed source artifact; no video generation."""
import hashlib,json,shutil,subprocess
from pathlib import Path
import fresh_bobo as generator
from bobo_voice import prepare_voice,mix_voice

def finish(source, plan, output):
    source=Path(source); output=Path(output)
    assert plan.get('observed_from_full_render') is True
    assert hashlib.sha256((source/'bobo_fresh.mp4').read_bytes()).hexdigest()==plan['source_sha256']
    metadata=json.loads((source/'episode.json').read_text())
    assert int(metadata['episode'])==int(plan['episode'])
    raw=source/'generated.mp4'
    duration=float(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration','-of','csv=p=0',str(raw)]))
    assert duration>=10.95, 'No frozen padding for insufficient footage'
    actions=plan['observed_actions']
    assert actions and plan.get('purposeful_action_by',1)<=.5
    def bounds(name):
        start,end=map(float,actions[name]); assert 0<=start<end<=11
        return start,end
    cue=plan['speech']; begin,end=bounds(cue['observed_action'])
    assert begin<=float(cue['start'])<end and cue.get('mouth_window_observed') is True
    output.mkdir(parents=True,exist_ok=True)
    for path in source.iterdir():
        if path.is_file(): shutil.copyfile(path,output/path.name)
    generator.OUT=output
    voice=prepare_voice(output,metadata['scene_id'],start=float(cue['start']),text=cue['text'])
    assert voice['cues'][0]['end']<=end+.05, 'Speech extends outside observed mouth window'
    effects=[]
    for effect in plan['effects']:
        start,end=bounds(effect['observed_action'])
        assert start-.05<=effect['start']<=end+.05
        assert effect.get('source') and effect.get('material_matched') is True
        assert effect['type'] in ('sand','snow','brush','wood','wood_creak','tap','roll','splash','pop','air','beep')
        if effect['type']=='beep': assert effect.get('visible_electronics') is True
        effects.append([effect['type'],effect['start'],effect['duration']])
    (output/'observed-effects.json').write_text(json.dumps(effects))
    generator.soundtrack(11,metadata['scene_id'],music_variant=metadata['music_variant'])
    mix_voice(output)
    captions=[dict(text=cue['text'],start=voice['cues'][0]['start'],end=voice['cues'][0]['end'])]
    for caption in plan['captions']:
        start,end=bounds(caption['observed_action'])
        assert start<=caption['start']<caption['end']<=end
        assert caption['end']<=cue['start'] or caption['start']>=voice['cues'][0]['end']+.08
        if caption.get('outcome'): assert caption['start']>=caption['result_visible_at']
        captions.append({k:caption[k] for k in ('text','start','end')})
    filters=['fps=30','scale=720:1280:force_original_aspect_ratio=increase:flags=lanczos','crop=720:1280']
    font='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
    for index,caption in enumerate(captions):
        text=output/f'finish-caption-{index}.txt'; text.write_text(caption['text'])
        filters.append(f"drawtext=fontfile={font}:textfile={text}:fontsize=34:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=8:x=(w-text_w)/2:y=1160:enable='gte(t,{caption['start']})*lt(t,{caption['end']})'")
    subprocess.run(['ffmpeg','-v','error','-y','-i',str(raw),'-i',str(output/'audio.wav'),'-vf',','.join(filters),'-map','0:v:0','-map','1:a:0','-af','loudnorm=I=-16:TP=-1.5:LRA=7','-c:v','libx264','-crf','16','-pix_fmt','yuv420p','-c:a','aac','-b:a','192k','-t','11','-movflags','+faststart',str(output/'bobo_fresh.mp4')],check=True)
    metadata.update(voice=voice,caption_timing=captions,social_caption=plan['social_caption'],finishing_required=False,planned_effects_unverified=False,observed_effects=plan['effects'],review_required=True,finishing_source_sha256=plan['source_sha256'])
    def stamp(value):
        milliseconds=round(float(value)*1000)
        return f"00:00:{milliseconds//1000:02d},{milliseconds%1000:03d}"
    (output/'captions.srt').write_text(''.join(str(i+1)+'\n'+stamp(x['start'])+' --> '+stamp(x['end'])+'\n'+x['text']+'\n\n' for i,x in enumerate(captions)))
    (output/'facebook-caption.txt').write_text(plan['social_caption'])
    (output/'episode.json').write_text(json.dumps(metadata,indent=2))
    (output/'captions-timing.json').write_text(json.dumps(captions,indent=2))
    (output/'observed-finishing-plan.json').write_text(json.dumps(plan,indent=2))
    print('Repaired artifact rendered. Full review of new SHA required; not approved.')

if __name__=='__main__':
    finish('source',json.loads(Path('bobo_finishing_plan.json').read_text()),'fresh_output')
