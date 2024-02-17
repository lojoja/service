# service

Extremely basic launchctl wrapper for macOS.

## Requirements

- macOS 12.x+
- Python 3.10.x, 3.11.x

## Installation

```
pip install py-service
```

## Usage

```
Usage: service [OPTIONS] COMMAND [ARGS]...

  Extremely basic launchctl wrapper for macOS.

Options:
  -c, --config TEXT  The configuration file to use
  --help             Show this message and exit.
  -v, --verbose      Increase verbosity
  --version          Show the version and exit.

Commands:
  disable  Disable a service (system domain only).
  enable   Enable a service (system domain only).
  restart  Restart a service.
  start    Start a service.
  stop     Stop a service.
```

Services can be referenced by name, file name (with or without ".plist" extension), or the full path to the file. When referenced by name the service will be resolved using the defined reverse domains (see [Configuration](#Configuration)). Examples of valid service references are:

- baz _(when reverse domains are defined)_
- com.foobar.baz
- com.foobar.baz.plist
- /Library/LaunchDaemons/com.foobar.baz
- /Library/LaunchDaemons/com.foobar.baz.plist

**Note:** Targeting a macOS system service found in the `/System/*` path will raise an error and terminate without attempting to modify the service state. These services typically cannot be changed unless SIP is disabled.

### Examples

Start a service:

```
$ service start com.gui.xserv
xserv started
```

Enable and start a service (system domain):

```
$ sudo service start --enable com.sys.xserv
xserv enabled and started
```

Stop a service:

```
$ service stop com.gui.xserv
xserv stopped
```

Stop and disable a service (system domain):

```
$ sudo service stop --disable com.sys.xserv
xserv stopped and disabled
```

Restart a service:

```
$ service restart com.gui.xserv
xserv restarted
```

Enable a service (system domain):

```
$ sudo service enable com.sys.xserv
xserv enabled
```

Disable a service (system domain):

```
$ sudo service disable com.sys.xserv
xserv disabled
```

## Configuration

Reverse domains can be defined in the file `~/.config/service.toml`. When a service is referenced by name it will be resolved to a file in the current domain (system/gui) using the defined reverse domains. Services cannot be referenced by their name alone if no reverse domains are defined.

Example configuration:

```
reverse-domains = [
  "com.bar.foo",
  "org.bat.baz"
]
```

With this configuration, a service in the gui domain at `~/Library/LaunchAgents/com.bar.foo.xserv.plist` can be targeted using only its name (`xserv`):

```
$ service start xserv
xserv started
```

## License

service is released under the [MIT License](./LICENSE)
