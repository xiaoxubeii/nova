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
from oslo.serialization import jsonutils
from oslo.utils import timeutils
import requests

from nova.scheduler.filters import trusted_filter
from nova import test
from nova.tests.unit.scheduler import fakes

CONF = cfg.CONF


class AttestationServiceTestCase(test.NoDBTestCase):

    def setUp(self):
        super(AttestationServiceTestCase, self).setUp()
        self.api_url = '/OpenAttestationWebServices/V1.0'
        self.host = 'localhost'
        self.port = '8443'
        self.statuses = (requests.codes.OK, requests.codes.CREATED,
                         requests.codes.ACCEPTED, requests.codes.NO_CONTENT)

    @mock.patch.object(requests, 'request')
    def test_do_request_possible_statuses(self, request_mock):
        """This test case checks if '_do_request()' method returns
        appropriate status_code (200) and result (text converted to json),
        while status_code returned by request is in one of fourth eligible
        statuses
        """

        for status_code in self.statuses:
            request_mock.return_value.status_code = status_code
            request_mock.return_value.text = '{"test": "test"}'

            attestation_service = trusted_filter.AttestationService()
            status, result = attestation_service._do_request(
                'POST', 'PollHosts', {}, {})

            self.assertEqual(requests.codes.OK, status)
            self.assertEqual(jsonutils.loads(request_mock.return_value.text),
                             result)

    @mock.patch.object(requests, 'request')
    def test_do_request_other_status(self, request_mock):
        """This test case checks if '_do_request()' method returns
        appropriate status (this returned by request method) and result
        (None), while status_code returned by request is not in one of fourth
        eligible statuses
        """

        request_mock.return_value.status_code = requests.codes.NOT_FOUND
        request_mock.return_value.text = '{"test": "test"}'

        attestation_service = trusted_filter.AttestationService()
        status, result = attestation_service._do_request(
            'POST', 'PollHosts', {}, {})

        self.assertEqual(requests.codes.NOT_FOUND, status)
        self.assertIsNone(result)

    @mock.patch.object(requests, 'request')
    def test_do_request_unconvertible_text(self, request_mock):
        for status_code in self.statuses:
            # this unconvertible_texts leads to TypeError and ValueError
            # in jsonutils.loads(res.text) in _do_request() method
            for unconvertible_text in ({"test": "test"}, '{}{}'):
                request_mock.return_value.status_code = status_code
                request_mock.return_value.text = unconvertible_text

                attestation_service = trusted_filter.AttestationService()
                status, result = attestation_service._do_request(
                    'POST', 'PollHosts', {}, {})

                self.assertEqual(requests.codes.OK, status)
                self.assertEqual(unconvertible_text, result)


