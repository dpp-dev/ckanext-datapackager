import json

import ckan.plugins.toolkit as toolkit
import ckan.lib.navl.dictization_functions as dictization_functions

import ckanext.b2.logic.schema
import ckanext.b2.logic.validators
import ckanext.b2.exceptions as custom_exceptions


def resource_schema_field_delete(context, data_dict):
    '''Delete a field from a resource's schema.

    :param resource_id: the ID of the resource whose schema the field should be
                        deleted from
    :type resource: string

    :param index: the index number of the field to delete
    :type index: int

    '''
    try:
        data_dict, errors = dictization_functions.validate(data_dict,
            ckanext.b2.logic.schema.resource_schema_field_delete_schema(),
            context)
    except custom_exceptions.InvalidResourceIDException, e:
        raise toolkit.ValidationError(e)
    if errors:
        raise toolkit.ValidationError(errors)

    resource_id = data_dict.pop('resource_id')
    index = data_dict['index']

    schema = toolkit.get_action('resource_schema_show')(context,
        {'resource_id': resource_id})

    new_fields = [field for field in schema['fields']
                  if field['index'] != index]
    assert len(new_fields) == len(schema['fields']) - 1
    schema['fields'] = new_fields

    # We need to pass the resource URL to resource_update or we get a
    # validation error, so we need to call resource_show() here to get it.
    url = toolkit.get_action('resource_show')(context,
                                              {'id': resource_id})['url']

    toolkit.get_action('resource_update')(context,
        {'id': resource_id, 'url': url, 'schema': json.dumps(schema)})
