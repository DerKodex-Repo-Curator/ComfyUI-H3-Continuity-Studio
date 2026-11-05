import {test} from 'node:test';
import assert from 'node:assert/strict';
import {compatibleVideoUrl,videoPlaybackUrl} from '../../web/h3c_video_preview.mjs';

const base='https://example.test:8188/';
const original=base+'api/view?filename=seg_0001.mp4&subfolder=h3_sequences%2Fseq&type=output&v=take1';
const preview=base+'api/h3c/video/preview?filename=seg_0001.mp4&subfolder=h3_sequences%2Fseq&type=output&v=take1';

test('phone playback uses the compatible preview and preserves the API prefix and take version', () => {
  assert.equal(videoPlaybackUrl(original,true,base),preview);
  assert.equal(compatibleVideoUrl(original,base),preview);
  assert.equal(videoPlaybackUrl(original,false,base),original);
});

test('external, input, non-video and already converted URLs are not sent to the preview route', () => {
  for(const url of [original.replace('example.test','other.test'),original.replace('type=output','type=input'),
    original.replace('.mp4','.png'),original.replace('h3_sequences%2Fseq','other'),preview]) {
    assert.equal(compatibleVideoUrl(url,base),null);
    assert.equal(videoPlaybackUrl(url,true,base),url);
  }
});
