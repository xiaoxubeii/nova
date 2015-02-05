# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
WSGI middleware for OpenStack Compute API.
"""

from oslo.config import cfg

import dalek.api.openstack
from dalek.api.openstack.compute import extensions
from dalek.api.openstack.compute import servers

CONF = cfg.CONF


class APIRouter(dalek.api.openstack.APIRouter):
    """Routes requests on the OpenStack API to the appropriate controller
    and method.
    """
    ExtensionManager = extensions.ExtensionManager

    def _setup_routes(self, mapper, ext_mgr, init_only):
        self.resources['servers'] = servers.create_resource()
        mapper.resource("server", "servers",
                        controller=self.resources['servers'],
                        collection={'detail': 'GET'},
                        member={'action': 'POST'})


