import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests.continuity_support import enable_comfy_cpu
enable_comfy_cpu()
from h3_continuity import saved_state, story_library
try:
    from h3_continuity.agent_api import projects
except ImportError:
    projects = None


def fixture():
    line = {'version': 1, 'boxes': [{'id': 'a', 'frames': 22, 'prompt': 'Old', 'seed': 18446744073709551615}], 'opaque': {'keep': True}}
    fields = {'name': 'native-study', 'timeline': json.dumps(line), 'width': 768, 'height': 448, 'context_frames': 39,
              'carry_audio': True, 'ref_image_size': 'match', 'audio_context_frames': 0}
    def node(identity, kind, values):
        return dict(id=identity, type=kind, inputs=[dict(name=name, widget={'name': name}) for name in values], widgets_values=list(values.values()))
    ui = dict(id='graph-a', nodes=[node(1, 'H3C_Story', {'state': '{}', 'idea': 'A study'}), node(2, 'H3C_Timeline', fields)], links=[])
    api = {'1': {'class_type': 'H3C_Story', 'inputs': {'state': '{}', 'idea': 'A study'}},
           '2': {'class_type': 'H3C_Timeline', 'inputs': copy.deepcopy(fields)},
           '9': {'class_type': 'H3C_SaveSegment', 'inputs': {'segment': ['2', 3]}}}
    return ui, api


