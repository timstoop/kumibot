# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, defer
from twisted.python import log

# local imports
from quest import Quest

# system imports
import time
import sys


class MessageLogger:
    """
    An independent logger class (because separation of application
    and protocol logic is a good thing).
    """
    def __init__(self, file):
        self.file = file

    def log(self, message):
        """Write a message to the file."""
        timestamp = time.strftime("[%H:%M:%S]", time.localtime(time.time()))
        msg = '%s %s\n' % (timestamp, message)
        self.file.write(msg)
        self.file.flush()
        log.msg(message)

    def close(self):
        self.file.close()


class QuestBot(irc.IRCClient):
    """An IRC bot that implements questing."""

    nickname = "RPGbot"
    channel = {}

    def connectionMade(self):
        irc.IRCClient.connectionMade(self)
        self.logger = MessageLogger(open(self.factory.filename, "a"))
        self.logger.log("[connected at %s]" %
                        time.asctime(time.localtime(time.time())))

    def connectionLost(self, reason):
        irc.IRCClient.connectionLost(self, reason)
        self.logger.log("[disconnected at %s]" %
                        time.asctime(time.localtime(time.time())))
        self.logger.close()

    # callbacks for events

    def signedOn(self):
        """Called when bot has succesfully signed on to server."""
        self.join(self.factory.channel)

    def joined(self, channel):
        """This will get called when the bot joins the channel."""
        self.logger.log("[I have joined %s]" % channel)
        self.names(channel).addCallback(self._log_channel_users).addCallback(
            self.init_quest, channel=channel)

    def privmsg(self, user, channel, msg):
        """This will get called when the bot receives a message."""
        user = user.split('!', 1)[0]

        # Check to see if they're sending me a private message
        if channel == self.nickname:
            self.logger.log(">%s< %s" % (user, msg))
            self.handle_query(user, msg)
            # Make sure we return asap
            self.logger.log(">%s< answer returned." % (self.nickname))
            return

        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            self.logger.log("<%s> %s" % (user, msg))
            reply = "%s: I am a log bot" % user
            self.msg(channel, reply)
            self.logger.log("<%s> %s" % (self.nickname, reply))

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        self.logger.log("* %s %s" % (user, msg))

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
        self.logger.log("%s is now known as %s" % (old_nick, new_nick))

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

    # Bot functionality

    def init_quest(self, users, channel):
        q = Quest(self.logger)
        for user in users:
            if user == self.nickname:
                continue
            q.create_user(user)

    def handle_query(self, user, msg):
        if msg.startswith('help'):
            with open('help/help.txt', 'r') as helpfile:
                for line in helpfile:
                    self.msg(user, line)
        else:
            self.msg(user, "Sorry, I don't get what you want. Try 'help'.")

    # Helper functions

    def _log_error(self, msg):
        self.logger.log("Something went wrong: %s" % msg)

    def _log_channel_users(self, users):
        self.logger.log("Users in channel: %s" % users)
        return users


class QuestBotFactory(protocol.ClientFactory):
    """A factory for QuestBots.

    A new protocol instance will be created each time we connect to the server.
    """

    def __init__(self, channel, filename):
        self.channel = channel
        self.filename = filename

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
    # initialize logging
    log.startLogging(sys.stdout)

    # create factory protocol and application
    f = QuestBotFactory(sys.argv[1], sys.argv[2])

    # connect factory to this host and port
    reactor.connectTCP("irc.kumina.nl", 6667, f)

    # run bot
    reactor.run()
