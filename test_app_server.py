#encoding:utf-8

import socket


s = socket.socket()
s.connect(("127.0.0.1", 27800))

s.send('hi')
s.close()
