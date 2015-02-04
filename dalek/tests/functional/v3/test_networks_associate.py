# Copyright 2012 Nebula, Inc.
# Copyright 2014 IBM Corp.
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

from oslo.config import cfg

from nova.network import api as network_api
from nova.tests.functional.v3 import api_sample_base

CONF = cfg.CONF
CONF.import_opt('osapi_compute_extension',
                'nova.api.openstack.compute.extensions')


class NetworksAssociateJsonTests(api_sample_base.ApiSampleTestBaseV3):
    extension_name = "os-networks-associate"
    extra_extensions_to_load = ["os-networks"]

    _sentinel = object()

    def _get_flags(self):
        f = super(NetworksAssociateJsonTests, self)._get_flags()
        f['osapi_compute_extension'] = CONF.osapi_compute_extension[:]
        # Networks_associate requires Networks to be update
        f['osapi_compute_extension'].append(
            'nova.api.openstack.compute.contrib.os_networks.Os_networks')
        return f

    def setUp(self):
        super(NetworksAssociateJsonTests, self).setUp()

        def fake_associate(self, context, network_id,
                           host=NetworksAssociateJsonTests._sentinel,
                           project=NetworksAssociateJsonTests._sentinel):
            return True

        self.stubs.Set(network_api.API, "associate", fake_associate)

    def test_disassociate(self):
        response = self._do_post('os-networks/1/action',
                                 'network-disassociate-req',
                                 {})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, "")

    def test_disassociate_host(self):
        response = self._do_post('os-networks/1/action',
                                 'network-disassociate-host-req',
                                 {})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, "")

    def test_disassociate_project(self):
        response = self._do_post('os-networks/1/action',
                                 'network-disassociate-project-req',
                                 {})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, "")

    def test_associate_host(self):
        response = self._do_post('os-networks/1/action',
                                 'network-associate-host-req',
                                 {"host": "testHost"})
        self.assertEqual(response.status_code, 202)
        self.assertEqual(response.content, "")
