# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

"""Starter script for Nova API.

Starts both the EC2 and OpenStack APIs in separate greenthreads.

"""

import sys

from oslo.config import cfg

from dalek import config
from dalek.openstack.common import log as logging
from dalek import service
from dalek import utils

CONF = cfg.CONF


def main():
    default_config = '/home/xiaoxubeii/PycharmProjects/dalek/etc/adaptor.conf'
    config.parse_args(sys.argv, default_config_files=[default_config])
    logging.setup("adaptor")
    utils.monkey_patch()

    launcher = service.process_launcher()
    api = 'adaptor'
    server = service.WSGIService(api, use_ssl=False)
    launcher.launch_service(server, workers=server.workers or 1)
    launcher.wait()


main()