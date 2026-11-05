"""H3 + add-ons: small nodes that turn on Studio features for an H3 Timeline and carry the settings they own.

They pass one H3C_PROJECT value along a chain into the Timeline's `project` input:
{"features": [...], "settings": {...}}. A connected add-on's setting replaces the Timeline's own advanced widget."""

from comfy_api.latest import io

from . import nodes as continuity

ProjectType = io.Custom("H3C_PROJECT")
CHAIN = "Connect to the next H3 + node or to H3 Timeline's project input."


def with_feature(project, feature, settings):
    """A new project value with `feature` listed once and `settings` (the add-on's own keys) set."""
    project = project if isinstance(project, dict) else {}
    features = list(project.get("features") or [])
    if feature not in features:
        features.append(feature)
    return {"features": features, "settings": {**(project.get("settings") or {}), **settings}}


def apply_project(project, **settings):
    """`settings` with each key that a connected add-on carries replaced by its value. Never adds keys."""
    carried = project.get("settings") if isinstance(project, dict) else None
    if not isinstance(carried, dict):
        return settings
    return {key: carried.get(key, value) for key, value in settings.items()}


def _schema(node_id, title, description, widgets=()):
    return io.Schema(
        node_id=node_id,
        display_name=title,
        category=continuity.CATEGORY,
        description=description,
        inputs=[ProjectType.Input("project", optional=True, tooltip="From another H3 + node; optional."), *widgets],
        outputs=[ProjectType.Output(display_name="project", tooltip=CHAIN)],
    )


class H3C_PlusReferences(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("H3C_PlusReferences", "H3 + References",
                       "Turns on pictures, first and last frames, and @image references in the H3 Timeline Studio.",
                       [io.Combo.Input("ref_image_size", options=["match", "max"], default="match",
                                       tooltip="Reference image sizing, as in MiniMax H3 Reference to Video.")])

    @classmethod
    def execute(cls, project=None, ref_image_size="match") -> io.NodeOutput:
        return io.NodeOutput(with_feature(project, "references", {"ref_image_size": ref_image_size}))


class H3C_PlusSound(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("H3C_PlusSound", "H3 + Sound",
                       "Turns on audio lanes, dialogue and timed text in the H3 Timeline Studio.",
                       [io.Boolean.Input("carry_audio", default=True, tooltip="Also carry and freeze the matching audio."),
                        io.Int.Input("audio_context_frames", default=0, min=0,
                                     tooltip="Incoming audio context in 24 fps frames; 0 follows video. Bounded to "
                                             "video context. Following-neighbour ending pins stay full length.")])

    @classmethod
    def execute(cls, project=None, carry_audio=True, audio_context_frames=0) -> io.NodeOutput:
        return io.NodeOutput(with_feature(project, "sound", {"carry_audio": carry_audio,
                                                             "audio_context_frames": audio_context_frames}))


class H3C_PlusContinuity(io.ComfyNode):
    @classmethod
    def define_schema(cls):
        return _schema("H3C_PlusContinuity", "H3 + Continuity tools",
                       "Turns on takes, bridges, visual memory and the continuity check in the H3 Timeline Studio.")

    @classmethod
    def execute(cls, project=None) -> io.NodeOutput:
        return io.NodeOutput(with_feature(project, "continuity", {}))
