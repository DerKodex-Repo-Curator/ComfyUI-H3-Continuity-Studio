"""Read-only native dependency, reuse and movie-splice planning."""

import copy
import json
from pathlib import Path

from .. import bridges, nodes, store, timeline as rules, timeline_node
from .assets import contained
from .contracts import APIError, canonical, digest, validate


def native_status(body):
    """Native compatibility plus exact manifest/file evidence, under one read lock."""
    with nodes.SEQUENCE_LOCK:
        status = timeline_node.request_status(body, materialize=False)
        if not status.get("ok"):
            raise APIError("native_state_unavailable", "Native Timeline status could not be inspected.", status=409)
        folder = Path(store.sequence_dir(nodes.sequences_root(), body["name"])).resolve()
        manifest = store.load_manifest(folder)
        evidence = {}
        for kind, entries in (("box", manifest["segments"]), ("bridge", manifest.get("bridges", []))):
            for entry in entries:
                box_id = (entry.get("timeline") or {}).get("box") if kind == "box" else entry.get("box")
                if box_id is None: continue
                filenames = [entry["stem"] + ".safetensors", entry["stem"] + "_last.png"]
                if entry.get("video"): filenames.append(entry["video"]["file"])
                stamps = []
                for filename in filenames:
                    path = contained(folder, folder / filename)
                    try:
                        stat = path.stat()
                        stamps.append([filename, stat.st_size, stat.st_mtime_ns])
                    except FileNotFoundError:
                        stamps.append([filename, None])
                evidence[kind + ":" + box_id] = digest({"entry": entry, "files": stamps})
        return {**status, "unit_evidence": evidence,
                "manifest_sha256": digest({"manifest": manifest, "unit_evidence": evidence})}


