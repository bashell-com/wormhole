Wormhole
========

*(forked from [https://github.com/devunt/warp](https://github.com/devunt/warp))*

Asynchronous IO HTTP and HTTPS Proxy on Python 3.5

Dependency
----------

*  python >= 3.5.0


Docker Image Usage
------------------

Run without authentication

```bash
$ docker pull bashell/wormhole
$ docker run -d -p 8800:8800 bashell/wormhole
```

Run with authentication

-   Create an empty directory on your docker host
-   Create an authentication file contains username and password in
    this format `username:password`
-   Link that directory to the container via option `-v` and also run
    wormhole container with option `-a /path/to/authentication_file`

```bash
$ docker pull bashell/wormhole
$ mkdir -p /path/to/dir
$ echo "user1:password1" > /path/to/dir/wormhole.passwd
$ docker run -d -v /path/to/dir:/opt/wormhole \
  -p 8800:8800 bashell/wormhole \
  -a /opt/wormhole/wormhole.passwd
```


How to install
--------------

You can install **wormhole** using `pip`:

```bash
$ pip install hg+https://bitbucket.org/bashell-com/wormhole
```

Or install from your local clone:

```bash
$ hg clone https://bitbucket.org/bashell-com/wormhole
$ cd wormhole/
$ pip install -e .
```


How to use
----------

1.  run `wormhole` command (or you might need to run `wormhole.py`
    instead if setuptools isn't installed in your system)
    
    ```
    $ wormhole
    ```

2.  set browser's proxy setting to

    http proxy

    :   host: 127.0.0.1 port: 8800


Command help
------------

```bash
$ python wormhole.py --help
```


License
-------

MIT License (included in `wormhole.py`)


Notice
------

*  may not work in
    -   some ISPs
    -   some company firewalls
    -   some school firewalls
    -   some browers (will be fixed later)