from rdfdatabank.lib.htpasswd import HtpasswdFile
import sys

def add_user(pwdfile, username, password):
    passwdfile = HtpasswdFile(pwdfile)
    passwdfile.load()
    passwdfile.update(username, password)
    passwdfile.save()
    return True

if __name__ == "__main__":
    username = sys.argv[1]
    password = sys.argv[2]
    pwdfile = '/var/lib/databank/passwd'
    add_user(pwdfile, username, password)

