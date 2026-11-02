from .h3_continuity import routes
from .h3_continuity.extension import comfy_entrypoint

routes.register()

WEB_DIRECTORY = "./web"

__all__ = ["WEB_DIRECTORY", "comfy_entrypoint"]
