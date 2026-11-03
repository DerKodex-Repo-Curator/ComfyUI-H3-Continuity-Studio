import test from 'node:test';
import assert from 'node:assert/strict';
import * as dialogue from '../../web/h3c_dialogue.mjs';

const wav = {type: 'input', filename: 'line.wav', subfolder: ''};
const clip = (extra = {}) => ({slot: 'audio1', file: wav, start: 0, source_start: 0, duration: 30, ...extra});
const cue = (extra = {}) => ({id: 'c1', recording: {slot: 'audio1', file: wav}, start: 1.5, end: 2.25,
  text: 'Hello there.', speaker: 'Mara', portrayal: 'on_screen', ...extra});

test('alignment keys match h3_continuity.dialogue.alignment_key', async () => {
  assert.equal(await dialogue.alignmentKey(cue()), '3c847fc62192e64e1dda27989d3425916e79f3e5');
  const other = cue({recording: {slot: 'audio2', file: {type: 'input', filename: 'voz.wav', subfolder: 'h3'}},
    start: 12, end: 13.5, text: '¿Qué tal? — ok 😀 "quoted" \\ tab\t'});
  assert.equal(await dialogue.alignmentKey(other), '04624ecb00d6b4af2102e8d5246f477fbdf9cf46');
});

test('checking a cue writes its alignment key; unchecking removes it', async () => {
  const item = cue();
  await dialogue.setChecked(item, true);
  assert.equal(item.aligned, '3c847fc62192e64e1dda27989d3425916e79f3e5');
  assert.equal(await dialogue.isChecked(item), true);
  item.text = 'Hello.';
  assert.equal(await dialogue.isChecked(item), false);
  await dialogue.setChecked(item, false);
  assert.equal('aligned' in item, false);
});

test('a transcript becomes unchecked cues of unknown portrayal that keep their speakers', () => {
  const data = {segments: [{start: 1.25, end: 2.5, text: ' Hello there. ', speaker: 'SPEAKER_00'},
    {start: 3, end: 3, text: 'empty interval'}, {start: 4, end: 5, text: '   '}, {start: 6, end: 7.5, text: 'Bye.'}]};
  const found = dialogue.cuesFromTranscript(data, clip(), []);
  assert.deepEqual(found.cues, [
    {id: 'c1', recording: {slot: 'audio1', file: wav}, start: 1.25, end: 2.5, text: 'Hello there.',
      speaker: 'SPEAKER_00', portrayal: 'unknown', origin: 'transcript'},
    {id: 'c2', recording: {slot: 'audio1', file: wav}, start: 6, end: 7.5, text: 'Bye.', speaker: '',
      portrayal: 'unknown', origin: 'transcript'}]);
  assert.equal(found.skipped, 2);
  assert.deepEqual(dialogue.cuesFromTranscript([{timestamp: [0, 1], text: 'Hi.'}], clip(), [cue({id: 'c1'})]).cues
    .map((item) => item.id), ['c2']);
});

test('transcript text with H3 control tokens is refused, naming the segment', () => {
  assert.throws(() => dialogue.cuesFromTranscript({segments: [{start: 0, end: 1, text: '<d>Hi</d>'}]}, clip(), []),
    /segment 1 .*<d>/);
  assert.throws(() => dialogue.cuesFromTranscript({words: [{start: 0, end: 1, word: 'Hi'}]}, clip(), []),
    /segments/);
});

test('Story dialogue maps from each box generation clock onto the recording', () => {
  const state = {boxes: [
    {id: 'a', frames: 107, cut: false, source: {frame: {carried: 0}, reply: {shots: [{dialogue: [
      {start_ms: 500, end_ms: 1500, speaker: 'Mara', subject: 'e1', text: 'Hello there.', voiceover: false}]}]}}},
    {id: 'b', frames: 68, cut: false, source: {frame: {carried: 39}, reply: {shots: [{dialogue: [
      {start_ms: 2000, end_ms: 2500, speaker: '', subject: 'e2', text: 'Who is it?', voiceover: true}]}]}}},
    {id: 'c', frames: 107, cut: true}]};
  const found = dialogue.cuesFromStory(state, clip({start: 0.25, source_start: 10, duration: 20}), [], 39);
  const [first, second] = found.cues;
  assert.equal(found.cues.length, 2);
  assert.deepEqual(first, {id: 'c1', recording: {slot: 'audio1', file: wav}, start: 10.25, end: 11.25,
    text: 'Hello there.', speaker: 'Mara', portrayal: 'on_screen', origin: 'story'});
  assert.deepEqual([second.id, second.text, second.speaker, second.portrayal], ['c2', 'Who is it?', 'e2', 'voiceover']);
  assert.ok(Math.abs(second.start - (10 + 107 / 24 - 39 / 24 + 2 - 0.25)) < 1e-9);
  assert.ok(Math.abs(second.end - second.start - 0.5) < 1e-9);
  assert.equal(found.skipped, 0);
});

test('Story lines outside the recording window are skipped and counted', () => {
  const state = {boxes: [{id: 'a', frames: 107, cut: false, source: {frame: {carried: 0}, reply: {shots: [{dialogue: [
    {start_ms: 0, end_ms: 400, speaker: 'Mara', text: 'Early.', voiceover: false},
    {start_ms: 1000, end_ms: 1500, speaker: 'Mara', text: 'Inside.', voiceover: false}]}]}}}]};
  const found = dialogue.cuesFromStory(state, clip({start: 0.5, duration: 10}), [], 39);
  assert.deepEqual(found.cues.map((item) => item.text), ['Inside.']);
  assert.equal(found.skipped, 1);
});

test('cue problems mirror the server validation', () => {
  assert.equal(dialogue.cueProblem(cue()), '');
  assert.match(dialogue.cueProblem(cue({end: 1.5})), /end after/);
  assert.match(dialogue.cueProblem(cue({text: ' '})), /words/);
  assert.match(dialogue.cueProblem(cue({text: 'Hi <d>there</d>'})), /<d>/);
  assert.match(dialogue.cueProblem(cue({portrayal: 'maybe'})), /portrayal/);
});

test('a new cue starts at the recording window and takes a free id', () => {
  const made = dialogue.newCue([cue({id: 'c1'}), cue({id: 'c3'})], clip({source_start: 4}));
  assert.deepEqual(made, {id: 'c2', recording: {slot: 'audio1', file: wav}, start: 4, end: 5, text: '', speaker: '',
    portrayal: 'unknown', origin: 'manual'});
});

test('cue status lines read the server summary', () => {
  assert.equal(dialogue.cueStatusLine(undefined), "Waiting for the Timeline's status.");
  assert.equal(dialogue.cueStatusLine({state: 'bound', placed: true, cut: false, aligned: true, sequence: [4, 4.5]}),
    'Checked · plays 4.00–4.50 s in the video.');
  assert.equal(dialogue.cueStatusLine({state: 'bound', placed: true, cut: true, aligned: false, sequence: [4, 4.5]}),
    'Not checked · plays 4.00–4.50 s in the video · cut by the clip window: extend the clip or edit the words.');
  assert.equal(dialogue.cueStatusLine({state: 'bound', placed: false, aligned: false}),
    'Not checked · outside the clip window, so no box speaks it.');
  assert.match(dialogue.cueStatusLine({state: 'changed', placed: false, aligned: false, slot: 'audio1'}),
    /@audio1 has a different file/);
  assert.match(dialogue.cueStatusLine({state: 'missing', placed: false, aligned: false, slot: 'audio2'}), /@audio2/);
});
