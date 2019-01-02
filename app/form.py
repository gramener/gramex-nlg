#! /usr/bin/env python
# -*- coding: utf-8 -*-
# vim:fenc=utf-8

from atexit import register
import os.path as op
from shutil import rmtree
from tempfile import mkdtemp

from tornado.web import RequestHandler, Application
from tornado.ioloop import IOLoop
from wtforms import Form, FileField, SubmitField, TextAreaField


class FileUpload(Form):

    file_upload = FileField('Upload a file')
    submit = SubmitField('Submit')


class NLGForm(Form):

    textbox = TextAreaField('Type Something')
    submit = SubmitField('Submit')


class UploadHandler(RequestHandler):

    _cache = mkdtemp()

    def get(self):
        self.render('html/preview-submit.html', form=NLGForm())

    def post(self):
        for fobj in self.request.files['file_upload']:
            outpath = op.join(self._cache, fobj['filename'])
            with open(outpath, 'wb') as fout:
                fout.write(fobj['body'])
        return self.write(self._cache)


if __name__ == '__main__':
    app = Application([(r'/', UploadHandler)], autoreload=True, autoescape=None)
    register(rmtree, UploadHandler._cache)
    app.listen(8888)
    IOLoop.current().start()
