"""Typed domain operations. Routing never comes from a caller-supplied URL."""
from typing import Any, Literal
from urllib.parse import quote, urlencode

from pydantic import BaseModel, StrictInt, model_validator

from .transport import StudioError, encoded, parse

PREFIX = '/h3c/api/v1'


class Target(BaseModel):
    kind: Literal['managed', 'native']
    id: str | None = None
    graph: str | None = None
    timeline_node: str | None = None
    story_node: str | None = None

    @model_validator(mode='after')
    def identity(self):
        if self.kind == 'managed' and not self.id:
            raise ValueError('Managed target needs its project id')
        if self.kind == 'native' and (not self.graph or not self.timeline_node):
            raise ValueError('Native target needs graph and timeline_node')
        return self

    def wire(self):
        return self.model_dump(exclude_none=True)


class JobHandle(BaseModel):
    kind: Literal['managed', 'video', 'story', 'still', 'reference']
    id: str
    target: Target | None = None
    request_key: str | None = None


def _object(text):
    try:
        value = parse(text)
        if not isinstance(value, dict):
            raise ValueError()
        return value
    except (ValueError, UnicodeError) as error:
        raise StudioError('Supply a finite JSON object string.', code='invalid_document') from error


def _project_path(target, suffix=''):
    if target.kind != 'managed':
        raise StudioError('Use the native saved-workflow operation for this target.', code='unsupported_target_operation')
    return PREFIX + '/projects/' + quote(target.id, safe='') + suffix


def _managed_revision(revision):
    if set(revision) != {'project'} or type(revision['project']) is not int:
        raise StudioError('Use the current managed project revision.', code='revision_conflict')
    return revision['project']


def managed_view(project):
    fields = {key: project[key] for key in ('name', 'timeline', 'settings', 'assets', 'consumer', 'semantic_boxes') if key in project}
    return dict(target={'kind': 'managed', 'id': project['id']}, revision={'project': project['revision']},
                document_json=encoded(fields).decode(), inspection_json=encoded(project.get('inspection', {})).decode(),
                execution_ready=True, profile=project.get('profile'), profile_sha256=project.get('profile_sha256'),
                sequence=project.get('sequence'), active_job=project.get('active_job'))


