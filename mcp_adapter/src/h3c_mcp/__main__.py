import argparse
import json
import os
import sys
from pathlib import Path

from .transport import StudioClient, StudioError


def main():
    parser = argparse.ArgumentParser(description='Connect an MCP agent to a local or remote H3 Continuity Studio.')
    parser.add_argument('--studio-url', default=os.environ.get('H3C_STUDIO_URL', 'http://127.0.0.1:8188'))
    parser.add_argument('--token-env', default='H3C_STUDIO_TOKEN', help='Environment variable containing the optional proxy bearer token')
    parser.add_argument('--workspace-root', action='append', type=Path, help='Allowed local file root (repeatable; default current directory)')
    default_state = Path(os.environ.get('LOCALAPPDATA', os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local' / 'state')))) / 'h3c-mcp'
    parser.add_argument('--state-dir', type=Path, default=default_state)
    parser.add_argument('--check', action='store_true', help='Check the host without starting MCP or changing project data')
    args = parser.parse_args()
    client = None
    try:
        client = StudioClient(args.studio_url, token=os.environ.get(args.token_env), roots=args.workspace_root)
        if args.check:
            catalog = client.json('/h3c/agent/catalog')
            if catalog.get('agent_api_version') != 1:
                raise StudioError('Update the Studio host to a version with agent API v1.', code='host_upgrade_required')
            capabilities = client.json('/h3c/api/v1/capabilities')
            print(json.dumps(dict(ok=True, agent_api_version=1, skills=len(catalog['skills']),
                                  profiles=len(capabilities.get('profiles', [])), render_ready=capabilities.get('readiness', {}).get('render', False))))
        else:
            from .server import create_server
            create_server(client, state_dir=args.state_dir).run(transport='stdio')
    except (StudioError, OSError) as error:
        detail = error.result() if isinstance(error, StudioError) else {'code': 'local_io', 'message': str(error)}
        print(json.dumps({'ok': False, 'error': detail}), file=sys.stderr)
        return 1
    finally:
        if client:
            client.close()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
