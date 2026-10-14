"""Publish only an already reviewed Bobo file to the connected Instagram."""
import hashlib,json,os,subprocess,time
from pathlib import Path
from urllib.parse import urlparse
import requests

def main():
    a=json.loads(Path('bobo_review_approval.json').read_text())
    ledger_path=Path('published_bobo.json')
    ledger=json.loads(ledger_path.read_text()); key='long-v2-'+str(a['episode'])
    record=ledger[key]; video=Path('reviewed/bobo_fresh.mp4')
    assert a['status']=='approved' and a['review']['reviewed_sha256']==a['final_sha256']
    assert record.get('facebook_video_id') and record['final_sha256']==a['final_sha256']
    assert hashlib.sha256(video.read_bytes()).hexdigest()==a['final_sha256']
    if record.get('instagram'):
        print('Instagram attempt already recorded; refusing duplicate.')
        return
    session=requests.Session()
    token=os.environ['FB_PAGE_ACCESS_TOKEN']
    session.headers['Authorization']='Bearer '+token
    base='https://graph.facebook.com/v26.0/'
    def request(method,path,**kwargs):
        response=session.request(method,base+path,timeout=45,**kwargs)
        data=response.json()
        if not response.ok or data.get('error'):
            error=data.get('error',{})
            raise RuntimeError('Instagram API error code '+str(error.get('code'))+' subcode '+str(error.get('error_subcode')))
        return data
    page=request('GET',os.environ['FB_PAGE_ID'],params={'fields':'instagram_business_account'})
    account=page.get('instagram_business_account',{}).get('id')
    if not account:
        raise RuntimeError('Connected Instagram account is not visible to Page token; authorize instagram_basic and instagram_content_publish.')
    info=request('GET',account,params={'fields':'username'})
    assert info.get('username')=='bobogigglegrove', 'Connected Instagram username differs; refusing wrong-account upload'
    def save():
        ledger_path.write_text(json.dumps(ledger,indent=2))
        subprocess.run(['git','add','published_bobo.json'],check=True)
        subprocess.run(['git','commit','-m','Record exact reviewed Bobo Instagram status'],check=True)
        subprocess.run(['git','pull','--rebase','origin','main'],check=True)
        subprocess.run(['git','push','origin','HEAD:main'],check=True)
    record['instagram']={'status':'attempt_started','source_sha256':a['final_sha256']}
    save()
    try:
        result=request('POST',account+'/media',data={'media_type':'REELS','upload_type':'resumable','caption':record['social_caption'],'share_to_feed':'true'})
        container=str(result['id']); uri=result.get('uri') or result.get('upload_uri')
        assert uri, 'Instagram did not supply upload URI'
        parsed=urlparse(uri)
        assert parsed.scheme=='https' and parsed.hostname=='rupload.facebook.com'
        record['instagram'].update(container_id=container,status='upload_started');save()
        with video.open('rb') as source:
            response=requests.post(uri,headers={'Authorization':'OAuth '+token,'offset':'0','file_size':str(video.stat().st_size),'Content-Type':'application/octet-stream'},data=source,timeout=120)
        assert response.ok and response.json().get('success'), 'Instagram did not confirm binary upload'
        for _ in range(30):
            status=request('GET',container,params={'fields':'status_code'}).get('status_code')
            if status=='FINISHED':break
            if status in ('ERROR','EXPIRED'):raise RuntimeError('Instagram container '+status)
            time.sleep(3)
        else:raise RuntimeError('Instagram processing timed out; no duplicate retry')
        record['instagram']['status']='publish_started';save()
        result=request('POST',account+'/media_publish',data={'creation_id':container})
        assert result.get('id'), 'Instagram acceptance missing'
        record['instagram'].update(status='accepted',media_id=str(result['id']));save()
        info=request('GET',str(result['id']),params={'fields':'permalink'})
        record['instagram']['permalink']=info.get('permalink');save()
        print('Instagram accepted reviewed Reel:',result['id'])
    except Exception as exc:
        record['instagram'].update(status='held',reason=str(exc)[:200]);save()
        raise

if __name__=='__main__':
    main()
