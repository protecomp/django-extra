"""
Code deployment commands
"""
import os

from fabric.api import *
from fabric.api import run, env, cd
from fabric.context_managers import hide
from fabric.contrib.console import confirm
from fabric.contrib.files import exists, sed

@roles('code')
def get_revision(output_level=2):
    """Get branch and revision currently in use (hg parent)
    output_level    0: No output
                    1: No hostnames
                    2: Hostnames and revision numbers (default)
    """
    if output_level > 1:
        print env.host
    with cd(env.remote_base):
        with hide('stdout', 'running'):
            log = run('hg parent')

        parts = log.split('\n')
        rev = parts[0].split(" ")[-1]
        with hide('stdout', 'running'):
            branch = run('hg branch').strip()
        
        if output_level: print "    {0:20} {1}".format(branch, rev)
        return tuple(rev.split(':'))

@task
@roles('code')
def revision(package=''):
    if package:
        VIRTUALENV_SRC_PATH = 'virtualenv/src'
        package_path = os.path.join(env.remote_base, VIRTUALENV_SRC_PATH, package)
        if exists(package_path):
            with cd(package_path):
                if exists(os.path.join(package_path, '.hg')):
                    with hide('stdout', 'running'):
                        log = run('hg parent')

                    parts = log.split('\n')
                    rev = parts[0].split(" ")[-1]
                    with hide('stdout', 'running'):
                        branch = run('hg branch').strip()
                    
                    print "    {0:20} {1}".format(branch, rev)
                    return tuple(rev.split(':'))
                else:
                    print "No Mercurial repository at %s!" % package_path
        else:
            print "The package %s at %s does not exist!" % (package, package_path)
    else:
        return get_revision()

@task
@roles('app-server')
def update_virtualenv(package=''):
    if package:
        VIRTUALENV_SRC_PATH = 'virtualenv/src'
        package_path = os.path.join(env.remote_base, VIRTUALENV_SRC_PATH, package)
        if exists(package_path):
            with cd(package_path):
                if exists(os.path.join(package_path, '.hg')):
                    print "Updating %s at %s" % (package, package_path)
                    run('hg pull -u')
                else:
                    print "No Mercurial repository at %s!" % package_path
        else:
            print "The package %s at %s does not exist!" % (package, package_path)

    else:
        """Run pip install on remote machine to update virtualenv/src/ -dir"""
        activate = os.path.join(env.remote_base, env.virtualenv_path)
        # Quirk: We have manage_path pointing to manage.py, so we can use it
        # and just change manage.py to pip-requirements.txt
        pip_requirements = os.path.join(env.remote_base, env.manage_path.replace('manage.py', 'pip-requirements.txt'))
        
        print "Updating repositories under virtualenv/src/ ..."
        with settings(
                cd(env.remote_base),
                hide('stdout', 'running'),
                ):
            run('source %s; pip install -r %s' % (activate, pip_requirements))
        print "Update finished."

@task
@roles('code')
def update(package=''):
    if package:
        update_virtualenv(package)
    else:
        """Pull and update remote repository"""
        print "Updating %s:" % env.host
        print "Revision before update:\t%s:%s" % get_revision(0)
        with settings(
                hide('stdout', 'running'),
                cd(env.remote_base),
                ):
            run('hg pull')
            run('hg update')
        print "Updated to revision: \t%s:%s" % get_revision(0)

@task
@roles('app-server')
def reload():
    """run reload.sh to reload code changes"""
    run("~/run/reload.sh")
    
@roles('migration')
def migrate(option=''):
    """Run syncdb and migrations. Allowed option: merge"""
    option = "--" + option if option == 'merge' else ''
    activate = os.path.join(env.remote_base, env.virtualenv_path)
    manage = os.path.join(env.remote_base, env.manage_path)
    run("source %s; python %s syncdb" % (activate, manage))
    run("source %s; python %s migrate %s" % (activate, manage, option))
