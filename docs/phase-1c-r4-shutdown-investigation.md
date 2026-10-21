# Phase 1C-R4 — shutdown investigation

**Verdict: PARTIAL — R3 dump symbolicated; shutdown wait located; underlying
cause and a reliable native clean-shutdown baseline remain unverified.**
Observed October 21, 2026, Asia/Dhaka. Phase 2 is not authorized.

## Scope and preserved build

R4 inspected the existing dump before launching anything. No Chromium source,
patch, dependency, GN argument, executable, signature or security configuration
was changed. No browser or diagnostic tool was built. Earlier R/R2/R3 evidence
and the successful compilation flags remain intact.

Initial product HEAD and origin/main were both
`43a631abfd6d3401d3902e19f10858ce2934fbc6`, clean on `main`. Authenticated owner
`A-K-M-Asifuzzaman` matched the numeric Git noreply author ID. Author remains
`Asif Zman <138548302+asif4762@users.noreply.github.com>`.
The checkout verifier passed Chromium
`0e66b94549a8bd85f03fbdf189b752d6e7b63c32`, depot_tools
`dca727ba1f8fa8f1e3b12a815d065818bb61d395`, version 155.0.8059.85 and the recorded
DEPS digest, with clean tracked checkouts. Historical dependency synchronization
was not repeated. The earlier full native build exited 0 after 39,487 actions.

The host is native Darwin arm64. The writable external APFS mount is still
`/Volumes/ssd(mac)2`, UUID `47F505A1-126A-4EC6-8DB6-135813AA6111`; the observed
physical store is disk6s2, with volume disk7s2. Device numbers are observations,
not the identity contract. Initial free space was 273,721,483,264 bytes, pressure
1 and swap used 1,081 MiB. There was no task-owned Chromium or active compiler.
After cleanup, pressure was again 1, swap used 3,802.75 MiB and physical available
capacity 270,755,524,608 bytes (252.16 GiB). Other applications remained running;
the host's swap growth over the intervening hours is not attributed to Chromium.

The exact launcher passed native arm64 Mach-O, execute-permission, bundle-ID and
version checks. Seven relevant Mach-O UUIDs match the R3 dump (below). This adds
identity evidence to R3's framework/resource checks; it is not a new exhaustive
artifact audit. The component build, symbol level 1, non-debug/non-official
configuration and remote-execution-disabled GN values are preserved.

## Dump validation and local symbolication

The R3 launch record supplies the isolated Crashpad directory. A filesystem
search confined to that directory found exactly one matching dump, whose
resolved path is:

```text
/Volumes/ssd(mac)2/TrinolBuild/test-profile-r3-15a6r33u/Crashpad-isolated/pending/e3d061ab-c5f7-487d-9abf-7e84bd01be89.dmp
```

Validation: 1,679,200 bytes; MDMP signature; nine streams with directory ranges
inside the file; 47 thread records; 1,583 module records; PID 61136. Header time
is **2026-10-21 06:02:46 UTC**, with file modification at 06:02:47.356 UTC.
SHA-256:
`b2e86db29709a380cd63c52760e01159785916b18b2376631b51e18f33d5ff46`.

Exception `0x43507378` is Crashpad's `CPsx` simulated exception, defined in
`third_party/crashpad/crashpad/util/mach/mach_extensions.h`; it is not evidence
of a hardware fault. Exception thread 822449 (`0xc8cb1`) is MacShutdownWatchdog.
The exception stack reaches DumpWithoutCrashing from shutdown_watchdog_mac.cc:79.
The dump therefore includes both the watchdog and the actual browser main thread.

Installed Xcode LLDB 2100.0.17.108 loaded this minidump successfully, without
attaching to a live browser or uploading anything. `xcrun dwarfdump --uuid`
verified the important module identities against the dump's CodeView records:

| Module | Matching UUID |
| --- | --- |
| Chromium launcher | 4C4C44B6-5555-3144-A1FB-E4AD36E5F79D |
| libchrome_dll.dylib | 4C4C445F-5555-3144-A132-BC493495A44B |
| libbase.dylib | 4C4C4473-5555-3144-A1C1-A6FDA21CDE2F |
| libcontent.dylib | 4C4C4423-5555-3144-A17F-408DB2CB3493 |
| libmojo_public_cpp_bindings.dylib | 4C4C44A3-5555-3144-A1A1-CACF192F12C2 |
| libgpu.dylib | 4C4C448E-5555-3144-A166-4E5B8EC313F8 |
| libgpu_ipc_client.dylib | 4C4C44CE-5555-3144-A140-4EAE955BA061 |

