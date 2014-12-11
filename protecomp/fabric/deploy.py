# -*- coding: utf-8 -*-
"""
Code deployment commands

Required env-variables:

- env.remote_base, the project base path on remote media-server, absolute path

The rest are relative to the remote_base path

- env.virtualenv, path to virtual environment root
- env.manage, path to manage.py -file
- env.pip_requirements, path to pip requirements-file
"""
import os

from fabric.api import *
from fabric.api import run, env, cd
from fabric.context_managers import hide
from fabric.contrib.console import confirm
from fabric.contrib.files import exists, sed

def revision_for_path(path):
    with settings(
            cd(path),
            hide('stdout', 'running'),
            warn_only=True,
        ):
        # Strange-looking commands with ||, this prevents unneeded errors when exit status is != 0
        if run('test -d .git || echo "failed"') != 'failed':
            # __git_ps1 gives nicely formatted output in all circumstances, 
            # but might not be available in all systems.
            branch_cmd = "source /etc/bash_completion.d/git*; __git_ps1 '%s'"
            branch = run(branch_cmd)
            rev = run('git rev-parse HEAD')
            if len(rev) > 8: rev = rev[:8]
        elif run('test -d .hg || echo "failed"') != 'failed':
            log = run('hg parent')
            parts = log.split('\n')
            rev = parts[0].split(" ")[-1]
            branch = run('hg branch').strip()
        else:
            return (False, False)
    return (branch, rev)

@task
@roles('code')
def get_revision(output_level=2):
    """Get branch and revision currently in use (hg parent)
    output_level    0: No output
                    1: No hostnames
                    2: Hostnames and revision numbers (default)
    """
    if output_level > 1:
        print env.host
    (branch, rev) = revision_for_path(env.remote_base)
    if branch is False: print "Unsupported revision control system or wrong remote_base"
    if output_level: print "    {0:15} {1}".format(branch, rev)

@task
@roles('code')
def revision(package=''):
    if package:
        package_path = os.path.join(env.remote_base, env.virtualenv, 'src', package)
        if exists(package_path):
            (branch, rev) = revision_for_path(package_path)
            print "%s: branch %s, revision %s" % (package, branch, rev)
        else:
            print "The package %s at %s does not exist!" % (package, package_path)
    else:
        return get_revision()

@task
@roles('code')
def update_requirements():
    """Run pip install on remote machine to update python libraries"""
    activate = os.path.join(env.remote_base, env.virtualenv, 'bin/activate')
    pip_requirements = os.path.join(env.remote_base, env.pip_requirements)
    
    print "Updating pip-requirements..."
    with settings(
            cd(env.remote_base),
            hide('stdout', 'running'),
            ):
        run('source %s; pip install -r %s' % (activate, pip_requirements))
    print "Update finished."

@task
@roles('code')
def update(package=''):
    """Pull and update remote repository. If package parameter is given, update the named repository under virtualenv/src."""
    if package:
        update_root = os.path.join(env.remote_base, env.virtualenv, 'src', package)
    else:
        update_root = env.remote_base

    print "Updating %s on %s:" % (os.path.split(update_root)[1], env.host)
    print "Revision before update:\t%s:%s" % revision_for_path(update_root)
    with settings(
            hide('stdout', 'running'),
            cd(update_root),
            ):
        if run('test -d .git || echo "failed"') != 'failed':
            # __git_ps1 gives nicely formatted output in all circumstances, 
            # but might not be available in all systems.
            run('git pull')
        elif run('test -d .hg || echo "failed"') != 'failed':
            run('hg pull')
            run('hg update')
        else:
            print "Unsupported revision control system or wrong remote_base"
    print "Updated to revision: \t%s:%s" % revision_for_path(update_root)

@task
@roles('media')
def collectstatic():
    """Run manage.py collectstatic script on media-server"""
    activate = os.path.join(env.remote_base, env.virtualenv, 'bin/activate')
    manage = os.path.join(env.remote_base, env.manage)
    run('source %s; python %s collectstatic ' % (activate, manage))

@task
@roles('app-server')
def reload():
    """run reload.sh to reload the application"""
    run("~/run/reload.sh")
    
@task
@roles('migration')
def migrate(option=''):
    """Run syncdb and migrations. Allowed option: merge"""
    option = "--" + option if option == 'merge' else ''
    activate = os.path.join(env.remote_base, env.virtualenv, 'bin/activate')
    manage = os.path.join(env.remote_base, env.manage)
    run("source %s; python %s syncdb" % (activate, manage))
    run("source %s; python %s migrate %s" % (activate, manage, option))
