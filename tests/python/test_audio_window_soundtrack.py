import unittest
import torch
from h3_continuity import audio_tracks, audio_windows, timeline, nodes, dialogue, replacement
from .helpers import box, clip, parse

def parts():
    return [dict(frames=96,coverage=[dict(box='a',first=0,frames=96)]),dict(frames=12,coverage=[]),dict(frames=96,coverage=[dict(box='b',first=0,frames=96)])]


class SoundtrackWindowsTest(unittest.TestCase):
    def lane(self):
        lane=clip(start=0,source_start=0,duration=8,in_full_video=True)
        lane['box_windows']=audio_windows.capture(lane,[dict(id='a',start=0,duration=4),dict(id='b',start=4,duration=4)],{'file':lane['file']})
        lane['windows']=audio_windows.resolve(lane,[dict(id='a',start=0,duration=4),dict(id='b',start=4,duration=4)])
        return lane

    def test_bound_bridge_is_silent_and_ownership_survives_different_saved_duration(self):
        lane=self.lane();rate=11025
        source={'audio1':dict(waveform=torch.ones(1,1,10*rate)*.5,sample_rate=rate)}
        output,_=audio_tracks.place([lane],source,parts())
        self.assertTrue(torch.equal(output[:,4*rate:round(4.5*rate)],torch.zeros_like(output[:,4*rate:round(4.5*rate)])))
        self.assertEqual(output[0,round(4.5*rate)+10],.5)
        short=parts();short[0]=dict(frames=48,coverage=[dict(box='a',first=0,frames=48)])
        mapped=audio_windows.on_output(lane,lane['windows'],short)
        self.assertEqual(mapped[1]['source_start'],4)
        self.assertEqual(mapped[1]['start'],2.5)

    def test_continuous_lane_keeps_playing_through_bridge_and_empty_stays_selected(self):
        lane=self.lane(); continuous=dict(lane);continuous.pop('box_windows');continuous.pop('windows')
        old=audio_windows.on_output(continuous,audio_windows.resolve(continuous,[]),parts())
        self.assertEqual((old[0]['start'],old[0]['duration']),(0,8))
        lane['box_windows']['by_box']={}
        parsed=parse([box('a',96,exact=True)],audio_clips=[lane],requires=[audio_windows.FEATURE])
        marked=audio_tracks.marked(parsed)
        self.assertEqual(len(marked),1);self.assertEqual(marked[0]['windows'],[])
        wave,_=audio_tracks.place(marked,{'audio1':dict(waveform=torch.ones(1,1,44100),sample_rate=11025)},parts())
        self.assertEqual(wave.count_nonzero().item(),0)

    def test_replacement_coverage_and_equivalence(self):
        lane=self.lane()
        whole=[dict(frames=192,coverage=[dict(box='a',first=0,frames=96),dict(box='b',first=0,frames=96)])]
        split=[dict(frames=90,coverage=[dict(box='a',first=0,frames=90)]),dict(frames=12,coverage=[dict(box='a',first=90,frames=6),dict(box='b',first=0,frames=6)]),dict(frames=90,coverage=[dict(box='b',first=6,frames=90)])]
        self.assertTrue(audio_windows.equivalent(audio_windows.on_output(lane,lane['windows'],whole),audio_windows.on_output(lane,lane['windows'],split)))
        continuous=dict(lane);continuous.pop('box_windows')
        self.assertFalse(audio_windows.equivalent(audio_windows.on_output(lane,lane['windows'],parts()),audio_windows.on_output(continuous,audio_windows.resolve(continuous,[]),parts())))

    def test_sequence_clock_lock_covers_internal_gaps_and_box_boundaries(self):
        lane=self.lane();lane['locked']=True
        parsed=parse([box('a',240,exact=True),box('b',96,cut=True,exact=True)],audio_clips=[lane],requires=[audio_windows.FEATURE],bridges=[dict(before='b',frames=12)])
        self.assertTrue(any('inserts' in problem for problem in dialogue.lock_conflicts(parsed)))

    def test_replacement_identity_tracks_effective_bound_source_changes(self):
        lane=self.lane();lane['box_windows']['by_box']['b']['duration']=3
        def parsed(): return parse([box('a',107),box('b',107,cut=True)],audio_clips=[lane],requires=[audio_windows.FEATURE],bridges=[dict(before='b',mode='replace',left=14,right=15)])
        before=parsed();key=replacement.static_key(before,before.replacements[0],39)
        lane['box_windows']['by_box']['b']['source_start']+=.5
        after=parsed()
        self.assertNotEqual(key,replacement.static_key(after,after.replacements[0],39))
