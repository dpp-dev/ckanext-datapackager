'''Custom action functions provided by this extension.

'''
import os.path

import ckan.plugins.toolkit as toolkit

import ckanext.b2.lib.csv as lib_csv


def _resource_create(context, data_dict):
    '''This is the CKAN core resource_create function, copy-pasted into this
    extension.

    We have to do this because we have to insert some stuff into the resource
    after it's created, and there's no nice plugin interface (that works) for
    this yet.

    '''
    # Add some imports that the code below needs to work in this module.
    import ckan.lib.uploader as uploader
    import ckan.logic as logic
    _get_or_bust = logic.get_or_bust
    _get_action = toolkit.get_action
    _check_access = toolkit.check_access
    ValidationError = logic.ValidationError

    model = context['model']
    # This variable is assigned but never used. Let's just comment it out to
    # shut Syntastic up.
    #user = context['user']

    package_id = _get_or_bust(data_dict, 'package_id')
    data_dict.pop('package_id')

    pkg_dict = _get_action('package_show')(context, {'id': package_id})

    _check_access('resource_create', context, data_dict)

    if not 'resources' in pkg_dict:
        pkg_dict['resources'] = []

    upload = uploader.ResourceUpload(data_dict)

    pkg_dict['resources'].append(data_dict)

    try:
        context['defer_commit'] = True
        context['use_cache'] = False
        _get_action('package_update')(context, pkg_dict)
        context.pop('defer_commit')
    except ValidationError, e:
        errors = e.error_dict['resources'][-1]
        raise ValidationError(errors)

    ## Get out resource_id resource from model as it will not appear in
    ## package_show until after commit
    upload.upload(context['package'].resources[-1].id,
                  uploader.get_max_resource_size())
    model.repo.commit()

    ##  Run package show again to get out actual last_resource
    pkg_dict = _get_action('package_show')(context, {'id': package_id})
    resource = pkg_dict['resources'][-1]

    return resource


def resource_create(context, data_dict):
    '''Wrap the core resource_create function and call our
    _after_resource_create() after it.

    This is what we like a CKAN plugin interface to do for us: call a plugin
    function after a given action function finishes.

    '''
    resource = _resource_create(context, data_dict)
    _after_resource_create(context, resource)


def _get_path_to_resource_file(resource_dict):
    '''Return the local filesystem path to an uploaded resource file.

    The given ``resource_dict`` should be for a resource whose file has been
    uploaded to the FileStore.

    :param resource_dict: dict of the resource whose file you want
    :type resource_dict: a resource dict, e.g. from action ``resource_show``

    :rtype: string
    :returns: the absolute path to the resource file on the local filesystem

    '''
    if 'id' not in resource_dict:
        return None

    # We need to do a direct import here, there's no nicer way yet.
    import ckan.lib.uploader as uploader
    upload = uploader.ResourceUpload(resource_dict)
    path = upload.get_path(resource_dict['id'])
    return os.path.abspath(path)


def _infer_schema_for_resource(resource):
    '''Return a JSON Table Schema for the given resource.

    This will guess column headers and types from the resource's CSV file.

    Assumes a resource with a CSV file uploaded to the FileStore.

    '''
    path = _get_path_to_resource_file(resource)
    if path is None:
        return None
    else:
        schema = lib_csv.infer_schema_from_csv_file(path)
        return schema

def _after_resource_create(context, resource):
    '''Add a schema to the given resource and save it.'''

    resource['schema'] = _infer_schema_for_resource(resource)
    toolkit.get_action('resource_update')(context, resource)