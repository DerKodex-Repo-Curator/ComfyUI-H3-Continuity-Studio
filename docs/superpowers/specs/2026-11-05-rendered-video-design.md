# Playback of rendered Timeline clips

The Full video view must work before all boxes are current. For ordinary timelines,
assemble current saved videos in Timeline order, skipping unfinished/stale boxes;
label the result with the number included. Preserve source-filled partial playback
for video_slices. No inference or changes to generated clip files are required.

Add a persisted Mux uploaded audio checkbox beside Full video, default on. Off keeps H3 sound; on uses tracks marked In the full video instead, falling back
to H3 sound when none are marked.
The setting affects assembly only and must not invalidate rendered boxes. Cache
keys must include the audio choice. The same file is played, opened and downloaded.
For compact previews, crop marked audio on the original Timeline clock before
joining the rendered windows, so a skipped clip does not shift the audio content.

Approaches: sequential browser playback would introduce gaps and disagree with
downloads. Extending existing server assembly gives one seekable MP4 and reuses
CPU encoding and cache validation. Keep complete export/API behavior intact;
compact partial previews omit bridges/replacements and disclose that limitation.

Implementation choices are inferred from the requested behavior; the user confirmed the choice is H3 sound versus uploaded audio tracks. Existing source-filled playback remains supported.
