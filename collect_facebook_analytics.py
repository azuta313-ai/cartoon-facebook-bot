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
            return {'unavailable':True,'code':e.get('code'),'subcode':e.get('error_subcode'),'message':e.get('message','')[:500].replace(os.environ['FB_PAGE_ACCESS_TOKEN'],'[redacted]').replace(os.environ['FB_PAGE_ID'],'[page]'),'required_permissions':sorted(set(re.findall(r'\b(?:read_insights|pages_[a-z_]+|instagram_[a-z_]+|business_management)\b',e.get('message',''))))}
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
story_ids={str(v['story']['video_id']) for v in ledger.values() if v.get('story',{}).get('video_id')}
def strategy_cohort(meta):
    if meta.get('publication_exception') or meta.get('review',{}).get('publication_exception'):
        return 'user_exception_not_quality_pass'
    if meta.get('production_strategy')=='observe-repair-reserve-v1' and meta.get('review',{}).get('review',{}).get('quality_passed') is True:
        return 'qualified_strategy'
    return 'historical_or_unverified'
def reel_completion_available(rows):
    return any(v.get('media_kind')!='story' and any(isinstance(v['metrics'].get(k),(int,float)) for k in ('post_video_complete_views_organic','total_video_complete_views')) for v in rows)
known={}
for entry in ledger.values():
    vid=entry.get('facebook_video_id')
    if vid: known[vid]=entry
listed=get(page_id+'/videos',{'fields':'id,title,created_time','limit':100})
for entry in listed.get('data',[]): known.setdefault(entry['id'],{'title':entry.get('title'),'generated_at':entry.get('created_time')})
report['video_discovery_status']=listed.get('unavailable',False)
metrics=['total_video_views','total_video_avg_time_watched','total_video_view_total_time','total_video_complete_views']
metrics += ['post_video_retention_graph','post_video_complete_views_organic']
metrics += ['blue_reels_play_count','fb_reels_total_plays','fb_reels_replay_count','post_video_avg_time_watched','post_video_view_time','post_video_likes_by_reaction_type','post_video_social_actions','post_impressions_unique']
old={v['id']:v for v in (previous or {}).get('videos',[])}
for vid,meta in known.items():
    row={'id':vid,'title':meta.get('title'),'created_at':meta.get('generated_at'),'scene_id':meta.get('scene_id'),'duration_seconds':meta.get('duration'),'metrics':{},'unavailable_metrics':{}}
    row.update(media_kind='story' if str(vid) in story_ids else 'video',strategy_cohort=strategy_cohort(meta),published_at=meta.get('published_at'))
    details=get(vid,{'fields':'permalink_url,created_time,length'})
    if not details.get('unavailable'):
        row.update(url=details.get('permalink_url'),created_at=details.get('created_time',row['created_at']),duration_seconds=details.get('length',row['duration_seconds']))
    for metric in metrics:
        result=get(vid+'/video_insights',{'metric':metric,'period':'lifetime'})
        entries=result.get('data',[])
        if entries and entries[0].get('values'):
            row['metrics'][metric]=entries[0]['values'][-1].get('value')
        else: row['unavailable_metrics'][metric]=result if result.get('unavailable') else {'unavailable':True,'reason':'empty_insights_response','period':'lifetime'}
    # Preserve native retention bins without guessing time units or completion.
    curve=row['metrics'].get('post_video_retention_graph')
    row['retention']={
        'status':'available_raw' if isinstance(curve,(dict,list)) and curve else 'unavailable',
        'metric':'post_video_retention_graph',
        'raw':curve,
        'bin_time_mapping':'Unverified; do not infer seconds or halfway exits from keys.',
        'causal_explanation':'Not supplied by Facebook; requires a controlled content experiment.'
    }
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
    row['watch_time_interpretation']={'unit':'milliseconds','average_includes_replays':True,'average_is_completion_rate':False,'exact_exit_timestamp':None}
    report['videos'].append(row)
report['page_changes_since_previous']={}
for key,value in report['page'].items():
    before=(previous or {}).get('page',{}).get(key)
    if isinstance(value,(int,float)) and isinstance(before,(int,float)):
        report['page_changes_since_previous'][key]=value-before
report['previous_collected_at']=(previous or {}).get('collected_at')
report['analytics_available']=any(any(k in v['metrics'] for k in ['total_video_views','blue_reels_play_count','fb_reels_total_plays']) for v in report['videos'])
experiment={
    'recorded_at':now.isoformat(),
    'evidence_snapshot':report['collected_at'],
    'decision':'Retain existing experiment; no new creative variable added.',
    'reason':'Observe-repair-reserve production and mandatory speech must first yield reviewed published episodes; historical replay/watch metrics cannot establish a voice effect.',
    'strategy':'observe-repair-reserve-v1',
    'primary_metrics':['blue_reels_play_count','fb_reels_total_plays','fb_reels_replay_count','post_video_view_time','post_video_retention_graph','followers_count'],
    'comparison':'Match actual publication ages and duration; record time-of-day, story exposure and production differences; small samples are exploratory.',
    'retention_mapping_verified':False,
    'completion_available':reel_completion_available(report['videos']),
    'story_completion_counter_ids':[v['id'] for v in report['videos'] if v.get('media_kind')=='story' and 'total_video_complete_views' in v['metrics']],
    'new_strategy_published_video_ids':[v['facebook_video_id'] for v in ledger.values() if strategy_cohort(v)=='qualified_strategy' and v.get('facebook_video_id')],
    'exception_video_ids':[v['facebook_video_id'] for v in ledger.values() if strategy_cohort(v)=='user_exception_not_quality_pass' and v.get('facebook_video_id')],
    'spend':0
}
(OUT/'experiment-status.json').write_text(json.dumps(experiment,indent=2))
(OUT/'snapshot.json').write_text(json.dumps(report,indent=2))
print('Videos checked:',len(report['videos']))
print('View insights available:',report['analytics_available'])
print('Report saved to private workflow artifact; no secrets printed.')
