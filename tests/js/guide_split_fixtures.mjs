// Timelines for the guide-split tests. Shared by the Node tests and the Python server-agreement test (through
// emit_guide_split.mjs), so both languages check the same edited JSON.
export const CONTEXT = 39;
export const guideFile = (name = 'guide_a') => ({ filename: `${name}.png`, subfolder: 'h3_previews', type: 'output' });

const box = (id, frames, prompt, extra = {}) => ({
  id, frames, prompt, seed: 7, cut: false, first: '', last: '', ...extra,
});

// A fresh clip; the accepted guide sits on Shot 2's start (frame 96).
export function shotGuideTimeline() {
  return {
    prompt: '',
    boxes: [box('a', 192, [
      '[Shot 1] A woman walks along the pier.',
      '[Shot 2] At 00:04.000, the camera cuts to a close-up of her face.',
      '[Shot 3] At 00:06.000, the camera cuts to the sea.',
    ].join('\n'), {
      previews: [
        { target: { kind: 'shot', shot: 2 }, frame: 96, guide: guideFile(), images: [{ file: guideFile('cand_b') }],
          still_prompt: 'Close-up of her face.' },
        { target: { kind: 'shot', shot: 3 }, frame: 144, guide: guideFile('guide_c') },
      ],
    })],
  };
}

const REF_PROMPT = [
  'subject_definitions:',
  '<Subject 1> is the woman from @image1.',
  '',
  'summary: [reference generation] 2 shots featuring <Subject 1>.',
  '',
  'retention_analysis:',
  '<Subject 1> (appears in [Shot 1], [Shot 2]): keep her face.',
  '',
  'detailed_description:',
  'Cinematic, warm light.',
  '[Shot 1] <Subject 1> walks along the pier, then stops at the railing.',
  '[Shot 2] At 00:06.000, the camera cuts to <Subject 1> looking at the sea.',
  '',
  'overall_soundscape: Waves.',
  '',
  'non_diegetic_music: N/A',
].join('\n');

// Clip 2 continues clip 1 and references @image1; a legacy guide sits inside Shot 1 at local frame 80.
export function continuingTimeline() {
  return {
    prompt: '',
    bible: { entities: [{ id: 'e1', name: 'Mia', kind: 'character', pins: [{ box: 'b', frame: 100 }, { box: 'b', frame: 10 }] }] },
    boxes: [
      box('a', 107, '[Shot 1] The pier at dawn.'),
      box('b', 204, REF_PROMPT, {
        previews: [
          { shot: 9, frame: 80, guide: guideFile() },
          { target: { kind: 'last' }, frame: 204, images: [{ file: guideFile('cand_last') }] },
        ],
        plate_changes: [{ slot: 'image1', frame: 150, revision: '' }, { slot: 'image1', frame: 20, revision: '' }],
      }),
      box('c', 102, '[Shot 1] She turns away.', { memory: 'selected', memories: [{ box: 'b', frame: 120, label: 'the railing' }] }),
    ],
  };
}

// A fresh clip with a reference but no First: cached RefMods cannot keep its left half FLF2VA.
export function noFirstTimeline() {
  const timeline = shotGuideTimeline();
  timeline.boxes[0].prompt = timeline.boxes[0].prompt.replace('A woman walks', 'The woman from @image1 walks');
  return timeline;
}
