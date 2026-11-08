"""Small agent support routes on the existing ComfyUI security boundary."""
import asyncio
import json

from aiohttp import web

from . import resources


def register(instance):
    @instance.routes.get('/h3c/agent/catalog')
    async def catalog(request):
        try:
            return web.json_response(await asyncio.to_thread(resources.catalog))
        except (ValueError, OSError) as error:
            return web.json_response({'ok': False, 'error': {'code': 'agent_catalog', 'message': str(error)}}, status=400)

    @instance.routes.get('/h3c/agent/resource')
    async def resource(request):
        try:
            raw, mime = await asyncio.to_thread(resources.read, request.query.get('uri'), request.query.get('digest'))
            return web.Response(body=raw, content_type=mime)
        except resources.ResourceChanged as error:
            return web.json_response({'ok': False, 'error': {'code': 'resource_changed', 'message': str(error)}}, status=409)
        except (ValueError, OSError) as error:
            return web.json_response({'ok': False, 'error': {'code': 'resource_not_found', 'message': str(error)}}, status=404)
