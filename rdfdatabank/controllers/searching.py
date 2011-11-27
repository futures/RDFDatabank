import logging

from rdfdatabank.lib.base import BaseController, render

class SearchingController(BaseController):
    def index(self):
        return render('/searching.html')
