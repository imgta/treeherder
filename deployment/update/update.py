"""
Deploy this project in dev/stage/production.

Requires commander_ which is installed on the systems that need it.

.. _commander: https://github.com/oremj/commander
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from commander.deploy import task, hostgroups
import commander_settings as settings


@task
def update_code(ctx, tag):
    """Update the code to a specific git reference (tag/sha/etc)."""
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('git checkout %s' % tag)
        ctx.local('git pull -f')
        ctx.local('git submodule sync')
        ctx.local('git submodule update --init --recursive')
        ctx.local("find . -type f -name '*.pyc' -delete")

def update_assets(ctx):
    ctx.remote("{0} grunt build".format(settings.WEB_DIR))

def update_oauth_credentials(ctx):

    ctx.local("python2.6 manage.py export_project_credentials")

    # Need to scp the credentials from admin node to workers and web service nodes

@task
def update_db(ctx):
    """Update the database schema, if necessary."""

    with ctx.lcd(settings.SRC_DIR):
        ctx.local('python2.6 manage.py syncdb')
        ctx.local('python2.6 manage.py migrate')

@task
def checkin_changes(ctx):
    """Use the local, IT-written deploy script to check in changes."""
    ctx.local(settings.DEPLOY_SCRIPT)

def deploy_admin_node(ctx):
    ctx.local('/usr/bin/supervisorctl restart celerybeat')
    ctx.local('/usr/bin/supervisorctl restart celerymon')
    ctx.local('/usr/bin/supervisorctl restart celery')

@hostgroups(settings.WEB_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def deploy_web_app(ctx):
    """Call the remote update script to push changes to webheads."""
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)

    # Make sure web assets are rebuilt when code is updated
    update_assets(ctx)

    ctx.remote('/usr/bin/supervisorctl restart gunicorn')
    ctx.remote('/usr/bin/supervisorctl restart socketio-server')

@hostgroups(settings.CELERY_HOSTGROUP, remote_kwargs={'ssh_key': settings.SSH_KEY})
def deploy_workers(ctx):
    """Call the remote update script to push changes to workers."""
    ctx.remote(settings.REMOTE_UPDATE_SCRIPT)
    ctx.remote('/usr/bin/supervisorctl restart celery')

@task
def update_info(ctx):
    """Write info about the current state to a publicly visible file."""
    with ctx.lcd(settings.SRC_DIR):
        ctx.local('date')
        ctx.local('git branch')
        ctx.local('git log -3')
        ctx.local('git status')
        ctx.local('git submodule status')

        ctx.local('git rev-parse HEAD > media/revision')


@task
def pre_update(ctx, ref=settings.UPDATE_REF):
    """Update code to pick up changes to this file."""
    update_code(ref)


@task
def update(ctx):
    update_assets()
    update_db()


@task
def deploy(ctx):
    checkin_changes()
    deploy_admin_node()
    deploy_web_app()
    deploy_workers()
    update_info()


@task
def update_site(ctx, tag):
    """Update the app to prep for deployment."""
    pre_update(tag)
    update()
