
# Taken from: http://code.google.com/p/coilmq/wiki/TwistedServerExample
"""
Reference classes to implement the socket server using the Twisted framework.

Note that while this implementation will work (function), the CoilMQ core is
not designed with an asynchronous framework in mind.  This means that if you're
using computationally-intensive or blocking backends (e.g. database queue), they will
block all other client traffic.

That being the case, this module is provided primarily as an example or a starting
point for others to develop a Twisted-based version of this software ;)
"""
import logging

from twisted.internet.protocol import Protocol, Factory

from coilmq.server import StompConnection
from coilmq.engine import StompEngine
from coilmq.util.buffer import StompFrameBuffer

class StompProtocol(Protocol, StompConnection):
    """
    Subclass of C{twisted.internet.protocol.Protocol} for handling STOMP communications.
    
    An instance of this class will be created for each connecting client. 
    
    @ivar buffer: A StompBuffer instance which buffers received data (to ensure we deal with
                    complete STOMP messages.
    @type buffer: C{stomper.stompbuffer.StompBuffer}
    
    @ivar engine: The STOMP protocol engine.
    @type engine: L{coilmq.engine.StompEngine}
    """
    def __init__(self, queue_manager, topic_manager):
        self.log = logging.getLogger('%s.%s' % (self.__class__.__module__, self.__class__.__name__))
        self.log.debug("Initializing StompProtocol.")
        self.buffer = StompFrameBuffer()
        self.engine = StompEngine(connection=self,
                                  authenticator=None, # FIXME: Add the authenticator
                                  queue_manager=queue_manager,
                                  topic_manager=topic_manager) 

    def connectionLost(self, reason):
        Protocol.connectionLost(self, reason)
        self.log.debug("Connection lost.")
        self.engine.unbind()

    def connectionMade(self):
        self.log.debug("Connection made.")

    def dataReceived(self, data):
        """ Twisted calls this method when data is received.
         
        Note: The data may not be not be a complete frame or may be more than
        one frame.
        """
        self.log.debug("Data received: %s" % data)
        self.buffer.append(data)
        
        # print '%r' % self.buffer
        
        for frame in self.buffer:
            self.log.debug("Processing frame: %s" % frame)
            self.engine.process_frame(frame)
    
    def send_frame(self, frame):
        """ Sends a frame to connected socket client.
        
        (Sorry, Twisted, our code is PEP-8.)
        
        @param frame: The frame to send.
        @type frame: L{coilmq.frame.StompFrame}
        """
        self.transport.write(frame.pack())
     
class StompFactory(Factory):
    """
    Subclass of C{twisted.internet.protocol.Factory} to handle new connections with 
    instances of L{StompProtocol}.
    
    @ivar queue_manager: The queue manager to use.
    @type queue_manager: L{coilmq.queue.QueueManager}
    
    @ivar topic_manager: The topic manager to use.
    @type topic_manager: L{coilmq.topic.TopicManager}
    """    
    protocol = StompProtocol
    
    def __init__(self, queue_manager, topic_manager):
        self.queue_manager = queue_manager
        self.topic_manager = topic_manager
        
    def buildProtocol(self, addr):
        p = self.protocol(queue_manager=self.queue_manager, topic_manager=self.topic_manager)
        p.factory = self
        return p