class Planner:
    def __init__(self, profiles, assets, native_status):
        self.profiles, self.assets, self.native_status = profiles, assets, native_status

    def _units(self, project):
        prepared = project["prepared"]
        parsed = rules.parse(canonical(prepared["timeline"]).decode("utf-8"))
        context = int(prepared["settings"]["context_frames"])
        asset_identity = sorted({item["sha256"] for item in prepared.get("assets", [])
                                 if any(binding['kind'] != 'candidate' for binding in item['bindings'])})
        asset_identity += sorted({item["asset_id"] for item in project.get("assets", [])
                                  if any(binding['kind'] != 'candidate' for binding in item['bindings'])})
        identity = {"profile_sha256": project["profile_sha256"], "settings": prepared["settings"], "assets": asset_identity}
        units, by_box = [], {}
        for index, box in enumerate(parsed.boxes):
            dependencies = []
            if not rules.is_fresh(parsed, index):
                dependencies.append("box:" + parsed.boxes[index - 1].id)
            dependencies.extend("box:" + parsed.boxes[source].id for source, _, _ in rules.memory_sources(parsed, index))
            length = prepared["boxes"][index]
            unit = {"id": "box:" + box.id, "kind": "box", "box_id": box.id, "index": index + 1,
                    "dependencies": list(dict.fromkeys(dependencies)), "frames": length["frames"],
                    "generated_frames": length["generated"], "carried_frames": length["carried"],
                    "delivered_range": length["delivered_range"], "generated_range": length["generated_range"],
                    "input_sha256": digest({**identity, "layout": rules.layout_key(parsed, index, context)})}
            conflict = rules.carry_conflict(parsed, index, context)
            if conflict: unit["blocked_reason"] = conflict
            by_box[box.id] = unit
            units.append(unit)
        for bridge in parsed.bridges:
            index = bridges.position(parsed, bridge)
            before, after = parsed.boxes[index - 1].id, bridge["before"]
            carried, frozen = bridges.ends(context, {"frames": by_box[before]["generated_frames"]},
                                           {"frames": by_box[after]["generated_frames"]})
            unit = {"id": "bridge:" + after, "kind": "bridge", "box_id": after,
                    "dependencies": ["box:" + before, "box:" + after], "frames": bridge["frames"],
                    "generated_frames": carried + bridge["frames"] + frozen, "carried_frames": carried,
                    "frozen_frames": frozen, "input_sha256": digest({**identity, "layout": bridges.layout(parsed, bridge),
                        "before": by_box[before]["input_sha256"], "after": by_box[after]["input_sha256"]})}
            conflict = bridges.problem(parsed, bridge)
            if conflict: unit["blocked_reason"] = conflict
            units.append(unit)
        return units

    def _record(self, project, unit):
        try:
            return self.assets.records.get_blob_record("unit", project["id"] + ":" + unit["id"])
        except APIError as error:
            if error.status != 404: raise
            return None

    def plan(self, project, selection):
        selection = validate("selection", selection)
        prepared = project["prepared"]
        profile = self.profiles.get(project["profile"], project["profile_sha256"])
        # Re-read original/role bytes and native preparation before any reuse.
        resolved = self.assets.resolve(project.get("assets", []), project["authored"]["timeline"], profile)
        fresh = self.profiles.prepare(profile, project["sequence"], project["authored"], resolved)
        if fresh["fingerprint"] != prepared["fingerprint"]:
            raise APIError("prepared_inputs_changed", "Pinned prepared inputs have changed; revise the project.", status=409)
        units = self._units(project)
        selected = selection.get("ids", [])
        known_boxes = {unit["box_id"] for unit in units if unit["kind"] == "box"}
        if set(selected) - known_boxes:
            raise APIError("invalid_selection", "Selection contains an unknown box.", path="/selection/ids")
        status = self.native_status({"name": project["sequence"], "timeline": canonical(prepared["timeline"]).decode("utf-8"),
                                     "settings": prepared["settings"]})
        native_states = {"box:" + item["id"]: item for item in status["boxes"]}
        native_states.update({"bridge:" + item["box"]: item for item in status.get("bridges", [])})
        forced = {"box:" + box_id for box_id in selected} if selection.get("rerender") else set()
        by_id = {}
        for unit in units:
            native = native_states.get(unit["id"], {})
            record = self._record(project, unit)
            evidence = status.get("unit_evidence", {}).get(unit["id"])
            reusable = (native.get("status") == "done" and record and record.get("verified")
                        and record.get("input_sha256") == unit["input_sha256"]
                        and evidence and record.get("native_sha256") == evidence)
            reasons = []
            affected = [source for source in unit["dependencies"] if by_id[source]["action"] != "reuse"]
            if unit.get("blocked_reason"):
                action = "blocked"; reasons.append(unit["blocked_reason"])
            elif any(by_id[source]["action"] == "blocked" for source in unit["dependencies"]):
                action = "blocked"; reasons.append("A required dependency is blocked.")
            elif unit["id"] in forced:
                action = "render"; reasons.append("Explicitly selected for a new take.")
            elif affected:
                action = "render"; reasons.append("Required dependency will render: " + ", ".join(affected))
            elif reusable:
                action = "reuse"; reasons.append("Native compatibility and verified API input/media identity match.")
            else:
                action = "render"
                reasons.append(native.get("reason") or native.get("note") or (
                    "Native media lacks matching verified API input identity; conservatively render." if native.get("status") == "done"
                    else "Full video requires this missing or stale unit."))
            unit.update(action=action, reasons=reasons, native_sha256=evidence)
            by_id[unit["id"]] = unit
        ranges, offset = [], 0
        for unit in [u for u in units if u["kind"] == "box"]:
            bridge_id = "bridge:" + unit["box_id"]
            if bridge_id in by_id:
                bridge = by_id[bridge_id]
                ranges.append({"unit_id": bridge_id, "range": [offset, offset + bridge["frames"]]})
                offset += bridge["frames"]
            ranges.append({"unit_id": unit["id"], "range": [offset, offset + unit["frames"]]})
            offset += unit["frames"]
        result = {"api_version": 1, "project_id": project["id"], "revision": project["revision"],
                  "profile_sha256": project["profile_sha256"], "fingerprint": prepared["fingerprint"],
                  "assets_sha256": digest(project.get("assets", [])), "manifest_sha256": status.get("manifest_sha256", digest(status)),
                  "selection": selection, "units": units, "total_frames": offset, "fps": 24, "splice_ranges": ranges}
        result["plan_sha256"] = digest(result)
        return result

    def invalidation(self, before, after):
        previous = {unit["id"]: unit for unit in self._units(before)}
        units = self._units(after)
        asset_changed = {asset["asset_id"] for asset in before.get("assets", [])
                         if any(binding['kind'] != 'candidate' for binding in asset['bindings'])} != {
                             asset["asset_id"] for asset in after.get("assets", [])
                             if any(binding['kind'] != 'candidate' for binding in asset['bindings'])}
        changed, result = set(), []
        for unit in units:
            old = previous.get(unit["id"])
            direct = old is None or old["input_sha256"] != unit["input_sha256"]
            dependencies = [item for item in unit["dependencies"] if item in changed]
            if direct or dependencies:
                changed.add(unit["id"])
                result.append({"id": unit["id"], "kind": unit["kind"], "box_id": unit["box_id"],
                               "reasons": [("Asset identity changed; conservative invalidation includes this unit." if asset_changed
                                            else "Prepared input identity changed.") if direct else "Dependency changed: " + ", ".join(dependencies)]})
        result.extend({"id": unit_id, "kind": old["kind"], "box_id": old["box_id"], "reasons": ["Unit removed."]}
                      for unit_id, old in previous.items() if unit_id not in {unit["id"] for unit in units})
        return result

    def selected_graph(self, project, unit):
        graph = copy.deepcopy(project["prepared"]["workflow"]["api"])
        target = project["prepared"]["workflow"]["timeline_node"]
        line = copy.deepcopy(project["prepared"]["timeline"])
        line.pop("render_box", None); line.pop("render_bridge", None)
        if unit["kind"] == "box":
            try:
                line["render_box"] = next(index + 1 for index, box in enumerate(line["boxes"]) if box["id"] == unit["box_id"])
            except StopIteration:
                raise APIError("invalid_selection", "Render unit box was not found.") from None
        elif unit["kind"] == "bridge":
            line["render_bridge"] = unit["box_id"]
        else:
            raise APIError("invalid_selection", "Render unit kind is invalid.")
        graph[target]["inputs"]["timeline"] = canonical(line).decode("utf-8")
        return graph
