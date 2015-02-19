# twisted imports
from twisted.words.protocols import irc
from twisted.internet import reactor, protocol, defer
from twisted.python import log

# local imports
from quest import Quest

# system imports
import time
import logging
import argparse


class QuestBot(irc.IRCClient):
    """An IRC bot that implements questing."""
    channel = {}
    nickname = ''

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
            log.msg(">%s< answer returned." % (self.nickname))
            return

        if channel in self.channel:
            log.msg("%s <%s> %s" % (channel, user, msg))

        # Otherwise check to see if it is a message directed at me
        if msg.startswith(self.nickname + ":"):
            log.msg("Public command received from %s in %s" % (user, channel))
            self.handle_public_query(channel, user, msg)

    def action(self, user, channel, msg):
        """This will get called when the bot sees someone do an action."""
        user = user.split('!', 1)[0]
        log.msg("* %s %s" % (user, msg))

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

    def irc_RPL_WHOISUSER(self, prefix, params):
        log.msg("Received response to whois on %s: %s" % (prefix, params))

    def irc_RPL_WHOISSERVER(self, prefix, params):
        # We ignore this, since it's not important
        pass

    def irc_RPL_WHOISCHANNELS(self, prefix, params):
        # We ignore this, since it's not important
        pass

    def irc_RPL_WHOISIDLE(self, prefix, params):
        # We ignore this, since it's not important
        pass

    def irc_RPL_ENDOFWHOIS(self, prefix, params):
        # We ignore this, since it's not important
        pass

    def irc_PONG(self, prefix, params):
        # Let's ignore this for now.
        pass

    def irc_unknown(self, prefix, command, params):
        # Log all server responses that we do not handle correctly.
        log.msg("Received a response from %s to the command '%s': %s" %
                (prefix, command, params))

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

    def handle_public_query(self, channel, user, msg):
        cmdarray = msg.split()
        cmd = cmdarray[1]
        assert cmdarray[0] == "%s:" % self.nickname

        if hasattr(self, 'handle_pubcmd_%s' % cmd):
            getattr(self, 'handle_pubcmd_%s' % cmd)(channel, user, msg)
        # We do not handle misses here, since that could cause a lot of
        # unneeded replies.

    def handle_cmd_help(self, user, msg):
        # Return helpful information
        with open('help/help.txt', 'r') as helpfile:
            for line in helpfile:
                self.msg(user, line)

    def handle_cmd_whoami(self, user, msg):
        pass

    def handle_pubcmd_help(self, channel, user, msg):
        # Return helpful information, but do it in a query
        self.msg(channel, ("%s: That's a lot of information, sending it in a" +
                 " query.") % user)
        self.handle_cmd_help(user, '')

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

    def __init__(self, channel, nick):
        self.channel = channel
        self.nick = nick

    def buildProtocol(self, addr):
        p = QuestBot()
        p.factory = self
        p.nickname = self.nick
        return p

    def clientConnectionLost(self, connector, reason):
        """If we get disconnected, reconnect to server."""
        connector.connect()

    def clientConnectionFailed(self, connector, reason):
        print "connection failed:", reason
        reactor.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("configfile", help="The configuration file to use.")
    parser.add_argument('-s', '--server', help="The server to connect to.")
    parser.add_argument('-c', '--channel', help="The channel to join.")
    parser.add_argument('-n', '--nick', help="The nickname to use for the " +
                        "bot.", default="QuestBot")
    parser.add_argument('-l', '--logfile', help="The logfile to use for the " +
                        "output.", default="out.log")
    args = parser.parse_args()
    # Parse the arguments
    logfile = args.logfile
    config = args.configfile

    if args.channel:
        if args.channel[0] != '#':
            channel = "#%s" % args.channel
        else:
            channel = args.channel

    if args.server:
        server = args.server

    nick = args.nick
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
    f = QuestBotFactory(channel, nick)

    # connect factory to this host and port
    reactor.connectTCP(server, 6667, f)

    # run bot
    reactor.run()
