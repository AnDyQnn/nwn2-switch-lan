#!/usr/bin/env python3
"""Check whether an NWN2 server answers on the LAN (UDP 5121).

  python lanprobe.py <host-ip> [--port 5121] [--src <your-lan-ip>]

Sends the NWN LAN query packets BNES (session) and BNXI (extended info).
REPLY  - the server is listening (reply contains server and module name)
closed - nothing listens on that port (ICMP port unreachable)
"""
import argparse
import socket

ap = argparse.ArgumentParser()
ap.add_argument('host')
ap.add_argument('--port', type=int, default=5121)
ap.add_argument('--src', default='')
a = ap.parse_args()
for q in (b'BNES\x00\x14\x00', b'BNXI\x00\x14\x00'):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if a.src:
        s.bind((a.src, 0))
    s.settimeout(2)
    try:
        s.sendto(q, (a.host, a.port))
        d, _ = s.recvfrom(4096)
        print('REPLY', q[:4].decode(), d[:80])
    except ConnectionResetError:
        print(q[:4].decode(), 'closed (nothing listening)')
    except socket.timeout:
        print(q[:4].decode(), 'no reply (port open or filtered)')
    finally:
        s.close()
