# Copyright 2013 IBM Corp.
# Copyright 2011 OpenStack Foundation
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

import mock
from oslo.config import cfg
import requests

from nova import test
from nova.virt.vmwareapi import read_write_util

CONF = cfg.CONF


class ReadWriteUtilTestCase(test.NoDBTestCase):

    @mock.patch.object(requests.api, 'request')
    def test_ipv6_host_read(self, mock_request):
        ipv6_host = 'fd8c:215d:178e:c51e:200:c9ff:fed1:584c'
        port = 7443
        folder = 'tmp/fake.txt'
        read_write_util.VMwareHTTPReadFile(ipv6_host,
                                           port,
                                           'fake_dc',
                                           'fake_ds',
                                           dict(),
                                           folder)
        base_url = 'https://[%s]:%s/folder/%s' % (ipv6_host, port, folder)
        base_url += '?dsName=fake_ds&dcPath=fake_dc'
        headers = {'User-Agent': 'OpenStack-ESX-Adapter'}
        mock_request.assert_called_once_with('get',
                                             base_url,
                                             headers=headers,
                                             allow_redirects=True,
                                             stream=True,
                                             verify=False)
