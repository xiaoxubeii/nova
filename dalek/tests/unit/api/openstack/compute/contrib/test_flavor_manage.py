# Copyright 2011 Andrew Bogott for the Wikimedia Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import datetime

import mock
from oslo.serialization import jsonutils
import webob

from nova.api.openstack.compute.contrib import flavor_access
from nova.api.openstack.compute.contrib import flavormanage as flavormanage_v2
from nova.api.openstack.compute.plugins.v3 import flavor_manage as \
    flavormanage_v21
from nova.compute import flavors
from nova import context
from nova import db
from nova import exception
from nova import test
from nova.tests.unit.api.openstack import fakes


def fake_db_flavor(**updates):
    db_flavor = {
        'root_gb': 1,
        'ephemeral_gb': 1,
        'name': u'frob',
        'deleted': False,
        'created_at': datetime.datetime(2012, 1, 19, 18, 49, 30, 877329),
        'updated_at': None,
        'memory_mb': 256,
        'vcpus': 1,
        'flavorid': 1,
        'swap': 0,
        'rxtx_factor': 1.0,
        'extra_specs': {},
        'deleted_at': None,
        'vcpu_weight': None,
        'id': 7,
        'is_public': True,
        'disabled': False,
    }
    if updates:
        db_flavor.update(updates)
    return db_flavor


def fake_get_flavor_by_flavor_id(flavorid, ctxt=None, read_deleted='yes'):
    if flavorid == 'failtest':
        raise exception.FlavorNotFound(flavor_id=flavorid)
    elif not str(flavorid) == '1234':
        raise Exception("This test expects flavorid 1234, not %s" % flavorid)
    if read_deleted != 'no':
        raise test.TestingException("Should not be reading deleted")
    return fake_db_flavor(flavorid=flavorid)


def fake_destroy(flavorname):
    pass


def fake_create(context, kwargs, projects=None):
    newflavor = fake_db_flavor()

    flavorid = kwargs.get('flavorid')
    if flavorid is None:
        flavorid = 1234

    newflavor['flavorid'] = flavorid
    newflavor["name"] = kwargs.get('name')
    newflavor["memory_mb"] = int(kwargs.get('memory_mb'))
    newflavor["vcpus"] = int(kwargs.get('vcpus'))
    newflavor["root_gb"] = int(kwargs.get('root_gb'))
    newflavor["ephemeral_gb"] = int(kwargs.get('ephemeral_gb'))
    newflavor["swap"] = kwargs.get('swap')
    newflavor["rxtx_factor"] = float(kwargs.get('rxtx_factor'))
    newflavor["is_public"] = bool(kwargs.get('is_public'))
    newflavor["disabled"] = bool(kwargs.get('disabled'))

    return newflavor


