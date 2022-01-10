# -*- coding: utf-8 -*-
from codecs import open
import logging
import os
import platform
import pwd
import re

import click
import subprocess32 as subprocess

from service import __version__, launchctl  # noqa
from service.log import change_logger_level, setup_logger

__all__ = ['cli']


PROGRAM_NAME = 'service'
MIN_MACOS_VERSION = 12.0

logger = logging.getLogger(PROGRAM_NAME)
setup_logger(logger)


class Configuration(object):
    """ Program configuration and environment settings. """
    def __init__(self, verbose):
        logger.debug('Gathering system and environment details')
        self.macos_version = self._get_mac_version()
        self.sudo = os.geteuid() == 0
        self.user = pwd.getpwnam(os.getenv('SUDO_USER' if self.sudo else 'USER'))
        self.reverse_domains = None
        self.service = None
        self.verbose = verbose

    def _find_reverse_domains_file(self):
        """ Locate the reverse domain configuration file to use. """
        logger.debug('Finding reverse domain config file')

        filename = '{}.conf'.format(PROGRAM_NAME)
        paths = [
            '/usr/local/etc',
            '/etc'
        ]

        for p in paths:
            file = os.path.join(p, filename)

            logger.debug('Trying reverse domain config file "{}"'.format(file))
            if os.path.isfile(file):
                logger.debug('Reverse domain config file found; using "{}"'.format(file))
                return file

        logger.debug('Reverse domain config file not found')
        return None

    def _get_mac_version(self):
        version = platform.mac_ver()[0]
        version = float('.'.join(version.split('.')[:2]))  # format as e.g., '10.10'
        return version

    def _get_reverse_domains(self):
        logger.debug('Loading reverse domains')

        file = self._find_reverse_domains_file()
        data = []

        if file:
            lines = []

            try:
                with open(file, mode='rb', encoding='utf-8') as f:
                    lines = f.read().splitlines()
            except IOError:
                raise click.ClickException('Failed to read reverse domains file')

            for line in lines:
                line = re.split('#|\s', line.strip(), 1)[0]

                if line:
                    logger.debug('Adding reverse domain "{}"'.format(line))
                    data.append(line)
        return data

    def get_reverse_domains(self):
        self.reverse_domains = self._get_reverse_domains()


class Service(object):
    """ A service on the system. """
    system_paths = [
        '/Library/LaunchAgents',
        '/Library/LaunchDaemons',
        '/System/Library/LaunchAgents',
        '/System/Library/LaunchDaemons'
    ]
    user_paths = [
        '{}/Library/LaunchAgents'
    ]

    def __init__(self, name, config):
        logger.debug('Initializing service')
        self._search_paths = self._get_search_paths(config.sudo, config.user)
        self._domain = self._get_target_domain(config.sudo, config.user)
        self._file = self._find(name, config.reverse_domains)

    @property
    def daemon(self):
        """ Service filename with extension. """
        return os.path.basename(self.file)

    @property
    def domain(self):
        """ Service target domain (e.g., system). """
        return self._domain

    @property
    def file(self):
        """ Full path to the service file. """
        return self._file

    @property
    def name(self):
        """ Service filename without extension. """
        return os.path.splitext(self.daemon)[0]

    @property
    def search_paths(self):
        return self._search_paths

    def _find(self, name, reverse_domains):
        """ Find the service based on the information given. """
        logger.debug('Finding service "{}"'.format(name))
        _name = name  # save the original name

        name = self._normalize_filename(name)
        path, filename = os.path.split(name)
        possible_paths = self._get_paths_to_check(path)
        possible_filenames = self._get_files_to_check(filename, reverse_domains)

        for pfile in possible_filenames:
            for ppath in possible_paths:
                service_file = os.path.join(ppath, pfile)
                logger.debug('Trying "{}"'.format(service_file))

                if os.path.isfile(service_file):
                    logger.debug('Service found, using "{}"'.format(service_file))
                    self._validate_domain(service_file)
                    return service_file

        raise click.ClickException('Service "{}" not found'.format(_name))

    def _get_files_to_check(self, file, reverse_domains):
        """
        Get list of possible services using the name from the CLI argument if it includes a reverse domain, otherwise
        constructing the list with all configured reverse domains.
        """
        segments = len(file.split('.'))
        return [file] if segments > 2 else ['{0}.{1}'.format(rd, file) for rd in reverse_domains]

    def _get_paths_to_check(self, path):
        """ Determine whether to use search_paths or the path from CLI argument. """
        return [path] if path else self.search_paths

    def _get_search_paths(self, sudo, user):
        """ Get the service search paths for system or user domains. """
        logger.debug('Identifying search paths')

        if sudo:
            logger.debug('Using "system" search paths')
            paths = self.system_paths
        else:
            logger.debug('Using "user" search paths')
            paths = self.user_paths
            paths[0] = paths[0].format(user.pw_dir)
        return paths

    def _get_target_domain(self, sudo, user):
        """ Get the service target domain. """
        return 'system' if sudo else 'gui/{}'.format(user.pw_uid)

    def _normalize_filename(self, name):
        """ Ensure filename has an extension. """
        ext = '.plist'
        if not name.endswith(ext):
            name += ext
        return name

    def _validate_domain(self, service):
        """
        Verify the service exists in the current domain. Used to check user full path input, if the program
        searched for and identified the service it's guaranteed to be in the correct domain.
        """
        logger.debug('Validating service domain')

        if self.domain == 'system' and not service.startswith(tuple(self.system_paths)):
            raise click.ClickException('Service "{}" is not in the system domain'.format(service))

        if self.domain.startswith('gui') and service.startswith(tuple(self.system_paths)):
            raise click.ClickException('Service "{}" is not in the gui domain'.format(service))


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
        config.get_reverse_domains()

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
    """ Enable a service. """
    launchctl.enable(config.service, sudo=config.sudo)
    logger.info('"{}" enabled'.format(config.service.name))


@cli.command()
@service_name_argument
@click.pass_obj
def restart(config, name):
    """ Restart a service. """
    launchctl.restart(config.service, sudo=config.sudo)
    logger.info('"{}" restarted'.format(config.service.name))


@cli.command()
@click.option('--enable', '-e', is_flag=True, default=False, help='Enable sevice before starting.')
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
@click.option('--disable', '-d', is_flag=True, default=False, help='Disable service after stopping.')
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
