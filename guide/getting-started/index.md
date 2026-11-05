# Getting started

1. **[Install](install.md)** the node pack next to a working MiniMax H3 setup in ComfyUI.
2. **[Render your first video](first-sequence.md)**: load Hello H3, pick your models, click ▶ Render and watch the join.
3. **[Add what you need](../build/add-ons.md)**: plug in the H3 + nodes for pictures, sound, takes and more.
4. **[Tour the Studio](studio-tour.md)** to see where everything lives.

Then pick what you need from [Build](../build/index.md), [Continuity](../continuity/index.md) and [Story](../story/index.md).

## Vocabulary

| Term | Meaning |
| --- | --- |
| **Timeline** | The H3 Timeline node. It holds the list of clips as JSON and exposes the conditioning, latent and seed that the sampler needs. |
| **Clip** (also called a **box**) | One H3 generation. The Studio says *clip*; older notes and the saved JSON say *box*. |
| **Join** | How a clip meets the one before it: **Continue**, **Cut**, **New scene** or a **bridge**. |
| **Take** | One render of a clip. A new render moves the previous take aside instead of deleting it. |
| **Studio** | The full-screen editor opened from the Timeline or Story node. |
| **Story** | The optional H3 Story node: a writer model that plans clips and writes prompts. |
| **Guide** | A first, last or timed-shot still image that anchors a clip. Not to be confused with the Story node's *Guide* text input. |
