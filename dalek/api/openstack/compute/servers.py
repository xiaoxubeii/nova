from dalek.api.openstack import wsgi


class Controller(wsgi.Controller):
    def __init__(self, **kwargs):
        super(Controller, self).__init__(**kwargs)

    def index(self, req):
        return {'index': 'success'}

    def update(self, req, id, body):
        return {'update': 'success', 'id': id, 'body': body}

    def delete(self, req, id):
        return {'delete': 'success', 'id': id}

    @wsgi.response(202)
    def create(self, req, body):
        return {'create': 'sucess', 'body': body}

    def show(self, req, id):
        return {'show': 'sucess', 'id': id}


def create_resource():
    return wsgi.Resource(Controller())
