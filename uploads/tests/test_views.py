from test_constants import *

from uploads.recap_config import config

#from uploads.BeautifulSoup import BeautifulSoup,HTMLParseError, Tag, NavigableString
#import uploads.ParsePacer as PP
#import uploads.DocketXML as DocketXML
#import re, os
#from lxml import etree

#from mock import patch, Mock

from django.test.client import Client
#from django.utils import simplejson

from uploads.models import Document, Uploader, BucketLock, PickledPut
#import uploads.InternetArchiveCommon as IACommon
#import uploads.InternetArchive as IA

import unittest
#import datetime
import time

class TestViews(unittest.TestCase):
    def setUp(self):
        self.client = Client()

    def tearDown(self):
        Document.objects.all().delete()


    # test index
    def test_index_view(self):
        response = self.client.get('/recap/')
        self.assertEquals("Well hello, there's nothing to see here.", response.content)

    # test upload view

    # test get_updated_cases
    def test_get_updated_cases_no_key(self):
        response = self.client.get('/recap/get_updated_cases/')
        self.assertEquals(403, response.status_code)
    
    def test_get_updated_cases_incorrect_key(self):
        response = self.client.get('/recap/get_updated_cases/', {'key' : 'incorrect_key'})
        self.assertEquals(403, response.status_code)
    
    def test_get_updated_cases_valid_request(self):
        d1 = Document(court='nysd', casenum='1234', docnum='1', subdocnum='0')
        d1.save()
        d2 = Document(court='dcd', casenum='100', docnum='1', subdocnum='0')
        d2.save()
        yesterday = time.time() - 60 * 60 * 24
        response = self.client.post('/recap/get_updated_cases/', {'key' : config['API_KEYS'][0], 
                                                                 'tpq' : yesterday})
        self.assertEquals(200, response.status_code)
        self.assertEquals('%s,%s\r\n%s,%s\r\n' % (d1.court, d1.casenum, d2.court, d2.casenum), response.content)
        self.assertEquals({'Content-Type': 'text/csv'}, response.headers)
                
    
    # heartbeat view tests
    def test_heartbeat_view_no_key(self):
        response = self.client.get('/recap/heartbeat/')
        self.assertEquals(403, response.status_code)
    
    def test_heartbeat_view_incorrect_key(self):
        response = self.client.get('/recap/heartbeat/', {'key' : 'incorrect_key'})
        self.assertEquals(403, response.status_code)
    
    def test_heartbeat_correct_key_no_db_connection(self):
        response = self.client.get('/recap/heartbeat/', {'key' : config['API_KEYS'][0]})
        self.assertEquals(500, response.status_code)
        self.assertEquals("500 Server error: He's Dead Jim", response.content)
        
    def test_heartbeat_correct_key_with_db_connection(self):

        document = Document(court='cand', casenum='215270', docnum='1', subdocnum='0')
        document.save()

        response = self.client.get('/recap/heartbeat/', {'key' : config['API_KEYS'][0]})
        self.assertEquals(200, response.status_code)
        self.assertEquals("It's Alive!", response.content)


