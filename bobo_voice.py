"""Free local CPU voice for Bobo; no hosted inference, keys or paid fallback."""
import hashlib,json,subprocess,wave
from pathlib import Path
import numpy as np
VOICE_MODEL='en_US-ljspeech-medium.onnx'
LINES=['Look at that!','Let us try!','My apple!','Careful now!','A puddle!','What is this?','My snowball!','Time to paint!']

def run(args):
    subprocess.run(args,check=True)

def prepare_voice(out,scene_id,total=11,start=.35,text=None):
    from piper import PiperVoice
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    model=Path('voice_models')/VOICE_MODEL
    if not model.is_file():
        raise RuntimeError('Free local voice model missing; no paid fallback permitted.')
    text=LINES[scene_id%8] if text is None else text
    if not isinstance(text,str) or not text.strip() or len(text)>90:
        raise RuntimeError('Bobo dialogue must be one short scene-specific line.')
    raw=out/'voice-raw.wav'
    voice=PiperVoice.load(str(model),use_cuda=False)
    with wave.open(str(raw),'wb') as wav:
        voice.synthesize_wav(text,wav)
    clip=out/'voice-line.wav'
    # Small pitch lift for a consistent cartoon voice; retain intelligibility.
    run(['ffmpeg','-v','error','-y','-i',str(raw),'-af',
         'silenceremove=start_periods=1:start_duration=0.02:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_duration=0.02:start_threshold=-45dB,areverse,asetrate=25357,aresample=48000,loudnorm=I=-17:TP=-2:LRA=7',
         '-ar','48000','-ac','2','-c:a','pcm_s16le',str(clip)])
    with wave.open(str(clip),'rb') as wav:
        rate=wav.getframerate(); channels=wav.getnchannels()
        samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').reshape(-1,channels)
    duration=len(samples)/rate
    if not .25<duration<2.5:
        raise RuntimeError('Spoken line duration outside reviewed short-line limit.')
    rms=float(np.sqrt(np.mean((samples.astype(float)/32768)**2)))
    if rms<.015:
        raise RuntimeError('Spoken line missing or too quiet.')
    track=np.zeros((round(total*rate),channels),dtype='<i2')
    offset=round(start*rate); track[offset:offset+len(samples)]=samples
    full=out/'voice-track.wav'
    with wave.open(str(full),'wb') as wav:
        wav.setnchannels(channels);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(track.tobytes())
    cue={'text':text,'start':start,'end':round(start+duration,4),'kind':'spoken dialogue','placement':'provisional; requires actual rendered mouth/action review'}
    record={'enabled':True,'engine':'Piper local CPU','model':VOICE_MODEL,'model_sha256':hashlib.sha256(model.read_bytes()).hexdigest(),
            'voice_sha256':hashlib.sha256(clip.read_bytes()).hexdigest(),'language':'en-US','pitch_factor':1.15,'cost':0,
            'lip_sync_verified':False,'listening_verified':False,'cues':[cue],
            'license':'Piper GPL-3.0; voice repository MIT; LJ Speech source public domain',
            'license_source':'https://huggingface.co/rhasspy/piper-voices/blob/main/en/en_US/ljspeech/medium/MODEL_CARD'}
    (out/'dialogue-timing.json').write_text(json.dumps(record,indent=2))
    return record

def mix_voice(out,total=11):
    out=Path(out); target=out/'audio-voiced.wav'
    # Use the measured cue window for reliable ducking. A sidechain driven by a
    # short stream can truncate the bed on some ffmpeg builds.
    dialogue=json.loads((out/'dialogue-timing.json').read_text())
    cue=dialogue['cues'][0]
    with wave.open(str(out/'voice-track.wav'),'rb') as wav:
        rate=wav.getframerate(); channels=wav.getnchannels()
        samples=np.frombuffer(wav.readframes(wav.getnframes()),dtype='<i2').astype(float).reshape(-1,channels)/32768
    speech=samples[round(float(cue['start'])*rate):round(float(cue['end'])*rate)]
    rms=float(np.sqrt(np.mean(speech*speech)))
    peak=float(np.max(np.abs(speech)))
    if rms<.015:
        raise RuntimeError('Mandatory Bobo speech is silent or too quiet.')
    # Aim for clear speech while retaining peak headroom.
    voice_gain=min(2.5,max(1.0,.12/rms),.75/max(peak,1e-9))
    duck_start=max(0,float(cue['start'])-.10)
    duck_end=min(float(total),float(cue['end'])+.16)
    graph=(f"[0:a]apad=whole_dur={total},atrim=duration={total},"
           f"volume=enable='between(t,{duck_start:.4f},{duck_end:.4f})':volume=0.22[bed];"
           f"[1:a]volume={voice_gain:.5f},apad=whole_dur={total},atrim=duration={total}[voice];"
           f"[bed][voice]amix=inputs=2:normalize=0:duration=first,"
           f"alimiter=limit=0.84:level=false:latency=true,"
           f"apad=whole_dur={total},atrim=duration={total}[out]")
    run(['ffmpeg','-v','error','-y','-i',str(out/'audio.wav'),'-i',str(out/'voice-track.wav'),'-filter_complex',graph,'-map','[out]','-ar','48000','-ac','2','-c:a','pcm_s16le',str(target)])
    target.replace(out/'audio.wav')

def subtitle_cues(actions,dialogue):
    cue=dialogue['cues'][0]
    # Never put an action caption on screen over the spoken subtitle.
    result=[(cue['text'],cue['start'],cue['end'])]
    for text,start,end in actions:
        start=max(start,cue['end']+.08)
        if end-start>=.3:
            result.append((text,start,end))
    return result
