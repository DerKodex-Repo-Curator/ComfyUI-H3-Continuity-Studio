// The video the Studio plays and downloads as the full video: the assembled full video, or, while a Timeline that
// still has clips to render, a partial video (current renders, with source-filled gaps for split-video Timelines).
export function exportedVideo(status) {
  if (status?.full_video) return {file: status.full_video, partial: null};
  if (status?.partial_video?.file) return {file: status.partial_video.file, partial: status.partial_video};
  return null;
}

const summary = (partial) => partial.mode === 'rendered'
  ? `${partial.rendered} of ${partial.boxes} clips rendered, unrendered clips skipped`
  : `${partial.rendered} of ${partial.boxes} clips repainted, the rest from the source`;

export const partialBadge = (partial) => `Partial video · ${summary(partial)}`;

export const partialTitle = (partial) => `${summary(partial)}.${partial.note ? ` ${partial.note}` : ''}`;
