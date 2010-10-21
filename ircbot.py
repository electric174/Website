# Copyright (c) 2009 Steven Robertson.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 or
# later, as published by the Free Software Foundation.

NAME="Google_Code_RSS_IRC_Bridge_Bot"
VERSION="0.1"

import simplejson

from twisted.internet import reactor, protocol, task
from twisted.web import server, resource
from twisted.words.protocols import irc

import re
import sys
import urllib
import urllib2

class AnnounceBot(irc.IRCClient):
  username = "%s-%s" % (NAME, VERSION)
  sourceURL = "http://strobe.cc/"

  # I am a terrible person.
  instance = None

  # Intentionally 'None' until we join a channel
  channel = None

  # Prevent flooding
  lineRate = 3

  def signedOn(self):
    self.join(self.factory.channel)
    AnnounceBot.instance = self

  def joined(self, channel):
    self.channel = self.factory.channel

  def left(self, channel):
    self.channel = None

  def trysay(self, msg):
    """Attempts to send the given message to the channel."""
    if self.channel:
      try:
        self.say(self.channel, msg)
        return True
      except:
        print 'Failed to send message'

class AnnounceBotFactory(protocol.ReconnectingClientFactory):
  protocol = AnnounceBot
  def __init__(self, channel):
    self.channel = channel

  def clientConnectionFailed(self, connector, reason):
    print "connection failed:", reason
    reactor.stop()

class WebHook(resource.Resource):
  isLeaf = True

  def render_GET(self, request):
    return 'foo'

  def render_POST(self, request):
    if request.path == '/commit':
      body = request.content
      if body:
        json = simplejson.load(body)
        for r in json['revisions']:
          url = 'http://code.google.com/p/clementine-player/source/detail?r=%d' % r['revision']
          try:
            data = urllib.urlencode({'url':url})
            request = urllib2.urlopen('http://goo.gl/api/shorten', data)
            url_json = simplejson.load(request)
            if 'short_url' in url_json:
              short_url = url_json['short_url']
              r['message'] = '(%s) %s' % (short_url, r['message'])
          except urllib2.URLError, ValueError:
            pass

          message = '\x033%s\x03 \x02\x037r%d\x03\x02 %s' % (
              r['author'], r['revision'], r['message'].rstrip().replace('\n', ' '))
          AnnounceBot.instance.trysay(message)
    return 'ok'

if __name__ == '__main__':
  # All per-project customizations should be done here

  AnnounceBot.nickname = 'clementine-bot'
  fact = AnnounceBotFactory("#clementine")
  reactor.connectTCP('chat.freenode.net', 6667, fact)

  site = server.Site(WebHook())
  reactor.listenTCP(8080, site)

  reactor.run()