class FlavorManageTestV21(test.NoDBTestCase):
    controller = flavormanage_v21.FlavorManageController()
    validation_error = exception.ValidationError
    base_url = '/v2/fake/flavors'

    def setUp(self):
        super(FlavorManageTestV21, self).setUp()
        self.stubs.Set(flavors,
                       "get_flavor_by_flavor_id",
                       fake_get_flavor_by_flavor_id)
        self.stubs.Set(flavors, "destroy", fake_destroy)
        self.stubs.Set(db, "flavor_create", fake_create)
        self.ctxt = context.RequestContext('fake', 'fake',
                                           is_admin=True, auth_token=True)
        self.app = self._setup_app()

        self.request_body = {
            "flavor": {
                "name": "test",
                "ram": 512,
                "vcpus": 2,
                "disk": 1,
                "OS-FLV-EXT-DATA:ephemeral": 1,
                "id": unicode('1234'),
                "swap": 512,
                "rxtx_factor": 1,
                "os-flavor-access:is_public": True,
            }
        }
        self.expected_flavor = self.request_body

    def _setup_app(self):
        return fakes.wsgi_app_v21(init_only=('os-flavor-manage',
                                             'os-flavor-rxtx',
                                             'os-flavor-access', 'flavors',
                                             'os-flavor-extra-data'))

    def test_delete(self):
        req = fakes.HTTPRequest.blank(self.base_url + '/1234')
        res = self.controller._delete(req, 1234)

        # NOTE: on v2.1, http status code is set as wsgi_code of API
        # method instead of status_int in a response object.
        if isinstance(self.controller,
                      flavormanage_v21.FlavorManageController):
            status_int = self.controller._delete.wsgi_code
        else:
            status_int = res.status_int
        self.assertEqual(202, status_int)

        # subsequent delete should fail
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller._delete, req, "failtest")

    def _test_create_missing_parameter(self, parameter):
        body = {
            "flavor": {
                "name": "azAZ09. -_",
                "ram": 512,
                "vcpus": 2,
                "disk": 1,
                "OS-FLV-EXT-DATA:ephemeral": 1,
                "id": unicode('1234'),
                "swap": 512,
                "rxtx_factor": 1,
                "os-flavor-access:is_public": True,
            }
        }

        del body['flavor'][parameter]

        req = fakes.HTTPRequest.blank(self.base_url)
        self.assertRaises(self.validation_error, self.controller._create,
                          req, body=body)

    def test_create_missing_name(self):
        self._test_create_missing_parameter('name')

    def test_create_missing_ram(self):
        self._test_create_missing_parameter('ram')

    def test_create_missing_vcpus(self):
        self._test_create_missing_parameter('vcpus')

    def test_create_missing_disk(self):
        self._test_create_missing_parameter('disk')

    def _create_flavor_success_case(self, body):
        req = webob.Request.blank(self.base_url)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dumps(body)
        res = req.get_response(self.app)
        self.assertEqual(200, res.status_code)
        return jsonutils.loads(res.body)

    def test_create(self):
        body = self._create_flavor_success_case(self.request_body)
        for key in self.expected_flavor["flavor"]:
            self.assertEqual(body["flavor"][key],
                             self.expected_flavor["flavor"][key])

    def test_create_public_default(self):
        del self.request_body['flavor']['os-flavor-access:is_public']
        body = self._create_flavor_success_case(self.request_body)
        for key in self.expected_flavor["flavor"]:
            self.assertEqual(body["flavor"][key],
                             self.expected_flavor["flavor"][key])

    def test_create_without_flavorid(self):
        del self.request_body['flavor']['id']
        body = self._create_flavor_success_case(self.request_body)
        for key in self.expected_flavor["flavor"]:
            self.assertEqual(body["flavor"][key],
                             self.expected_flavor["flavor"][key])

    def _create_flavor_bad_request_case(self, body):
        self.stubs.UnsetAll()

        req = fakes.HTTPRequest.blank('')
        self.assertRaises(self.validation_error, self.controller._create,
                          req, body=body)

    def test_create_invalid_name(self):
        self.request_body['flavor']['name'] = 'bad !@#!$%\x00 name'
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_flavor_name_is_whitespace(self):
        self.request_body['flavor']['name'] = ' '
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_with_name_too_long(self):
        self.request_body['flavor']['name'] = 'a' * 256
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_without_flavorname(self):
        del self.request_body['flavor']['name']
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_empty_body(self):
        body = {
            "flavor": {}
        }
        self._create_flavor_bad_request_case(body)

    def test_create_no_body(self):
        body = {}
        self._create_flavor_bad_request_case(body)

    def test_create_invalid_format_body(self):
        body = {
            "flavor": []
        }
        self._create_flavor_bad_request_case(body)

    def test_create_invalid_flavorid(self):
        self.request_body['flavor']['id'] = "!@#!$#!$^#&^$&"
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_check_flavor_id_length(self):
        MAX_LENGTH = 255
        self.request_body['flavor']['id'] = "a" * (MAX_LENGTH + 1)
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_with_leading_trailing_whitespaces_in_flavor_id(self):
        self.request_body['flavor']['id'] = "   bad_id   "
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_without_ram(self):
        del self.request_body['flavor']['ram']
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_with_0_ram(self):
        self.request_body['flavor']['ram'] = 0
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_without_vcpus(self):
        del self.request_body['flavor']['vcpus']
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_with_0_vcpus(self):
        self.request_body['flavor']['vcpus'] = 0
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_without_disk(self):
        del self.request_body['flavor']['disk']
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_with_minus_disk(self):
        self.request_body['flavor']['disk'] = -1
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_with_minus_ephemeral(self):
        self.request_body['flavor']['OS-FLV-EXT-DATA:ephemeral'] = -1
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_with_minus_swap(self):
        self.request_body['flavor']['swap'] = -1
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_with_minus_rxtx_factor(self):
        self.request_body['flavor']['rxtx_factor'] = -1
        self._create_flavor_bad_request_case(self.request_body)

    def test_create_with_non_boolean_is_public(self):
        self.request_body['flavor']['os-flavor-access:is_public'] = 123
        self._create_flavor_bad_request_case(self.request_body)

    def test_flavor_exists_exception_returns_409(self):
        expected = {
            "flavor": {
                "name": "test",
                "ram": 512,
                "vcpus": 2,
                "disk": 1,
                "OS-FLV-EXT-DATA:ephemeral": 1,
                "id": 1235,
                "swap": 512,
                "rxtx_factor": 1,
                "os-flavor-access:is_public": True,
            }
        }

        def fake_create(name, memory_mb, vcpus, root_gb, ephemeral_gb,
                        flavorid, swap, rxtx_factor, is_public):
            raise exception.FlavorExists(name=name)

        self.stubs.Set(flavors, "create", fake_create)
        req = fakes.HTTPRequest.blank('')
        self.assertRaises(webob.exc.HTTPConflict, self.controller._create,
                          req, body=expected)

    @mock.patch('nova.compute.flavors.create',
                side_effect=exception.FlavorCreateFailed)
    def test_flavor_create_db_failed(self, mock_create):
        request_dict = {
            "flavor": {
                "name": "test",
                'id': "12345",
                "ram": 512,
                "vcpus": 2,
                "disk": 1,
                "OS-FLV-EXT-DATA:ephemeral": 1,
                "swap": 512,
                "rxtx_factor": 1,
                "os-flavor-access:is_public": True,
            }
        }
        req = fakes.HTTPRequest.blank('')
        ex = self.assertRaises(webob.exc.HTTPInternalServerError,
                               self.controller._create,
                               req, body=request_dict)
        self.assertIn('Unable to create flavor', ex.explanation)

    def test_invalid_memory_mb(self):
        """Check negative and decimal number can't be accepted."""

        self.stubs.UnsetAll()
        self.assertRaises(exception.InvalidInput, flavors.create, "abc",
                          -512, 2, 1, 1, 1234, 512, 1, True)
        self.assertRaises(exception.InvalidInput, flavors.create, "abcd",
                          512.2, 2, 1, 1, 1234, 512, 1, True)
        self.assertRaises(exception.InvalidInput, flavors.create, "abcde",
                          None, 2, 1, 1, 1234, 512, 1, True)
        self.assertRaises(exception.InvalidInput, flavors.create, "abcdef",
                          512, 2, None, 1, 1234, 512, 1, True)
        self.assertRaises(exception.InvalidInput, flavors.create, "abcdef",
                          "test_memory_mb", 2, None, 1, 1234, 512, 1, True)


