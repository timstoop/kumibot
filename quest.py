import os.path
import cPickle
import logging

logger = logging.getLogger(__name__)


class Quest:
    def __init__(self):
        self.users = {}

    def create_user(self, username):
        # Remove operator signs
        if '@' in username and username.index('@') == 0:
            username = username[1:]
        if username not in self.users:
            self.users[username] = QuestUser(username)

    def hibernate_user(self, username):
        if username in self.users:
            self.users[username].hibernate()
            del self.users[username]


class QuestUser:
    def __init__(self, username):
        self.version = 1
        self.username = username
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

        self.__dict__.update(tmp_dict)

    def save(self):
        with open('archive/' + self.username + '.user', 'wb') as f:
            cPickle.dump(self.__dict__, f, 2)

        logger.info("Saved user file for '%s', data format version %i." %
                    (self.username, self.version))
