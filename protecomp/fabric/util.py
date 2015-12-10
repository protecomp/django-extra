"""
Misc commands and utilities. Not to be run directly with fab, only as util.command()
from other fabfiles
"""

from fabric.api import run, sudo, env, local
from protecomp.fabric.server_settings import get_roles_for_host

import itertools

def _sed(filename, before, after, limit='', use_sudo=False, backup='.bak'):
    """
    Modified sed-command

    Equivalent to ``sed -i<backup> -r -e "<limit> s/<before>/<after>/g
    <filename>"``.

    For convenience, ``before`` and ``after`` will automatically escape forward
    slashes (and **only** forward slashes) for you, so you don't need to
    specify e.g.  ``http:\/\/foo\.com``, instead just using ``http://foo\.com``
    is fine.

    If ``use_sudo`` is True, will use `sudo` instead of `run`.

    `sed` will pass ``shell=False`` to `run`/`sudo`, in order to avoid problems
    with many nested levels of quotes and backslashes.
    """
    func = use_sudo and sudo or run
    expr = r"sed -i%s -r -e '%s s/%s/%s/g' %s"
    before = before.replace('/', r'\/')
    after = after.replace('/', r'\/')
    command = expr % (backup, limit, before, after, filename)
    return func(command, shell=False)

def manage(command):
    """Runs local management command"""
    local('python %s/%s %s' % (env.local_base, env.manage_path, command), capture=False)


def supervisor_process(process_name, reload_command=None):
    return {
        'status': "supervisorctl status %s" % process_name,
        'reload': reload_command or
                  "supervisorctl restart %s" % process_name,
        'restart': "supervisorctl restart %s" % process_name,
        'stop': "supervisorctl stop %s" % process_name,
        'start': "supervisorctl start %s" % process_name,
    }


def pm2_process(process_name, process_file = None):
    if not process_file:
        process_file = "/home/%s/config/%s-pm2-app.json" % (env.user, process_name),

    return {
        'status': "pm2 status",
        'reload': "pm2 reload %s" % process_name,
        'restart': "pm2 restart %s" % process_file,
        'stop': "pm2 delete %s" % process_name,
        'start': "pm2 startOrRestart %s" % process_file,
    }


def get_processes(hostname, process_names=None):
    """Get all process definitions for the specified host roles.

    processes are defined as:
    env.processes = {
        'role-name': {
            'process1': process_definition1,
            'process2': process_definition2,
        },
        'role2-name': {
            'process3': process_definition3,
        },
    }
    """
    host_roles = get_roles_for_host(hostname)

    # Collect process_definitions to a dict from matching roles
    process_definitions = {}
    for role, d in env.processes.iteritems():
        if role in host_roles:
            process_definitions.update({k: v for k, v in d.iteritems()})

    # Return processes matching one of the process names
    # or all processes if process_names is empty
    return [
        v for k, v in process_definitions.iteritems()
        if not process_names or k in process_names
    ]
