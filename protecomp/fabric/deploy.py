"""
Code deployment commands

Required env-variables:

– env.remote_base, the project base path on semote media-server, absolute path

The rest are relative to the remote_base path

- env.virtualenv_path, the path to virtual environment activate-script (relative)
- env.manage_path, the path to manage.py -file, (relative)
- env.pip_requirements, the path to pip-requirements.txt file (relative)
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
    return tuple(branch, rev)

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
        VIRTUALENV_SRC_PATH = 'virtualenv/src'
        package_path = os.path.join(env.remote_base, VIRTUALENV_SRC_PATH, package)
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
    activate = os.path.join(env.remote_base, env.virtualenv_path)
    # Quirk: We have manage_path pointing to manage.py, so we can use it
    # and just change manage.py to pip-requirements.txt
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
def update():
    """Pull and update remote repository"""
    print "Updating %s:" % env.host
    print "Revision before update:\t%s:%s" % get_revision(0)
    with settings(
            hide('stdout', 'running'),
            cd(env.remote_base),
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
    print "Updated to revision: \t%s:%s" % get_revision(0)

@task
@roles('media')
def collectstatic():
    """Run manage.py collectstatic script on media-server"""
    activate = os.path.join(env.remote_base, env.virtualenv_path)
    manage = os.path.join(env.remote_base, env.manage_path)
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
    activate = os.path.join(env.remote_base, env.virtualenv_path)
    manage = os.path.join(env.remote_base, env.manage_path)
    run("source %s; python %s syncdb" % (activate, manage))
    run("source %s; python %s migrate %s" % (activate, manage, option))
