// A lossless view of the compiler's H3 text. Editing a field replaces only its body;
// headers, labels, alignment instructions and whitespace stay in the saved prompt.
const TITLES = {
  subject_definitions: 'Subjects & references', summary: 'Summary', retention_analysis: 'Reference retention',
  detailed_description: 'Shots', integrated_multimodal_description: 'Shots',
  overall_soundscape: 'Soundscape', non_diegetic_music: 'Background music',
};
const BASE = ['integrated_multimodal_description', 'overall_soundscape', 'non_diegetic_music'];
const REF = ['subject_definitions', 'summary', 'retention_analysis', 'detailed_description', ...BASE.slice(1)];
// Fast-mode prose may put several definitions on one line. A new statement can start another entry.
const REFERENCE = /(?:^[ \t]*|(?<=[.;])[ \t]+)(<(?:Subject|Picture|Audio|Video) [1-9]\d*>|@(?:image|audio|video_audio|video)\d+(?!\w))/gm;

export function promptSections(source) {
  const dialogue = [...source.matchAll(/<d>[\s\S]*?(?:<\/d>|$)/g)];
  const matches = (pattern, start = 0, end = source.length) => [...source.slice(start, end).matchAll(pattern)]
    .map((match) => ({ index: start + match.index, text: match[0], label: match[1] }))
    .filter(({ index }) => !dialogue.some((d) => index >= d.index && index < d.index + d[0].length));
  const headers = matches(new RegExp(`^[ \\t]*(${Object.keys(TITLES).join('|')}):`, 'gm'));
  const keys = headers.map((h) => h.label).join(',');
  if (keys !== BASE.join(',') && keys !== REF.join(',')) return null;

  function field(start, end, label) {
    const body = source.slice(start, end);
    if (!body.trim()) {
      const at = start + body.match(/^[ \t]*/)[0].length;
      return { start: at, end: at, label, value: '' };
    }
    const leading = body.match(/^\s*/)[0].length;
    const trailing = body.match(/\s*$/)[0].length;
    return { start: start + leading, end: end - trailing, label, value: body.trim() };
  }

  const sections = [];
  if (source.slice(0, headers[0].index).trim()) {
    sections.push({ key: 'alignment', title: 'Frame alignment', fields: [field(0, headers[0].index, 'Frame alignment')] });
  }
  headers.forEach((header, i) => {
    const key = header.label;
    const start = header.index + header.text.length;
    const end = headers[i + 1]?.index ?? source.length;
    const shots = key === 'detailed_description' || key === 'integrated_multimodal_description';
    const refs = key === 'subject_definitions' || key === 'retention_analysis';
    const entries = shots ? matches(/^[ \t]*(\[Shot [1-9]\d*\])(?=\s|$)/gm, start, end)
      : refs ? matches(REFERENCE, start, end) : [];
    const fields = [];
    if (entries.length) {
      if (source.slice(start, entries[0].index).trim()) {
        fields.push(field(start, entries[0].index, shots ? 'Style & scene' : 'Notes'));
      }
      entries.forEach((entry, j) => fields.push(field(entry.index + entry.text.length,
        entries[j + 1]?.index ?? end, entry.label)));
    } else {
      fields.push(field(start, end, TITLES[key]));
    }
    sections.push({ key, title: TITLES[key], fields });
  });
  return sections;
}

export function writePromptSections(source, sections) {
  let result = '', at = 0;
  for (const field of sections.flatMap((section) => section.fields)) {
    result += source.slice(at, field.start) + field.value;
    at = field.end;
  }
  return result + source.slice(at);
}

// Use the same shot boundaries for previews and splitting, including manually written prompts.
export function promptShots(source) {
  const sections = promptSections(source);
  const scene = sections?.find((s) => ['detailed_description', 'integrated_multimodal_description'].includes(s.key));
  const numbered = (p) => /^\[Shot \d+\]$/i.test(p.label);
  if (sections) return { sections, shots: scene.fields.filter(numbered),
    style: scene.fields.filter((p) => !numbered(p)).map((p) => p.value).join('\n') };
  const masked = source.replace(/<d>[\s\S]*?(?:<\/d>|$)/g, (text) => ' '.repeat(text.length));
  const markers = [...masked.matchAll(/^[ \t]*(\[Shot [1-9]\d*\])(?=\s|$)/gmi)];
  return { sections, style: markers.length ? source.slice(0, markers[0].index).trim() : '',
    shots: markers.map((m, i) => ({ label: m[1], value: source.slice(m.index + m[0].length,
      markers[i + 1]?.index ?? source.length).trim() })) };
}
