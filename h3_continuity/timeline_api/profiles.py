"""Pinned host-configured render graphs and flat editable workflow exports."""

import copy
import json
import os
import re
import uuid
from pathlib import Path

from .. import timeline_prepare
from .contracts import APIError, canonical, digest


class Profiles:
    def __init__(self, root, node_info):
        self.root = Path(root).resolve()
        self.node_info = node_info
        self.shipped = Path(__file__).with_suffix("")
        (self.root / "snapshots").mkdir(parents=True, exist_ok=True)

    def _configured(self):
        files = {p.stem: p for p in self.shipped.glob("*.json")}
        files.update({p.stem: p for p in (self.root / "configured").glob("*.json")})
        return files

    def _read(self, path):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            value.pop("sha256", None)
            canonical(value)
            return value
        except (OSError, ValueError, TypeError):
            raise APIError("profile_unavailable", "Configured profile cannot be read.", status=503) from None

    def _probe(self, profile):
        reasons = []
        workflow = profile.get("workflow", {})
        api, ui = workflow.get("api", {}), workflow.get("ui", {})
        info = self.node_info({node["class_type"] for node in api.values()})
        target = workflow.get("timeline_node")
        saves = [key for key, node in api.items() if node.get("class_type") == "H3C_SaveSegment"]
        captured = profile.get("captured_api") == 2
        selected = workflow.get("save_node") if captured else (saves[0] if len(saves) == 1 else None)
        if target not in api or api[target].get("class_type") != "H3C_Timeline" or selected not in saves:
            return [{"code": "profile_graph", "message": "Profile needs one Timeline and one native Save Segment."}]
        save = api[selected]["inputs"]
        fps = profile.get("output_fps", 24) if captured else 24
        if (type(fps) not in (int, float) or not 1 <= fps <= 240
                or (captured and (not isinstance(workflow.get("execution_outputs"), list)
                    or not 1 <= len(workflow["execution_outputs"]) <= 2
                    or workflow["execution_outputs"][0] != selected
                    or (len(workflow["execution_outputs"]) == 2 and api.get(workflow["execution_outputs"][1], {}).get("class_type") != "SaveVideo")))):
            return [{"code": "profile_graph", "message": "Invalid captured delivery contract."}]
        if save.get("segment") != [target, 3] or save.get("fps") != fps or save.get("write_full_video") is not True:
            reasons.append({"code": "profile_graph", "message": "Save Segment must consume the Timeline and write native 24 fps full video."})
        noise = [node for node in api.values() if node.get("class_type") == "RandomNoise"]
        if (not any(n["inputs"].get("noise_seed") == [target, 4] for n in noise)
                or (not captured and len(noise) != 1)):
            reasons.append({"code": "profile_graph", "message": "RandomNoise must use the Timeline seed."})
        ui_nodes = {str(node["id"]): node for node in ui.get("nodes", [])}
        if set(ui_nodes) != set(api):
            reasons.append({"code": "profile_ui", "message": "Profile UI and API node identities differ."})
        active = set()
        def visit(node_id):
            if node_id in active or node_id not in api: return
            active.add(node_id)
            for value in api[node_id].get("inputs", {}).values():
                if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str): visit(value[0])
        if captured:
            for output in workflow["execution_outputs"]: visit(output)
        for node_id, node in api.items():
            if captured and node_id not in active: continue
            kind = node.get("class_type")
            schema = info.get(kind)
            if schema is None:
                reasons.append({"code": "missing_node", "node": node_id, "class_type": kind})
                continue
            fields = {**schema.get("input", {}).get("required", {}), **schema.get("input", {}).get("optional", {})}
            for name, value in node.get("inputs", {}).items():
                specification = fields.get(name, fields.get(name.split(".")[0]))
                if specification is None and captured and kind == "CustomCombo":
                    values = node["inputs"]
                    index = values.get("index")
                    bound = type(index) is int and index >= 0 and isinstance(values.get("choice"), str) and values.get("choice") == values.get("option" + str(index + 1))
                    if bound and ((name == "index" and type(value) is int) or (re.fullmatch(r"option[1-9]\d*", name) and isinstance(value, str))):
                        specification = ["INT" if name == "index" else "STRING"]
                if specification is None:
                    reasons.append({"code": "input_schema", "node": node_id, "input": name})
                elif not isinstance(value, list) and isinstance(specification[0], list) and value not in specification[0]:
                    reasons.append({"code": "missing_choice", "node": node_id, "input": name,
                                    "message": "Configured choice is not installed."})
            if node_id in ui_nodes:
                outputs = ui_nodes[node_id].get('outputs', [])
                native = list(schema.get('output', []))
                images = outputs[len(native):] if kind == 'H3C_Timeline' else []
                if ([o.get('type') for o in outputs[:len(native)]] != native
                        or (len(outputs) != len(native) and not images)
                        or any(o.get('type') != 'IMAGE' or not re.fullmatch(r'image_[1-9]\d*', o.get('name', '')) for o in images)):
                    reasons.append({"code": "output_schema", "node": node_id, "class_type": kind})
                try:
                    timeline_prepare.ui_connections(ui, ui_nodes[node_id], api, list(node["inputs"]))
                except (ValueError, KeyError, TypeError):
                    reasons.append({"code": "profile_ui", "node": node_id, "message": "UI edges do not match native graph."})
        return reasons

    def _snapshot(self, profile):
        checksum = digest(profile)
        destination = self.root / "snapshots" / (checksum + ".json")
        content = canonical(profile)
        if destination.exists():
            if destination.read_bytes() != content:
                raise APIError("profile_unavailable", "Pinned profile snapshot is damaged.", status=503)
        else:
            temporary = destination.with_suffix("." + uuid.uuid4().hex + ".tmp")
            try:
                with temporary.open("xb") as stream:
                    stream.write(content); stream.flush(); os.fsync(stream.fileno())
                os.replace(temporary, destination)
            finally:
                temporary.unlink(missing_ok=True)
        return {**profile, "sha256": checksum}

    def list(self):
        result = []
        for profile_id, path in sorted(self._configured().items()):
            try:
                profile = self._snapshot(self._read(path))
                reasons = self._probe(profile)
                result.append({"id": profile_id, "title": profile.get("title", profile_id),
                               "sha256": profile["sha256"], "ready": not reasons, "reasons": reasons})
            except APIError as error:
                result.append({"id": profile_id, "ready": False, "reasons": [{"code": error.code, "message": str(error)}]})
        return result

    def get(self, profile_id, sha256=None):
        if not isinstance(profile_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", profile_id):
            raise APIError("not_found", "Render profile was not found.", status=404)
        if sha256 is not None:
            if not re.fullmatch(r"[a-f0-9]{64}", sha256):
                raise APIError("invalid_request", "Profile digest is invalid.")
            path = self.root / "snapshots" / (sha256 + ".json")
        else:
            path = self._configured().get(profile_id)
        if path is None or not path.is_file():
            raise APIError("not_found", "Render profile was not found.", status=404)
        profile = self._read(path)
        if profile.get("id") != profile_id or (sha256 is not None and digest(profile) != sha256):
            raise APIError("profile_unavailable", "Pinned profile identity does not match its snapshot.", status=503)
        reasons = self._probe(profile)
        if reasons:
            raise APIError("profile_unavailable", "Configured render profile is unavailable on this host.", status=503,
                           details={"profile": profile_id, "reasons": reasons})
        return self._snapshot(profile)

    def prepare(self, profile, sequence, body, resolved_assets):
        if profile.get("immutable_settings") is True and body.get("settings"):
            raise APIError("immutable_profile", "Technical settings belong to this saved workflow; upload a new revision.", status=409)
        request = {"version": 1, "name": sequence, "timeline": copy.deepcopy(body["timeline"]),
                   "settings": copy.deepcopy(body.get("settings", {})), "workflow": copy.deepcopy(profile["workflow"]),
                   "assets": copy.deepcopy(resolved_assets), "semantic_boxes": copy.deepcopy(body.get("semantic_boxes", {}))}
        prepared = timeline_prepare.prepare(request)
        if not prepared.get("ok"):
            error = prepared["errors"][0]
            pointer = "/" + "/".join(error["path"].split(".")) if error["path"] != "$" else ""
            raise APIError("invalid_timeline", error["message"], path=pointer)
        return prepared

    def workflow(self, profile, project, *, mode="fork"):
        if mode not in ("fork", "attached"):
            raise APIError("invalid_request", "Workflow mode must be fork or attached.", path="/mode")
        prepared = project["prepared"]
        ui = copy.deepcopy(prepared["workflow"]["ui"])
        target = prepared["workflow"]["timeline_node"]
        node = next(node for node in ui["nodes"] if str(node["id"]) == target)
        node.setdefault("properties", {})["h3c_project"] = {
            "id": project["id"], "revision": project["revision"], "profile_sha256": project["profile_sha256"], "mode": mode}
        # The native widget is already a string, retaining uint64 seed digits.
        node["properties"]["h3c_asset_bindings"] = copy.deepcopy(project.get("assets", []))
        return ui

# static-configuration-interop-v1

# captured-api-delivery-v2

# captured-api-choice-v1

# captured-api-active-outputs-v1
