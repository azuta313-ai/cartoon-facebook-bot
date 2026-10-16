import json,tempfile,unittest
from datetime import datetime
from pathlib import Path
from bobo_pipeline import TZ,next_episode,stage_and_select

class ReserveTests(unittest.TestCase):
    def test_four_ready_stops_generation(self):
        now=datetime(2026,10,15,6,tzinfo=TZ)
        reserve={20261015*2+i:{} for i in range(4)}
        self.assertIsNone(next_episode(now,{},reserve))

    def test_select_unfilled_morning_before_evening(self):
        now=datetime(2026,10,15,6,tzinfo=TZ)
        self.assertEqual(next_episode(now,{},{}),40522030)
        self.assertEqual(next_episode(now,{'long-v2-40522030':{}},{}),40522031)

    def test_expired_preparation_slots_are_skipped(self):
        now=datetime(2026,10,16,23,21,tzinfo=TZ)
        self.assertEqual(next_episode(now,{},{}),40522034)
        self.assertEqual(next_episode(datetime(2026,10,17,8,tzinfo=TZ),{},{}),40522035)
        self.assertEqual(next_episode(datetime(2026,10,17,7,59,tzinfo=TZ),{},{}),40522034)

    def test_approval_waits_and_pending_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            approval={'status':'approved','episode':40522030,'final_sha256':'abc','artifact_run_id':'123','review':{'reviewed_sha256':'abc'}}
            (root/'published_bobo.json').write_text('{}')
            (root/'bobo_review_approval.json').write_text(json.dumps(approval))
            (root/'bobo_review_pending.json').write_text(json.dumps({'episode':40522030}))
            self.assertIsNone(stage_and_select(root,datetime(2026,10,15,8,tzinfo=TZ)))
            self.assertTrue((root/'bobo_pending/40522030.json').exists())
            self.assertTrue((root/'bobo_review_pending.json').exists())
            self.assertEqual(stage_and_select(root,datetime(2026,10,15,9,tzinfo=TZ)),approval)
            (root/'published_bobo.json').write_text(json.dumps({'long-v2-40522030':{'published_at':'2026-10-15T09:00:00+05:00'}}))
            self.assertIsNone(stage_and_select(root,datetime(2026,10,15,10,tzinfo=TZ)))

    def test_no_third_daily_publish(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'bobo_reserve').mkdir()
            (root/'published_bobo.json').write_text(json.dumps({'a':{'published_at':'2026-10-15T09:00:00+05:00'},'b':{'published_at':'2026-10-15T17:00:00+05:00'}}))
            (root/'bobo_reserve/40522030.json').write_text('{}')
            self.assertIsNone(stage_and_select(root,datetime(2026,10,15,18,tzinfo=TZ)))

if __name__=='__main__': unittest.main()
