"""Publish one user-authorized Bobo still without changing video cadence."""
import hashlib,json,os,subprocess,time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import requests

p=Path('bobo_photo_request.json')
a=json.loads(p.read_text())
assert a['id']=='bobo-thinking-2026-10-16'
assert a['source_run_id']==38935041435
assert a['source_sha256']=='03faffe1a940cfdbed9e124835e21ed0918040d2f08dbe0fc0cea8ebd9ecd85b'
v=Path('photo_source/bobo_fresh.mp4')
assert hashlib.sha256(v.read_bytes()).hexdigest()==a['source_sha256']
subprocess.run(['ffmpeg','-v','error','-y','-ss','8','-i',str(v),'-frames:v','1','-vf','crop=720:900:0:100','bobo-photo.jpg'],check=True)
photo=Path('bobo-photo.jpg')
ledger_path=Path('bobo_photo_posts.json')
ledger=json.loads(ledger_path.read_text()) if ledger_path.exists() else {}
if a['id'] in ledger:
    print('Photo request already attempted; refusing duplicate.')
    raise SystemExit(0)
record={'source_run_id':a['source_run_id'],'source_sha256':a['source_sha256'],'frame_seconds':8,'crop':'720:900:0:100','caption':a['caption'],'photo_sha256':hashlib.sha256(photo.read_bytes()).hexdigest(),'created_at':datetime.now(ZoneInfo('Asia/Karachi')).isoformat()}
ledger[a['id']]=record
def save():
    ledger_path.write_text(json.dumps(ledger,indent=2))
    subprocess.run(['git','add',str(ledger_path)],check=True)
    if subprocess.run(['git','diff','--cached','--quiet']).returncode==0:return
    subprocess.run(['git','commit','-m','Record authorized Bobo photo publication status'],check=True)
    subprocess.run(['git','pull','--rebase','--autostash','origin','main'],check=True)
    subprocess.run(['git','push','origin','HEAD:main'],check=True)
session=requests.Session()
session.headers['Authorization']='Bearer '+os.environ['FB_PAGE_ACCESS_TOKEN']
base='https://graph.facebook.com/v26.0/'
def api(method,path,**kw):
    r=session.request(method,base+path,timeout=60,**kw)
    try:d=r.json()
    except ValueError:raise RuntimeError('Unreadable platform response; no automatic retry')
    if not r.ok or d.get('error'):
        e=d.get('error',{})
        raise RuntimeError('Platform error code '+str(e.get('code'))+' subcode '+str(e.get('error_subcode')))
    return d
record['facebook']={'status':'attempt_started'};save()
try:
    with photo.open('rb') as f:
        d=api('POST',os.environ['FB_PAGE_ID']+'/photos',files={'source':('bobo-photo.jpg',f,'image/jpeg')},data={'message':a['caption'],'published':'true'})
    assert d.get('id')
    photo_id=str(d['id'])
    record['facebook'].update(status='accepted',photo_id=photo_id,post_id=d.get('post_id'),url='https://www.facebook.com/photo/?fbid='+photo_id);save()
    # Facebook's published photo supplies a public image URL for Instagram.
    info=api('GET',photo_id,params={'fields':'images'})
    image_url=info['images'][0]['source']
    page=api('GET',os.environ['FB_PAGE_ID'],params={'fields':'instagram_business_account'})
    account=page['instagram_business_account']['id']
    assert api('GET',account,params={'fields':'username'})['username']=='bobogigglegrove'
    record['instagram']={'status':'attempt_started'};save()
    d=api('POST',account+'/media',data={'image_url':image_url,'caption':a['caption']})
    container=str(d['id'])
    record['instagram'].update(container_id=container,status='processing');save()
    for _ in range(20):
        status=api('GET',container,params={'fields':'status_code'})['status_code']
        if status=='FINISHED':break
        if status in ('ERROR','EXPIRED'):raise RuntimeError('Instagram photo container '+status)
        time.sleep(3)
    else:raise RuntimeError('Instagram photo processing timeout')
    record['instagram']['status']='publish_started';save()
    d=api('POST',account+'/media_publish',data={'creation_id':container})
    assert d.get('id')
    record['instagram'].update(status='accepted',media_id=str(d['id']));save()
    info=api('GET',str(d['id']),params={'fields':'permalink'})
    record['instagram']['url']=info.get('permalink');save()
    print('Facebook and Instagram accepted authorized Bobo photo.')
except Exception as exc:
    kind='instagram' if record.get('facebook',{}).get('status')=='accepted' else 'facebook'
    if record.get(kind,{}).get('status')!='accepted':
        record.setdefault(kind,{}).update(status='held',reason=str(exc)[:180]);save()
    raise
