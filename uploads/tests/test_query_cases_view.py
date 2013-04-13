from test_constants import *

from uploads.recap_config import config

#from uploads.BeautifulSoup import BeautifulSoup,HTMLParseError, Tag, NavigableString
#import uploads.ParsePacer as PP
#import uploads.DocketXML as DocketXML
#import re, os
#from lxml import etree

#from mock import patch, Mock

from django.test.client import Client
from django.utils import simplejson

from uploads.models import Document, Uploader, BucketLock, PickledPut
import uploads.InternetArchiveCommon as IACommon
#import uploads.InternetArchive as IA

import unittest
import datetime
#import time

class TestQueryCasesView(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.valid_params = {'court': 'nysd', 
                             'casenum' : '1234'} 
        
        self.available_doc = Document(court='nysd', casenum='1234', docnum='2', subdocnum='0', 
                                        dm_id = '1234', de_seq_num = '111', docid = '1230445')
        self.available_doc.available = '1'
        self.available_doc.lastdate = datetime.datetime.now()
        self.available_doc.save()
    
    def tearDown(self):
        Document.objects.all().delete()

    def test_query_cases_post_request_only(self):
        response = self.client.get('/recap/query_cases/', {'blah' : 'foo'})
        self.assertEquals('query_cases: Not a POST request.', response.content)
    
    def test_query_cases_no_params(self):
        response = self.client.post('/recap/query_cases/')
        self.assertEquals("query_cases: no 'json' POST argument", response.content)
    
    def test_query_cases_missing_court_param(self):
        del self.valid_params['court']
        response = self.client.post('/recap/query_cases/', {'json': simplejson.dumps(self.valid_params)})
        self.assertEquals("query_cases: missing json 'court' argument.", response.content)
    
    def test_query_cases_missing_casenum_param(self):
        del self.valid_params['casenum']
        response = self.client.post('/recap/query_cases/', {'json': simplejson.dumps(self.valid_params)})
        self.assertEquals("query_cases: missing json 'casenum' argument.", response.content)

    def test_valid_query_cases_response_no_match(self):

        response = self.client.post('/recap/query_cases/', {'json': simplejson.dumps(self.valid_params)})
        self.assertEquals("{}", response.content)
    
    def test_valid_query_cases_response_no_match(self):
        self.valid_params['casenum'] = '99999'
        response = self.client.post('/recap/query_cases/', {'json': simplejson.dumps(self.valid_params)})
        self.assertEquals("{}", response.content)
    
    def test_valid_query_cases_response_available_doc_match(self):
        response = self.client.post('/recap/query_cases/', {'json': simplejson.dumps(self.valid_params)})
        output= simplejson.loads(response.content)

        self.assertEquals(2, len(output))
        self.assertEquals(self.available_doc.lastdate.strftime("%m/%d/%y"), output['timestamp'])
        self.assertEquals(IACommon.get_dockethtml_url('nysd', '1234'), output['docket_url'])
    
    def test_valid_query_cases_response_unavailable_doc_currently_uploading(self):
        self.available_doc.available = 0
        self.available_doc.save()
        ppquery = PickledPut(filename=IACommon.get_docketxml_name('nysd', '1234'))
        ppquery.save()
        response = self.client.post('/recap/query_cases/', {'json': simplejson.dumps(self.valid_params)})
        self.assertEquals("{}", response.content)
        PickledPut.objects.all().delete()
    
    def test_valid_query_cases_response_old_doc_currently_uploading(self):
        self.available_doc.available = 0
        two_days_ago = datetime.datetime.now() - datetime.timedelta(2)
        self.available_doc.modified= two_days_ago
        self.available_doc.save()

        ppquery = PickledPut(filename=IACommon.get_docketxml_name('nysd', '1234'))
        ppquery.save()
        response = self.client.post('/recap/query_cases/', {'json': simplejson.dumps(self.valid_params)})
        
        output= simplejson.loads(response.content)

        self.assertEquals(2, len(output))
        self.assertEquals(self.available_doc.lastdate.strftime("%m/%d/%y"), output['timestamp'])
        self.assertEquals(IACommon.get_dockethtml_url('nysd', '1234'), output['docket_url'])
        PickledPut.objects.all().delete()

