from dalek.api.openstack import wsgi
from dalek import compute


class Controller(wsgi.Controller):
    def __init__(self, **kwargs):
        self.compute_api = compute.API()
        super(Controller, self).__init__(**kwargs)

    @wsgi.response(202)
    def create(self, req, body):
        context = req.environ['context']
        return self.compute_api.create(context)


def create_resource():
    return wsgi.Resource(Controller())
