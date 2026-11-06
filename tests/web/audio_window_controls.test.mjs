import test from 'node:test';
import assert from 'node:assert/strict';
import {installDom} from './fake_dom.mjs';
import {AudioLanes} from '../../web/h3c_audio_lanes.mjs';
import * as model from '../../web/h3c_timeline_model.mjs';
import {lockEligibility} from '../../web/h3c_audio_windows.mjs';
installDom();
const create=document.createElement;
document.createElement=tag=>{const node=create(tag);if(tag==='audio')node.pause=()=>{node.paused=true;};return node;};
const all=node=>[node,...node.children.flatMap(all)];
function setup(){
  const state=model.parseState(JSON.stringify({boxes:[{id:'a',frames:96,exact:true},{id:'b',frames:96,exact:true,cut:true}],audio_clips:[{slot:'audio1',title:'Voice',file:{type:'input',filename:'voice.wav'},start:0,source_start:30,duration:8,source_duration:40}]}));
  const editor={state,selected:0,commits:0,host:{connected:()=>({audios:[]}),context:()=>0,viewUrl:()=>'/voice.wav',confirmAudioUnlock:async()=>true},commit(){this.commits++;},inspect(){},inspectClip(){}};
  const lanes=new AudioLanes(editor);lanes.settings.querySelector=tag=>all(lanes.settings).find(node=>node.tagName===tag.toUpperCase());
  return {editor,lanes,clip:state.audio_clips[0]};
}
test('eligibility rejects only conflicting soundtrack bridges and empty timelines',()=>{
  const {editor,clip}=setup();editor.state.bridges=[{before:'b',frames:12}];clip.in_full_video=true;
  assert.equal(lockEligibility(editor.state,clip).ok,false);
  assert.match(lockEligibility(editor.state,clip).conflicts.join(' '),/bridge.*2/i);
  clip.in_full_video=false;assert.equal(lockEligibility(editor.state,clip).ok,true);
  clip.in_full_video=true;clip.duration=2;assert.equal(lockEligibility(editor.state,clip).ok,true);
  editor.state.boxes=[];assert.equal(lockEligibility(editor.state,clip).ok,false);
});
test('lock captures one edit, disables placement edits and preserves shared controls',async()=>{
  const {editor,lanes,clip}=setup();lanes.renderSettings();
  const toggle=()=>all(lanes.settings).find(n=>n.getAttribute('aria-label')==='Lock audio to boxes');
  assert.equal(toggle().checked,false);
  assert.equal(await lanes.setBoxLock(true),true);assert.equal(editor.commits,1);
  lanes.renderSettings();assert.equal(toggle().checked,true);
  for(const label of ['Video start (s)','Source in (s)','Length (s)'])assert.equal(all(lanes.settings).find(n=>n.getAttribute('aria-label')===label).disabled,true);
  assert.equal(all(lanes.settings).find(n=>n.textContent==='Fit to video').disabled,true);
  assert.equal(all(lanes.settings).find(n=>n.getAttribute('aria-label')==='In the full video').disabled,false);
  assert.throws(()=>model.editAudioClip(clip,'move',1),/unlock/i);
  assert.throws(()=>model.setReferenceReplacement(editor.state,'audio1',{file:{type:'input',filename:'other.wav'}},{audios:[]}),/unlock/i);
});
test('cancelled or stale unlock cannot discard bindings or overwrite new edits',async()=>{
  const {editor,lanes,clip}=setup();await lanes.setBoxLock(true);editor.state.boxes[0].frames=144;
  const original=structuredClone(clip.box_windows);editor.host.confirmAudioUnlock=async()=>false;
  assert.equal(await lanes.setBoxLock(false),false);assert.deepEqual(clip.box_windows,original);
  let finish;editor.host.confirmAudioUnlock=()=>new Promise(resolve=>finish=resolve);
  const pending=lanes.setBoxLock(false);editor.state.boxes[1].prompt='newer';finish(true);
  assert.equal(await pending,false);assert.deepEqual(clip.box_windows,original);
  assert.equal(editor.state.boxes[1].prompt,'newer');
});
test('failed commit rolls back one complete transition and bound audition clips hidden tails',async()=>{
  const {editor,lanes,clip}=setup();editor.commit=()=>{throw Error('save failed');};
  assert.equal(await lanes.setBoxLock(true),false);assert.equal(clip.box_windows,undefined);
  editor.commit=()=>{};await lanes.setBoxLock(true);editor.state.boxes[0].frames=48;
  lanes.auditionBox='a';lanes.renderPlayer(clip.file,clip);
  const player=lanes.settings.querySelector('audio');player.currentTime=33;player.fire('play');
  assert.equal(player.currentTime,30);player.currentTime=32;player.fire('timeupdate');assert.equal(player.paused,true);
});
