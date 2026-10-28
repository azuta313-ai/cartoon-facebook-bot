import json,tempfile,unittest
from datetime import datetime
from pathlib import Path
from bobo_pipeline import TZ,next_episode,published_story_serials,stage_and_select

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

    def test_published_story_serials_accepts_verified_reel_or_video_endpoint(self):
        ledger = {
            'reel': {
                'story_serial': 1,
                'final_sha256': 'reel-sha',
                'facebook_reel_id': 'reel-id',
                'facebook_reel_verified': True,
                'instagram': {'media_id': 'ig-1', 'permalink': 'https://instagram.test/1'},
            },
            'video': {
                'story_serial': 2,
                'final_sha256': 'video-sha',
                'facebook_video_id': 'video-id',
                'published_at': '2026-10-18T17:28:38+05:00',
                'instagram': {
                    'media_id': 'ig-2',
                    'permalink': 'https://instagram.test/2',
                    'source_sha256': 'video-sha',
                },
            },
            'unverified': {
                'story_serial': 3,
                'final_sha256': 'missing-facebook-acceptance',
                'instagram': {'media_id': 'ig-3', 'permalink': 'https://instagram.test/3'},
            },
            'wrong-file': {
                'story_serial': 4,
                'final_sha256': 'expected',
                'facebook_video_id': 'video-id-4',
                'published_at': '2026-10-18T18:00:00+05:00',
                'instagram': {
                    'media_id': 'ig-4',
                    'permalink': 'https://instagram.test/4',
                    'source_sha256': 'different',
                },
            },
        }
        self.assertEqual(published_story_serials(ledger), {1, 2})

if __name__=='__main__': unittest.main()
