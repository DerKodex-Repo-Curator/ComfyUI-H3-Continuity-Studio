# Saved takes, delivery clocks and visual memory

The user has11 saved clips but only4 are current, and reports lipsync drift in
Full video and inability to use box11 as memory for box12. Older saved clips are
playable footage, independently of whether their edited recipes need rendering.

Ordinary partials include saved takes by stable box ID in current Timeline order,
with saved lengths and an older-take count. Repaint source-filled previews keep
their existing current-render policy. Do not change render-current flags.

Video windows convert native24fps start/end boundaries to each delivered fps.
Keep native audio timing; place marked tracks on the authored Timeline clock,
then extract each displayed clip's window using its saved length. Invalidate old
assembly caches. Do not alter segment MP4s, latents, prompts or queue state.

Visual memory may use older matching native latents at compatible resolution.
Explicit selected moments must exist in saved footage. Continuation's independent
guide/reference/text/plate checks remain intact. No GPU generation is needed.

Reuse existing assembly and memory paths. Regressions decode actual48fps files,
load actual native windows, and check missing/incompatible sources. Live evidence
must verify11 clips,1704 delivered frames and35.5s picture/audio; physical lipsync
acceptance remains separate from technical timing checks.
