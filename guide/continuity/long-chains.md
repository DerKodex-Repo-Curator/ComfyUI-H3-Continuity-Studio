# Long continuing chains

Each continuing clip copies the end of the clip before it and adds its own small errors on top. Over many clips this compounds: skin, fabric and backgrounds get crisper and more etched ("burn"), the way a photocopy of a photocopy gains contrast. The [continuity check](check.md) measures it as texture drift, for example *Drift: 104% grainier than box 1.*

These settings are experimental and off by default. They were compared on one six-clip chain (a woman talking to camera in a kitchen, FastH3 8-step at 960 × 544); results on other models and scenes may differ, so compare a few clips before relying on them.

## What was measured

Texture is the finest-detail energy of each clip against clip 1 (1.00 = no change). A "jump" is the largest frame-to-frame change at a join; the unchanged chain's joins measured 2.5 to 4.2.

| Setting | Clip 6 texture | Joins | Result |
| --- | --- | --- | --- |
| None (default) | 2.04 | 2.5–4.2 | Burn builds steadily. |
| `context_noise` | **1.75** | 2.6–3.2 | Much less burn; same framing; about 10% slower per continuing clip. |
| H3 Sigmas Tail, 3 steps, 0.5 | 1.93 | 2.4–3.2 | A little less burn. |
| `context_noise` and Sigmas Tail together | **1.67** | 2.7–3.3 | The least burn of all; same framing. |
| `continuation_guide: false` | 2.19 | 4.1–5.8 | See below: removes a hitch in moving shots. |
| Anti-burn LoRA 0.5 via H3 Continuation Model | (1.77) | **59 at clip 2** | Cut to a close-up at the first join; rejected. |
| Anti-burn LoRA 0.3 | 1.99 | 2.5–3.2 | No measurable effect on FastH3 int8. |

## Context noise

Add `"context_noise": true` to the Timeline JSON (or send it through the [API](../automation/api.md)). For each continuing clip, the carried frames are decoded, given seeded noise that fades from strong at the start of the overlap to none at its last frame, and encoded again; only the difference the noise makes is added to the original carried latent, so the VAE's own round-trip error is not carried forward. The carried frames stay frozen while H3 samples; audio is unchanged. It costs one decode and two encodes of the overlap per continuing clip.

## Guide at the first new frame

A continuing clip normally uses the previous clip's last frame as a guide at its first new frame, so the pose does not reset. In moving shots this produces a short hitch: about three nearly identical frames at the join, which the check reports as *Holds still: 3 frames at the join.* `"continuation_guide": false` removes the guide and the hitch; in calm shots the join then moves a little more. It is a per-Timeline setting; the default keeps the guide.

## H3 Sigmas Tail

A node for your graph (`BasicScheduler → H3 Sigmas Tail → the sampler's sigmas`, with the Timeline's `segment` connected so clip 1 is unchanged). It raises the last noise levels before zero, so the final step of a distilled model settles less fine detail. See [Nodes](../reference/nodes.md#h3-sigmas-tail).

## H3 Continuation Model

Routes continuing clips (and bridges) to a different model, for a LoRA trained for continuations. The public H3 Anti-Burn LoRA was tested with it on FastH3 int8 and did not help (table above); its authors trained it on other turbo models, so it may behave differently on yours.

The Studio keeps `context_noise` and `continuation_guide` when it saves, but has no control for them yet.
