#!/usr/bin/python
# -*- coding: utf-8 -*-

VERSION = "v0.1.1 (poc code)"

"""
Copyright (c) 2013 devunt

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

from socket import TCP_NODELAY
from re import compile
from optparse import OptionParser
import logging
import asyncio


REGEX_HOST = compile(r'(^:+):([0-9]{1,5})')
REGEX_CONTENT_LENGTH = compile(r'\r\nContent-Length: ([0-9]+)\r\n')
REGEX_PROXY_CONNECTION = compile(r'\r\nProxy-Connection: (.+)\r\n')
REGEX_CONNECTION = compile(r'\r\nConnection: (.+)\r\n')
REGEX_USER_AGENTS_WITHOUT_PROXY_CONNECTION_HEADER = compile(r'\r\nUser-Agent: .*(Firefox|Opera).+\r\n')

clients = {}

def accept_client(client_reader, client_writer):
    task = asyncio.Task(process_warp(client_reader, client_writer))
    clients[task] = (client_reader, client_writer)

    def client_done(task):
        del clients[task]
        client_writer.close()
        logging.debug('End Connection')

    logging.debug('New Connection')
    task.add_done_callback(client_done)


@asyncio.coroutine
def process_warp(client_reader, client_writer):
    logging.debug('Accept new task')
    cont = ''
    try:
        RECV_MAX_RETRY = 1
        recvRetry = 0
        while True:
            line = yield from client_reader.readline()
            if not line:
                if len(cont) == 0 and recvRetry < RECV_MAX_RETRY:
                    # handle the case when the client make connection but sending data is delayed for some reasons
                    recvRetry += 1
                    yield from asyncio.sleep(0.2)
                    continue
                else:
                    break
            cont += line.decode('utf-8')
            if line == b'\r\n':
                break
        m = REGEX_CONTENT_LENGTH.search(cont)
        if m:
            cl = int(m.group(1))
            ct = cont.split('\r\n\r\n')[1]
            while (len(ct) < cl):
                ct += client_reader.read(1024)
            cont = cont.split('\r\n\r\n')[0] + '\r\n\r\n' + ct
    except:
        pass

    if len(cont) == 0:
        logging.debug('!!! Task reject (empty request)')
        return

    m1 = REGEX_PROXY_CONNECTION.search(cont)
    m2 = REGEX_USER_AGENTS_WITHOUT_PROXY_CONNECTION_HEADER.search(cont)
    if not m1 and not m2:
        logging.debug('!!! Task reject (no Proxy-Connection header)')
        return

    req = cont.split('\r\n')
    if len(req) < 4:
        logging.debug('!!! Task reject (invalid request)')
        return
    head = req[0].split(' ')
    phost = False
    sreq = []
    sreqHeaderEndIndex = 0
    for line in req[1:]:
        headerNameAndValue = line.split(': ', 1)
        if len(headerNameAndValue) == 2:
            headerName, headerValue = headerNameAndValue
        else:
            headerName, headerValue = headerNameAndValue[0], None

        if headerName == "Host":
            phost = headerValue
        elif headerName == "Connection":
            if headerValue.lower() in ('keep-alive', 'persist'):
                sreq.append("Connection: close")    # current version of this program does not support the HTTP keep-alive feature
            else:
                sreq.append(line)
        elif headerName != 'Proxy-Connection':
            sreq.append(line)
            if len(line) == 0 and sreqHeaderEndIndex == 0:
                sreqHeaderEndIndex = len(sreq) - 1
    if sreqHeaderEndIndex == 0:
        sreqHeaderEndIndex = len(sreq)

    m = REGEX_CONNECTION.search(cont)
    if not m:
        sreq.insert(sreqHeaderEndIndex, "Connection: close")

    if not phost:
        phost = '127.0.0.1'
    path = head[1][len(phost)+7:]

    logging.debug('Process - %s' % req[0])

    new_head = ' '.join([head[0], path, head[2]])

    m = REGEX_HOST.search(phost)
    if m:
        host = m.group(1)
        port = int(m.group(2))
    else:
        host = phost
        port = 80
        phost = "%s:80" % host

    try:
        req_reader, req_writer = yield from asyncio.open_connection(host, port, flags=TCP_NODELAY)
        req_writer.write(('%s\r\n' % new_head).encode('utf-8'))
        yield from req_writer.drain()
        yield from asyncio.sleep(0.2)

        req_writer.write(b'Host: ')
        def feed_phost(phost):
            import random
            i = 1
            while phost:
                yield random.randrange(2, 4), phost[:i]
                phost = phost[i:]
                i = random.randrange(2, 5)
        for delay, c in feed_phost(phost):
            yield from asyncio.sleep(delay/10.0)
            req_writer.write(c.encode('utf-8'))
            yield from req_writer.drain()
        req_writer.write(list(map(lambda x: x.encode('utf-8'), [''] + sreq + ['', ''])))
        yield from req_writer.drain()
    except:
        pass

    while True:
        try:
            buf = yield from req_reader.readline()
            if len(buf) == 0:
                break
            client_writer.write(buf)
        except:
            pass

    client_writer.close()
    logging.debug('Task done')


@asyncio.coroutine
def start_warp_server(host, port):
    try:
        yield from asyncio.start_server(accept_client, host=host, port=port)
    except error as e:
        logging.critical('!!! Fail to bind server at [%s:%d]: %s' % (host, port, e.args[1]))
        return 1
    logging.info('Server bound at [%s:%d].' % (host, port))


def main():
    """CLI frontend function.  It takes command line options e.g. host,
    port and provides ``--help`` message.

    """
    parser = OptionParser(description='Simple HTTP transparent proxy',
                          version=VERSION)
    parser.add_option('-H', '--host', default='127.0.0.1',
                      help='Host to listen [%default]')
    parser.add_option('-p', '--port', type='int', default=8800,
                      help='Port to listen [%default]')
    parser.add_option('-v', '--verbose', action="store_true",
                      help='Print verbose')
    options, args = parser.parse_args()
    if not (1 <= options.port <= 65535):
        parser.error('port must be 1-65535')
    if options.verbose:
        lv = logging.DEBUG
    else:
        lv = logging.INFO
    logging.basicConfig(level=lv, format='[%(asctime)s] {%(levelname)s} %(message)s')
    loop = asyncio.get_event_loop()
    try:
        asyncio.async(start_warp_server(options.host, options.port))
        loop.run_forever()
    except KeyboardInterrupt:
        print('bye')
    finally:
        loop.close()


if __name__ == '__main__':
    exit(main())
