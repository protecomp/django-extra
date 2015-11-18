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

from distutils.util import strtobool

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

@roles('code')
@task
def revision(*args):
    """Show revision and branch for all repositories on the server, or only the specified ones"""
    host = env.host.split('.', 1)[0]
    packages = args if args else env.repository_roots.keys()

    for package in packages:
        (branch, rev) = revision_for_path(env.repository_roots[package])
        print "%s:\t{0:28} {1}".format("%s:%s" % (package, branch), rev) % host

@roles('app-server')
@task
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

@roles('code')
@task
def update(*args):
    """Pull and update remote repositories. If argument is not given, only default repos are updated.

    Requires env.repository_roots dict and env.update_defaults.
    env.repository_roots = {
        'proj1': '/path/to/proj1',
        'proj2': '/path/to/proj2',
    }
    env.update_default = ('proj1', )

    """
    host = env.host.split('.', 1)[0]

    packages = args if args else env.update_default

    for package in packages:
        update_root = env.repository_roots[package]

        print "%s:\tUpdating %s..." % (host, package)
        print "%s:\tRevision before update:\t%s:%s" % ((host, ) + revision_for_path(update_root))
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
        print "%s:\tUpdated to revision: \t%s:%s" % ((host, ) + revision_for_path(update_root))

@roles('code')
@task
def checkout(branch, force='false', reset='false', default='master'):
    """Pull and checkout all remote repositories to a named branch, if it exists (fallback to master)

examples:

    checkout:my_branch
    - checkouts my_branch, fallbacking to master if the branch does not exist

    checkout:release,reset=true
    - checkouts release-branch and resets it to remote branch, deleting all local changes

    checkout:feature/my_feature,default=release
    - checkouts the branch, fallbacking to release-branch (release-branch must exist on all repos)

args:

    branch: branch name (required)
    force: force checkout, overwriting local uncommitted changes
    reset: after checkout, hard reset to remote branch
    default: The branch to checkout if 'branch' does not exist
    """
    host = env.host.split('.', 1)[0]
    force = bool(strtobool(str(force)))
    reset = bool(strtobool(str(reset)))
    if not branch:
        raise Exception("No branch specified")
    for package, repository_root in env.repository_roots.items():
        with settings(
                hide('stdout', 'running'),
                cd(repository_root),
                ):
            print "%s:\t Fetching %s" % (host, package)
            run('git fetch --all')
            if run("git branch -a | grep '%s' || echo 'failed'" % branch) != 'failed':
                branch_to_checkout = branch
            else:
                branch_to_checkout = default
            print "%s:\t Checking out branch %s" % (host, branch_to_checkout)
            args = ' --force' if force else ''
            run("git checkout -q %s%s" % (args, branch_to_checkout))
            if reset:
                run("git reset --hard -q origin/%s" % branch_to_checkout)
            else:
                run("git merge -q --ff-only origin/%s" % branch_to_checkout)

@roles('media')
@task
def collectstatic():
    """Run manage.py collectstatic script on media-server"""
    activate = os.path.join(env.remote_base, env.virtualenv, 'bin/activate')
    manage = os.path.join(env.remote_base, env.manage)
    run('source %s; python %s collectstatic --noinput' % (activate, manage))

@roles('app-server')
@task
def reload():
    """run reload.sh to reload the application"""
    run("~/run/reload.sh")
    
@roles('migration')
@task
def migrate(option=''):
    """Run syncdb and migrations. Allowed option: merge"""
    option = "--" + option if option == 'merge' else ''
    activate = os.path.join(env.remote_base, env.virtualenv, 'bin/activate')
    manage = os.path.join(env.remote_base, env.manage)
    run("source %s; python %s syncdb" % (activate, manage))
    run("source %s; python %s migrate %s" % (activate, manage, option))
