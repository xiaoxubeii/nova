import oslo.config.cfg
from oslo.utils import importutils

_compute_opts = [
    oslo.config.cfg.StrOpt('compute_api_class',
                           default='dalek.compute.nova.API',
                           help='The full class name of the '
                                'compute API class to use'),
]

oslo.config.cfg.CONF.register_opts(_compute_opts)


def API():
    compute_api_class = oslo.config.cfg.CONF.compute_api_class
    cls = importutils.import_class(compute_api_class)
    return cls()
