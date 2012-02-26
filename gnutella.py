#!/usr/bin/python
# CS 114 Gnutella Project

import socket
import sys
import os

from twisted.internet import reactor, protocol, stdio 
from twisted.protocols import basic
#from twisted.web import client

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
TWISTED CLASSES
"""
class GnutellaProtocol(basic.LineReceiver):
  def lineReceived(self, line):
    print "Line received: {0}".format(line)


class GnutellaFactory(protocol.ServerFactory):
  protocol = GnutellaProtocol




class DataForwardingProtocol(protocol.Protocol):
  def __init__(self):
    self.output = None
    self.normalizeNewlines = False


class StdioProxyProtocol(DataForwardingProtocol):
  def connectionMade(self):
    inputForwarder = DataForwardingProtocol()
    inputForwarder.output = self.transport
    inputForwarder.normalizeNewlines = True
    stdioWrapper = stdio.StandardIO(inputForwarder)
    self.output = stdioWrapper
    peer = self.transport.getPeer()
    print "Connected to {0}:{1}".format(peer.host, peer.port)
    #all_server.append(self)


class StdioProxyFactory(protocol.ReconnectingClientFactory):
  protocol = StdioProxyProtocol

  def startedConnecting(self, connector):
    self.host = connector.host
    self.port = connector.port
    print "Trying to connect to {0}:{1}".format(self.host, self.port)

  def clientConnectionLost(self, transport, reason):
    #reactor.stop()
    print "Disconnected with {0}:{1}".format(self.host, self.port)

  def clientConnectionFailed(self, transport, reason):
    print "Trying to connect to %s:%s" % (transport.host, transport.port)
    protocol.ReconnectingClientFactory.clientConnectionFailed(self, transport, reason)


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
  targetIP = None
  targetPort = None
  for arg in args:
    if(arg == "-i"):
      hasIP = True
    elif(arg == "-p"):
      hasPort = True
    elif(hasIP):
      targetIP = arg
      hasIP = False
    elif(hasPort):
      targetPort = int(arg)
      hasPort = False
    else:
      directory = arg

  print "directory: {0}".format(directory)

  #Set up Twisted client and log file
  global logFile 
  logFile = open("output.log", "w")
  if(targetIP and targetPort):
    reactor.connectTCP(targetIP, targetPort, StdioProxyFactory())
  usedPort = reactor.listenTCP(port, GnutellaFactory())
  host = usedPort.getHost()
  IP = host.host
  port = host.port
  print "IP address: {0}:{1}".format(host.host, host.port)
  reactor.run()
  logFile.close()


if __name__=="__main__":
  main()
