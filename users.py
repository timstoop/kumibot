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
    current_hostmask = ''
    hostmasks = []

    def __init__(self, username, hostmask=None):
        self.username = str(username)
        self.currentNick = str(username)
        self.version = self.version
        self.is_admin = self.is_admin
        self.current_hostmask = hostmask
        if os.path.exists("archive/" + self.username + ".user"):
            logger.info("User '%s' found in archive." % self.username)
            self.load()
            if hostmask:
                self._check_hostmask(hostmask)
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
        # We only save when we're registered.
        if not self.is_registered():
            logger.info("Not saving file for '%s', not registered." %
                        self.username)
            return
        # Otherwise, save.
        with open('archive/' + self.username + '.user', 'wb') as f:
            cPickle.dump(self.__dict__, f, 2)

        logger.info("Saved user file for '%s', data format version %i." %
                    (self.username, self.version))

    def add_hostmask(self, hostmask):
        self.hostmasks.append(hostmask)
        logger.info("Add hostmask '%s' to known hostmasks for user '%s'." %
                    (hostmask, self.username))

    def set_admin(self, admin):
        self.is_admin = admin
        self.save()
        logger.info("User %s has been made an admin." % self.username)

    def set_pw_hash(self, pwhash, replace=False):
        if not replace and hasattr(self, 'pwhash'):
            raise AccountAlreadyCreatedException('Account already has a ' +
                                                 'password.')
        else:
            self.pwhash = pwhash
            self.hostmasks.append(self.current_hostmask)
            self.save()

    def is_registered(self):
        # Nothing too fancy yet, only check if a password hash is set.
        if hasattr(self, 'pwhash') and self.pwhash is not None:
            return True
        else:
            return False

    def _check_hostmask(self, hostmask):
        """We check if the found hostmask is a known hostmask."""
        if hostmask not in self.hostmasks:
            raise UnknownHostmaskException(("Hostmask %s is not known for " +
                                           "user %s.") % (hostmask,
                                                          self.username))


class UnknownHostmaskException(Exception):
    pass


class AccountAlreadyCreatedException(Exception):
    pass
