import nova

novaclient = nova.novaclient(None)
print novaclient.servers.list()