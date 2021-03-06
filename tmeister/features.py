from aiohttp import web

from asyncpg.exceptions import UniqueViolationError

from .dataaccess import featureda
from . import permissions
from . import toggles
from . import auditing


async def create_feature(request):
    body = await request.json()
    feature_name = body.get('name', None)
    user = request.get('user')
    if not feature_name.isidentifier():
        return web.json_response({'Message': "Not a valid name"},
                                 status=400)

    await permissions.check_permissions(
        user, permissions.Action.create_feature)
    try:
        response = await featureda.add_feature(feature_name)
        await auditing.audit_event(
            'feature.add', user, {'feature_name': feature_name})
        return web.json_response(response, status=201)

    except UniqueViolationError as e:
        return web.json_response(
            {'Message': "The feature name '{}' already exists"
                .format(feature_name)},
            status=409)


async def get_features(request):
    feature_list = await featureda.get_features()
    features = {'features': [{'name': f} for f in feature_list]}
    return web.json_response(features,
                             headers={'Access-Control-Allow-Origin': '*'})


async def delete_feature(request):
    """ This method currently deletes EVERYTHING for a given feature.
        It should be used only for cleanup, and requires admin permissions
        A better way to clean up is to do a soft-delete
        TODO: implement a soft-delete, and hard-delete only when safe
    """
    feature = request.match_info['name']
    user = request.get('user')

    if not feature.isidentifier():
        return web.json_response({'Message': 'No valid feature provided'})

    await permissions.check_permissions(
        user, permissions.Action.delete_feature)

    # first, turn off all toggles (this cleans up the toggle db)
    await toggles._toggle_all_for_feature(feature, state='OFF')

    # now delete the feature
    await featureda.delete_feature(feature)

    await auditing.audit_event(
        'feature.remove', user, {'feature_name': feature})
    return web.json_response(None, status=204)
