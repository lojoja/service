import logging
import subprocess

import click


logger = logging.getLogger(__name__)


def _call(sudo, *args):
    """
    Call the launchctl program.

    NOTE: Sudo is not optional when calling `_call` and must be the first argument because the rest of the command
    is arbitrary in length. This is different than the public API functions which use an optional keyword argument
    for sudo.
    """
    cmd = []
    if sudo:
        cmd.append('sudo')
    cmd.append('launchctl')
    cmd.extend(args)

    logger.debug('Calling launchctl with command "{}"'.format(cmd))
    subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _bootout(service, sudo=False, ignore_missing=False):
    try:
        _call(sudo, 'bootout', service.domain, service.file)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.split(': ')[1].lower()

        if stderr.startswith('could not find'):
            msg = 'Service "{}" is not running{}'

            if ignore_missing:
                logger.debug(msg.format(service.name, ' (ignored)'))
            else:
                raise click.ClickException(msg.format(service.name, ''))
        elif stderr.startswith('operation not permitted'):
            raise click.ClickException(
                'Cannot stop system service "{}" while SIP is enabled'.format(
                    service.name
                )
            )
        else:
            raise click.ClickException(
                'Failed to stop service "{}"'.format(service.name)
            )


def _bootstrap(service, sudo=False):
    try:
        _call(sudo, 'bootstrap', service.domain, service.file)
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.split(': ')[1].lower()

        if stderr.startswith('no such file'):
            raise click.ClickException(
                'Service file "{}" not found'.format(service.file)
            )
        elif stderr.startswith('service already'):
            raise click.ClickException(
                'Service "{}" is already running'.format(service.name)
            )
        elif stderr.startswith('service is disabled'):
            raise click.ClickException('Service "{}" is disabled'.format(service.name))
        else:
            raise click.ClickException(
                'Failed to start service "{}"'.format(service.name)
            )


def disable(service, sudo=False):
    """ Disable a service. """
    logger.debug('Disabling service "{}"'.format(service.name))

    try:
        _call(sudo, 'disable', '{}/{}'.format(service.domain, service.name))
    except subprocess.CalledProcessError as e:
        raise click.ClickException('Failed to disable "{}"'.format(service.name))


def enable(service, sudo=False):
    """ Enable a service. """
    logger.debug('Enabling service "{}"'.format(service.name))

    try:
        _call(sudo, 'enable', '{}/{}'.format(service.domain, service.name))
    except subprocess.CalledProcessError as e:
        raise click.ClickException('Failed to enable "{}"'.format(service.name))


def restart(service, sudo=False):
    """ Restart a service. """
    logger.debug('Restarting service "{}"'.format(service.name))

    _bootout(service, sudo, ignore_missing=True)
    _bootstrap(service, sudo)


def start(service, sudo=False):
    """ Start a service. """
    logger.debug('Starting service "{}"'.format(service.name))
    _bootstrap(service, sudo)


def stop(service, sudo=False):
    """ Stop a service. """
    logger.debug('Stopping service "{}"'.format(service.name))
    _bootout(service, sudo)
