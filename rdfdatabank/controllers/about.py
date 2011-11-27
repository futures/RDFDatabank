import logging

from rdfdatabank.lib.base import BaseController, render

class AboutController(BaseController):
    def index(self):
        return render('/about.html')
