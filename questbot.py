# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, defer
from twisted.python import log

# local imports
from quest import Quest

# system imports
import time
import sys
import logging


class QuestBot(irc.IRCClient):
    """An IRC bot that implements questing."""

    nickname = "kumina"
    channel = {}

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        log.msg("[connected at %s]" %
                time.asctime(time.localtime(time.time())))

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        log.msg("[disconnected at %s]" %
                time.asctime(time.localtime(time.time())))

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        log.msg("[I have joined %s]" % channel)
        self.names(channel).addCallback(self._log_channel_users).addCallback(
            self.init_quest, channel=channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]

        # Check to see if they're sending me a private message
        if channel == self.nickname:
            log.msg(">%s< %s" % (user, msg))
            self.handle_query(user, msg)
            # Make sure we return asap
            log.debug(">%s< answer returned." % (self.nickname))
            return

        if channel in self.channel:
            log.debug("%s <%s> %s" % (channel, user, msg))

        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            log.msg("#%s <%s> %s" % (channel, user, msg))
            reply = "%s: I am a log bot" % user
            self.msg(channel, reply)
            log.msg("#%s <%s> %s" % (channel, self.nickname, reply))

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        log.debug("* %s %s" % (user, msg))

    # irc commands

    def names(self, channel):
        channel = channel.lower()
        d = defer.Deferred()
        if channel not in self.channel:
            self.channel[channel] = {}
        self.channel[channel]['namecallback'] = d
        self.channel[channel]['users'] = []
        self.sendLine("NAMES %s" % channel)
        return d

    # irc callbacks

    def irc_NICK(self, prefix, params):
        """Called when an IRC user changes their nickname."""
        old_nick = prefix.split('!')[0]
        new_nick = params[0]
        log.msg("%s is now known as %s" % (old_nick, new_nick))

    def irc_RPL_NAMREPLY(self, prefix, params):
        channel = params[2].lower()
        nicklist = params[3].split(' ')

        if channel not in self.channel:
            return

        n = self.channel[channel]['users']
        n += nicklist

    def irc_RPL_ENDOFNAMES(self, prefix, params):
        channel = params[1].lower()

        if (channel not in self.channel) or ('namecallback' not in
                                             self.channel[channel]):
            return

        names = self.channel[channel]['users']
        self.channel[channel]['namecallback'].callback(names)

        del self.channel[channel]['namecallback']

    def userJoined(self, user, channel):
        log.msg("User '%s' joined channel '%s'." % (user, channel))
        self.quest.create_user(user)

    def userLeft(self, user, channel):
        log.msg("User '%s' left channel '%s'." % (user, channel))
        self.quest.hibernate_user(user)

    # Bot functionality

    def init_quest(self, users, channel):
        self.quest = Quest()
        for user in users:
            if user == self.nickname or user == ("@%s" % (self.nickname)):
                continue
            self.quest.create_user(user)

    def handle_query(self, user, msg):
        cmd = msg.split()[0]

        if hasattr(self, 'handle_cmd_%s' % cmd):
            getattr(self, 'handle_cmd_%s' % cmd)(user, msg)
        else:
            self.msg(user, "Sorry, I don't get what you want. Try 'help'.")

    def handle_cmd_help(self, user, msg):
        # Return helpful information
        with open('help/help.txt', 'r') as helpfile:
            for line in helpfile:
                self.msg(user, line)

    # Helper functions

    def _log_error(self, msg):
        log.msg("Something went wrong: %s" % msg)

    def _log_channel_users(self, users):
        log.msg("Users in channel: %s" % users)
        return users


class QuestBotFactory(protocol.ClientFactory):
    """A factory for QuestBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel):
        self.channel = channel

    def buildProtocol(self, addr):
        p = QuestBot()
        p.factory = self
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    channel = sys.argv[1]
    logfile = sys.argv[2]
    # initialize logging, we use the default logging module, but want to allow
    # twisted to write there as well. Found the solution on their own page:
    # http://twistedmatrix.com/documents/current/core/howto/logging.html
    observer = log.PythonLoggingObserver()
    observer.start()
    formatstring = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
    logging.basicConfig(level=logging.DEBUG,
                        format=formatstring,
                        datefmt='%m-%d %H:%M',
                        filename=logfile,
                        filemode='w')
    # We also want to log directly to the console
    console = logging.StreamHandler()
    formatter = logging.Formatter(formatstring)
    console.setFormatter(formatter)
    # add the handler to the root logger
    logging.getLogger('').addHandler(console)

    # create factory protocol and application
    f = QuestBotFactory(channel)

    # connect factory to this host and port
    reactor.connectTCP("irc.kumina.nl", 6667, f)

    # run bot
    reactor.run()
