#!/usr/bin/python
# CS 114 Gnutella Project

import socket
import sys
import os

from uuid import getnode as getmac

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
MAX_CONNS = 3
msgID = 0
msgRoutes = {}
netData = []

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
    connections.append(self)
    peer = self.transport.getPeer()
    print "Connected to {0}:{1}".format(peer.host, peer.port)
    if self.initiator:
      self.sendLine("GNUTELLA CONNECT/0.4\n\n")
    host = self.transport.getHost()
    global IP
    IP = host.host

  def connectionLost(self, reason):
    connections.remove(self)
    peer = self.transport.getPeer()
    print "Disconnected with {0}:{1}".format(peer.host, peer.port)

  def dataReceived(self, data):
    print "Data received: {0}".format(data)
    peer = self.transport.getPeer()
    if(data.startswith("GNUTELLA CONNECT")):
      if(len(connections) <= MAX_CONNS):
        self.sendLine("GNUTELLA OK\n\n")
      else:
        self.sendLine("WE'RE OUT OF NUTELLA\n")
    elif (self.initiator and not self.verified):
      if(data.startswith("GNUTELLA OK")):
        print "Connection with {0}:{1} verified".format(peer.host, peer.port)
        self.verified = True
        self.sendPing(7)
      else:
        print "Connection with {0}:{1} rejected".format(peer.host, peer.port)
        reactor.stop()
    else:
      message = data.split('&', 3)
      msgid = message[0]
      pldescrip = int(message[1])
      ttl = int(message[2])
      payload = message[3]
      if(pldescrip == 0):
        self.handlePing(msgid, ttl)
      elif(pldescrip == 1):
        self.handlePong(msgid, payload)
      elif(pldescrip == 80):
        self.handleQuery
      elif(pldescrip == 81):
        self.handleQueryHit

  def buildHeader(self, descrip, ttl):
    global msgID
    header = "{0}{1:02}".format(nodeID, msgID)
    msgID += 1
    if(msgID > 99):
      msgID = 0
    return "{0}&{1}&{2}&".format(header, descrip, ttl) 

  def sendPing(self, ttl, msgid=None):
    if(ttl <= 0):
      return
    if msgid:
      message = "{0}&{1}&{2}&".format(msgid, "00", ttl)
    else:
      message = self.buildHeader("00", ttl)
    for cn in connections:
      if(msgid == None or cn != self):
        cn.transport.write(message)
      else:
        print "skipped one :)"

  def sendPong(self, msgid, payload=None):
    nfiles = 0
    nkb = 0
    global port
    IP = self.transport.getHost().host
    header = "{0}&{1}&{2}&".format(msgid, "01", 7)
    if payload:
      message = "{0}{1}".format(header, payload)
    else: 
      message = "{0}{1}&{2}&{3}&{4}".format(header, port, IP, nfiles, nkb)
    global msgRoutes
    msgRoutes[msgid].transport.write(message)


  def handlePing(self, msgid, ttl):
    #send pong, store data, forward ping
    global msgRoutes
    if msgid in msgRoutes.keys():
      return
    msgRoutes[msgid] = self
    self.sendPong(msgid)
    self.sendPing(ttl-1, msgid)

  def handlePong(self, msgid, payload):
    #store data
    global nodeID
    if(msgid.startswith(nodeID)):
      print "I OWN THIS PONG: ", msgid, payload
      #TODO: store info, make new conn if necessary
      global netData
      netData.append(payload.split('&'))
      print netData
    else:
      self.sendPong(msgid, payload)



class GnutellaFactory(protocol.ReconnectingClientFactory):

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

#  def clientConnectionLost(self, transport, reason):
    #reactor.stop()
#    print "Disconnected with {0}:{1}".format(self.host, self.port)

  def clientConnectionFailed(self, transport, reason):
    print "Retrying connection to %s:%s" % (transport.host, transport.port)
    #protocol.ReconnectingClientFactory.clientConnectionFailed(self, transport, reason)



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
  nodeID = "{0}{1:05}".format(getmac(), port)
  print "IP address: {0}:{1}".format(host.host, host.port)
  reactor.run()
  logFile.close()
