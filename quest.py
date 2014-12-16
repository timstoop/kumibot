import os.path
import cPickle


class Quest:
    def __init__(self, logger):
        self.users = []
        self.usernames_in_use = []
        self.logger = logger

    def create_user(self, username):
        if username not in self.usernames_in_use:
            self.users.append(QuestUser(self.logger, username))
            self.usernames_in_use.append(username)


class QuestUser:
    def __init__(self, logger, username):
        self.version = 1
        self.username = username
        self.logger = logger
        if os.path.exists("archive/" + self.username + ".user"):
            self.logger.log("User '%s' found in archive." % self.username)
            self.load()
        else:
            self.logger.log("User '%s' not found in archive." % self.username)
            self.save()

    def load(self):
        f = open('archive/' + self.username + '.user')
        tmp_dict = cPickle.load(f)
        f.close()

        loaded_version = tmp_dict['version']
        self.logger.log(" - Loaded userfile with data format version %i." %
                        loaded_version)

        self.__dict__.update(tmp_dict)

    def save(self):
        f = open('archive/' + self.username + '.user', 'wb')
        cPickle.dump(self.__dict__, f, 2)
        f.close()

        self.logger.log("Saved user file for '%s', data format version %i." %
                        (self.username, self.version))
