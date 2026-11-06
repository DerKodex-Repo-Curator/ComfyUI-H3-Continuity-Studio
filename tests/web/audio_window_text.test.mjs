import test from 'node:test';
import assert from 'node:assert/strict';
import {projectTimedText,textClock} from '../../web/h3c_timed_text.mjs';
import {resolveWindows,captureWindows} from '../../web/h3c_audio_windows.mjs';
const boxes=[{id:'a',start:0,duration:4},{id:'b',start:4,duration:4}];
test('synced text follows bound windows, independent text keeps its clock',()=>{
  const lane={slot:'audio1',start:0,source_start:0,duration:8};lane.box_windows=captureWindows(lane,boxes,{source:'audio1'});
  const moved=[{id:'a',start:0,duration:6},{id:'b',start:6,duration:4}];
  const placements=resolveWindows(lane,moved).map(w=>({...w,slot:'audio1'}));
  const value={enabled:true,sync_audio:true,audio_slot:'audio1',start:0,source_start:0,duration:8,direction:'',cues:[{id:'x',start:5,end:6,text:' Hello'}]};
  assert.equal(projectTimedText(value,[lane],6,96,0,placements).cues[0].start_ms,1000);
  assert.equal(projectTimedText(value,[lane],4,48,0,placements).cues.length,0);
  assert.equal(projectTimedText({...value,sync_audio:false},[lane],4,96,0,placements).cues[0].start_ms,1000);
  assert.ok(textClock(value,[lane]).box_windows);
});
