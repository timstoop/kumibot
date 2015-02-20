import os.path
import cPickle
import logging

logger = logging.getLogger(__name__)


class UserList:
    def __init__(self):
        self.users = {}

    def create_user(self, username, hostmask):
        # Remove operator signs
        if '@' in username and username.index('@') == 0:
            username = username[1:]
        if username not in self.users:
            self.users[username] = User(username, hostmask)

    def hibernate_user(self, username):
        if username in self.users:
            self.users[username].hibernate()
            del self.users[username]


class User:
    version = 1
    username = ''
    currentNick = ''
    is_admin = False

    def __init__(self, username, hostmask):
        self.username = username
        self.currentNick = username
        self.version = self.version
        self.is_admin = self.is_admin
        if os.path.exists("archive/" + self.username + ".user"):
            logger.info("User '%s' found in archive." % self.username)
            self.load()
        else:
            logger.info("User '%s' not found in archive." % self.username)
            self.save()

    def hibernate(self):
        logger.info("User '%s' goes into hibernation." % (self.username))
        self.save()

    def load(self):
        with open('archive/' + self.username + '.user') as f:
            tmp_dict = cPickle.load(f)

        loaded_version = tmp_dict['version']
        logger.info(" - Loaded userfile with data format version %i." %
                    loaded_version)

        for key in tmp_dict:
            self.__dict__[key] = tmp_dict[key]

        # Do some sanity checking
        if self.currentNick == '':
            self.currentNick = self.username

    def save(self):
        with open('archive/' + self.username + '.user', 'wb') as f:
            cPickle.dump(self.__dict__, f, 2)

        logger.info("Saved user file for '%s', data format version %i." %
                    (self.username, self.version))

    def set_admin(self, admin):
        self.is_admin = admin
        self.save()
        logger.info("User %s has been made an admin." % self.username)

    def _check_hostmask(self, hostmask):
        """We check if the found hostmask is a known hostmask."""
        if hostmask not in self.hostmask:
            raise UnknownHostmaskException("Hostmask %s is not known for " +
                                           "user %s." % (hostmask, self.user))


class UnknownHostmaskException(Exception):
    pass
