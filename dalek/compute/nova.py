from novaclient import client as nova_client
from oslo.config import cfg
from dalek.openstack.common import log as logging

CONF = cfg.CONF

LOG = logging.getLogger(__name__)


def novaclient(context):

    return nova_client.Client(2, 'admin', 'admin', 'admin', 'http://10.20.0.7:5000/v2.0', service_type='compute')
