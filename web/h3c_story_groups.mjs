// Saved stories are stored one entry per workflow identity, and a new identity is made by New project,
// Keep this workflow and loading a story into different wiring. The picker folds entries that carry the same
// title into one group, with each entry a numbered version, so one story is not listed over and over.

const UNTITLED='Untitled story';

export function groupKey(title) {
  return String(title||UNTITLED).normalize('NFKC').trim().replace(/\s+/g,' ').toLocaleLowerCase();
}

// rows: library listing entries ({id,title,updated,...}); names: {groupKey: name} the user gave. Returns groups
// newest-activity first; versions inside a group are newest first, numbered from 1 in the order they were last saved.
// A name the user gave replaces the title shown for the group; the group is still found by its title.
export function groupStories(rows,names={}) {
  const groups=new Map();
  for(const row of rows??[]) {
    const key=groupKey(row.title);
    if(!groups.has(key))groups.set(key,{key,title:String(row.title||UNTITLED).trim()||UNTITLED,versions:[]});
    groups.get(key).versions.push(row);
  }
  const result=[...groups.values()];
  for(const group of result) {
    group.versions.sort((a,b)=>b.updated-a.updated||String(a.id).localeCompare(String(b.id)));
    group.versions=group.versions.map((row,index)=>({...row,version:group.versions.length-index}));
    group.title=String(group.versions[0].title||'').trim().replace(/\s+/g,' ')||UNTITLED;
    group.name=typeof names?.[group.key]==='string'&&names[group.key].trim()?names[group.key].trim():'';
    group.label=group.name||group.title;
    group.updated=group.versions[0].updated;
  }
  return result.sort((a,b)=>b.updated-a.updated||a.label.localeCompare(b.label));
}

export function groupLabel(group) {
  const count=group.versions.length;
  return count>1?`${group.label} · ${count} versions`:group.label;
}

export function versionLabel(row,formatDate=value=>new Date(value*1000).toLocaleString()) {
  return `v${row.version} · ${row.boxes} clips · ${row.status} · ${formatDate(row.updated)}${row.current?' · open now':''}`;
}

// Which group and version to show first: keep the user's choice, else the story open in this workflow, else none.
export function initialSelection(groups,{key,id}={}) {
  const holds=(group,wanted)=>group.versions.some(row=>row.id===wanted);
  const keep=groups.find(group=>group.key===key);
  if(keep)return {key:keep.key,id:holds(keep,id)?id:''};
  const current=groups.find(group=>group.versions.some(row=>row.current));
  if(current)return {key:current.key,id:current.versions.find(row=>row.current).id};
  return {key:'',id:''};
}
