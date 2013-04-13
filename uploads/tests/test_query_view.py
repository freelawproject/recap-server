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

class TestQueryView(unittest.TestCase): 
    def setUp(self):
        self.client = Client()
        self.not_avail_doc= Document(court='nysd', casenum='1234', docnum='1', subdocnum='0', 
                                        dm_id = '1234', de_seq_num = '111', docid = '12304213')
        self.not_avail_doc.save()

        self.available_doc = Document(court='nysd', casenum='1234', docnum='2', subdocnum='0', 
                                        dm_id = '1234', de_seq_num = '111', docid = '1230445')
        self.available_doc.available = '1'
        self.available_doc.lastdate = datetime.datetime.now()
        self.available_doc.save()

        self.docs = [self.not_avail_doc, self.available_doc]

        self.valid_params = {'court': 'nysd', 
                             'urls' : [self._show_doc_url_for_document(d) for d in self.docs]}
        
        self.valid_params_doc1 = {'court': 'nysd', 
                                 'urls' : [self._doc1_url_for_document(d) for d in self.docs]}
    
    def tearDown(self):
        Document.objects.all().delete()

    def _show_doc_url_for_document(self, doc):
        show_doc_url = "".join(['/cgi-bin/show_doc.pl?',
                                'caseid=%(casenum)s',
                                '&de_seq_num=%(de_seq_num)s',
                                '&dm_id=%(dm_id)s',
                                '&doc_num=%(docnum)s',
                                '&pdf_header=2'])
        show_doc_dict = {'casenum': doc.casenum, 'de_seq_num': doc.de_seq_num,
                            'dm_id': doc.dm_id, 'docnum': doc.docnum}

        return show_doc_url % show_doc_dict
    
    def _doc1_url_for_document(self, doc):
        return "/doc1/%s" % doc.docid

    def _ia_url_for_doc(self, doc):
        return IACommon.get_pdf_url(doc.court, doc.casenum, doc.docnum, doc.subdocnum)


    def test_query_post_request_only(self):
        response = self.client.get('/recap/query/', {'blah' : 'foo'})
        self.assertEquals('query: Not a POST request.', response.content)
    
    def test_query_no_params(self):
        response = self.client.post('/recap/query/')
        self.assertEquals("query: no 'json' POST argument", response.content)
    
    def test_query_invalid_json(self):
        response = self.client.post('/recap/query/', {'json': 'dkkfkdk'})
        self.assertEquals("query: malformed 'json' POST argument", response.content)

    def test_query_missing_court_param(self):
        del self.valid_params['court']
        response = self.client.post('/recap/query/', {'json': simplejson.dumps(self.valid_params)})
        self.assertEquals("query: missing json 'court' argument.", response.content)

    def test_query_missing_url_param(self):
        del self.valid_params['urls']
        response = self.client.post('/recap/query/', {'json': simplejson.dumps(self.valid_params)})
        self.assertEquals("query: missing json 'urls' argument.", response.content)
    
    def test_valid_show_doc_query_response(self):
        response = self.client.post('/recap/query/', {'json': simplejson.dumps(self.valid_params)})
       
        output = simplejson.loads(response.content)
        avail_show_doc_url = self._show_doc_url_for_document(self.available_doc)
        self.assertTrue(avail_show_doc_url in output)
        self.assertFalse(self._show_doc_url_for_document(self.not_avail_doc) in output)
        self.assertEquals(self.available_doc.lastdate.strftime("%m/%d/%y"), output[avail_show_doc_url]['timestamp'])
        self.assertEquals(self._ia_url_for_doc(self.available_doc), output[avail_show_doc_url]['filename'])
    
    def test_valid_doc1_url_query_response(self):
        response = self.client.post('/recap/query/', {'json': simplejson.dumps(self.valid_params_doc1)})
        output = simplejson.loads(response.content)

        avail_show_doc_url = self._doc1_url_for_document(self.available_doc)
        self.assertFalse(self._doc1_url_for_document(self.not_avail_doc) in output)
        self.assertEquals(self.available_doc.lastdate.strftime("%m/%d/%y"), output[avail_show_doc_url]['timestamp'])
        self.assertEquals(self._ia_url_for_doc(self.available_doc), output[avail_show_doc_url]['filename'])
    
    def test_valid_query_response_with_subdocuments(self):
        subdoc1 = Document(court='nysd', casenum='1234', docnum='2', subdocnum='1', 
                                    available=1, lastdate = datetime.datetime.now())
        subdoc2 = Document(court='nysd', casenum='1234', docnum='2', subdocnum='2',
                                    available=1, lastdate = datetime.datetime.now())
        subdoc3 = Document(court='nysd', casenum='1234', docnum='2', subdocnum='3')
        subdoc1.save()
        subdoc2.save()
        subdoc3.save()
        
        response = self.client.post('/recap/query/', {'json': simplejson.dumps(self.valid_params)})
        output = simplejson.loads(response.content)
        
        avail_show_doc_url = self._show_doc_url_for_document(self.available_doc)
        self.assertTrue(avail_show_doc_url in output)
        self.assertTrue('subDocuments' in output[avail_show_doc_url])
        subdoc_dict = output[avail_show_doc_url]['subDocuments']
        self.assertEquals(2, len(subdoc_dict))
        self.assertEquals(self._ia_url_for_doc(subdoc1), subdoc_dict['1']['filename'])


