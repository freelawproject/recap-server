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
#import uploads.InternetArchiveCommon as IACommon
#import uploads.InternetArchive as IA

import unittest
#import datetime
#import time

class TestAddDocMetaView(unittest.TestCase): 
    def setUp(self):
        self.client = Client()
        self.existing_document  = Document(court='nysd', casenum='1234', docnum='1', subdocnum='0')
        self.existing_document.save()
        self.adddocparams =  { 'court': 'nysd', 'casenum': '1234', 
                               'docnum': '1', 'de_seq_num': '1111',
                               'dm_id': '2222', 'docid': '3330'}
    def tearDown(self):
        Document.objects.all().delete()


    
    def test_adddoc_only_post_requests_allowed(self):
        response = self.client.get('/recap/adddocmeta/')
        self.assertEquals("adddocmeta: Not a POST request.", response.content)
    
    def test_adddoc_request_data_missing(self):
        response = self.client.post('/recap/adddocmeta/', {'docid': '1234'})
        self.assertTrue(response.content.startswith("adddocmeta: \"Key 'court' not found"))

    def test_adddoc_updates_meta(self):
        self.assertEquals(None, self.existing_document.docid)
        response = self.client.post('/recap/adddocmeta/', self.adddocparams)
        self.assertEquals("adddocmeta: DB updated for docid=3330", response.content)
        query = Document.objects.filter(court='nysd', casenum='1234', 
                                        docnum='1', subdocnum='0')

        saved_document = query[0]
        self.assertEquals(1111, saved_document.de_seq_num)
        self.assertEquals(2222, saved_document.dm_id)
        self.assertEquals('3330', saved_document.docid)
    
    def test_adddoc_coerces_doc_id(self):
        self.adddocparams['docid'] = '123456789'
        response = self.client.post('/recap/adddocmeta/', self.adddocparams)
        query = Document.objects.filter(court='nysd', casenum='1234', 
                                        docnum='1', subdocnum='0')

        saved_document = query[0]
        self.assertEquals('123056789', saved_document.docid)
    
    def test_adddoc_creates_new_document(self):
        query = Document.objects.filter(court='nysd', casenum='5678', 
                                        docnum='1', subdocnum='0')

        self.adddocparams['casenum'] = '5678'
        self.assertEquals(0, query.count()) 
        response = self.client.post('/recap/adddocmeta/', self.adddocparams)
        self.assertEquals(1, query.count()) 
        created_doc = query[0]
        created_doc.docid = self.adddocparams['docid']
    
    def test_adddoc_responds_with_document_dict(self):
        self.adddocparams['add_case_info'] = True
        response = self.client.post('/recap/adddocmeta/', self.adddocparams)
        response_dict = simplejson.loads(response.content)
        self.assertEquals(1, len(response_dict['documents']))
        self.assertTrue(self.adddocparams['docid'] in response_dict['documents'])