class FakeRequest(object):
    environ = {"nova.context": context.get_admin_context()}


class PrivateFlavorManageTestV21(test.TestCase):
    controller = flavormanage_v21.FlavorManageController()
    base_url = '/v2/fake/flavors'

    def setUp(self):
        super(PrivateFlavorManageTestV21, self).setUp()
        self.flavor_access_controller = flavor_access.FlavorAccessController()
        self.ctxt = context.RequestContext('fake', 'fake',
                                           is_admin=True, auth_token=True)
        self.app = self._setup_app()
        self.expected = {
            "flavor": {
                "name": "test",
                "ram": 512,
                "vcpus": 2,
                "disk": 1,
                "OS-FLV-EXT-DATA:ephemeral": 1,
                "swap": 512,
                "rxtx_factor": 1
            }
        }

    def _setup_app(self):
        return fakes.wsgi_app_v21(init_only=('os-flavor-manage',
                                             'os-flavor-access',
                                             'os-flavor-rxtx', 'flavors',
                                             'os-flavor-extra-data'),
                                 fake_auth_context=self.ctxt)

    def _get_response(self):
        req = webob.Request.blank(self.base_url)
        req.headers['Content-Type'] = 'application/json'
        req.method = 'POST'
        req.body = jsonutils.dumps(self.expected)
        res = req.get_response(self.app)
        return jsonutils.loads(res.body)

    def test_create_private_flavor_should_not_grant_flavor_access(self):
        self.expected["flavor"]["os-flavor-access:is_public"] = False
        body = self._get_response()
        for key in self.expected["flavor"]:
            self.assertEqual(body["flavor"][key], self.expected["flavor"][key])
        flavor_access_body = self.flavor_access_controller.index(
            FakeRequest(), body["flavor"]["id"])
        expected_flavor_access_body = {
            "tenant_id": "%s" % self.ctxt.project_id,
            "flavor_id": "%s" % body["flavor"]["id"]
        }
        self.assertNotIn(expected_flavor_access_body,
                         flavor_access_body["flavor_access"])

    def test_create_public_flavor_should_not_create_flavor_access(self):
        self.expected["flavor"]["os-flavor-access:is_public"] = True
        body = self._get_response()
        for key in self.expected["flavor"]:
            self.assertEqual(body["flavor"][key], self.expected["flavor"][key])


class FlavorManageTestV2(FlavorManageTestV21):
    controller = flavormanage_v2.FlavorManageController()
    validation_error = webob.exc.HTTPBadRequest

    def setUp(self):
        super(FlavorManageTestV2, self).setUp()
        self.flags(
            osapi_compute_extension=[
                'nova.api.openstack.compute.contrib.select_extensions'],
            osapi_compute_ext_list=['Flavormanage', 'Flavorextradata',
                'Flavor_access', 'Flavor_rxtx', 'Flavor_swap'])

    def _setup_app(self):
        return fakes.wsgi_app(init_only=('flavors',),
                              fake_auth_context=self.ctxt)


class PrivateFlavorManageTestV2(PrivateFlavorManageTestV21):
    controller = flavormanage_v2.FlavorManageController()

    def setUp(self):
        super(PrivateFlavorManageTestV2, self).setUp()
        self.flags(
            osapi_compute_extension=[
                'nova.api.openstack.compute.contrib.select_extensions'],
            osapi_compute_ext_list=['Flavormanage', 'Flavorextradata',
                'Flavor_access', 'Flavor_rxtx', 'Flavor_swap'])

    def _setup_app(self):
        return fakes.wsgi_app(init_only=('flavors',),
                              fake_auth_context=self.ctxt)
