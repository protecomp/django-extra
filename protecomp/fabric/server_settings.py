# -*- coding: utf-8 -*-
from fabric.api import *

import itertools
##
# The main server settings file. Add new servers in the dictionaries below.
# 
# The roledefs are generated from host: {'role': True/False} -dictionaries.
# Add all hosts to a single dictionary (env.my_hosts_dictionary) and load role
# definitions using get_roledefs()
#
# example:
# env.my_servers = {
#     'first_server.my.com':  {'app-server': True, 'code': True, 'media': True},
#     'second_server.my.com': {'app-server': True, 'database': True},
# }
#
# in other file, you can do:
# env.roledefs = get_roledefs(env.my_servers)
#
# result:
# env.roledefs = {
#     'app-server':      ['first_server.my.com', 'second_server.my.com'],
#     'media':    ['first_server.my.com'],
#     'database': ['second_server.my.com'],
# }
##

def get_roledefs(hostinfo):
    """Convert a given host dictionary into a role dictionary based on specified tags"""

    # Init a dictionary with an empty list for all tags specified in the hosts-dict
    roledefs = {}
    all_tags = set(itertools.chain(*[d.keys() for d in hostinfo.values()]))
    for tag in all_tags:
        roledefs[tag] = []

    # Convert host information to host and role lists
    for hostname, host_tags in hostinfo.iteritems():
        for tag in all_tags:
            # If host_tags[tag] is True, this host can be added to a role
            if host_tags.get(tag, False):
                roledefs[tag].append(hostname)

    return roledefs

@task
@runs_once
def help():
    print
    print "Usage: fab production/testing task"
    print
    print "See fab -l for all tasks"
    print
    print "Roles:"
    print
    for tag in env.my_tags:
        line = "   "
        line = line + tag + ": "
        for host in env.my_hostinfo.iteritems():
            try:
                if host[1][tag] == True:
                    line = line + "\n     " + host[0]
            except KeyError:
                pass
        print line

    print
    print "All hosts:"
    print
    for host in env.my_hostinfo.iteritems():
        print "   "+host[0]
