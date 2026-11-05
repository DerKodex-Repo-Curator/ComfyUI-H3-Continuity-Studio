# Nodes

All nodes appear under the **H3 Continuity** category.

## H3 Timeline

The heart of the pack. Draw clips in the Studio; each queued run renders the next clip that needs it.

| Input | Type | Notes |
| --- | --- | --- |
| `name` | string | Folder under `output/h3_sequences`. |
| `width`, `height` | int | Output size. |
| `context_frames` | 22, 39, 90, 141 | Frames each clip carries from the clip before (0.9 s, 1.6 s, 3.75 s, 5.9 s). |
| `carry_audio` | boolean | Advanced. Also carry and freeze the matching audio. A connected **H3 + Sound** sets it. |
| `ref_image_size` | `match` or `max` | Advanced. Reference image sizing, as in MiniMax H3 Reference to Video. A connected **H3 + References** sets it. |
| `audio_context_frames` | int | Advanced. Incoming audio context in 24 fps frames; 0 follows video. A connected **H3 + Sound** sets it. |
| `timeline` | string | The clips as JSON, written by the editor. |
| `clip`, `vae`, `audio_vae` | optional | H3 CLIP, video VAE and audio VAE. Without the audio VAE, `@audio` references only label the prompt. |
| `images.imageN`, `videos.videoN`, `video_audios.…`, `audios.audioN` | optional | [Connected references](../build/references.md). |
| `negative` | optional | Negative conditioning. |
| `still_recipe` | optional | A [Still Recipe](../build/frame-guides.md); video rendering never evaluates it. |
| `story` | optional | From **H3 Story**. Renders never wait for it. |
| `project` | optional | From the [H3 + add-on nodes](../build/add-ons.md). Turns on their Studio features; their settings replace the advanced ones above. |

| Output | Type |
| --- | --- |
| `positive`, `negative` | CONDITIONING |
| `latent` | LATENT (empty audio+video latent to sample) |
| `segment` | H3C_SEGMENT (to H3 Save Segment) |
| `seed` | INT |
| `prompt` | STRING |
| `info` | STRING |
| `image_1`, `image_2`… | IMAGE, the clip's final `<Picture N>` pixels |

## H3 + References, H3 + Sound, H3 + Continuity tools

The [add-on nodes](../build/add-ons.md). Each has an optional `project` input and a `project` output (`H3C_PROJECT`) and chains into the Timeline's `project` input. **H3 + References** owns `ref_image_size`; **H3 + Sound** owns `carry_audio` and `audio_context_frames`; **H3 + Continuity tools** has no settings.

## H3 Story

Plans and writes the Timeline's prompts through an OpenAI-compatible API. Output: `story`. Settings are on [the writer page](../story/writer.md). The `writing_mode` widget is retired (every Write uses Fast) and kept only so saved workflows load.

## H3 Save Segment

Saves the run as the next segment (the finished video without repeated frames, plus latents for the next run) and then rebuilds the full video.

| Input | Notes |
| --- | --- |
| `segment`, `latent` | From the Timeline and the sampler. |
| `images`, `audio` | Decoded frames and audio. Needed for the segment and full videos. |
| `fps` | 24 unless you interpolate. |
| `crf` | H.264 quality; lower is better and larger. |
| `color_space` | HDR videos use 10-bit BT.2020. |
| `description` | Text stored with the segment, such as the prompt. |
| `write_full_video` | Only affects the deprecated H3 Sequence chain; the Timeline always exports when every clip is done. |

## H3 Continuation Model

Picks the model the sampler uses for this run: `continuation_model` when the Timeline's `segment` carries frames from the clip before (a continuing clip or a bridge), `model` otherwise. Put it between your model chain and the guider, for example with a LoRA meant only for continuations on `continuation_model`. See [Long continuing chains](../continuity/long-chains.md).

| Input | Notes |
| --- | --- |
| `model` | For clips that start fresh or cut. |
| `segment` | From H3 Timeline. |
| `continuation_model` | Optional. Unconnected, every clip uses `model`. |

## H3 Sigmas Tail

Experimental. Raises the last few noise levels before zero (`BasicScheduler → H3 Sigmas Tail → sampler sigmas`), so a distilled 8-step model settles less fine detail in its final step. Each moved level keeps its ratio to the level above the tail, raised to the power 1 / (1 + `strength`); the first level, the levels above the tail and the final zero stay. With `segment` connected, clips that start fresh or cut keep their schedule. Defaults: `tail_steps` 3, `strength` 0.5; 0 changes nothing.

## H3 Context Windows, H3 Join Chain

For [long clips](../build/long-clips.md). **Context Windows** wraps ComfyUI's MiniMax H3 Context Windows (model → model); **Join Chain** joins saved continuing segments into one latent for refinement.

## Still nodes

| Node | Purpose |
| --- | --- |
| **Still Recipe** | Wraps a native image generator's `IMAGE` output with `bindings` that say where its prompt, seed, size and references are. Connect it to the Timeline's `still_recipe`. |
| **H3 Still Conditioning** | Adapts a still generator invocation for pinned-source and reference presentation. Used inside the supplied H3 still examples. |
| **Still Image Source** | Supplies source pixels to a still request. |
| **H3 Timeline Image** | Resolved pixels for `<Picture N>` in the selected clip. |

## Deprecated

**H3 Sequence** and **H3 Continue** are the earlier chain-based way of continuing a sequence. Use **H3 Timeline** instead. They remain so old workflows load.