@mock.patch.object(trusted_filter.AttestationService, '_request')
class TestTrustedFilter(test.NoDBTestCase):

    def setUp(self):
        super(TestTrustedFilter, self).setUp()
        # TrustedFilter's constructor creates the attestation cache, which
        # calls to get a list of all the compute nodes.
        fake_compute_nodes = [
            {'hypervisor_hostname': 'node1',
             'service': {'host': 'host1'},
            }
        ]
        with mock.patch('nova.db.compute_node_get_all') as mocked:
            mocked.return_value = fake_compute_nodes
            self.filt_cls = trusted_filter.TrustedFilter()

    def test_trusted_filter_default_passes(self, req_mock):
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024}}
        host = fakes.FakeHostState('host1', 'node1', {})
        self.assertTrue(self.filt_cls.host_passes(host, filter_properties))
        self.assertFalse(req_mock.called)

    def test_trusted_filter_trusted_and_trusted_passes(self, req_mock):
        oat_data = {"hosts": [{"host_name": "node1",
                                   "trust_lvl": "trusted",
                                   "vtime": timeutils.isotime()}]}
        req_mock.return_value = requests.codes.OK, oat_data

        extra_specs = {'trust:trusted_host': 'trusted'}
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024,
                                               'extra_specs': extra_specs}}
        host = fakes.FakeHostState('host1', 'node1', {})
        self.assertTrue(self.filt_cls.host_passes(host, filter_properties))
        req_mock.assert_called_once_with("POST", "PollHosts", ["node1"])

    def test_trusted_filter_trusted_and_untrusted_fails(self, req_mock):
        oat_data = {"hosts": [{"host_name": "node1",
                                    "trust_lvl": "untrusted",
                                    "vtime": timeutils.isotime()}]}
        req_mock.return_value = requests.codes.OK, oat_data
        extra_specs = {'trust:trusted_host': 'trusted'}
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024,
                                               'extra_specs': extra_specs}}
        host = fakes.FakeHostState('host1', 'node1', {})
        self.assertFalse(self.filt_cls.host_passes(host, filter_properties))

    def test_trusted_filter_untrusted_and_trusted_fails(self, req_mock):
        oat_data = {"hosts": [{"host_name": "node",
                                    "trust_lvl": "trusted",
                                    "vtime": timeutils.isotime()}]}
        req_mock.return_value = requests.codes.OK, oat_data
        extra_specs = {'trust:trusted_host': 'untrusted'}
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024,
                                               'extra_specs': extra_specs}}
        host = fakes.FakeHostState('host1', 'node1', {})
        self.assertFalse(self.filt_cls.host_passes(host, filter_properties))

    def test_trusted_filter_untrusted_and_untrusted_passes(self, req_mock):
        oat_data = {"hosts": [{"host_name": "node1",
                                    "trust_lvl": "untrusted",
                                    "vtime": timeutils.isotime()}]}
        req_mock.return_value = requests.codes.OK, oat_data
        extra_specs = {'trust:trusted_host': 'untrusted'}
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024,
                                               'extra_specs': extra_specs}}
        host = fakes.FakeHostState('host1', 'node1', {})
        self.assertTrue(self.filt_cls.host_passes(host, filter_properties))

    def test_trusted_filter_update_cache(self, req_mock):
        oat_data = {"hosts": [{"host_name": "node1",
                                    "trust_lvl": "untrusted",
                                    "vtime": timeutils.isotime()}]}

        req_mock.return_value = requests.codes.OK, oat_data
        extra_specs = {'trust:trusted_host': 'untrusted'}
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024,
                                               'extra_specs': extra_specs}}
        host = fakes.FakeHostState('host1', 'node1', {})

        self.filt_cls.host_passes(host, filter_properties)  # Fill the caches

        req_mock.reset_mock()
        self.filt_cls.host_passes(host, filter_properties)
        self.assertFalse(req_mock.called)

        req_mock.reset_mock()

        timeutils.set_time_override(timeutils.utcnow())
        timeutils.advance_time_seconds(
            CONF.trusted_computing.attestation_auth_timeout + 80)
        self.filt_cls.host_passes(host, filter_properties)
        self.assertTrue(req_mock.called)

        timeutils.clear_time_override()

    def test_trusted_filter_update_cache_timezone(self, req_mock):
        oat_data = {"hosts": [{"host_name": "node1",
                                    "trust_lvl": "untrusted",
                                    "vtime": "2012-09-09T05:10:40-04:00"}]}
        req_mock.return_value = requests.codes.OK, oat_data
        extra_specs = {'trust:trusted_host': 'untrusted'}
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024,
                                               'extra_specs': extra_specs}}
        host = fakes.FakeHostState('host1', 'node1', {})

        timeutils.set_time_override(
            timeutils.normalize_time(
                timeutils.parse_isotime("2012-09-09T09:10:40Z")))

        self.filt_cls.host_passes(host, filter_properties)  # Fill the caches

        req_mock.reset_mock()
        self.filt_cls.host_passes(host, filter_properties)
        self.assertFalse(req_mock.called)

        req_mock.reset_mock()
        timeutils.advance_time_seconds(
            CONF.trusted_computing.attestation_auth_timeout - 10)
        self.filt_cls.host_passes(host, filter_properties)
        self.assertFalse(req_mock.called)

        timeutils.clear_time_override()

    def test_trusted_filter_combine_hosts(self, req_mock):
        fake_compute_nodes = [
            {'hypervisor_hostname': 'node1',
             'service': {'host': 'host1'},
            },
            {'hypervisor_hostname': 'node2',
             'service': {'host': 'host2'},
            },
        ]
        with mock.patch('nova.db.compute_node_get_all') as mocked:
            mocked.return_value = fake_compute_nodes
            self.filt_cls = trusted_filter.TrustedFilter()
        oat_data = {"hosts": [{"host_name": "node1",
                                    "trust_lvl": "untrusted",
                                    "vtime": "2012-09-09T05:10:40-04:00"}]}
        req_mock.return_value = requests.codes.OK, oat_data
        extra_specs = {'trust:trusted_host': 'trusted'}
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024,
                                               'extra_specs': extra_specs}}
        host = fakes.FakeHostState('host1', 'node1', {})

        self.filt_cls.host_passes(host, filter_properties)  # Fill the caches
        req_mock.assert_called_once_with("POST", "PollHosts",
                                         ["node1", "node2"])

    def test_trusted_filter_trusted_and_locale_formated_vtime_passes(self,
            req_mock):
        oat_data = {"hosts": [{"host_name": "host1",
                                    "trust_lvl": "trusted",
                                    "vtime": timeutils.strtime(fmt="%c")},
                                   {"host_name": "host2",
                                    "trust_lvl": "trusted",
                                    "vtime": timeutils.strtime(fmt="%D")},
                                    # This is just a broken date to ensure that
                                    # we're not just arbitrarily accepting any
                                    # date format.
                        ]}
        req_mock.return_value = requests.codes.OK, oat_data
        extra_specs = {'trust:trusted_host': 'trusted'}
        filter_properties = {'context': mock.sentinel.ctx,
                             'instance_type': {'memory_mb': 1024,
                                               'extra_specs': extra_specs}}
        host = fakes.FakeHostState('host1', 'host1', {})
        bad_host = fakes.FakeHostState('host2', 'host2', {})

        self.assertTrue(self.filt_cls.host_passes(host, filter_properties))
        self.assertFalse(self.filt_cls.host_passes(bad_host,
                                                   filter_properties))
