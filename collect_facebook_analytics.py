"""Read-only Facebook analytics; keep reports in private workflow artifacts."""
import json, os, io, zipfile, re
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import requests
OUT=Path('analytics_output'); OUT.mkdir(exist_ok=True)
now=datetime.now(ZoneInfo('Asia/Karachi'))
session=requests.Session()
session.headers['Authorization']='Bearer '+os.environ['FB_PAGE_ACCESS_TOKEN']
BASE='https://graph.facebook.com/v26.0/'
def get(path, params):
    try:
        response=session.get(BASE+path,params=params,timeout=45)
        data=response.json()
        if not response.ok or 'error' in data:
            e=data.get('error',{})
            return {'unavailable':True,'code':e.get('code'),'subcode':e.get('error_subcode'),'message':e.get('message','')[:500].replace(os.environ['FB_PAGE_ACCESS_TOKEN'],'[redacted]').replace(os.environ['FB_PAGE_ID'],'[page]'),'required_permissions':sorted(set(re.findall(r'\\b(?:read_insights|pages_[a-z_]+)\\b',e.get('message',''))))}
        return data
    except (requests.RequestException,ValueError):
        return {'unavailable':True,'reason':'request_failed'}
previous=None
# Read an earlier private analytics artifact to calculate changes.
try:
    gh=requests.Session(); gh.headers['Authorization']='Bearer '+os.environ['GH_TOKEN']
    url='https://api.github.com/repos/'+os.environ['GITHUB_REPOSITORY']+'/actions/artifacts'
    artifacts=gh.get(url,params={'name':'bobo-page-analytics','per_page':10},timeout=30).json().get('artifacts',[])
    for artifact in artifacts:
        if artifact.get('expired'): continue
        archive=gh.get(artifact['archive_download_url'],timeout=60)
        if archive.ok:
            with zipfile.ZipFile(io.BytesIO(archive.content)) as z:
                previous=json.loads(z.read('snapshot.json'))
            break
except Exception:
    previous=None
page_id=os.environ['FB_PAGE_ID']
report={'collected_at':now.isoformat(),'page':{},'videos':[],'monetization_status':'Not exposed by this collector; dashboard eligibility remains unverified'}
for field in ['name','followers_count','fan_count']:
    report['page'][field]=get(page_id,{'fields':field}).get(field)
ledger=json.loads(Path('published_bobo.json').read_text())
known={}
for entry in ledger.values():
    vid=entry.get('facebook_video_id')
    if vid: known[vid]=entry
listed=get(page_id+'/videos',{'fields':'id,title,created_time','limit':100})
for entry in listed.get('data',[]): known.setdefault(entry['id'],{'title':entry.get('title'),'generated_at':entry.get('created_time')})
report['video_discovery_status']=listed.get('unavailable',False)
metrics=['total_video_views','total_video_views_unique','total_video_avg_time_watched','total_video_view_total_time','total_video_complete_views','total_video_impressions']
old={v['id']:v for v in (previous or {}).get('videos',[])}
for vid,meta in known.items():
    row={'id':vid,'title':meta.get('title'),'created_at':meta.get('generated_at'),'scene_id':meta.get('scene_id'),'duration_seconds':meta.get('duration'),'metrics':{},'unavailable_metrics':{}}
    details=get(vid,{'fields':'permalink_url,created_time,length'})
    if not details.get('unavailable'):
        row.update(url=details.get('permalink_url'),created_at=details.get('created_time',row['created_at']),duration_seconds=details.get('length',row['duration_seconds']))
    for metric in metrics:
        result=get(vid+'/video_insights',{'metric':metric})
        entries=result.get('data',[])
        if entries and entries[0].get('values'):
            row['metrics'][metric]=entries[0]['values'][-1].get('value')
        else: row['unavailable_metrics'][metric]=result
    for kind in ['reactions','comments']:
        result=get(vid+'/'+kind,{'summary':'true','limit':0})
        count=result.get('summary',{}).get('total_count')
        if count is not None: row['metrics'][kind]=count
        else: row['unavailable_metrics'][kind]=result
    shares=get(vid,{'fields':'shares'})
    if 'shares' in shares: row['metrics']['shares']=shares['shares'].get('count')
    elif shares.get('unavailable'): row['unavailable_metrics']['shares']=shares
    row['changes_since_previous']={}
    for key,value in row['metrics'].items():
        before=old.get(vid,{}).get('metrics',{}).get(key)
        if isinstance(value,(int,float)) and isinstance(before,(int,float)):
            row['changes_since_previous'][key]=value-before
    avg=row['metrics'].get('total_video_avg_time_watched')
    duration=row.get('duration_seconds')
    if isinstance(avg,(int,float)) and isinstance(duration,(int,float)) and duration:
        row['estimated_average_watch_fraction']=avg/1000/duration
    report['videos'].append(row)
report['previous_collected_at']=(previous or {}).get('collected_at')
report['analytics_available']=any('total_video_views' in v['metrics'] for v in report['videos'])
(OUT/'snapshot.json').write_text(json.dumps(report,indent=2))
print('Videos checked:',len(report['videos']))
print('View insights available:',report['analytics_available'])
print('Report saved to private workflow artifact; no secrets printed.')
