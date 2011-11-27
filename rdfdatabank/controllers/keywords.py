import logging

from rdfdatabank.lib.base import BaseController, render

class KeywordsController(BaseController):
    def index(self):
        return render('/keywords.html')
