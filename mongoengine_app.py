# -*- coding: utf-8 -*-
# Created on 2015/10/27


import logging
import json
from datetime import datetime

import tornado
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.gen
import tornado.httpclient
from tornado.web import RequestHandler
from tornado.options import define, options
import six
from six import text_type
from mongoengine import *

__author__ = 'restran'

# 是否调试模式
DEBUG = True
# HOST = '127.0.0.1'
HOST = '0.0.0.0'
PORT = 8500

MONGO_HOST = '192.168.14.108'
MONGO_PORT = 27017
MONGO_USERNAME = 'test_db_user'
MONGO_PASSWORD = 'test_db_P@ssw0rd'
MONGO_DBNAME = 'mongodb_test'
LOGGING_LEVEL = 'DEBUG' if DEBUG else 'INFO'

define("host", default=HOST, help="run on the given host", type=str)
define("port", default=PORT, help="run on the given port", type=int)

logging.basicConfig(level=LOGGING_LEVEL)

logger = logging.getLogger(__name__)


class Post(Document):
    title = StringField(max_length=120, required=True)
    created = DateTimeField()

    meta = {
        'indexes': ['-created']
    }

    def get_json(self):
        json_data = {
            '_id': text_type(self.id),
            'title': self.title,
            'created': self.created.strftime('%Y-%m-%d %H:%M:%S') if self.created else None
        }

        return json_data


class APIHandler(RequestHandler):
    def __init__(self, app, request, **kwargs):
        super(APIHandler, self).__init__(app, request, **kwargs)
        self.post_data = {}

    def initialize(self):
        self.set_header("Content-Type", "application/json; charset=utf-8")

    def prepare(self):
        if self.request.method == 'POST':
            content_type = self.request.headers.get('Content-Type', '').split(';')[0]
            if content_type == 'application/json':
                self.post_data = json.loads(self.request.body)

    def success(self, data=None, message=''):
        json_str = json.dumps({'code': 200, 'data': data, 'message': message}, ensure_ascii=False)
        self.write(json_str)
        self.finish()


class QueryHandler(APIHandler):
    def get(self):
        posts = Post.objects[:30]
        self.success([t.get_json() for t in posts])


class WriteHandler(APIHandler):
    def post(self):
        Post(title=self.post_data['title'], created=datetime.now()).save()
        self.success()


class PostBaseDataHandler(APIHandler):
    def post(self):
        for t in xrange(10000):
            Post(title=self.post_data['title'], created=datetime.now()).save()
        self.success()


class DeleteAllHandler(APIHandler):
    def post(self):
        Post.objects.delete()
        self.success()


class Application(tornado.web.Application):
    def __init__(self):
        tornado_settings = dict(
            debug=DEBUG,
        )

        connect(
            db=MONGO_DBNAME,
            username=MONGO_USERNAME,
            password=MONGO_PASSWORD,
            host=MONGO_HOST,
            port=MONGO_PORT
        )

        handlers = [
            (r'/api/posts/query/?', QueryHandler),
            (r'/api/posts/?', WriteHandler),
            (r'/api/posts/delete_all/?', DeleteAllHandler),
            (r'/api/posts/post_base_data/?', PostBaseDataHandler),
        ]

        tornado.web.Application.__init__(self, handlers, **tornado_settings)


app = Application()


def main():
    # 启动 tornado 之前，先测试 redis 是否能正常工作
    # r = RedisHelper()
    # r.ping_redis()

    # 重新设置一下日志级别，默认情况下，tornado 是 info
    # options.logging 不能是 Unicode
    options.logging = six.binary_type(LOGGING_LEVEL)
    # parse_command_line 的时候将logging的根级别设置为info
    tornado.options.parse_command_line()

    http_server = tornado.httpserver.HTTPServer(app, xheaders=True)
    http_server.listen(options.port, options.host)

    logger.info('tornado server is running on %s:%s' % (options.host, options.port))
    tornado.ioloop.IOLoop.instance().start()


if __name__ == "__main__":
    main()
