import {test} from 'node:test';
import assert from 'node:assert/strict';
import {savedStoryContent,sameStoryWiring} from '../../web/h3c_story_library.mjs';

const widget = name => ({name,widget:{name},link:null});
function savedStory() {
  return {story:'2',sequence:'saved-renders',workflow:{nodes:[
    {id:1,type:'H3C_Timeline',inputs:['name','width','timeline'].map(widget),
      widgets_values:['saved-renders',736,JSON.stringify({boxes:[{id:'b1',prompt:'A room',frames:22,
        previews:[{id:'p1',image:'candidate.png',still_source:{box:'b1'}}]}]})],
      properties:{h3c_image_output_box:8}},
    {id:2,type:'H3C_Story',inputs:['state'].map(widget),widgets_values:['{"timeline":"1"}']},
    {id:3,type:'CLIPLoader',inputs:['clip_name'].map(widget),widgets_values:['model.safetensors']},
    {id:4,type:'GetImageSize',inputs:[{name:'image',link:1}]},
    {id:5,type:'Result',inputs:['filename_prefix'].map(widget),widgets_values:['rebuild'],
      widgets_values_named:{filename_prefix:'rebuild'}},
  ],links:[[1,1,0,4,0,'IMAGE']]}};
}

for (const [label,edit] of [
  ['selected image-output box', g => { g.nodes[0].properties.h3c_image_output_box=11; }],
  ['empty widget collections', g => { g.nodes[3].widgets_values=[];g.nodes[3].widgets_values_named={}; }],
  ['blank output display', g => { g.nodes[4].widgets_values.push('');g.nodes[4].widgets_values_named.comparison=''; }],
  ['populated output display', g => { g.nodes[4].widgets_values.push('Last render');g.nodes[4].widgets_values_named.comparison='Last render'; }],
  ['redundant named input values', g => { g.nodes[2].widgets_values_named={clip_name:'model.safetensors'}; }],
]) {
  test(`reopening with a different ${label} retains saved videos and still candidates`, () => {
    const saved=savedStory(),before=structuredClone(saved),current=structuredClone(saved.workflow);
    edit(current);
    const loaded=savedStoryContent(saved,current);
    assert.equal(loaded.renders,true);
    assert.equal(loaded.sequence,'saved-renders');
    assert.equal(JSON.parse(loaded.timeline).boxes[0].previews[0].image,'candidate.png');
    assert.equal(sameStoryWiring(saved.workflow,current),true);
    assert.deepEqual(saved,before);
  });
}

for (const [label,edit] of [
  ['model',g => {g.nodes[2].widgets_values[0]='other.safetensors';}],
  ['named generator input',g => {g.nodes[4].widgets_values[0]='other';g.nodes[4].widgets_values_named.filename_prefix='other';}],
  ['render width',g => {g.nodes[0].widgets_values[1]=1024;}],
  ['link',g => {g.links[0][1]=3;}],
  ['node type',g => {g.nodes[2].type='OtherLoader';}],
  ['unknown node property',g => {g.nodes[2].properties={precision:'int8'};}],
  ['unlabelled legacy widget',g => {g.nodes[3].widgets_values=['actual setting'];}],
]) {
  test(`reopening with a changed ${label} still forks safely`, () => {
    const saved=savedStory(),current=structuredClone(saved.workflow);edit(current);
    const loaded=savedStoryContent(saved,current);
    assert.equal(loaded.renders,false);
    assert.notEqual(loaded.sequence,'saved-renders');
    assert.match(loaded.sequence,/^Project-/);
    assert.equal(JSON.parse(loaded.timeline).boxes[0].previews[0].image,undefined);
  });
}

test('auxiliary seed controls do not shift input positions or hide generator changes', () => {
  const saved=savedStory();saved.workflow.nodes.push({id:6,type:'Sampler',
    inputs:['seed','steps','sampler'].map(widget),widgets_values:[1,'fixed',8,'euler'],
    widgets_values_named:{seed:1,control_after_generate:'fixed',steps:8,sampler:'euler'}});
  const current=structuredClone(saved.workflow);
  current.nodes.at(-1).widgets_values[3]='heun';current.nodes.at(-1).widgets_values_named.sampler='heun';
  assert.equal(savedStoryContent(saved,current).renders,false);
});

test('unlabelled trailing values are preserved when display widgets cannot be identified', () => {
  const saved=savedStory();delete saved.workflow.nodes[4].widgets_values_named;
  saved.workflow.nodes[4].widgets_values.push('setting');
  const current=structuredClone(saved.workflow);current.nodes[4].widgets_values[1]='changed';
  assert.equal(savedStoryContent(saved,current).renders,false);
});

test('subgraph display widgets do not detach renders, but subgraph inputs still do', () => {
  const saved=savedStory();saved.workflow.definitions={subgraphs:[{id:'sub',
    nodes:[structuredClone(saved.workflow.nodes[4])],links:[]}]};
  const current=structuredClone(saved.workflow),node=current.definitions.subgraphs[0].nodes[0];
  node.widgets_values.push('Result');node.widgets_values_named.comparison='Result';
  assert.equal(savedStoryContent(saved,current).sequence,'saved-renders');
  node.widgets_values[0]='changed';node.widgets_values_named.filename_prefix='changed';
  assert.equal(savedStoryContent(saved,current).renders,false);
});