Available diagnostic tools also include dwarfdump, llvm-dwarfdump, llvm-nm,
llvm-objdump and llvm-symbolizer. Standalone minidump_stackwalk/dump_syms were
not on PATH or built in this output. Pinned `third_party/breakpad/BUILD.gn`
declares minidump_stackwalk with stackwalk_common and the system-allocator
host/default toolchains, plus minidump_dump and macOS dump_syms. Generated
Ninja descriptions exist. No tool build/dependency dry run was needed because
LLDB already recovered the required stacks. No dSYM bundle was present at the
output's top level; preserved local build debug information resolved function
and source-line locations directly.

Commands used included `xcrun lldb --no-lldbinit --batch -c <exact-dump>`,
`process status`, `thread list`, `thread backtrace all -c 20`, `image list -u`,
then focused `thread select 1; bt 100`, `thread select 13; bt 45` and
`thread select 27; bt 40` in a second local invocation. Both LLDB invocations
exited 0 under explicit subprocess timeouts.

Limits: optimized component code has inlined/folded frames and unavailable
variables. LLDB reported dyld shared-cache section-overlap warnings. Some system
pthread frames lack names. This is useful symbolication, not a claim that every
module, variable or frame is fully resolved. No memory-derived profile strings,
raw dumps or full debugger output are included in Git.

## Observed stacks

The following is a selected, source-normalized call chain from the matched
symbols, ordered caller to callee. It is not a speculative reconstructed stack:

```text
CrBrowserMain, thread 1 / TID 0x28a91
  BrowserMainLoop::ShutdownThreadsAndCleanUp (browser_main_loop.cc:1264)
  ImageTransportFactory::Terminate (image_transport_factory.cc:25)
  VizProcessTransportFactory::~VizProcessTransportFactory
  ContextProviderCommandBuffer::~ContextProviderCommandBuffer
  CommandBufferProxyImpl::~CommandBufferProxyImpl
  CommandBufferProxyImpl::DisconnectChannel (command_buffer_proxy_impl.cc:939)
  GpuChannelProxy::DestroyCommandBuffer (generated gpu_channel.mojom.cc:2868)
  ThreadSafeInterfaceEndpointClientProxy::SendMessageWithResponder (:360)
  WaitableEvent::Wait -> TimedWaitImpl -> mach_msg
```

**Confirmed location:** at capture, browser main was synchronously awaiting the
GPU command-buffer destruction reply/cancellation during compositor teardown.
This is a response-event wait, not evidence of a same-thread mutex deadlock.
The snapshot alone cannot measure how long this particular wait had lasted.

Other relevant observations:

- **Chrome_IOThread, thread 13 / TID 0x28b71:** processing a Mojo transport
  disconnection, reaching VideoCaptureDevicesChangedObserver::OnConnectionError,
  EnsureConnectedToService and GetVideoCaptureService. The source posts a UI
  proxy-binding task when needed; this path does not itself show a synchronous
  wait on the main thread. A starvation/reconnection loop is possible but not
  established by one snapshot.
- **Thread 27 / TID 0x28bf4:** persistent-cache destruction through SQLite WAL
  checkpoint/close, SandboxedFile::Sync and File::Flush, inside fcntl.
- **Thread 10 / TID 0x28b6e:** SQLite database close inside the kernel close call.
  These show concurrent filesystem work, not proof that it blocked the main
  thread or that the external drive caused the hang.
- **Thread 43 / TID 0xc8cb1:** shutdown watchdog -> base::DumpWithoutCrashing ->
  Crashpad simulated exception. It detects the incomplete teardown.
- **Thread 2:** Crashpad client restart thread waiting for a Mach message; no
  main-thread dependency on Crashpad is visible in the selected chain.
- Other threads include normal worker/event-loop waits, the signal detector
  blocked in read, and a separate shutdown watchdog in a condition-variable
  timed wait. A sleeping thread is not automatically a defective lock owner.

The dump contains only the browser process. GPU, renderer, network and storage
helper stacks are absent. R3 process observations show helpers alive around the
failure, but do not establish which side failed to deliver the GPU response.

## Pinned shutdown sequence and timing ambiguity

1. Native Quit causes browser window/tab teardown and eventual exit from the
   browser main loop. These earlier UI operations had progressed far enough to
   enter the observed content shutdown path.
