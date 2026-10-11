#!/usr/bin/env python3
"""Tiny TCP proxy for the Atmosphere gdbstub.

Useful when the route to the console goes through a VPN or another interface:
the outgoing connection can be bound to a chosen local address.

  python gdbproxy.py <console-ip> [--listen 127.0.0.1:22225] [--src <your-lan-ip>]

Then point gdb / nwn2dbg.py at 127.0.0.1:22225.
"""
import argparse
import socket
import threading


def pipe(a, b):
    try:
        while True:
            d = a.recv(65536)
            if not d:
                break
            b.sendall(d)
    except OSError:
        pass
    for s in (a, b):
        try:
            s.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('console', help='console IP')
    ap.add_argument('--port', type=int, default=22225, help='gdbstub port on the console')
    ap.add_argument('--listen', default='127.0.0.1:22225')
    ap.add_argument('--src', default='', help='local address to connect from, e.g. your Wi-Fi IP')
    a = ap.parse_args()
    host, port = a.listen.rsplit(':', 1)
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, int(port)))
    srv.listen(4)
    print(f'proxy {a.listen} -> {a.console}:{a.port}', flush=True)
    while True:
        c, _ = srv.accept()
        r = socket.socket()
        if a.src:
            r.bind((a.src, 0))
        r.settimeout(10)
        r.connect((a.console, a.port))
        r.settimeout(None)
        print('connected', flush=True)
        threading.Thread(target=pipe, args=(c, r), daemon=True).start()
        threading.Thread(target=pipe, args=(r, c), daemon=True).start()


if __name__ == '__main__':
    main()
