---
name: h3-continuity-video
description: Use when authoring or rendering native H3 Timeline video from an external creative brief, including typography, timed text, motion graphics, or narrative video.
---

# Native H3 Timeline video

Read `GET /h3c/timeline/instructions` on the chosen ComfyUI host before authoring.
Its `skill`, `guides[].body`, `examples[].body`, `limits`, and `revisions` are a
self-contained public bundle; `client.body` supplies the runnable stdlib example.
For a local checkout, start with
[the external contract](../../docs/EXTERNAL-TIMELINE.md). Use the actual guide
bodies, not just their titles or repository paths. If a native guide is not installed,
consult the official MiniMax documentation subject to its applicable terms.

For a new production without a caller-supplied ComfyUI graph, read `timeline-api`
and `GET /h3c/api/v1/capabilities`. If the host has a workflow-selection library,
read its human-selected task roles before choosing a generic ready profile.
Use the selected ready configured profile, upload original
assets, create a project with a saved key, inspect its read-only plan and create
a revision-pinned job with another saved key. Poll its known ID after disconnect;
retry a lost acceptance response with the identical body/key. Verify immutable
downloads before reporting technical completion. Explicit attached workflow export
shares API revisions with the Studio; default export forks. The public guide owns
the endpoint, lease, take, source-clock and recovery rules; `clients` supplies
`timeline_api.py`. For an existing graph-based production, continue its pinned
`client` lifecycle below, preserving its acknowledged attempts and receipt.

Preserve the user's creative brief, supplied wording, references and requested
deliverable. Timeline accepts native prompts directly; Story and a writing
provider are optional. No particular cast, canon, style or duration is assumed.

Choose guidance by the intended video and prepared mode:

- Read `base` for text generation and first/last-frame modes; add `ref` for
  Ref2VA reference syntax. Use `prompt-writing` for shared motion, camera and
  physical-state direction. Author logical `@imageN` / `@audioN` references;
  preparation reports their native tags and effective mode.
- For typography, subtitles or supplied timed wording, read `timeline-text`
  and the normalized Whisper/source-in-30 example in `external-timeline`.
  Preserve exact phrase/word intervals and source SHA-256. Describe the desired
  lettering treatment and motion in `timed_text.direction`. Visible text is
  native H3 visual prompt content; `<d>` is reserved for audible dialogue/lyrics.
- For reference audio, read `timeline-audio`. Synchronized text uses that lane's
  clock; source-in 30 at movie start 0 maps source time 30 to movie time 0.
  Reference audio conditions H3. If the user wants the original recording as
  the final soundtrack, set `"in_full_video": true` on its uploaded clip; mixing
  it with H3's audio is a separate consumer finishing operation.
- For continued action or transitions, read `transitions` and
  `native-transitions`. H3 generates motivated cover/reveal; a hard-cut box
  resets carry. Honor replay windows and the actual reached state.
- For an edit of many short cuts, give each box `"exact": true` so it plays
  exactly its `frames` (see `limits.exact_frames`). H3 generates the next length
  on its grid and drops the rest, so a box that drops frames must be followed by
  a cut. Stage each cut's pictures and bind them with `picture` bindings into
  saved slots from `image17` up (`limits.saved_picture_slots`), with no upper
  limit; a box still sends H3 at most 9 pictures. The "Long edits" section of
  `external-timeline` has the rules and examples. Keep your own box metadata,
  such as a cut's place in your edit, under a key H3 doesn't own (for example
  `edit`); `external-timeline` lists H3's box keys, and `source` is the Story's.
- To turn a hard cut between two rendered boxes into a generated move without
  rendering either again, add a top-level `bridges` entry that leads into the
  box with the cut (12, 29 or 46 frames, `limits.bridge_frames`). It renders
  after every box, on a plain run or with `render_bridge`, and only the full
  video gets longer, never a box. The "Bridges" section of `external-timeline`
  has the rules.

For the graph-based route, prepare the complete existing H3 API graph via `/h3c/timeline/prepare` and inspect
the returned snapped ranges, text windows, references and diagnostics. Preserve
its model/sampler/decode/save ancestry and flat computed media sockets. Use a
unique stable sequence name and a stable production ID.

For authorized rendering, save the remote `client.body` as `client.filename`
and run `python external_timeline.py --help` (or use `examples/external_timeline.py`
in the repository)
and use its receipt-first lifecycle described in `external-timeline`. Reuse the
same prepared input, host, sequence and receipt on resume. Ambiguous delivery
requires reconciliation, never an automatic new submission. In the Timeline API a
held (`needs_reconciliation`) job is closed only by POST `/jobs/{id}/abandon` with
a person's reason and the held prompt ID. Report the job and its `blocked_by`
dependants to the human and wait for their decision; never abandon automatically.

Report technical completion separately from visual review: examine actual
spelling, readable intervals, onset/clear timing, motion and transitions. Prompt
validation and retrievable MP4s alone cannot certify creative acceptance.
