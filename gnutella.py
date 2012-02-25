#!/usr/bin/python
# CS 114 Gnutella Project

import socket
import sys

"""
GLOBAL DATA
"""
connections = []
nodeID = None
data = []
directory = None
IP = None
port = 0

"""
RECEIVE FUNCTIONS
"""
def decode_message():
  pass


"""
SEND FUNCTIONS
"""
def send_ping():
  pass

def send_pong():
  pass

def send_query():
  pass

def send_query_hit():
  pass

def push_file():
  pass

def request_conn():
  pass

def setup_conn():
  pass

"""
MAIN FUNCTION
"""
def main():
  args = sys.argv[1:]
  hasIP = False
  hasPort = False
  #must redeclare variables as globals within function
  #otherwise, python recreates a local variable 
  global directory
  global IP
  global port
  for arg in args:
    if(arg == "-i"):
      hasIP = True
    elif(arg == "-p"):
      hasPort = True
    elif(hasIP):
      IP = arg
      hasIP = False
    elif(hasPort):
      port = int(arg)
      hasPort = False
    else:
      directory = arg

  print "directory: {0}".format(directory)
  print "IP: {0}". format(IP)
  print "Port: {0}". format(port)


if __name__=="__main__":
  main()
