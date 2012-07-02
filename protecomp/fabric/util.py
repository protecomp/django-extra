"""
Misc commands and utilities. Not to be run directly with fab, only as util.command()
from other fabfiles
"""

from fabric.api import *
from fabric.context_managers import hide
from fabric.contrib.console import confirm
from fabric.contrib.files import exists, sed

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
    
def single_host(hostname):
    """Returns a role definition with all roles defined to a single host. 
    Usage:
    
        import util
        env.roledefs = util.single_host('my.host.com')
    """
    return {
        'media-server': [hostname],
        'app-server':   [hostname],
        'code':         [hostname],
        'migration':    [hostname],
        'database':     [hostname],
    }