2. ChromeBrowserMainParts::PostMainMessageLoopRun performs extra-part cleanup,
   process-singleton cleanup, metrics stop and ShutdownPreThreadsStop, then
   BrowserProcessImpl::StartTearDown.
3. StartTearDown arms the macOS watchdog, destroys browser services and the
   ProfileManager, then performs policy/platform/network-context cleanup.
   ProfileImpl destruction performs interlocked keyed-service shutdown and
   storage-partition shutdown. The observed stack is later than this call;
   a direct ProfileManager/KeyedService deadlock is not shown at capture.
4. BrowserMainLoop requests network-service shutdown and calls
   BrowserProcessIOThread::ProcessHostCleanUp. On this configuration the latter
   can wait **up to ten seconds** for the network process, then requests
   termination of remaining child-process hosts.
5. ImageTransportFactory::Terminate destroys the Viz transport/context provider.
   Its command-buffer proxy sends synchronous DestroyCommandBuffer through the
   browser I/O thread. GpuChannelHost is explicitly created with the I/O task
   runner. In the GPU service, GpuChannelMessageFilter::DestroyCommandBuffer
   posts work and a reply through the GPU main task runner.
6. Only afterward does content close the GPU channel, release Mojo IPC support,
   join the I/O thread and shut down the thread pool, followed by PostDestroyThreads.
   ChromeBrowserMainParts' destructor eventually signals OnShutdownComplete.
7. R3's watchdog did not observe that completion event before its deadline;
   it dumped and used `_exit(RESULT_CODE_HUNG)`. The actual OS exit code was not
   captured and is not invented from this source path.

The release-configured teardown watchdog budget is **ten seconds for the entire
sequence after StartTearDown begins**. Network-process waiting alone permits the
same ten seconds. Therefore the captured GPU wait may be the principal stall,
or merely the operation in progress when an earlier stage consumed the budget.
No R3 timing trace or GPU-process stack distinguishes these cases. Disabling or
extending the watchdog would conceal this uncertainty rather than diagnose it;
no such modification was made.

## Ranked hypotheses and discriminating tests

These are investigation priorities, not probabilities or confirmed causes.
All proposed new runtime tests require review of the failed R4 lifecycle first.

| Rank / hypothesis | Support | Counterevidence / limit | Confidence | Safest discriminating test and expected result |
| --- | --- | --- | --- | --- |
| 1. Aggregate deadline exhausted before GPU cleanup finishes | Global watchdog and network wait each allow 10 s; main was in a later teardown stage | No stage timing shows whether network wait consumed its allowance | Medium | Capture existing shutdown trace events plus browser/network state; early stages consuming nearly the budget would support this explanation |
| 2. GPU destruction response/disconnect fails to complete | Exact main-thread synchronous DestroyCommandBuffer wait; request crosses browser I/O and GPU task runners | No GPU stack, message timing or proven cycle; snapshot does not establish wait duration | Medium | Capture paired browser/GPU samples just after a reviewed native Quit; a persistent GPU teardown wait or unprocessed reply would discriminate |
| 3. Browser I/O reconnection work delays response processing | IO thread is reconnecting video capture after child transport error | One active stack, not a measured loop; no synchronous UI wait shown | Low–medium | Short repeated paired samples/trace; repeated reconnect processing without GPU-reply dispatch would support starvation |
| 4. Slow filesystem operations contribute to aggregate shutdown time | SQLite close and persistent-cache fsync are present; U states observed | Main snapshot is in IPC, not filesystem I/O; no latency measurements | Low–medium | Correlate shutdown events with local filesystem timing; long measured writes preceding expiry would support contribution, not prove drive failure |
| 5. Profile/keyed-service or thread-pool deadlock | These are shutdown dependencies generally | Profile teardown already returned; thread-pool shutdown has not been reached | Low for the captured location | Confirm phase timings; a future stack inside these phases would be needed |
| 6. Crashpad, signing clone or duplicate-class cleanup causes hang | Earlier warnings and Crashpad CPU incident exist | Watchdog dump succeeded; main stack contains none of those paths; R3 browsing worked | Low | Require a directly relevant blocking stack before changing these components |
| 7. Long session/workload or GUI automation timing | R3 had many features and a long gap; R4 early native Quit was refused | Later R4 menu cleanup lacked a watchdog, but it was also long-lived and lacked an exit status | Unknown | After harness review, independent short fresh-profile blank and browsing sessions with captured native exits; compare without changing browser security |

**Root cause is not established.** The blocking location and watchdog mechanism
are established. No browser-side patch, linker change or recompilation is justified.

