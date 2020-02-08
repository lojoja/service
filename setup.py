from codecs import open
import re
from setuptools import setup


def get_long_description():
    with open('README.md', encoding='utf-8') as f:
        return f.read()


def get_version():
    pattern = r'^__version__ = \'([^\']*)\''
    with open('service/__init__.py', encoding='utf-8') as f:
        text = f.read()
    match = re.search(pattern, text, re.M)

    if match:
        return match.group(1)
    raise RuntimeError('Unable to determine version')


setup(
    name='service',
    version=get_version(),
    description='Extremely basic launchctl wrapper for macOS.',
    long_description=get_long_description(),
    url='https://github.com/lojoja/service',
    author='lojoja',
    author_email='github@lojoja.com',
    license='MIT',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Console',
        'License :: OSI Approved :: MIT License',
        'Operating System :: MacOS :: MacOS X',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.7',
    ],
    keywords='macOS launchctl',
    packages=['service'],
    data_files=[('/usr/local/etc', ['service.default.conf'])],
    install_requires=['click>=7.0'],
    entry_points={'console_scripts': ['service=service.core:cli',]},
)
