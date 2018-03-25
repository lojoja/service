service
=======

Extremely basic launchctl wrapper for macOS.


Requirements
------------

* macOS 10.10.x+
* Python 2.7.x
* System Integrity Protection must be [disabled](https://developer.apple.com/library/content/documentation/Security/Conceptual/System_Integrity_Protection_Guide/ConfiguringSystemIntegrityProtection/ConfiguringSystemIntegrityProtection.html) to disable a running system daemon or agent


Installation
------------

```
pip install git+https://github.com/lojoja/service.git
```


Use
---

```
Usage: service [OPTIONS] COMMAND [OPTIONS] [NAME]

Options:
      --version                   Show the version and exit
      --help                      Show this message and exit
  -q, --quiet                     Decrease verbosity
  -v, --verbose                   Increase verbosity

Commands:
  disable                         Disable a service
  enable                          Enable a service
  restart                         Restart a service
  start                           Start a service, optionally enabling it first
  stop                            Stop a service, optionally disabling it afterward

Command Options:
  -d, --disable                   Disable service after stopping
  -e, --enable                    Enable service before starting
```

`[NAME]` can be the filename or full path, with or with `.plist` extension:

```
com.foobar.baz
com.foobar.baz.plist
/System/Library/LaunchDaemons/com.foobar.baz
/System/Library/LaunchDaemons/com.foobar.baz.plist
```


Configure
---------

Copy `/usr/local/etc/service.default.conf` to `/usr/local/etc/service.conf`. Each line is a reverse domain to search for a service name. This allows short, friendly names without a path or full filename passed as the `[NAME]` argument to be resolved to a file automatically. It's recommended to limit the reverse domains to those you control.

Consider the service `/Library/LaunchDaemons/com.foobar.baz.plist`:

```
# service.conf

com.foobar
```

```
$ sudo service start baz
"com.foobar.baz" started
```


License
-------

service is released under the [MIT License](./LICENSE)
