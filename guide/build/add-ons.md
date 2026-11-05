# Add-on nodes

A fresh **H3 Timeline** shows only the core: clips, prompts, length, seed and the join choice (Continue, Cut, New scene). Every other feature comes from a small node you connect when you want it. Once that node is connected, the feature appears in the Studio and its sockets appear on the Timeline node.

To add one, use **Add:** on the Timeline node or the **Add to this Timeline** row at the bottom of the Studio. Either way the node is placed next to the Timeline and wired for you. You can also search for "H3 +" and connect its `project` output to the Timeline's `project` input yourself. The **H3 +** nodes chain, in any order: connect one's `project` output to the next one's `project` input.

A muted add-on turns its feature off, and so does every add-on before it in the chain. A bypassed add-on turns only its own feature off; the chain passes through it. Adding or removing an add-on changes what the Studio shows, never what is in your Timeline.

## Guided and Full

Each Timeline node is in one of two modes, saved with the workflow:

- **Guided** shows the core plus the features whose nodes are connected. New Timeline nodes and the `examples/v1` workflows start here.
- **Full** shows every feature, as in 0.12. Workflows saved before 1.0.0 open in Full mode and look as they did.

Switch with **Show all features** / **Simplify** in the Studio's top bar. Switching only changes what is shown.

In Guided mode the Timeline node hides unconnected sockets that belong to features you have not added. A connected socket always stays. To connect negative conditioning, switch to Full; the `negative` socket then stays when you switch back.

When a hidden feature already holds data, for example audio clips in a project now shown in Guided mode, the Studio shows a line such as *This project has audio or timed text. They are kept, and still rendered. Add H3 + Sound to see and edit them.* Its **Add the node** button adds the node.

## H3 + Continuity tools

Turns on [Takes](../continuity/takes.md), [bridges](../continuity/joins-and-bridges.md), [visual memory](../continuity/visual-memory.md) choices and the [continuity check](../continuity/check.md). It has no settings. Example: `examples/v1/04-continuity-tools.json`, a cut that keeps the same chef in the same kitchen.

## H3 + References

Turns on the **Pictures** and **RefMods** pages, the **References** column, the **Shots** tab (first and last frames) and the Timeline's picture and video inputs. It owns `ref_image_size` (`match` or `max`), which replaces the Timeline's own advanced setting while it is connected. Example: `examples/v1/02-references.json`; copy `examples/assets/h3_example_lantern.png` into `ComfyUI/input` first. See [References and pictures](references.md) and [First and last frames](frame-guides.md).

## H3 Story

The [Story writer](../story/writer.md) node turns on the **Story** and **Cast** pages when it is linked to the Timeline's `story` input. It needs an OpenAI-compatible endpoint, which may cost money. Example: `examples/v1/05-story.json`.

## H3 + Sound

Turns on [audio lanes](../sound/audio.md), [dialogue cues](../sound/dialogue.md), [timed text](../sound/timed-text.md) and the Timeline's audio inputs. It owns `carry_audio` and `audio_context_frames`. Connect an audio VAE to the Timeline's `audio_vae` input to send audio clips to H3. Example: `examples/v1/03-sound.json`.

## H3 Context Windows (advanced)

Samples one clip in overlapping windows. It is placed in the model chain, between the model loader and the sampler, not on the Timeline, so adding it from the Studio leaves it unconnected for you to wire. Example: `examples/v1/06-long-clips.json`. See [Long clips](long-clips.md).

## Stills

`examples/v1/07-stills.json` feeds a still generator into the Timeline's `still_recipe` input and uses **H3 + References** for the **Shots** tab. See [Stills with P-H3-Image](p-h3-image-stills.md).