class StudioTools:
    def __init__(self, client, guidance, state_dir=None):
        self.client, self.guidance, self.state_dir = client, guidance, state_dir
        self.jobs = None

    def _post(self, path, body, key=None):
        return self.client.json(path, method='POST', body=body, key=key)

    def _context(self, target, revision, operation):
        if target.kind != 'native':
            raise StudioError('This operation is native-only; deliberately export/fork first if needed.', code='unsupported_target_operation')
        return self._post('/h3c/agent/projects/context', dict(target=target.wire(), expected_revision=revision, operation=operation))

    def h3_capabilities(self) -> dict[str, Any]:
        """Inspect this host's readiness/profiles, skill resources and capability coverage before authoring."""
        return {**self.client.json(PREFIX + '/capabilities'), 'agent_api_version': 1, 'coverage': self.guidance.catalog().get('coverage', {})}

    def h3_read_guidance(self, uri: str = 'skill://h3-continuity-video/SKILL.md') -> dict[str, Any]:
        """Read current host guidance as ordinary context. This does not activate a client skill."""
        raw, mime = self.guidance.read(uri)
        return dict(uri=uri, mime_type=mime, text=raw.decode('utf-8'))

    def h3_list_projects(self, kind: Literal['managed', 'native'] = 'managed', cursor: str | None = None, limit: int = 50) -> dict[str, Any]:
        """List one saved-project kind at a time; keep its pagination cursor with that kind."""
        query = urlencode({'limit': limit, **({'cursor': cursor} if cursor is not None else {})})
        return self.client.json((PREFIX + '/projects' if kind == 'managed' else '/h3c/agent/projects') + '?' + query)

    def h3_get_project(self, target: Target) -> dict[str, Any]:
        """Read saved authored data and revisions. Edit document_json to preserve uint64 seeds and opaque fields."""
        if target.kind == 'managed':
            return managed_view(self.client.json(_project_path(target)))
        return self._post('/h3c/agent/projects/read', {'target': target.wire()})

    def h3_create_project(self, document_json: str, request_key: str) -> dict[str, Any]:
        """Create a managed project with a ready profile and a saved idempotency key; never guess a profile."""
        return managed_view(self._post(PREFIX + '/projects', _object(document_json), request_key))

    def h3_save_project(self, target: Target, expected_revision: dict[str, StrictInt], document_json: str) -> dict[str, Any]:
        """Replace saved authored data under its current revision. Conflicts require rereading; no automatic merge."""
        document = _object(document_json)
        if target.kind == 'managed':
            project = self.client.json(_project_path(target), method='PUT', body={**document, 'expected_revision': _managed_revision(expected_revision)})
            return managed_view(project)
        return self._post('/h3c/agent/projects/save', dict(target=target.wire(), expected_revision=expected_revision, document=document))

    def h3_register_workflow(self, target: Target, workflow_json: str, expected_revision: dict[str, StrictInt] | None = None) -> dict[str, Any]:
        """Register an explicit native {ui,api} snapshot; existing saved targets require their current revision."""
        if target.kind != 'native':
            raise StudioError('Managed profiles cannot be replaced with native snapshots.', code='unsupported_target_operation')
        workflow = _object(workflow_json)
        return self._post('/h3c/agent/projects/register', dict(target=target.wire(), workflow_ui=workflow.get('ui'),
                          workflow_api=workflow.get('api'), expected_revision=expected_revision))

    def h3_export_workflow(self, target: Target, mode: Literal['fork', 'attached'] = 'fork') -> dict[str, Any]:
        """Export an editable managed workflow. Fork is deliberate and does not run or change the source project."""
        workflow = self.client.json(_project_path(target, '/workflow?' + urlencode({'mode': mode})))
        return dict(workflow_json=encoded(workflow).decode())

    def h3_upload_asset(self, path: str, kind: Literal['picture', 'guide', 'audio', 'video', 'whisper']) -> dict[str, Any]:
        """Upload original bytes from an allowed adapter-local path, returning host asset identity and hash."""
        return self.client.upload(path, kind)

    def h3_download_artifact(self, artifact_id: str, destination: str) -> dict[str, Any]:
        """Download immutable managed media into an allowed local path only after hash/size verification."""
        self.client.local_path(destination)
        descriptor = self.client.json(PREFIX + '/artifacts/' + quote(artifact_id, safe=''))
        return self.client.download(descriptor, destination)

    def h3_plan_video(self, target: Target, expected_revision: dict[str, StrictInt], selection_json: str = '{"kind":"all"}') -> dict[str, Any]:
        """Inspect render dependencies/reuse before submission. Planning itself never queues a render."""
        if target.kind == 'native':
            return self._native_jobs().prepare(target, expected_revision, _object(selection_json))
        plan = self._post(_project_path(target, '/plan'), dict(expected_revision=_managed_revision(expected_revision), selection=_object(selection_json)))
        return dict(plan_sha256=plan['plan_sha256'], plan_json=encoded(plan).decode(), target=target.wire(), revision=expected_revision)

    def h3_render_video(self, target: Target, expected_revision: dict[str, StrictInt], request_key: str,
                        plan_sha256: str, selection_json: str = '{"kind":"all"}') -> dict[str, Any]:
        """Explicitly submit approved video work. Keep this request/key; uncertain replies must not cause duplicate work."""
        if target.kind == 'native':
            return self._native_jobs().submit_video(target, expected_revision, _object(selection_json), plan_sha256, request_key)
        data = self._post(_project_path(target, '/jobs'), dict(expected_revision=_managed_revision(expected_revision),
                          selection=_object(selection_json), plan_sha256=plan_sha256), request_key)
        return dict(job=dict(kind='managed', id=data['id'], target=target.wire(), request_key=request_key), data_json=encoded(data).decode(), state=data['state'])

    def _native_jobs(self):
        if self.jobs is None:
            from .jobs import NativeJobs
            self.jobs = NativeJobs(self.client, self.state_dir)
        return self.jobs

    def h3_job_status(self, job: JobHandle) -> dict[str, Any]:
        """Poll once; status never submits the next native unit. Retain failed/held evidence and completed proposals."""
        if job.kind != 'managed':
            return self._native_jobs().status(job)
        data = self.client.json(PREFIX + '/jobs/' + quote(job.id, safe=''))
        return dict(job=job.model_dump(exclude_none=True), state=data['state'], data_json=encoded(data).decode(),
                    blocked_by=data.get('blocked_by'), artifacts=data.get('artifacts', []))

    def h3_cancel_job(self, job: JobHandle) -> dict[str, Any]:
        """Request scoped cancellation. Never clears the global ComfyUI queue or interrupts unrelated work."""
        if job.kind != 'managed':
            return self._native_jobs().cancel(job)
        return self._post(PREFIX + '/jobs/' + quote(job.id, safe='') + '/cancel', {})

    def h3_resume_job(self, job: JobHandle) -> dict[str, Any]:
        """Reconcile retained evidence, not rerun failed/uncertain work."""
        if job.kind != 'managed':
            return self._native_jobs().status(job)
        return self._post(PREFIX + '/jobs/' + quote(job.id, safe='') + '/resume', {})

    def h3_abandon_job(self, job: JobHandle, reason: str, confirm_prompt_id: str | None = None) -> dict[str, Any]:
        """Human-attested close of a held managed job. Requires the person's reason and matching held prompt id."""
        if job.kind != 'managed':
            raise StudioError('Native uncertain submissions require retained evidence; do not automatically abandon them.', code='unsupported_target_operation')
        return self._post(PREFIX + '/jobs/' + quote(job.id, safe='') + '/abandon', dict(reason=reason, confirm_prompt_id=confirm_prompt_id))
