import logging

import click
import subprocess


LC_DOMAIN_GUI = 'gui'
LC_DOMAIN_SYSTEM = 'system'

LC_ERROR_GUI_ALREADY_STARTED = 5
LC_ERROR_GUI_ALREADY_STOPPED = 5
LC_ERROR_SIP = 150
LC_ERROR_SYSTEM_ALREADY_STARTED = 37
LC_ERROR_SYSTEM_ALREADY_STOPPED = 113

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


def _bootout(service, sudo=False):
    try:
        _call(sudo, 'bootout', service.domain, service.file)
    except subprocess.CalledProcessError as e:
        if e.returncode in [LC_ERROR_GUI_ALREADY_STOPPED, LC_ERROR_SYSTEM_ALREADY_STOPPED]:
            raise click.ClickException('Service "{}" is not running'.format(service.name))
        elif e.returncode == LC_ERROR_SIP:
            raise click.ClickException('Service "{}" cannot be stopped due to SIP'.format(service.name))
        else:
            raise click.ClickException('Failed to stop service "{}"'.format(service.name))


def _bootstrap(service, sudo=False):
    try:
        _call(sudo, 'bootstrap', service.domain, service.file)
    except subprocess.CalledProcessError as e:
        if e.returncode in [LC_ERROR_GUI_ALREADY_STARTED, LC_ERROR_SYSTEM_ALREADY_STARTED]:
            raise click.ClickException('Service "{}" is not running'.format(service.name))
        elif e.returncode == LC_ERROR_SIP:
            raise click.ClickException('Service "{}" cannot be started due to SIP'.format(service.name))
        else:
            raise click.ClickException('Failed to start service "{}"'.format(service.name))


def disable(service, sudo=False):
    """ Disable a service. """
    if service.domain != LC_DOMAIN_SYSTEM:
        raise click.ClickException('Cannot disable services in the "{}" domain'.format(service.domain))

    logger.debug('Disabling service "{}"'.format(service.name))

    try:
        _call(sudo, 'disable', '{}/{}'.format(service.domain, service.name))
    except subprocess.CalledProcessError:
        raise click.ClickException('Failed to disable "{}"'.format(service.name))


def enable(service, sudo=False):
    """ Enable a service. """
    if service.domain != LC_DOMAIN_SYSTEM:
        raise click.ClickException('Cannot enable services in the "{}" domain'.format(service.domain))

    logger.debug('Enabling service "{}"'.format(service.name))

    try:
        _call(sudo, 'enable', '{}/{}'.format(service.domain, service.name))
    except subprocess.CalledProcessError:
        raise click.ClickException('Failed to enable "{}"'.format(service.name))


def restart(service, sudo=False):
    """ Restart a service. """
    logger.debug('Restarting service "{}"'.format(service.name))
    _bootout(service, sudo)
    _bootstrap(service, sudo)


def start(service, sudo=False):
    """ Start a service. """
    logger.debug('Starting service "{}"'.format(service.name))
    _bootstrap(service, sudo)


def stop(service, sudo=False):
    """ Stop a service. """
    logger.debug('Stopping service "{}"'.format(service.name))
    _bootout(service, sudo)
