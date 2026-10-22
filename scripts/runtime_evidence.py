"""Bounded local evidence transport; the observer never waits for disk writes."""
from collections import deque
from contextlib import ExitStack
import json
import os
from pathlib import Path
import subprocess
import sys
import time


class Latency:
    def __init__(self, clock=time.monotonic):
        self.clock = clock
        self.records = []
        self.overflow = False

    def call(self, name, function, *args, scheduled=None, **kwargs):
        start = self.clock()
        outcome = 'complete'
        try:
            return function(*args, **kwargs)
        except Exception as exc:
            outcome = 'timeout' if isinstance(exc, (TimeoutError, subprocess.TimeoutExpired)) else 'error'
            raise
        finally:
            end = self.clock()
            self.add(dict(operation=name, start=start, end=end, duration=end-start,
                          start_delay=None if scheduled is None else max(0, start-scheduled),
                          outcome=outcome))

    def add(self, record):
        if len(self.records) >= 4096:
            self.overflow = True
        else:
            self.records.append(record)

    def take(self):
        records, self.records = self.records, []
        return records


class EvidenceWriter:
    MAX_RECORD = 65536
    MAX_BYTES = 2 * 1024 * 1024
    MAX_RECORDS = 128

    def __init__(self, root, run, device, timing=None):
        self.timing = timing or Latency()
        self.pending = deque()
        self.inflight = {}
        self.offset = 0
        self.buffer = b''
        self.sequence = self.acked = self.bytes = self.peak_bytes = self.dropped = 0
        self.error = None
        self.ready = self.flushed = False
        self.flush_duration = None
        self.writer_timings = []
        self.process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()),
            str(root), str(run), str(device)], stdin=subprocess.PIPE,
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=0)
        os.set_blocking(self.process.stdin.fileno(), False)
        os.set_blocking(self.process.stdout.fileno(), False)
        end = time.monotonic() + 5
        while not self.ready and self.process.poll() is None and time.monotonic() < end:
            self.pump()
            time.sleep(.01)
        if not self.ready:
            self.error = self.error or 'writer_start_failed'
            self.finish(1)
            raise RuntimeError(self.error)

    def submit(self, name, value):
        def serialize():
            return (json.dumps(dict(seq=self.sequence+1, submitted=time.monotonic(),
                                    file=name, value=value), separators=(',', ':'))+'\n').encode()
        try:
            data = self.timing.call('evidence_serialization', serialize)
            if (len(data) > self.MAX_RECORD or len(self.inflight) >= self.MAX_RECORDS or
                    self.bytes + len(data) > self.MAX_BYTES):
                self.dropped += 1
                self.error = self.error or 'evidence_queue_full_or_oversize'
                return False
            def enqueue():
                self.sequence += 1
                self.pending.append((self.sequence, data))
                self.inflight[self.sequence] = len(data)
                self.bytes += len(data)
                self.peak_bytes = max(self.peak_bytes, self.bytes)
            self.timing.call('evidence_queue_submission', enqueue)
            self.timing.call('evidence_transport', self.pump)
            return True
        except Exception as exc:
            self.dropped += 1
            self.error = self.error or 'evidence_submission_failed: ' + str(exc)
            return False

    def pump(self):
        # Bound work as well as memory even if the producer outruns disk.
        eof = False
        try:
            for _ in range(8):
                if not self.pending:
                    break
                _, data = self.pending[0]
                try:
                    written = os.write(self.process.stdin.fileno(), memoryview(data)[self.offset:])
                except BlockingIOError:
                    break
                self.offset += written
                if self.offset == len(data):
                    self.pending.popleft()
                    self.offset = 0
            for _ in range(8):
                try:
                    chunk = os.read(self.process.stdout.fileno(), 65536)
                except BlockingIOError:
                    break
                if not chunk:
                    eof = True
                    break
                self.buffer += chunk
                if len(self.buffer) > 131072:
                    raise ValueError('Oversize writer response')
                while b'\n' in self.buffer:
                    line, self.buffer = self.buffer.split(b'\n', 1)
                    response = json.loads(line)
                    if 'error' in response:
                        self.error = self.error or response['error']
                    elif response.get('ready'):
                        self.ready = True
                    elif response.get('flushed') is not None:
                        self.flushed = response['flushed'] == self.sequence
                        self.flush_duration = response.get('flush_duration')
                    else:
                        seq = response['ack']
                        if seq != self.acked + 1 or seq not in self.inflight:
                            raise ValueError('Writer acknowledgment out of order')
                        self.acked = seq
                        self.bytes -= self.inflight.pop(seq)
                        if len(self.writer_timings) < 4096:
                            self.writer_timings.append(response)
                        else:
                            self.error = self.error or 'writer_timing_overflow'
            # Exit can race the nonblocking read; drain stdout before judging flush.
            if eof and self.process.poll() is not None and not self.flushed:
                self.error = self.error or 'writer_exited_without_flush'
        except Exception as exc:
            self.error = self.error or 'writer_transport_error: ' + str(exc)

    def finish(self, timeout=5):
        end = time.monotonic() + timeout
        closed = self.process.stdin.closed
        while time.monotonic() < end:
            self.pump()
            if not self.pending and not closed:
                self.process.stdin.close()  # EOF asks for fsync and final acknowledgment.
                closed = True
            if self.process.poll() is not None:
                self.pump()
                break
            time.sleep(.01)
        if not closed:
            self.process.stdin.close()
        running = self.process.poll() is None
        if running:
            self.error = self.error or 'writer_shutdown_timeout'
        if not self.flushed or self.acked != self.sequence:
            self.error = self.error or 'evidence_flush_unacknowledged'
        return dict(error=self.error, submitted=self.sequence, acknowledged=self.acked,
                    dropped=self.dropped, unacknowledged=len(self.inflight),
                    peak_queue_bytes=self.peak_bytes, flushed=self.flushed,
                    flush_duration=self.flush_duration,
                    writer_pid=self.process.pid, writer_remaining=running,
                    writer_timings=self.writer_timings)


