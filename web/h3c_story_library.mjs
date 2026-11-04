import {parseJSON,stringifyJSON} from './h3c_project.mjs?v=20261031-held-jobs-1';
import {settledPreparation} from './h3c_reference_preparation.mjs?v=20261014-reference-thumbnails-1';
import {applyResult,parseStoryState,serializeStoryState} from './h3c_story_model.mjs?v=20261011-reference-preparation-1';
import {reconcileSceneAnchors} from './h3c_still_scene.mjs?v=20261011-reference-preparation-1';

const CONTENT_FIELDS=new Set(['name','timeline','idea','state','idea_images','template']);

function savedFields(workflow,node,textNodes=new Set()) {
  if(!node)throw Error('The saved story has no linked Story and Timeline.');
  const fields={};
  for(const [index,input]of (node.inputs??[]).filter(input=>input.widget).entries()) {
    const name=input.widget.name;
    let value=node.widgets_values?.[index];
    let port=input;
    const seen=new Set();
    while(port?.link!=null&&!seen.has(port.link)) {
      seen.add(port.link);
      const raw=workflow.links.find(link=>String(Array.isArray(link)?link[0]:link.id)===String(port.link));
      const source=workflow.nodes.find(node=>String(node.id)===String(Array.isArray(raw)?raw[1]:raw?.origin_id));
      if(!['PrimitiveString','PrimitiveStringMultiline'].includes(source?.type))break;
      textNodes.add(String(source.id));
      value=source.widgets_values?.[0];port=source.inputs?.find(input=>(input.widget?.name??input.name)==='value');
    }
    if(value!==undefined)fields[name]=value;
  }
  return fields;
}

export function sameStoryWiring(a,b) {
  const wiring=workflow=>{
    const graph=structuredClone(workflow);
    const graphs=[graph];
    while(graphs.length) {
      const current=graphs.pop();
      graphs.push(...(current.definitions?.subgraphs??[]));
      const textNodes=new Set();
      for(const node of current.nodes??[])if(['H3C_Story','H3C_Timeline'].includes(node.type))savedFields(current,node,textNodes);
      if(current.extra)delete current.extra.ds;
      for(const node of current.nodes??[]) {
        for(const key of ['pos','size','order','title','showAdvanced'])delete node[key];
        if(['H3C_Story','H3C_Timeline'].includes(node.type)) {
          node.widgets_values=Object.fromEntries(Object.entries(savedFields(current,node)).filter(([name])=>!CONTENT_FIELDS.has(name)));
          delete node.widgets_values_named;
          // Uploaded guide and asset registries record media, not generator wiring.
          for(const key of ['h3c_library_revision','h3c_fork_sequence','h3c_project','h3c_asset_bindings','h3c_generation_import','h3c_manual_guides','h3c_uploaded_assets'])
            if(node.properties)delete node.properties[key];
        }
        if(textNodes.has(String(node.id))){delete node.widgets_values;delete node.widgets_values_named;}
        if(node.properties&&!Object.keys(node.properties).length)delete node.properties;
      }
    }
    // Layout and native tab identity do not determine whether saved takes belong to this generator.
    return stringifyJSON({nodes:graph.nodes,links:graph.links,definitions:graph.definitions});
  };
  return wiring(a)===wiring(b);
}

export function savedStoryContent(value,current) {
  const workflow=value.workflow,source=workflow?.nodes?.find(node=>node.type==='H3C_Story'&&String(node.id)===String(value.story));
  const story=savedFields(workflow,source),state=parseJSON(story.state||'{}');
  if(!state||typeof state!=='object'||Array.isArray(state))throw Error('The saved Story state is invalid.');
  const linked=workflow.links?.find(link=>String(Array.isArray(link)?link[1]:link.origin_id)===String(source.id)
    &&workflow.nodes.some(node=>node.type==='H3C_Timeline'&&String(node.id)===String(Array.isArray(link)?link[3]:link.target_id)));
  const targetId=state.timeline||value.job?.timeline||(Array.isArray(linked)?linked[3]:linked?.target_id);
  const target=workflow.nodes.find(node=>node.type==='H3C_Timeline'&&String(node.id)===String(targetId));
  const fields=savedFields(workflow,target),timeline=parseJSON(fields.timeline);
  if(!Array.isArray(timeline?.boxes))throw Error('The saved story has no valid Timeline.');
  const before=stringifyJSON(timeline),result=value.job?.view?.result;
  if(result) {
    const recovered=applyResult(timeline,parseStoryState(story.state),result,String(target.id),Number(fields.context_frames)||39);
    story.state=serializeStoryState(recovered.state);
  }
  const renders=sameStoryWiring(current,workflow);
  if(!renders) {
    delete timeline.still_requests;
    if(timeline.reference_preparation)timeline.reference_preparation=settledPreparation(timeline.reference_preparation);
    // Accepted guides are the user's chosen frames, not renders of the saved generator; keep them.
    // Candidates, in-flight jobs and saved-take sources belong to the old generator and sequence.
    for(const box of timeline.boxes)for(const preview of box.previews??[])
      for(const key of ['image','images','pending','job','still_source'])delete preview[key];
    // Scene anchors are pinned accepted guides; keep only those whose guide is still accepted.
    if(Array.isArray(timeline.continuity?.anchors))reconcileSceneAnchors(timeline);
    else if(timeline.continuity)delete timeline.continuity.anchors;
  }
  return {story,timeline:before===stringifyJSON(timeline)?fields.timeline:stringifyJSON(timeline),
    sequence:renders?value.sequence:`Project-${crypto.randomUUID().slice(0,8)}`,renders};
}

