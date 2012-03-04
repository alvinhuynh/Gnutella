#!/usr/bin/python
# CS 114 Gnutella Project

import socket
import sys
import os
import re

from uuid import getnode as getmac
from urllib2 import urlopen

from twisted.internet import reactor, protocol, stdio 
from twisted.protocols import basic
from twisted.web.server import Site
from twisted.web.static import File
#from twisted.web import client

"""
GLOBAL DATA
"""
connections = []
listener = None
nodeID = None
files = []
directory = None
logPath = None
logFile = None
IP = None
port = 0
serverPort = None
initiating = True
MAX_CONNS = 3
msgID = 0
msgRoutes = {}
netData = []

"""
GNUTELLA TWISTED CLASSES
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
    writeLog("Connected to {0}:{1}\n".format(peer.host, peer.port))
    if self.initiator:
      self.sendLine("GNUTELLA CONNECT/0.4\n\n")
      writeLog("Sending GNUTELLA CONNECT to {0}:{1}\n".format(peer.host, peer.port))
    host = self.transport.getHost()
    global IP
    IP = host.host

  def connectionLost(self, reason):
    connections.remove(self)
    peer = self.transport.getPeer()
    writeLog("Disconnected with {0}:{1}--{2}\n".format(peer.host, peer.port, reason))

  def dataReceived(self, data):
    peer = self.transport.getPeer()
    if(data.startswith("GNUTELLA CONNECT")):
      writeLog("Received GNUTELLA CONNECT from {0}:{1}\n".format(peer.host, peer.port))
      if(len(connections) <= MAX_CONNS):
        self.sendLine("GNUTELLA OK\n\n")
        writeLog("Sending GNUTELLA OK to {0}:{1}\n".format(peer.host, peer.port))
      else:
        self.sendLine("WE'RE OUT OF NUTELLA\n")
        writeLog("Sending WE'RE OUT OF NUTELLA to {0}:{1}\n".format(peer.host, peer.peer))
    elif (self.initiator and not self.verified):
      if(data.startswith("GNUTELLA OK")):
        writeLog("Connection with {0}:{1} verified\n".format(peer.host, peer.port))
        self.verified = True
        self.sendPing()
      else:
        writeLog("Connection with {0}:{1} rejected\n".format(peer.host, peer.port))
        reactor.stop()
    else:
      writeLog("\nIncoming message: {0}\n".format(data))
      message = data.split('&', 3)
      msgid = message[0]
      pldescrip = int(message[1])
      ttl = int(message[2])
      payload = message[3]
      if(pldescrip == 0):
        writeLog("Received PING: msgid={0} ttl={1}\n".format(msgid, ttl))
        self.handlePing(msgid, ttl)
      elif(pldescrip == 1):
        writeLog("Received PONG: msgid={0} payload={1}\n".format(msgid, payload))
        self.handlePong(msgid, payload)
      elif(pldescrip == 80):
        writeLog("Received Query: msgid={0} ttl={1} query={2}\n".format(msgid, ttl, payload))
        self.handleQuery(msgid, ttl, payload)
      elif(pldescrip == 81):
        writeLog("Received QueryHit: msgid={0} payload={1}\n".format(msgid, payload))
        self.handleQueryHit(msgid, payload)

  def buildHeader(self, descrip, ttl):
    global msgID
    header = "{0}{1:02}".format(nodeID, msgID)
    msgID += 1
    if(msgID > 99):
      msgID = 0
    return "{0}&{1}&{2}&".format(header, descrip, ttl) 

  def sendPing(self, msgid=None, ttl=7):
    if(ttl <= 0):
      return
    if msgid:
      message = "{0}&{1}&{2}&".format(msgid, "00", ttl)
      writeLog("Forwarding PING: {0}\n".format(message))
    else:
      message = self.buildHeader("00", ttl)
      writeLog("Sending PING: {0}\n".format(message))
    for cn in connections:
      if(msgid == None or cn != self):
        cn.transport.write(message)

  def sendPong(self, msgid, payload=None):
    nfiles = 0
    nkb = 0
    global port
    IP = self.transport.getHost().host
    header = "{0}&{1}&{2}&".format(msgid, "01", 7)
    if payload:
      message = "{0}{1}".format(header, payload)
      writeLog("Forwarding PONG: {0}\n".format(message))
    else: 
      message = "{0}{1}&{2}&{3}&{4}".format(header, port, IP, nfiles, nkb)
      writeLog("Sending PONG: {0}\n".format(message))
    global msgRoutes
    msgRoutes[msgid].transport.write(message)

  def handlePing(self, msgid, ttl):
    #send pong, store data, forward ping
    global msgRoutes
    if msgid in msgRoutes.keys():
      return
    msgRoutes[msgid] = self
    self.sendPong(msgid)
    self.sendPing(msgid, ttl-1)

  def handlePong(self, msgid, payload):
    #store data
    global nodeID
    if(msgid.startswith(nodeID)):
      #TODO: store info, make new conn if necessary
      global netData
      netData.append(payload.split('&'))
    else:
      self.sendPong(msgid, payload)

  def sendQuery(self, query, msgid=None, ttl=7):
    if(ttl <= 0):
      return
    if(msgid):
      header = "{0}&80&{1}&".format(msgid, ttl)
    else:
      header = self.buildHeader(80, ttl)
    message = "{0}{1}".format(header, query)
    global connections
    for cn in connections:
      if(msgid == None or cn != self):
        cn.transport.write(message)

  def sendQueryHit(self, msgid, query=None, payload=None):
    header = "{0}&81&7&".format(msgid)
    global msgRoutes
    if msgid not in msgRoutes.keys():
      return
    if payload:
      message = "{0}{1}".format(header, payload)
    else:
      global IP
      global serverPort
      message = "{0}{1}&{2}&{3}".format(header, serverPort, IP, query)
    msgRoutes[msgid].transport.write(message)

  def handleQuery(self, msgid, ttl, query):
    global msgRoutes
    if msgid in msgRoutes.keys():
      return
    msgRoutes[msgid] = self
    global directory
    filepath = os.path.join(directory, query)
    if os.path.isfile(filepath):
      self.sendQueryHit(msgid, query=query)
      writeLog("File found: {0}; Sending QueryHit\n".format(query))
    else:
      self.sendQuery(query, msgid, ttl-1)
      writeLog("Forwarding Query: {0} {1}".format(query, msgid))

  def handleQueryHit(self, msgid, payload):
    global nodeID
    if(msgid.startswith(nodeID)):
      info = payload.split('&', 2)
      port = info[0]
      ip = info[1]
      query = info[2]
      print "Found port, ip, file: ", info
      global directory
      filepath = os.path.join(directory, query) 
      if not os.path.isfile(filepath):
        printLine("Getting file \"{0}\" from {1}:{2}".format(query, ip, port)) 
        reactor.callInThread(self.getFile, port, ip, query, filepath)
    else:
      self.sendQueryHit(msgid, payload=payload)

  def getFile(self, port, ip, query, filepath):
    request = os.path.join(port, query)
    url = "http://{0}:{1}".format(ip, request)
    fp = open(filepath, "w")
    fp.write(urlopen(url).read())
    fp.close()


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
    writeLog("Trying to connect to {0}:{1}\n".format(self.host, self.port))

#  def clientConnectionLost(self, transport, reason):
    #reactor.stop()
#    print "Disconnected with {0}:{1}".format(self.host, self.port)

  def clientConnectionFailed(self, transport, reason):
    writeLog("Retrying connection with %s:%s\n" % (transport.host, transport.port))
    #protocol.ReconnectingClientFactory.clientConnectionFailed(self, transport, reason)

"""
GLOBAL HELPER FUNCTIONS
"""
def readInput():
  global connections
  print "Requests files with \"GET [filename];\""
  pattern = re.compile("GET\s+(.+);$")
  while(1):
    request = raw_input()
    match = pattern.match(request)
    if(match):
      query = match.group(1)
      if (len(connections) > 0):
        connections[0].sendQuery(query)
      else:
        print "No other nodes in network at the moment" 
    elif(request.startswith("QUIT")):
      return
    else:
      print "Requests must be in the format \"GET [filename];\"\n"

def writeLog(line):
  global logFile
  logFile = open(logPath, "a")
  logFile.write(line)
  logFile.close()

def printLine(line):
  print line
  writeLog("{0}\n".format(line))

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

  if directory:
    #Set up directories and log file
    if not os.path.isdir(directory):
      os.makedirs(directory)
    logPath = os.path.join(directory,"output.log")
    open(logPath, "w").close() #Create or empty current log file
#    logFile = open(os.path.join(directory, "output.log"), "w")
    directory = os.path.join(directory, 'files')
    if not os.path.exists(directory):
      os.makedirs(directory)
    print "Run \"tail -f {0}\" in another terminal to see output".format(logPath)
    printLine("Using directory: {0}".format(directory))

    #Set up Twisted clients
    if(targetIP and targetPort):
      reactor.connectTCP(targetIP, targetPort, GnutellaFactory(initiating))
    listener = GnutellaFactory()
    usedPort = reactor.listenTCP(port, listener)
    host = usedPort.getHost()
    IP = host.host
    port = host.port
    nodeID = "{0}{1:05}".format(getmac(), port)
    printLine("IP address: {0}:{1}".format(host.host, host.port))
    resource = File(directory)
    fileServer = reactor.listenTCP(0, Site(resource))
    serverPort = fileServer.getHost().port
    printLine("File serving port: {0}".format(serverPort))
    printLine("Node ID: {0}".format(nodeID))
    reactor.callInThread(readInput)
    reactor.run()
    logFile.close()
  else:
    print "Must give a directory path"