## Lifecycle harness and regression coverage

Added [test_chromium_lifecycle_macos.py](../scripts/test_chromium_lifecycle_macos.py)
and [offline tests](../tests/test_runtime_lifecycle.py). The script reuses existing
checkout, storage, containment, memory and exclusive-build-lock helpers.

It requires an explicit canonical build root and expected volume UUID; validates
native arm64 executable/bundle identity and tracked source/tool pins; checks
physical capacity, mount identity and idle pressure; refuses a concurrent build
or compiled browser. A new private external profile and supported
BREAKPAD_DUMP_LOCATION isolate user and crash data. No browser feature flags,
security bypasses or watchdog suppression are added.

The real executable is the direct Popen child, not a wrapper. Identity combines
PID, start time, kernel-reported executable and profile/Crashpad arguments.
Helpers are tracked by matching identities and current ancestry, including
separately grouped Crashpad handlers. Native Quit uses NSRunningApplication for
the existing PID with a fresh identity/path check; it cannot launch an ambiguous
installed bundle. No terminate/kill signals are sent. The script records actual
Popen status, CPU/RSS samples, resources, Quit attempts, dumps and watchdog text.

A persistent `logs/TrinolLifecycle.blocked.json` marker is written before launch
and retained on failure, including supervisor failure. It is removed only by
that run's verified PASS path. R4's marker remains present; do not remove it just
to rerun. A PASS requires an accepted Quit request, real exit 0, no watchdog/dump,
no inspection/lifecycle failure and no remaining tracked helpers. GUI/features
remain NOT TESTED unless independently inspected.

The first implementation had two confirmed harness defects: it advanced Quit
on a transient U/sample delay, then returned on native Quit refusal instead of
continuing to supervise the live child. The delivered implementation preserves
the startup window for U/delay observations, keeps the failure flag, records
Quit errors, allows at most two native requests separated by at least five
seconds, and continues observing/reaping to the absolute runtime-plus-grace
bound. Regression tests cover late real exits after refusal and delayed samples
not moving Quit into startup. No native rerun of this correction was performed.

Limits: runtime options are 10–600 seconds plus 10–60 seconds of grace. Native
subprocess calls have timeouts (5 seconds for process/Quit commands; inherited
storage probes up to 30 seconds); kernel/filesystem stalls can delay a sample.
The script fails delayed observations rather than claiming real-time guarantees.
It cannot guarantee termination if macOS refuses Quit, identity/mount inspection
fails, or a process stays uninterruptible. Such a run is FAIL with preserved
identity/evidence and a blocked next launch, never a fabricated successful exit.

## Actual R4 run and cleanup

Only one browser instance was launched, after the offline investigation:

```sh
python3 scripts/test_chromium_lifecycle_macos.py \
  --build-root '/Volumes/ssd(mac)2/TrinolBuild' \
  --volume-uuid 47F505A1-126A-4EC6-8DB6-135813AA6111 \
  --seconds 45 --grace-seconds 30
```

Evidence: `logs/phase1cr4-lifecycle-gwmalazh`, profile
`test-profile-r4-qi_hrzex`. Launch was 13:33:02 Asia/Dhaka, PID 55645, a single
about:blank tab with the same no-first-run/no-default-browser-check flags as R3.
The initial version recorded browser Us samples at approximately 6.4, 8.5, 10.7,
12.8 and 15.0 seconds. A later sample was delayed until 38.85 seconds. The browser
had returned to Ss, but the early native Quit request was refused. At 39.17 seconds
the supervisor exited **1**, with browser exit code **null**, no watchdog and
no dump. This was a failed lifecycle test, not a new confirmed watchdog repro.

Native UI inspection was temporarily blocked because automatic approval review
hit the account usage limit. The action was not executed. After the user resumed
and access worked again, the same PID/start/executable/profile still existed.
The browser had remained open through another gap, approximately **4h34m**.
This repeats the lifecycle problem R4 intended to avoid; the initial harness
must not be described as a validated unattended runtime supervisor.

The existing about:blank GUI and native menu responded. CUA selected **Quit
Chromium** from the application's menu. The subsequent UI inspection timed out,
but process observation found all compiled browser/helper identities gone by
**18:07:11 Asia/Dhaka (12:07:11 UTC)**. No new watchdog message or dump appeared.
A short bounded cleanup observer intended browser/GPU stack samples only if
those processes were still present; they exited before its sampling point, so
no paired live stacks were captured. No signals, relaunches or restart occurred.

