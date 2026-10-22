"""Synthetic latency and local writer tests; no browser or application signals."""
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import test_chromium_lifecycle_macos as life
from runtime_evidence import EvidenceWriter, Latency


class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.run = self.root / 'run'; self.run.mkdir()

    def writer(self):
        writer = EvidenceWriter(self.root, self.run, self.root.stat().st_dev)
        def cleanup():
            if writer.process.poll() is None:
                writer.finish(1)
                writer.process.wait(timeout=2)
            writer.process.stdout.close()
        self.addCleanup(cleanup)
        return writer

    def test_latency_duration_and_start_delay(self):
        now = [4]
        t = Latency(lambda: now[0])
        def operation(): now[0] = 7; return 8
        self.assertEqual(t.call('probe', operation, scheduled=2), 8)
        self.assertEqual(t.take(), [dict(operation='probe', start=4, end=7,
            duration=3, start_delay=2, outcome='complete')])

    def test_incomplete_timeout_record(self):
        t = Latency()
        with self.assertRaises(subprocess.TimeoutExpired):
            t.call('diskutil', Mock(side_effect=subprocess.TimeoutExpired('diskutil', 5)))
        self.assertEqual(t.records[0]['outcome'], 'timeout')

    def test_real_writer_order_and_acknowledged_fsync(self):
        w = self.writer()
        for n in range(6): self.assertTrue(w.submit('events.jsonl', {'n': n}))
        result = w.finish(2)
        self.assertIsNone(result['error'])
        self.assertTrue(result['flushed'])
        self.assertEqual(result['submitted'], result['acknowledged'])
        self.assertFalse(result['writer_remaining'])
        self.assertEqual([json.loads(x)['n'] for x in (self.run/'events.jsonl').read_text().splitlines()], list(range(6)))
        self.assertTrue(all(x['end'] >= x['start'] for x in result['writer_timings']))

    def test_queue_submission_does_not_wait_for_writer(self):
        w = self.writer()
        with patch.object(w, 'pump'):
            start = time.monotonic()
            self.assertTrue(w.submit('events.jsonl', {'n': 1}))
            self.assertLess(time.monotonic()-start, .25)
            self.assertEqual(w.acked, 0)
        self.assertIsNone(w.finish(2)['error'])

    def test_exit_racing_flush_ack_does_not_report_false_failure(self):
        w = self.writer()
        with patch('runtime_evidence.os.read', side_effect=BlockingIOError), \
                patch.object(w.process, 'poll', return_value=0):
            w.pump()
        self.assertIsNone(w.error)
        self.assertIsNone(w.finish(2)['error'])

    def test_queue_saturation_is_explicit_and_memory_bounded(self):
        w = self.writer()
        with patch.object(w, 'pump'):
            for n in range(w.MAX_RECORDS): self.assertTrue(w.submit('events.jsonl', {'n': n}))
            self.assertFalse(w.submit('events.jsonl', {'n': 'overflow'}))
        result = w.finish(2)
        self.assertEqual(result['dropped'], 1)
        self.assertIn('queue_full', result['error'])
        self.assertLessEqual(result['peak_queue_bytes'], w.MAX_BYTES)

    def test_oversize_record_rejected(self):
        w = self.writer()
        self.assertFalse(w.submit('events.jsonl', 'x' * w.MAX_RECORD))
        self.assertEqual(w.dropped, 1)
        self.assertTrue(w.finish(2)['error'])

    def test_writer_failure_propagated(self):
        (self.run/'events.jsonl').symlink_to(self.root/'unrelated')
        w = self.writer(); w.submit('events.jsonl', {'n': 1})
        result = w.finish(2)
        self.assertTrue(result['error'])
        self.assertFalse((self.root/'unrelated').exists())
        self.assertFalse(result['flushed'])

    def test_writer_shutdown_timeout_cannot_pass(self):
        w = self.writer()
        with patch.object(w, 'pump'):
            w.submit('events.jsonl', {'critical': True})
            result = w.finish(0)
        self.assertTrue(result['error'])
        self.assertEqual(result['unacknowledged'], 1)
        self.assertFalse(result['flushed'])

    def test_serialization_latency_measured(self):
        w = self.writer()
        original = json.dumps
        def slow(*a, **kw): time.sleep(.02); return original(*a, **kw)
        with patch('runtime_evidence.json.dumps', side_effect=slow):
            w.submit('events.jsonl', {'n': 1})
        record = next(r for r in w.timing.records if r['operation']=='evidence_serialization')
        self.assertGreaterEqual(record['duration'], .02)
        w.finish(2)

    def test_latency_memory_limit(self):
        t = Latency()
        for _ in range(4097): t.add({})
        self.assertTrue(t.overflow)
        self.assertEqual(len(t.records), 4096)

    def test_process_list_and_libproc_latency_separate(self):
        now = [0]
        t = Latency(lambda: now[0]); app=self.root/'Chromium.app'
        text=f'123 1 S Thu Oct 22 00:00:00 2026 0.1 100 {app}/bin --test\n'
        def command(*_): now[0]+=3; return text
        def path(_): now[0]+=4; return str(app/'bin')
        with patch.object(life,'TIMING',t), patch.object(life,'command',side_effect=command), \
                patch.object(life,'executable_path',side_effect=path):
            self.assertEqual(life.snapshot(app)[0]['pid'],123)
        self.assertEqual([(r['operation'],r['duration']) for r in t.records],
                         [('full_process_list',3),('executable_path',4)])

    def test_timing_completion_order_is_monotonic(self):
        t=Latency()
        t.call('outer',lambda:t.call('inner',lambda:None))
        self.assertEqual([r['end'] for r in t.records],sorted(r['end'] for r in t.records))
        self.assertTrue(all(r['end']>=r['start'] for r in t.records))

    def test_targeted_process_disappearance_is_not_pid_reuse(self):
        with patch.object(life,'command',side_effect=subprocess.CalledProcessError(1,'ps',output='')):
            self.assertEqual(life.snapshot(self.root,123),[])

    def test_failed_resource_probe_is_incomplete(self):
        t=Latency();volume=SimpleNamespace(mount=str(self.root),device='disk-test')
        probe=Mock(disk=Mock(side_effect=subprocess.TimeoutExpired('diskutil',5)))
        guard=life.runtime_guard(self.root,volume,'expected',{'swap_bytes':0},probe,t)
        with patch.object(life,'assert_mount'):
            with self.assertRaises(subprocess.TimeoutExpired):guard()
        self.assertEqual(t.records[-1]['operation'],'apfs_uuid_diskutil')
        self.assertEqual(t.records[-1]['outcome'],'timeout')

    def test_resource_components_timed_and_safety_preserved(self):
        now=[0];t=Latency(lambda:now[0])
        volume=SimpleNamespace(mount=str(self.root), device='disk-test')
        def disk(_): now[0]+=3;return {'VolumeUUID':'expected'}
        def capacity(_):now[0]+=2;return SimpleNamespace(f_bavail=100*life.GIB,f_frsize=1)
        probe=Mock(disk=Mock(side_effect=disk))
        guard=life.runtime_guard(self.root,volume,'expected',{'swap_bytes':0},probe,t)
        with patch.object(life,'assert_mount'), patch.object(life.os,'statvfs',side_effect=capacity), \
                patch.object(life,'memory',return_value={'pressure':1,'swap_bytes':0}) as memory:
            guard()
            self.assertEqual({r['operation']:r['duration'] for r in t.records}['apfs_uuid_diskutil'],3)
            self.assertEqual({r['operation']:r['duration'] for r in t.records}['storage_capacity'],2)
            memory.return_value={'pressure':4,'swap_bytes':0}
            with self.assertRaises(ValueError):guard()
            memory.return_value={'pressure':1,'swap_bytes':3*life.GIB}
            with self.assertRaises(ValueError):guard()
        with patch.object(life,'assert_mount',side_effect=ValueError('disconnected')):
            with self.assertRaises(ValueError):guard()

    def test_exact_r5_recovery_and_changed_marker_rejection(self):
        logs=self.root/'logs';logs.mkdir();evidence=logs/'previous';evidence.mkdir()
        result=dict(pid=123,profile=str(self.root/'profile'),exit_code=0, failure='observation_delayed',
                    remaining=[],watchdog=False,dumps=[],clean_shutdown='FAIL')
        for name,value in [('result.json',result),('launch.json',result),('final-health.json',{'remaining':[]})]:
            (evidence/name).write_text(json.dumps(value))
        for name in ('events.jsonl','samples.jsonl','browser.log'):(evidence/name).touch()
        marker=logs/'TrinolLifecycle.blocked.json'
        raw=json.dumps(dict(evidence=str(evidence),result=result)).encode();marker.write_bytes(raw)
        with patch.object(life,'R5_MARKER_SHA256',hashlib.sha256(raw).hexdigest()):
            retry=life.review_r5_marker(self.root,marker,[])
            with self.assertRaises(ValueError):life.review_r5_marker(self.root,marker,[{}])
            life.arm_latch(marker,self.run,retry)
            self.assertEqual(Path(retry['archive']).read_bytes(),raw)
            with self.assertRaises(ValueError):life.review_r5_marker(self.root,marker,[])
            marker.write_bytes(raw)
            with self.assertRaises(ValueError):life.review_r5_marker(self.root,marker,[])

    def simulate(self, slow=None, writer_error=None, u_gap=False, unexpected=False):
        now=[0.];t=Latency(lambda:now[0]);p=Mock(pid=123,poll=lambda:0 if now[0]>=18 else None)
        profile=self.root/'profile';exe=self.root/'Chromium.app/bin'
        row=dict(pid=123,ppid=1,state='S',start='original',executable=str(exe),
                 command=str(exe)+' --user-data-dir='+str(profile))
        def sample():
            if slow and now[0]<3:now[0]+=16
            rows = [dict(row,state='U' if u_gap else 'S')] if now[0]<18 else []
            if unexpected:
                rows.append(dict(row, pid=456, command=str(exe)))
            return rows
        w=Mock(error=writer_error,submit=Mock(return_value=not writer_error))
        r=life.supervise(p,profile,self.run,10,15,sample,Mock(),Mock(return_value='accepted'),
            clock=lambda:now[0],sleep=lambda n:now.__setitem__(0,now[0]+n),timing=t,writer=w)
        return r

    def test_slow_observation_zero_exit_still_fails(self):
        r=self.simulate(slow=True)
        self.assertEqual(r['exit_code'],0)
        self.assertEqual(r['failure'],'observation_delayed')
        self.assertGreater(r['max_poll_gap'],15)

    def test_writer_failure_keeps_real_child_exit(self):
        r=self.simulate(writer_error='writer_failed')
        self.assertEqual(r['exit_code'],0)
        self.assertEqual(r['failure'],'writer_failed')
        self.assertFalse(r['remaining'])

    def test_valid_supervision_has_frequent_child_polls(self):
        r=self.simulate()
        self.assertIsNone(r['failure'])
        self.assertEqual(r['exit_code'],0)
        self.assertLessEqual(r['max_poll_gap'],.25)

    def test_sampling_gap_is_not_continuous_u_evidence(self):
        r=self.simulate(slow=True,u_gap=True)
        self.assertFalse(r['persistent_uninterruptible'])
        self.assertEqual(r['failure'],'observation_delayed')

    def test_unexpected_process_requires_operator_cleanup_without_adoption(self):
        r = self.simulate(unexpected=True)
        self.assertEqual(r['exit_code'], 0)
        self.assertEqual(r['failure'], 'unexpected_compiled_app_process')
        self.assertFalse(r['remaining'])
        self.assertEqual(r['unexpected_remaining'][0]['pid'], 456)
        self.assertTrue(r['cleanup_required'])
        event = next(e for e in r['events'] if e['event']=='unexpected_compiled_app_process')
        self.assertNotIn('command', event['processes'][0])


if __name__=='__main__': unittest.main()
