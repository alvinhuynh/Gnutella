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
initiating = True


"""
TWISTED CLASSES
"""
class GnutellaProtocol(basic.LineReceiver):
  def __init__(self):
    self.output = None
    self.normalizeNewlines = True
    self.initiator = False
    self.verified = True

  def setInitiator(self):
    self.initiator = True
    self.verified = False

  def connectionMade(self):
    #inputForwarder = DataForwardingProtocol()
    #inputForwarder.output = self.transport
    #inputForwarder.normalizeNewlines = True
    #stdioWrapper = stdio.StandardIO(inputForwarder)
    #self.output = stdioWrapper
    peer = self.transport.getPeer()
    print "Connected to {0}:{1}".format(peer.host, peer.port)
    if self.initiator:
      self.sendLine("GNUTELLA CONNECT/0.4\n\n")
    #all_server.append(self)

  def dataReceived(self, data):
    print "Data received: {0}".format(data)
    peer = self.transport.getPeer()
    if(data.startswith("GNUTELLA CONNECT")):
      self.sendLine("GNUTELLA OK\n\n")
    elif (self.initiator and not self.verified):
      if(data.startswith("GNUTELLA OK")):
        print "Connection with {0}:{1} verified".format(peer.host, peer.port)
        self.verified = True
      else:
        print "Connection with {0}:{1} rejected".format(peer.host, peer.port)
        self.transport.loseConnection()


class GnutellaFactory(protocol.ReconnectingClientFactory):
  #protocol = GnutellaProtocol

  def __init__(self, isInitiator=False):
    self.initiator = False
    if isInitiator:
      self.initiator = True

  def buildProtocol(self, addr):
    prot = GnutellaProtocol()
    if self.initiator:
      prot.setInitiator()
    return prot
 
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
if __name__=="__main__":
  args = sys.argv[1:]
  hasIP = False
  hasPort = False
  #must redeclare variables as globals within function
  #otherwise, python recreates a local variable 
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
  logFile = open("output.log", "w")
  if(targetIP and targetPort):
    reactor.connectTCP(targetIP, targetPort, GnutellaFactory(initiating))
  usedPort = reactor.listenTCP(port, GnutellaFactory())
  host = usedPort.getHost()
  IP = host.host
  port = host.port
  print "IP address: {0}:{1}".format(host.host, host.port)
  reactor.run()
  logFile.close()
