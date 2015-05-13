#!/usr/bin/env python
import os
import socketserver
import threading
import random
import time

import json

import api

def readuntil(reader, ch):
  l = []
  c = reader.recv(1).decode('utf-8')
  while c != ch:
    l.append(c)
    c = reader.recv(1).decode('utf-8')
  return ''.join(l)

class incoming(socketserver.StreamRequestHandler):
  def handle(self):
    account_name = readuntil(self.request, '\n')
    pid = readuntil(self.request, '\n')
    key = readuntil(self.request, '\n')

    try:
      account_data = api.user.get_user(account_name)
      tid = account_data['tid']
      uid = account_data['uid']
      result = api.problem.submit_key(tid=tid, pid=pid, key=key, uid=uid)
      if (result['correct']):
        self.request.send(b'\xff\xff\xff\xff')
      else:
        self.request.send(b'\x00\x00\x00\x00')
    except:
      self.request.send(b'\x00\x00\x00\x00')
    self.request.close()

class ReusableTCPServer(socketserver.ForkingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

if __name__ == "__main__":
  HOST = '0.0.0.0'
  PORT = 8891
  server = ReusableTCPServer((HOST, PORT), incoming)
  server.serve_forever()
