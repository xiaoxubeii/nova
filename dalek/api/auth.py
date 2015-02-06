from oslo.config import cfg
import webob.dec
import webob.exc

from dalek import context
from dalek.openstack.common import log as logging
from dalek import wsgi

auth_opts = [
    cfg.StrOpt('auth_strategy',
               default='authcontext',
               help='The strategy to use for auth: noauth or keystone.'),
    cfg.StrOpt('auth_password',
               default='auth_password',
               help='The user auth password'),
]

CONF = cfg.CONF
CONF.register_opts(auth_opts)

LOG = logging.getLogger(__name__)


def _load_pipeline(loader, pipeline):
    filters = [loader.get_filter(n) for n in pipeline[:-1]]
    app = loader.get_app(pipeline[-1])
    filters.reverse()
    for filter in filters:
        app = filter(app)
    return app


def pipeline_factory(loader, global_conf, **local_conf):
    """A paste pipeline replica that keys off of auth_strategy."""
    pipeline = local_conf[CONF.auth_strategy]
    pipeline = pipeline.split()
    return _load_pipeline(loader, pipeline)


class AdaptorContext(wsgi.Middleware):
    """Make a request context from keystone headers."""

    @webob.dec.wsgify(RequestClass=wsgi.Request)
    def __call__(self, req):
        user_id = req.headers.get('X_USER_ID')
        user_name = req.headers.get('X_USER_NAME')
        user_password = CONF.auth_password
        ctx = context.RequestContext(user_id=user_id, user_name=user_name, user_password=user_password)

        req.environ['context'] = ctx
        return self.application