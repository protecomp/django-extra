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
    env.hostinfo = hostinfo
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

def single_host(hostname):
    """Returns a role definition with all roles defined to a single host. 
    Usage:
    
        import util
        env.roledefs = util.single_host('my.host.com')
    """
    return get_roledefs({
        hostname: {
            'media': True,
            'app-server': True,
            'worker': True,
            'code': True,
            'migration': True,
            'database': True,
        },
    })


def get_roles_for_host(hostname):
    role_dict = env.hostinfo.get(hostname, {})
    return [key for key, val in role_dict.items() if val]


def env_task(*args, **kwargs):
    """Decorate the task as an deployment environment -defining task

    see fabric.task decorator.
    """
    wrapper_function = task(*args, **kwargs)
    wrapper_function.decorated_env_task = True
    return wrapper_function


def is_env_task(func):
    return isinstance(func, object) and getattr(func, 'decorated_env_task', False)


@task
def info():
    execute('help')


@task
@runs_once
def help():
    if not getattr(env, 'roledefs', False):
        print "No role definitions"
        try:
            import fabfile
            env_tasks = [(n, val) for n, val in vars(fabfile).items() if is_env_task(val)]
            print "Select one of the following environments:"
            print
            print "\tenv_name: \t description:"
            for task_name, task in env_tasks:
                print "\t%s \t %s" % (task_name, getattr(task, '__doc__'))
            print
        except:
            print "Define a deployment environment first"
            print

        print "More info: f <env_name> help"
    else:
        print "Environment: %s" % env.tasks[0]
        print
        print "Servers:"
        hostinfo = sorted(env.hostinfo.items(), key=lambda k: k[0])
        for server, tags in hostinfo:
            print "\t%s  \t%s" % (
                server,
                ','.join([name for name, value in tags.items() if value])
            )
        print
        print "Update targets (commands: revision, update):"
        for name, path in env.repository_roots.iteritems():
            print "\t%s" % name
        print
        print "Process targets (commands: status, reload, restart):"
        for role, roledict in env.processes.items():
            for name, definition in roledict.iteritems():
                print "\t%s" % name
        print
        migration_hosts = [name for name, tags in env.hostinfo.items() if tags.get('migration')]
        if len(migration_hosts):
            print "Production server shell (migrations etc.):"
            print "\tssh %s@%s" % (env.user, migration_hosts[0])
            print "\tcd %s; source activate" % env.remote_base
        else:
            print "No migration server for this environment"
        print
        database_hosts = [name for name, tags in env.hostinfo.items() if tags.get('database')]
        if len(database_hosts):
            print "Database shell:"
            print "\tssh %s@%s" % (env.user, database_hosts[0])
            print "\tmysql"
        else:
            print "No database host in this environment"

        print
    print "see fab -l for all tasks, fab -d command for command description"