The original Popen parent had already exited, so this later cleanup has **no
captured browser exit code**. Process absence and lack of a dump are encouraging
cleanup evidence, not a passing bounded lifecycle. The failure marker is retained.
No second blank session, browsing session, restoration attempt or other new
browser launch was performed after the U-state/failure observation.

## Functional results

Previously verified functionality is carried forward explicitly, not silently
reclassified as a fresh R4 pass. New secondary checks remain gated on a captured
clean shutdown.

| Feature | R4 result | Evidence / previous status |
| --- | --- | --- |
| Responsive native GUI | PASS, limited | Existing about:blank window/menu responded during cleanup; R3 already passed responsive startup |
| Clean bounded shutdown | FAIL | Initial supervisor exited 1 with null browser exit; later menu cleanup had no wait status |
| Correct version | NOT TESTED in GUI | Source/bundle identity and matching module UUIDs verified; R3 GUI version passed |
| Local HTML/CSS/JavaScript | NOT TESTED | R3 passed; not repeated after failed lifecycle |
| HTTPS rendering/security indicator | NOT TESTED | R3 passed; not repeated |
| Tabs/back/forward/reload | NOT TESTED | R3 passed; not repeated |
| Bookmarks/history/downloads/settings | NOT TESTED | R3 passed; not repeated |
| PDF/print preview | NOT TESTED | R3 passed; not repeated |
| Second window | NOT TESTED | Clean-shutdown gate not achieved |
| Incognito | NOT TESTED | Clean-shutdown gate not achieved |
| Extensions management | NOT TESTED | Clean-shutdown gate not achieved |
| Site permission prompt | NOT TESTED | Clean-shutdown gate not achieved |
| Session restoration | NOT TESTED | No further launch allowed after failure |
| HTTPS JavaScript assertion | NOT TESTED | Not established by R3 either |
| Clean shutdown after normal browsing | NOT TESTED | Initial blank lifecycle failed |

## Evidence, checks and delivery

Offline diagnostic evidence stays in
`/Volumes/ssd(mac)2/TrinolBuild/logs/phase1cr4-5_frxwpb`: dump-metadata.json,
module-identity.json, lldb-dump.txt and lldb-focused.txt. Lifecycle evidence stays
in the separate run directory above, including the original failure result and
later cleanup-samples.jsonl/cleanup-result.json. Raw dumps, debug output, profiles
and extracted memory are not staged or uploaded. Only sanitized function-level
findings appear here.

All **143 offline tests pass**, including 30 new lifecycle tests. Executable,
profile/Crashpad containment, PID reuse, helpers outside the browser group,
mount/space rejection, exclusive locking, failure latching, genuine mocked exit
codes, native refusal, bounded retries, U-state protection and classifications
are covered. These tests do not launch Chromium or validate the corrected native
Quit path. Foundation validation, Python syntax, shell syntax and whitespace
checks also pass. The initial test filename collided with the script module;
it was renamed before the successful suite. No full Chromium tests were built.

Tooling milestone `c622f9f6652ce34c3f56adba4eda7e95b0aa579a` —
`test(runtime): add bounded Chromium lifecycle verification` — was pushed and
remote SHA verified. [Actions run 39597654526](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39597654526)
passed. Follow-up `679ccfa58454e0002fea7f40ecf42b808c6932f8` —
`fix(runtime): preserve startup deadline after delayed samples` — was also
pushed with matching remote HEAD; [Actions run 39597923048](https://github.com/A-K-M-Asifuzzaman/TRINOL-BROWSER/actions/runs/39597923048)
passed. Final documentation commit/CI evidence
accompanies delivery. Git history is preserved; no force-push was used.

## Next engineering action and phase boundary

Architect review should first approve a fresh validation of the corrected
supervisor and its native Quit readiness/refusal behavior, with an operator
available for safe cleanup. Preserve the failure marker until that review.
If another shutdown stalls, collect stage timings plus paired browser/GPU and
network-process state early in the ten-second watchdog window. That distinguishes
aggregate-budget exhaustion from a delayed GPU response or disconnected IPC
cleanup; one browser-only snapshot does not.

Do not patch security-sensitive IPC, extend/disable the watchdog, change GPU
flags or rebuild based on the current hypotheses. No branding or Phase 2 work
has begun. Compilation and R3 browsing remain successful; the safe bounded
clean-shutdown requirement remains outstanding.

PHASE 1C-R4 PARTIAL — AWAITING ARCHITECT REVIEW
