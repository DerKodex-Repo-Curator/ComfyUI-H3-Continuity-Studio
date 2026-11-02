"""Optional integration with the installed H3 RefMod numbered encoder."""

import os
import sys

from PIL import Image, UnidentifiedImageError


def backend():
    import nodes
    loader = nodes.NODE_CLASS_MAPPINGS.get("MiniMaxH3RefModsLoader")
    encoder = nodes.NODE_CLASS_MAPPINGS.get("MiniMaxH3RefModTextEncode")
    if loader is None or encoder is None:
        raise ValueError("H3 Timeline: install ComfyUI-MiniMaxH3Mod with the numbered RefMod encoder")
    return sys.modules[loader.__module__], sys.modules[encoder.__module__]


def metadata(ref, pack):
    path = pack._find_mod_path(ref["name"])
    meta = pack.read_refmod_meta(path)
    member = ref.get("member", -1)
    if not isinstance(meta, dict):
        raise ValueError(f"H3 Timeline: RefMod {ref['name']} has no metadata")
    if meta.get("kind") == "bundle":
        members = pack.bundle_members(meta)
        if not 0 <= member < len(members):
            raise ValueError(f"H3 Timeline: choose a member of RefMod {ref['name']}")
        meta = members[member]
    elif member != -1:
        raise ValueError(f"H3 Timeline: RefMod {ref['name']} is no longer a bundle; select it again")
    if meta.get("kind") not in ("image", "video", "audio"):
        raise ValueError(f"H3 Timeline: unsupported RefMod type in {ref['name']}")
    return path, meta


def resolve(timeline, images=(), audios=()):
    active = [ref for ref in timeline.refmods if ref["slot"] not in timeline.disabled_refs and ref.get("strength", 1) > 0]
    if not active:
        return
    pack, _ = backend()
    for ref in active:
        if ref["slot"] in images or ref["slot"] in audios:
            raise ValueError(f"H3 Timeline: {ref['slot']} has both an input and a RefMod; disconnect the input or remove the RefMod")
        path, meta = metadata(ref, pack)
        ref["kind"] = meta["kind"]
        if (meta["kind"] == "audio") != ref["slot"].startswith("audio"):
            raise ValueError(f"H3 Timeline: RefMod {ref['name']} has changed type; select a matching slot")
        ref["title"] = meta.get("name") or ref["name"]
        ref["saved_description"] = str(meta.get("description") or "")
        ref["stamp"] = pack._file_stamp(path)


def thumbnail(path):
    # Only explicit neighboring previews; browsing the library never decodes latents.
    for suffix in (".preview.png", ".png", ".jpg", ".jpeg", ".webp"):
        candidate = os.path.realpath(path + suffix)
        if os.path.dirname(candidate) != os.path.dirname(os.path.realpath(path + ".safetensors")):
            continue
        try:
            with Image.open(candidate) as image:
                image.verify()
            return candidate
        except (OSError, ValueError, UnidentifiedImageError, Image.DecompressionBombError):
            pass
    return None


def library():
    pack, _ = backend()
    entries = []
    for name in pack._list_mod_names():
        path = pack._find_mod_path(name)
        meta = pack.read_refmod_meta(path)
        if not isinstance(meta, dict):
            continue
        members = enumerate(pack.bundle_members(meta)) if meta.get("kind") == "bundle" else [(-1, meta)]
        preview = thumbnail(path)
        for member, item in members:
            entries.append({"name": name, "member": member, "kind": item["kind"],
                            "title": item.get("name") or name, "description": item.get("description") or "",
                            "thumbnail": bool(preview)})
    return entries


def load(refs):
    pack, _ = backend()
    loaded = []
    for ref in refs:
        member = ref.get("member", -1)
        if member < 0:
            mod = pack._load_mod(ref["name"])
        else:
            components = pack._load_components(ref["name"], 1, {"components_1": "Audio" if ref["kind"] == "audio" else "Visual"})
            mod = next(mod for mod, _ in components if mod.bundle_index == member)
        loaded.append((mod, ref.get("strength", 1)))
    return loaded


class ReferenceClip:
    """Append saved-reference presentation to the core node's ordinary references."""

    def __init__(self, clip, items):
        self.clip, self.items = clip, items

    def tokenize(self, prompt, minimax_ref_items=None, images=None):
        items = list(minimax_ref_items or []) or [{"type": "image", "data": image} for image in (images or [])]
        return self.clip.tokenize(prompt, minimax_ref_items=items + self.items)

    def encode_from_tokens_scheduled(self, tokens):
        result = self.clip.encode_from_tokens_scheduled(tokens)
        if any("minimax_token_tags" not in meta for _, meta in result):
            raise ValueError("H3 Timeline: saved references need an H3-compatible CLIP returning minimax_token_tags")
        return result


def prepare(clip, vae, refs):
    _, prompt = backend()
    items, blocks = prompt.prepare_references(load(refs), vae)
    return ReferenceClip(clip, items), blocks
