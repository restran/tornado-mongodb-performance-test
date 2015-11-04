# -*- coding: utf-8 -*-
# Created on 2015/10/27

from gevent import monkey
monkey.patch_all()

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
from pymongo import MongoClient
import pymongo

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


class APIHandler(RequestHandler):
    def __init__(self, app, request, **kwargs):
        super(APIHandler, self).__init__(app, request, **kwargs)
        # MongoDB 数据库连接
        self.db_client = app.db_client
        self.database = app.database
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
        cursor = self.database.post.find(limit=30)
        json_data = []
        for t in cursor:
           j = {
               '_id': text_type(t['_id']),
               'title': t['title'],
               'created': t['created'].strftime('%Y-%m-%d %H:%M:%S') if t['created'] else None
           }
           json_data.append(j)

        self.success(json_data)


class WriteHandler(APIHandler):
    def post(self):
        self.database.post.insert_one({'title': self.post_data['title'], 'created': datetime.now()})
        self.success()


class Application(tornado.web.Application):
    def __init__(self):
        tornado_settings = dict(
            debug=DEBUG,
        )

        handlers = [
            (r'/api/posts/query/?', QueryHandler),
            (r'/api/posts/?', WriteHandler),
        ]

        # 创建一个数据库连接池
        self.db_client = MongoClient(MONGO_HOST, MONGO_PORT, maxPoolSize=200)
        # 验证数据库用户名和密码
        self.db_client[MONGO_DBNAME].authenticate(
            MONGO_USERNAME, MONGO_PASSWORD, mechanism='SCRAM-SHA-1')
        self.database = self.db_client[MONGO_DBNAME]

        tornado.web.Application.__init__(self, handlers, **tornado_settings)


app = Application()


def main():
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