export function isWiringConflict(error) {
  return error?.code==='h3c_story_wiring_conflict'||/Workflow wiring changed in another browser/.test(error?.message??'');
}

// New project promises to preserve the current project before clearing it.
// A stale imported workflow must save an independent copy, never replace the
// other browser's wiring or discard the local prompts to load that snapshot.
export async function saveBeforeNewProject(story, saved) {
  try {
    await saved.flush();
    await story?.saved.flush();
    await story?.saveLibrary?.(true);
  } catch(error) {
    if(!story?.forkLibrary||!isWiringConflict(error))throw error;
    await story.forkLibrary();
  }
}

export class StoryLibrary {
  constructor(host) { this.host=host; this.pending=false; }
  check() { if(this.host.busy())throw Error('Wait for writing, uploads and rendering to finish before switching stories.'); }
  async refresh() {
    const {stories,names}=await this.host.request('/h3c/stories');
    return {stories,names:names??{}};
  }
  // The name the user wants for a story, null if they cancel; an empty name goes back to the story's own title.
  async ask(group) {
    const name=await this.host.prompt('Name this story. Leave it empty to use its own title.',group.name||group.title);
    return typeof name==='string'?name:null;
  }
  async rename(key,name) {
    if(this.pending)return false;
    this.pending=true;
    try {await this.host.request('/h3c/stories/rename',{key,name});return true;}
    finally {this.pending=false;}
  }
  async open(id) {
    if(this.pending)return;
    this.check();this.pending=true;
    try {
      await this.host.save();
      this.check();
      const revision=this.host.revision?.();
      const value=await this.host.request('/h3c/stories?id='+encodeURIComponent(id));this.check();
      if(revision!==undefined&&JSON.stringify(revision)!==JSON.stringify(this.host.revision()))throw Error('The open story changed while loading. Your edits were kept; load again.');
      await this.host.load(value);
    } finally {this.pending=false;}
  }
  async remove(entry) {
    if(this.pending)return false;
    this.check();this.pending=true;
    try {
      if(!await this.host.confirm(`Permanently delete “${entry.title}” and its generated videos, stills and takes? Shared uploads and RefMods are kept. This cannot be undone.`))return false;
      this.check();await this.host.request('/h3c/stories/delete',{id:entry.id});
      await this.host.deleted(entry.id);return true;
    } finally {this.pending=false;}
  }
  // Every version of one story, after one confirmation. Stops at the first failure and says how many were removed.
  async removeAll(group) {
    if(this.pending)return false;
    this.check();this.pending=true;
    let removed=0;
    try {
      const count=group.versions.length;
      if(!await this.host.confirm(`Permanently delete “${group.label}”, all ${count} ${count===1?'version':'versions'}, and their generated videos, stills and takes? Shared uploads and RefMods are kept. This cannot be undone.`))return false;
      for(const entry of group.versions) {
        this.check();await this.host.request('/h3c/stories/delete',{id:entry.id});
        removed++;await this.host.deleted(entry.id);
      }
      // The name belonged to this story only; a failure to clear it leaves a harmless label.
      if(group.name)await this.host.request('/h3c/stories/rename',{key:group.key,name:''}).catch(()=>{});
      return true;
    } catch(error) {
      error.message=`${error.message} (${removed} of ${group.versions.length} versions deleted.)`;
      error.partial=removed>0;throw error;
    } finally {this.pending=false;}
  }
}
