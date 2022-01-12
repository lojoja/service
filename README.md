service
=======

Extremely basic launchctl wrapper for macOS.


Requirements
------------

* macOS 12.x+
* Python 3.9.x+


Installation
------------

```
pip install git+https://github.com/lojoja/service.git
```


Use
---

```
Usage: service [OPTIONS] COMMAND [NAME]...

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
```

`[NAME]` can be the filename or full path, with or with `.plist` extension:

```
com.foobar.baz
com.foobar.baz.plist
/Library/LaunchDaemons/com.foobar.baz
/Library/LaunchDaemons/com.foobar.baz.plist
```

Targeting a macOS system service found in the `/System/*` path will raise an error and terminate without attempting to modify the service state. These services typically cannot be changed unless SIP is disabled.


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
