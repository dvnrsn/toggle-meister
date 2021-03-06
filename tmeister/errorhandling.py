from aiohttp import web
import json
import os

from .permissions import InsufficientPermissionsError

LOCAL_DEV = os.getenv('IS_LOCAL', 'false').lower() == 'true'


async def error_middleware(app, handler):
    async def middleware_handler(request: web.Request):
        try:
            response = await handler(request)
        except InsufficientPermissionsError:
            return web.HTTPForbidden()
        except json.decoder.JSONDecodeError as e:
            return web.json_response(data={'Message': e.msg}, status=400)
        except Exception as e:
            if app.raven:
                data = {
                    'request': {
                        'method': request.method,
                        'data': None,
                        'query_string': request.query_string,
                        'url': request.path
                    },
                    # 'user': {
                    #     # put user data here
                    #     'id': 3,
                    #     'username': 'myuser',
                    # }
                }
                tags = {
                    # Put things you want to filter by in sentry here
                }
                extra_data = {
                    # Put extra data here
                }
                if request.has_body:
                    data['request']['data'] = await request.text()

                if not LOCAL_DEV:
                    app.raven.captureException(extra=extra_data,
                                               tags=tags, data=data)
            raise
        return response

    return middleware_handler
