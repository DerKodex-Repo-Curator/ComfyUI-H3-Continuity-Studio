import test from 'node:test';
import assert from 'node:assert/strict';
import {installDom} from './fake_dom.mjs';
import {Studio} from '../../web/h3c_studio.mjs';
import {idleWatch, watchEvent} from '../../web/h3c_render_watch.mjs';

installDom();
const createElement = document.createElement;
// Media DOM behavior needed by the real player, without loading video files.
document.createElement = tag => {
  const node = createElement(tag);
  Object.defineProperty(node, 'src', {
    get: () => node.getAttribute('src'), set: value => node.setAttribute('src', value),
  });
  node.matches = selector => selector === '.h3cx-message' ? node.className === 'h3cx-message'
    : selector === '.h3cx-live' ? node.className === 'h3cx-live'
    : selector === 'video:not(.h3cx-live)' ? tag === 'video' && node.className !== 'h3cx-live'
    : selector === `${tag}.h3cx-live` && node.className === 'h3cx-live';
  node.querySelectorAll = selector => node.children.filter(child => child.matches(selector));
  node.querySelector = selector => node.querySelectorAll(selector)[0] ?? null;
  node.pause = node.load = () => {};
  return node;
};

function player() {
  const studio = Object.create(Studio.prototype);
  for (const name of ['screen', 'badge', 'hint', 'fullButton', 'takeButton', 'switchButton', 'fullLinks',
    'takeLinks', 'takeOpen', 'takeDownload', 'pinButton', 'pinMenu', 'pinNote', 'soundtrackNote', 'muxAudio']) {
    studio[name] = document.createElement('div');
  }
  const editor = {
    selected: 0, state: {boxes: [{id: 'a'}, {id: 'b'}, {id: 'c'}]}, status: {ok: true},
    box() { return this.state.boxes[this.selected]; },
    statusOf(box) { return box.id === 'b' ? {status: 'done', video: {file: {filename: 'b.mp4'}}} : null; },
    fullLink: Object.assign(document.createElement('a'), {hidden: true}),
    cast: {pinTargets: () => [{id: 'actor', name: 'Actor'}]},
  };
  studio.view = 'take';
  studio.host = {editor, runningBox: () => 1, viewUrl: file => `/view/${file.filename}`};
  return studio;
}

for (const source of ['kj', 'core']) {
  test(`${source} live preview follows the selected rendering box and restores other boxes' content`, () => {
    const studio = player(), editor = studio.host.editor;
    const watch = watchEvent({...idleWatch(), running: true}, source === 'kj' ? 'kj_preview_override' : 'b_preview',
      source === 'kj' ? {image: 'frame', mime: 'image/webp', step: 2, total: 8} : new Blob(['frame'], {type: 'image/jpeg'}));
    studio.refreshPlayer(watch);
    assert.equal(studio.screen.firstElementChild.className, 'h3cx-live');
    assert.match(studio.badge.textContent, /^Live · box 1/);

    editor.selected = 1;
    studio.refreshPlayer(watch);
    assert.equal(studio.screen.firstElementChild.tagName, 'VIDEO');
    assert.equal(studio.screen.firstElementChild.src, '/view/b.mp4');
    assert.equal(studio.badge.hidden, true);
    assert.equal(studio.hint.hidden, true);
    assert.equal(studio.pinButton.hidden, false);
    assert.equal(studio.blobSrc, null);
    // Further preview updates must not replace the selected box's video.
    studio.refreshPlayer({...watch, preview: {...watch.preview, step: 3}});
    assert.equal(studio.screen.firstElementChild.src, '/view/b.mp4');

    editor.selected = 2;
    studio.refreshPlayer(watch);
    assert.equal(studio.screen.textContent, 'Not rendered yet');

    editor.selected = 0;
    studio.refreshPlayer(watch);
    assert.equal(studio.screen.firstElementChild.className, 'h3cx-live');
    assert.equal(studio.hint.hidden, source !== 'core');

    studio.refreshPlayer(watchEvent(watch, 'execution_success'));
    assert.equal(studio.screen.textContent, 'Not rendered yet');
    assert.equal(studio.blobSrc, null);
  });
}

test('an unassociated render cannot take over the selected clip viewer', () => {
  const studio = player();
  studio.host.editor.selected = 1;
  studio.host.runningBox = () => null;
  studio.refreshPlayer({...idleWatch(), running: true, preview: {source: 'kj', mime: 'video/mp4', data: 'frame'}});
  assert.equal(studio.screen.firstElementChild.src, '/view/b.mp4');
});

test('Full video remains playable while another clip is rendering', () => {
  const studio = player();
  studio.view = 'full';
  studio.host.editor.fullLink.hidden = false;
  studio.host.editor.fullLink.setAttribute('href', '/view/seq_partial.mp4');
  studio.host.editor.partialVideo = {rendered: 1, boxes: 3, mode: 'rendered'};
  studio.refreshPlayer({...idleWatch(), running: true, preview: {source: 'kj', mime: 'video/mp4', data: 'frame'}});
  assert.equal(studio.screen.firstElementChild.src, '/view/seq_partial.mp4');
  assert.match(studio.badge.textContent, /1 of 3 clips rendered/);
  assert.equal(studio.fullButton.disabled, false);
});

test('saved player retries unsupported video with a compatible preview and keeps it on refresh', () => {
  const studio=player();
  const original='http://localhost/api/view?filename=a.mp4&subfolder=h3_sequences%2Fseq&type=output';
  studio.showVideo(original,'/poster.png');
  const video=studio.screen.firstElementChild;
  assert.equal(video.playsInline,true);
  assert.equal(video.poster,'/poster.png');
  video.dispatchEvent(new Event('error'));
  assert.match(video.src,/\/api\/h3c\/video\/preview\?/);
  studio.showVideo(original,'/poster.png');
  assert.equal(studio.screen.firstElementChild,video);
  const fallback=video.src;
  video.dispatchEvent(new Event('error'));
  assert.equal(video.src,fallback,'a failed preview must not trigger a retry loop');
});
