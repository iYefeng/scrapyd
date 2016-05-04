import sys, os
from pkgutil import get_data
from cStringIO import StringIO

from twisted.trial import unittest

from scrapy.utils.test import get_pythonpath
from scrapyd.interfaces import IEggStorage
from scrapyd.utils import get_crawl_args, get_spider_list, UtilsCache, get_scrapyd_host
from scrapyd import get_application

def get_pythonpath_scrapyd():
    scrapyd_path = __import__('scrapyd').__path__[0]
    return os.path.dirname(scrapyd_path) + os.pathsep + get_pythonpath() + os.pathsep + os.environ.get('PYTHONPATH', '')


class UtilsTest(unittest.TestCase):

    def test_get_crawl_args(self):
        msg = {'_project': 'lolo', '_spider': 'lala'}
        self.assertEqual(get_crawl_args(msg), ['lala'])
        msg = {'_project': 'lolo', '_spider': 'lala', 'arg1': u'val1'}
        cargs = get_crawl_args(msg)
        self.assertEqual(cargs, ['lala', '-a', 'arg1=val1'])
        assert all(isinstance(x, str) for x in cargs), cargs

    def test_get_crawl_args_with_settings(self):
        msg = {'_project': 'lolo', '_spider': 'lala', 'arg1': u'val1', 'settings': {'ONE': 'two'}}
        cargs = get_crawl_args(msg)
        self.assertEqual(cargs, ['lala', '-a', 'arg1=val1', '-s', 'ONE=two'])
        assert all(isinstance(x, str) for x in cargs), cargs

class GetSpiderListTest(unittest.TestCase):
    def setUp(self):
        path = os.path.abspath(self.mktemp())
        j = os.path.join
        eggs_dir = j(path, 'eggs')
        os.makedirs(eggs_dir)
        dbs_dir = j(path, 'dbs')
        os.makedirs(dbs_dir)
        logs_dir = j(path, 'logs')
        os.makedirs(logs_dir)
        os.chdir(path)
        with open('scrapyd.conf', 'w') as f:
            f.write("[scrapyd]\n")
            f.write("eggs_dir = %s\n" % eggs_dir)
            f.write("dbs_dir = %s\n" % dbs_dir)
            f.write("logs_dir = %s\n" % logs_dir)
        self.app = get_application()

    def add_test_version(self, file, project, version):
        eggstorage = self.app.getComponent(IEggStorage)
        eggfile = StringIO(get_data("scrapyd.tests", file))
        eggstorage.put(eggfile, project, version)

    def test_get_spider_list(self):
        # mybot.egg has two spiders, spider1 and spider2
        self.add_test_version('mybot.egg', 'mybot', 'r1')
        spiders = get_spider_list('mybot', pythonpath=get_pythonpath_scrapyd())
        self.assertEqual(sorted(spiders), ['spider1', 'spider2'])

        # mybot2.egg has three spiders, spider1, spider2 and spider3...
        # BUT you won't see it here because it's cached.
        # Effectivelly it's like if version was never added
        self.add_test_version('mybot2.egg', 'mybot', 'r2')
        spiders = get_spider_list('mybot', pythonpath=get_pythonpath_scrapyd())
        self.assertEqual(sorted(spiders), ['spider1', 'spider2'])

        # Let's invalidate the cache for this project...
        UtilsCache.invalid_cache('mybot')

        # Now you get the updated list
        spiders = get_spider_list('mybot', pythonpath=get_pythonpath_scrapyd())
        self.assertEqual(sorted(spiders), ['spider1', 'spider2', 'spider3'])

        # Let's re-deploy mybot.egg and clear cache. It now sees 2 spiders
        self.add_test_version('mybot.egg', 'mybot', 'r3')
        UtilsCache.invalid_cache('mybot')
        spiders = get_spider_list('mybot', pythonpath=get_pythonpath_scrapyd())
        self.assertEqual(sorted(spiders), ['spider1', 'spider2'])

        # And re-deploying the one with three (mybot2.egg) with a version that
        # isn't the higher, won't change what get_spider_list() returns.
        self.add_test_version('mybot2.egg', 'mybot', 'r1a')
        UtilsCache.invalid_cache('mybot')
        spiders = get_spider_list('mybot', pythonpath=get_pythonpath_scrapyd())
        self.assertEqual(sorted(spiders), ['spider1', 'spider2'])

    def test_get_scrapyd_host(self):
        ip = get_scrapyd_host()
        print ip
        self.assertEqual(ip, '192.168.238.200')

