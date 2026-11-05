// The video the Studio plays and downloads as the full video: the assembled full video, or, while a Timeline that
// splits a video across clips still has clips to render, the partial video (rendered clips, the source for the rest).
export function exportedVideo(status) {
  if (status?.full_video) return {file: status.full_video, partial: null};
  if (status?.partial_video?.file) return {file: status.partial_video.file, partial: status.partial_video};
  return null;
}

const summary = (partial) => `${partial.rendered} of ${partial.boxes} clips repainted, the rest from the source`;

export const partialBadge = (partial) => `Partial video · ${summary(partial)}`;

export const partialTitle = (partial) => `${summary(partial)}.${partial.note ? ` ${partial.note}` : ''}`;
