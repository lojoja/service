# -*- coding: utf-8 -*-
import logging

import click

__all__ = ['change_logger_level', 'setup_logger']


VERBOSITY_MAP = {
    True: logging.DEBUG,
    False: logging.WARNING,
    None: logging.INFO,
}


class ClickFormatter(logging.Formatter):
    colors = {
        'critical': 'red',
        'debug': 'blue',
        'error': 'red',
        'exception': 'red',
        'warning': 'yellow'
    }

    def format(self, record):
        if not record.exc_info:
            level = record.levelname.lower()
            msg = record.msg
            if level in self.colors:
                prefix = click.style('{}: '.format(level.title()), fg=self.colors[level])
                if not isinstance(msg, (str, bytes)):
                    msg = str(msg)
                msg = '\n'.join(prefix + l for l in msg.splitlines())
            return msg
        return logging.Formatter.format(self, record)


class ClickHandler(logging.Handler):
    error_levels = [
        'critical',
        'error',
        'exception',
        'warning'
    ]

    def emit(self, record):
        try:
            msg = self.format(record)
            err = record.levelname.lower() in self.error_levels
            click.echo(msg, err=err)
        except Exception:
            self.handleError(record)


def setup_logger(logger):
    logger.setLevel(VERBOSITY_MAP[None])

    formatter = ClickFormatter()

    handler = ClickHandler()
    handler.setFormatter(formatter)

    logger.addHandler(handler)


def change_logger_level(logger, level):
    current_level = logger.getEffectiveLevel()
    logger.setLevel(VERBOSITY_MAP.get(level, current_level))
