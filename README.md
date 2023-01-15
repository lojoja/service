# service

Extremely basic launchctl wrapper for macOS.


## Requirements

* macOS 12.x+
* Python 3.10.x+


## Installation

### Local

```
pip install --trusted-host=gitea.lojoja.com --extra-index-url=https://gitea.lojoja.com/api/packages/lojoja/pypi/simple service
```

### Remote

```
pip install git+ssh://github.com/lojoja/service@main
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

Services can be referenced by name, file name (with or without extension), or the full path to the file. When referenced by name, the service will be resolved using the defined reverse domains (see [Configuration](#Configuration)). All the following are valid references:

- baz
- com.foobar.baz
- com.foobar.baz.plist
- /Library/LaunchDaemons/com.foobar.baz
- /Library/LaunchDaemons/com.foobar.baz.plist


Targeting a macOS system service found in the `/System/*` path will raise an error and terminate without attempting to modify the service state. These services typically cannot be changed unless SIP is disabled.


### Examples

Start a service:

```
> service start com.bar.foo
```

Enable and start a service:

```
> sudo service start --enable com.bar.foo
```

Stop a service:

```
> service stop com.bar.foo
```

Stop and disable a service:

```
> sudo service stop --disable com.bar.foo
```

Restart a service:
```
> service restart com.bar.foo
```

Enable a service:

```
> sudo service enable com.bar.foo
```

Disable a service:

```
> sudo service disable com.bar.foo
```


## Configuration

Reverse domains can be defined in the file `~/.config/service.toml`. When a service is referenced by name it will be resolved to a file in the current domain using the defined reverse domains. Services cannot be referenced by name only if no reverse domains are defined.

Example configuration:

```
reverse-domains: [
  "com.bar.foo",
  "org.bat.baz"
]
```


## License

service is released under the [MIT License](./LICENSE)
