import os.path


class Quest:
    def __init__(self, logger):
        self.users = []
        self.logger = logger

    def create_user(self, username):
        if os.path.exists("archive/" + username + ".user"):
            self.logger.log("User '%s' found in archive." % username)
        else:
            self.logger.log("User '%s' not found in archive." % username)
