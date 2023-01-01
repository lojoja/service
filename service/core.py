import logging
import os
import pathlib
import platform
import re

import click

import service
from service import launchctl


__all__ = ["cli"]


PROGRAM_NAME = "service"
MIN_MACOS_VERSION = 12.0
CONFIG_FILE = '{}.conf'.format(PROGRAM_NAME)


logger = logging.getLogger(__package__)


class Configuration(object):
    """ Program configuration and environment settings. """

    def __init__(self, verbose):
        logger.debug('Gathering system and environment details')
        self.macos_version = self._get_macos_version()
        self.user = os.geteuid()
        self.sudo = self.user == 0
        self.reverse_domains = None
        self.service = None
        self.verbose = verbose

    def _find_reverse_domains_config(self):
        """ Locate the reverse domain configuration file to use. """
        logger.debug('Finding reverse domain config file')

        paths = ['/usr/local/etc', '/etc']

        for p in paths:
            conf = pathlib.Path(p, CONFIG_FILE)

            logger.debug('Trying reverse domain config file "{}"'.format(conf))
            if conf.is_file():
                logger.debug('Reverse domain config file found; using "{}"'.format(conf))
                return conf

        logger.debug('Reverse domain config file not found')
        return None

    def _get_macos_version(self):
        version = platform.mac_ver()[0]
        version = float('.'.join(version.split('.')[:2]))  # format as e.g., '10.10'
        return version

    def load_reverse_domains(self):
        logger.debug('Loading reverse domains')

        conf = self._find_reverse_domains_config()
        data = []

        if conf:
            lines = []

            try:
                with conf.open(mode='r', encoding='utf-8') as f:
                    lines = f.read().splitlines()
            except IOError:
                raise click.ClickException('Failed to read reverse domains file')

            for line in lines:
                line = re.split(r'#|\s', line.strip(), 1)[0]

                if line:
                    logger.debug('Adding reverse domain "{}"'.format(line))
                    data.append(line)

        self.reverse_domains = data


@click.group(cls=CLIGroup)
@click.option('--verbose/--quiet', '-v/-q', is_flag=True, default=None, help='Specify verbosity level.')
@click.version_option()
@click.pass_context
def cli(ctx, verbose):
    change_logger_level(logger, verbose)

    logger.debug('{} started'.format(PROGRAM_NAME))

    config = Configuration(verbose)

    logger.debug('Checking macOS version')
    if config.macos_version < MIN_MACOS_VERSION:
        raise click.ClickException('{0} requires macOS {1} or higher'.format(PROGRAM_NAME, MIN_MACOS_VERSION))
    else:
        logger.debug('macOS version is {}'.format(config.macos_version))

    # Load reverse domains and initiate service only when a subcommand is given without the `--help` option
    if ctx.invoked_subcommand and '--help' not in ctx.obj:
        config.load_reverse_domains()

        logger.debug('Processing group command arguments')
        name = next((arg for arg in ctx.obj if not arg.startswith('-')), '')

        service = Service(name, config)
        config.service = service

        # Store config on context.obj for subcommands to access
        ctx.obj = config


def service_name_argument(func):
    func = click.argument("name", default="")(func)
    return func


@cli.command()
@service_name_argument
@click.pass_obj
def disable(config, name):
    """Disable a service."""
    launchctl.change_state(config.service, enable=False)
    logger.info('"{}" disabled'.format(config.service.name))


@cli.command()
@service_name_argument
@click.pass_obj
def enable(config, name):
    """Enable a service. Only available for system domain services."""
    launchctl.change_state(config.service, enable=True)
    logger.info('"{}" enabled'.format(config.service.name))


@cli.command()
@service_name_argument
@click.pass_obj
def restart(config, name):
    """Restart a service. Only available for system domain services."""
    launchctl.boot(config.service, run=False)
    launchctl.boot(config.service, run=True)

    logger.info('"{}" restarted'.format(config.service.name))


@cli.command()
@click.option(
    "--enable",
    "-e",
    is_flag=True,
    default=False,
    help="Enable sevice before starting. Only available for services in the system domain.",
)
@service_name_argument
@click.pass_obj
def start(config, name, enable):
    """Start a service, optionally enabling it first."""
    if enable:
        launchctl.change_state(config.service, enable=True)
        logger.debug('"{}" enabled'.format(config.service.name))

    launchctl.boot(config.service, run=True)
    logger.info('"{}" started'.format(config.service.name))


@cli.command()
@click.option(
    "--disable",
    "-d",
    is_flag=True,
    default=False,
    help="Disable service after stopping. Only available for services in the system domain.",
)
@service_name_argument
@click.pass_obj
def stop(config, name, disable):
    """Stop a service, optionally disabling it afterward."""
    launchctl.boot(config.service, run=False)
    logger.info('"{}" stopped'.format(config.service.name))

    if disable:
        launchctl.change_state(config.service, enable=False)
        logger.debug('"{}" disabled'.format(config.service.name))
    logger.error(self.message)