def writer_main(root, run, device):
    """Only this child opens/appends runtime evidence; no daemon or forced kill."""
    root, run = Path(root), Path(run)
    handles = {}
    allowed = {'events.jsonl', 'samples.jsonl', 'timings.jsonl', 'launch.json'}
    seq = 0
    def validate():
        if (root.resolve() != root or run.resolve() != run or not run.is_relative_to(root) or
                root.stat().st_dev != device or run.stat().st_dev != device):
            raise ValueError('Writer filesystem identity changed')
    def reply(value):
        print(json.dumps(value), flush=True)
    try:
        validate()
        reply(dict(ready=True))
        with ExitStack() as stack:
            while True:
                line = sys.stdin.buffer.readline(EvidenceWriter.MAX_RECORD+1)
                if not line:
                    break
                if len(line) > EvidenceWriter.MAX_RECORD or not line.endswith(b'\n'):
                    raise ValueError('Invalid evidence frame')
                start = time.monotonic()
                record = json.loads(line)
                if record['seq'] != seq+1 or record['file'] not in allowed:
                    raise ValueError('Invalid evidence order/target')
                validate()  # Before opening or writing, never cache mount identity forever.
                path = run / record['file']
                if record['file'] not in handles:
                    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    handles[record['file']] = stack.enter_context(os.fdopen(fd, 'w'))
                out = handles[record['file']]
                out.write(json.dumps(record['value'])+'\n')
                out.flush()
                seq += 1
                reply(dict(ack=seq, start=start, end=time.monotonic(),
                           queue_wait=start-record['submitted']))
            flush_start = time.monotonic()
            validate()
            for out in handles.values():
                out.flush()
                os.fsync(out.fileno())
        reply(dict(flushed=seq, flush_duration=time.monotonic()-flush_start))
        return 0
    except Exception as exc:
        reply(dict(error='writer_failure: '+str(exc)))
        return 1


if __name__ == '__main__':
    raise SystemExit(writer_main(sys.argv[1], sys.argv[2], int(sys.argv[3])))
