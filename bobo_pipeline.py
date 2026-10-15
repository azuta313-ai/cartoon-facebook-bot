"""Free-only preparation planner and reviewed reserve selection. No network calls."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

TZ = ZoneInfo('Asia/Karachi')
RESERVE_TARGET = 4

def slot_time(episode):
    day, slot = divmod(int(episode), 2)
    return datetime.strptime(str(day), '%Y%m%d').replace(hour=9 if slot == 0 else 17, tzinfo=TZ)

def approvals(root=Path('.')):
    return {int(p.stem): json.loads(p.read_text()) for p in (root/'bobo_reserve').glob('*.json')}

def next_episode(now, ledger, reserve):
    occupied = {int(k.removeprefix('long-v2-')) for k in ledger if k.startswith('long-v2-')}
    occupied.update(int(k) for k in reserve)
    future = sum(e not in {int(k.removeprefix('long-v2-')) for k in ledger if k.startswith('long-v2-')} for e in reserve)
    if future >= RESERVE_TARGET:
        return None
    for offset in range(4):
        day = int((now + timedelta(days=offset)).strftime('%Y%m%d'))
        for slot in (0, 1):
            episode = day*2+slot
            if episode not in occupied:
                return episode
    return None

def stage_and_select(root=Path('.'), now=None):
    now = now or datetime.now(TZ)
    ledger = json.loads((root/'published_bobo.json').read_text())
    path = root/'bobo_review_approval.json'
    current = json.loads(path.read_text()) if path.exists() else {}
    if current.get('status') == 'approved':
        assert current['review']['reviewed_sha256'] == current['final_sha256']
        episode = int(current['episode'])
        directory = root/'bobo_reserve'; directory.mkdir(exist_ok=True)
        target = directory/f'{episode}.json'
        if target.exists():
            previous = json.loads(target.read_text())
            assert previous['final_sha256'] == current['final_sha256'], 'Reserve entry immutable'
        else:
            target.write_text(json.dumps(current, indent=2))
        # Preserve every pending record until publication or deliberate rejection.
        pending = root/'bobo_review_pending.json'
        if pending.exists():
            record = json.loads(pending.read_text())
            if int(record['episode']) == episode:
                directory = root/'bobo_pending'; directory.mkdir(exist_ok=True)
                (directory/f'{episode}.json').write_text(json.dumps(record, indent=2))
    accepted_today = sum(str(v.get('published_at','')).startswith(now.date().isoformat()) for v in ledger.values())
    if accepted_today >= 2:
        return None
    for episode, record in sorted(approvals(root).items()):
        if f'long-v2-{episode}' not in ledger and slot_time(episode) <= now:
            return record
    return None

if __name__ == '__main__':
    import os
    selected = stage_and_select()
    with open(os.environ['GITHUB_OUTPUT'], 'a') as stream:
        stream.write('ready='+str(bool(selected)).lower()+'\n')
        if selected:
            Path('bobo_review_approval.json').write_text(json.dumps(selected, indent=2))
            stream.write('run_id='+str(int(selected['artifact_run_id']))+'\n')