class NativeProjectsTest(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(projects, 'Saved native projects need an agent interface')
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        self.addCleanup(mock.patch.stopall)
        mock.patch('folder_paths.get_system_user_directory', side_effect=lambda name: str(root / name)).start()
        mock.patch('folder_paths.get_user_directory', return_value=str(root / 'user')).start()
        mock.patch('folder_paths.get_output_directory', return_value=str(root / 'output')).start()
        mock.patch('h3_continuity.nodes.sequences_root', return_value=str(root / 'output' / 'h3_sequences')).start()
        self.ui, self.api = fixture()
        self.target = dict(kind='native', graph='graph-a', timeline_node='2', story_node='1')

    def registered(self):
        return projects.register(self.target, self.ui, self.api)

    def test_old_story_is_editable_without_execution_snapshot(self):
        story_library.save('graph-a', '1', self.ui, 'native-study')
        before = projects.read(self.target)
        self.assertFalse(before['execution_ready'])
        document = json.loads(before['document_json'])
        self.assertEqual(document['timeline']['boxes'][0]['seed'], 18446744073709551615)
        document['timeline']['boxes'][0]['prompt'] = 'Changed'
        after = projects.save(self.target, before['revision'], document)
        self.assertEqual(json.loads(after['document_json'])['timeline']['boxes'][0]['prompt'], 'Changed')

    def test_registration_and_edits_update_execution_inputs(self):
        before = self.registered()
        self.assertTrue(before['execution_ready'])
        document = json.loads(before['document_json'])
        document['timeline']['boxes'][0]['prompt'] = 'Changed'
        after = projects.save(self.target, before['revision'], document)
        context = projects.context(self.target, after['revision'], 'video')
        self.assertEqual(json.loads(context['workflow']['api']['2']['inputs']['timeline'])['boxes'][0]['prompt'], 'Changed')
        self.assertEqual(context['workflow']['ui']['id'], 'graph-a')
        self.assertEqual(context['outputs'], ['9'])

    def test_stale_save_preserves_newer_seed_and_metadata(self):
        before = self.registered()
        document = json.loads(before['document_json'])
        document['timeline']['boxes'][0]['prompt'] = 'Accepted'
        accepted = projects.save(self.target, before['revision'], document)
        with self.assertRaisesRegex(ValueError, 'revision'):
            projects.save(self.target, before['revision'], document)
        self.assertEqual(projects.read(self.target)['document_json'], accepted['document_json'])
        self.assertEqual(json.loads(accepted['document_json'])['timeline']['opaque'], {'keep': True})

    def test_primitive_binding_is_updated_without_changing_link(self):
        self.api['width'] = dict(class_type='PrimitiveInt', inputs={'value': 768})
        self.api['2']['inputs']['width'] = ['width', 0]
        before = self.registered()
        document = json.loads(before['document_json'])
        document['settings']['width'] = 1024
        after = projects.save(self.target, before['revision'], document)
        api = projects.context(self.target, after['revision'], 'video')['workflow']['api']
        self.assertEqual(api['width']['inputs']['value'], 1024)
        self.assertEqual(api['2']['inputs']['width'], ['width', 0])

    def test_computed_binding_remains_editable_but_requires_recapture(self):
        self.api['width'] = dict(class_type='SomeComputedWidth', inputs={})
        self.api['2']['inputs']['width'] = ['width', 0]
        before = self.registered()
        document = json.loads(before['document_json'])
        document['settings']['width'] = 1024
        after = projects.save(self.target, before['revision'], document)
        self.assertFalse(after['execution_ready'])
        with self.assertRaisesRegex(ValueError, 'snapshot'):
            projects.context(self.target, after['revision'], 'video')

    def test_browser_widget_overlay_updates_context(self):
        before = self.registered()
        saved_state.write('workflow', 'graph-a', 'workflow', {'2/H3C_Timeline/width': 1024})
        after = projects.read(self.target)
        self.assertNotEqual(after['revision'], before['revision'])
        self.assertEqual(projects.context(self.target, after['revision'], 'video')['settings']['width'], 1024)

    def test_snapshot_cannot_replace_registered_identity_without_revision(self):
        self.registered()
        with self.assertRaisesRegex(ValueError, 'revision'):
            projects.register(self.target, self.ui, self.api)

    def test_wiring_change_invalidates_execution(self):
        self.registered()
        library = story_library.save('graph-a', '1', self.ui, 'native-study')
        changed = copy.deepcopy(self.ui)
        changed['nodes'].append(dict(id=4, type='Other', inputs=[], widgets_values=[]))
        story_library.save('graph-a', '1', changed, 'native-study', library_revision=library['revision'])
        self.assertFalse(projects.read(self.target)['execution_ready'])

    def test_managed_sequence_is_rejected(self):
        self.ui['nodes'][1]['properties'] = {'h3c_project': {'mode': 'attached', 'id': 'managed'}}
        with self.assertRaisesRegex(ValueError, 'managed'):
            self.registered()

    def test_snapshot_save_hook_and_discovery(self):
        story_library.save('graph-a', '1', self.ui, 'native-study', execution=self.api)
        self.assertTrue(projects.read(self.target)['execution_ready'])
        self.assertEqual(projects.list_projects()['projects'][0]['target']['graph'], 'graph-a')

    def test_busy_native_sequence_cannot_be_saved(self):
        before = self.registered()
        with mock.patch('h3_continuity.takes.busy', return_value=True), self.assertRaisesRegex(ValueError, 'busy'):
            projects.save(self.target, before['revision'], json.loads(before['document_json']))

    def test_captured_api_must_match_authored_literal_widgets(self):
        self.api['2']['inputs']['timeline'] = '{"boxes":[]}'
        with self.assertRaisesRegex(ValueError, 'match'):
            self.registered()

    def test_busy_native_sequence_cannot_replace_snapshot(self):
        before = self.registered()
        with mock.patch('h3_continuity.takes.busy', return_value=True), self.assertRaisesRegex(ValueError, 'busy'):
            projects.register(self.target, self.ui, self.api, before['revision'])

    def test_failure_after_widget_save_never_executes_old_authored_inputs(self):
        before = self.registered()
        document = json.loads(before['document_json'])
        document['timeline']['boxes'][0]['prompt'] = 'Saved before interruption'
        with mock.patch.object(projects, '_write', side_effect=OSError('disk unavailable')), self.assertRaises(OSError):
            projects.save(self.target, before['revision'], document)
        after = projects.read(self.target)
        self.assertEqual(json.loads(after['document_json'])['timeline']['boxes'][0]['prompt'], 'Saved before interruption')
        context = projects.context(self.target, after['revision'], 'video')
        self.assertEqual(json.loads(context['workflow']['api']['2']['inputs']['timeline'])['boxes'][0]['prompt'], 'Saved before interruption')

    def test_checkpoint_is_readable_but_cannot_be_saved(self):
        self.registered()
        library = saved_state.read('library', 'graph-a', 'library')['value']
        library['checkpoint_name'] = 'Locked version'
        saved_state.write('library', 'graph-a', 'library', library)
        before = projects.read(self.target)
        self.assertTrue(before['checkpoint'])
        with self.assertRaisesRegex(ValueError, 'checkpoint'):
            projects.save(self.target, before['revision'], json.loads(before['document_json']))

    def test_timeline_only_registration_does_not_invent_a_story(self):
        self.ui['nodes'] = self.ui['nodes'][1:]
        del self.api['1']
        del self.target['story_node']
        before = self.registered()
        self.assertTrue(before['execution_ready'])
        self.assertNotIn('story', json.loads(before['document_json']))
        self.assertEqual(projects.list_projects()['projects'][0]['target'], self.target)

    def test_wrong_timeline_identity_is_rejected(self):
        self.target['timeline_node'] = 'unrelated'
        with self.assertRaisesRegex(ValueError, 'Timeline'):
            self.registered()


if __name__ == '__main__':
    unittest.main()
