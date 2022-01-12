import logging
import os
import pathlib
import platform
import re

import click

from service import __version__, launchctl  # noqa
from service.log import change_logger_level, setup_logger

__all__ = ['cli']


PROGRAM_NAME = 'service'
MIN_MACOS_VERSION = 12.0
CONFIG_FILE = '{}.conf'.format(PROGRAM_NAME)

logger = logging.getLogger(PROGRAM_NAME)
setup_logger(logger)


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


class Service(object):
    """ A service on the system. """

    def __init__(self, name, config):
        logger.debug('Initializing service')
        self._domain = launchctl.DOMAIN_SYSTEM if config.sudo else '{}/{}'.format(launchctl.DOMAIN_GUI, config.user)
        self._search_paths = self._get_search_paths()
        self._file = self._find(name, config.reverse_domains)

    @property
    def domain(self):
        """ Service target domain (e.g., system). """
        return self._domain

    @property
    def file(self):
        """ Full path to the service file, as a string. """
        return str(self._file)

    @property
    def name(self):
        """ Service filename without extension, as a string. """
        return self._file.stem

    @property
    def search_paths(self):
        return self._search_paths

    def _find(self, name, rev_domains):
        """
        Find the service based on the information given. Uses the `name` argument as input on the CLI if it includes
        an absolute or relative path, adding the file extension if missing, otherwise constructs and tests all possible
        file paths in the current launchctl domain for a match.
        """
        logger.debug('Finding service "{}"'.format(name))
        _name = name  # save the original name
        service_path = None

        if not name.endswith('.plist'):
            name += '.plist'

        path = pathlib.Path(name)

        if len(path.parts) > 1:
            logger.debug('Resolving path from CLI input')
            path = path.expanduser().absolute()

            logger.debug('Trying "{}"'.format(path))
            if path.is_file():
                service_path = path
        else:
            filenames = [path.name] if len(path.suffixes) > 1 else ['{}.{}'.format(rd, path.name) for rd in rev_domains]

            for search_path in self.search_paths:
                for filename in filenames:
                    possible_file = search_path.joinpath(filename)
                    logger.debug('Trying "{}"'.format(possible_file))

                    if possible_file.is_file():
                        service_path = possible_file
                        break
                else:
                    continue
                break

        if not service_path:
            raise click.ClickException('Service "{}" not found'.format(_name))

        logger.debug('Service found, using "{}"'.format(service_path))
        self._validate_domain(service_path)
        return service_path

    def _get_search_paths(self):
        """ Get the service search paths for system or user domains. """
        logger.debug('Identifying search paths')

        common_paths = ['Library/LaunchAgents', 'Library/LaunchDaemons']
        prefixes = ['/', '/System'] if self.domain == launchctl.DOMAIN_SYSTEM else [pathlib.Path.home()]
        search_paths = []

        for prefix in prefixes:
            for common_path in common_paths:
                path = pathlib.Path(prefix, common_path)
                if path.is_dir():
                    search_paths.append(path)
        return search_paths

    def _validate_domain(self, service_path):
        """ Verify the service exists in the current domain and is not a macOS system service. """
        logger.debug('Validating service domain')

        if self.domain == launchctl.DOMAIN_SYSTEM:
            if service_path.parts[1] == ('System'):
                raise click.ClickException('Service "{}" is a macOS system service'.format(service_path))

            if service_path.parts[1] == ('Users'):
                raise click.ClickException('Service "{}" is not in the "{}" domain'.format(service_path, self.domain))
        else:
            if not service_path.parts[1] == ('Users'):
                raise click.ClickException('Service "{}" is not in the "{}" domain'.format(service_path, self.domain))


class CLIGroup(click.Group):
    """
    CLI Command group

    Collect common group subcommand arguments so they can be handled once at the group level.
    This provides a better cli interface without duplicating the code in each subcommand. Argument names
    must still be included in each command's function signature.
    """
    def invoke(self, ctx):
        ctx.obj = tuple(ctx.args)
        super(CLIGroup, self).invoke(ctx)


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
    func = click.argument('name', default='')(func)
    return func


@cli.command()
@service_name_argument
@click.pass_obj
def disable(config, name):
    """ Disable a service. """
    launchctl.disable(config.service, sudo=config.sudo)
    logger.info('"{}" disabled'.format(config.service.name))


@cli.command()
@service_name_argument
@click.pass_obj
def enable(config, name):
    """ Enable a service. Only available for system domain services."""
    launchctl.enable(config.service, sudo=config.sudo)
    logger.info('"{}" enabled'.format(config.service.name))


@cli.command()
@service_name_argument
@click.pass_obj
def restart(config, name):
    """ Restart a service. Only available for system domain services. """
    launchctl.restart(config.service, sudo=config.sudo)
    logger.info('"{}" restarted'.format(config.service.name))


@cli.command()
@click.option(
    '--enable', '-e', is_flag=True, default=False,
    help='Enable sevice before starting. Only available for services in the system domain.',
)
@service_name_argument
@click.pass_obj
def start(config, name, enable):
    """ Start a service, optionally enabling it first. """
    if enable:
        launchctl.enable(config.service, sudo=config.sudo)
        logger.debug('"{}" enabled'.format(config.service.name))

    launchctl.start(config.service, sudo=config.sudo)
    logger.info('"{}" started'.format(config.service.name))


@cli.command()
@click.option(
    '--disable', '-d', is_flag=True, default=False,
    help='Disable service after stopping. Only available for services in the system domain.',
)
@service_name_argument
@click.pass_obj
def stop(config, name, disable):
    """ Stop a service, optionally disabling it afterward. """
    launchctl.stop(config.service, sudo=config.sudo)
    logger.info('"{}" stopped'.format(config.service.name))

    if disable:
        launchctl.disable(config.service, sudo=config.sudo)
        logger.debug('"{}" disabled'.format(config.service.name))


def show_exception(self, file=None):
    logger.error(self.message)


click.ClickException.show = show_exception
click.UsageError.show = show_exception
