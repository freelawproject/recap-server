from test_constants import *

from uploads.recap_config import config

#from uploads.BeautifulSoup import BeautifulSoup,HTMLParseError, Tag, NavigableString
#import uploads.ParsePacer as PP
#import uploads.DocketXML as DocketXML
#import re, os
#from lxml import etree

from mock import patch, Mock

from django.test.client import Client
from django.utils import simplejson

from uploads.models import Document, Uploader, BucketLock, PickledPut
#import uploads.InternetArchiveCommon as IACommon
import uploads.InternetArchive as IA

import unittest
#import datetime
#import time

class TestUploadView(unittest.TestCase):
    def setUp(self):
        self.client = Client()
        self.f = open(TEST_DOCKET_PATH + 'DktRpt_111111.html')
        self.valid_params = {'court': 'nysd', 
                             'casenum' : '1234',
                             'mimetype' : 'text/html',
                             'data': self.f} 
        self.f_pdf = open(TEST_DOCUMENT_PATH + 'gov.uscourts.cand.206019.18.0.pdf')
        self.valid_params_pdf = {'court': 'cand', 
                                 'casenum': '206019',
                                 'mimetype': 'application/pdf',
                                 'url': 'https://ecf.cand.uscourts.gov/doc1/123456', #docid
                                 'data': self.f_pdf} 

        #Doc id is 'coerced', so doesn't match one above
        self.pdf_doc = Document(court='cand', casenum='206019', 
                                docnum='18', subdocnum='0', docid=123056)
        self.pdf_doc.save()
        
        self.f_doc1 = open(TEST_DOC1_PATH + 'ecf.cand.uscourts.gov.03517852828')
        self.valid_params_doc1 = {'court': 'cand', 
                                 'casenum': '206019',
                                 'mimetype': 'text/html',
                                 'data': self.f_doc1} 

    def tearDown(self):
        self.f.close()
        self.f_pdf.close()
        self.f_doc1.close()
        for p in PickledPut.objects.all():
            IA.delete_pickle(p.filename)
            p.delete()
        Document.objects.all().delete()
    
    def test_upload_post_request_only(self):
        response = self.client.get('/recap/upload/', {'blah' : 'foo'})
        self.assertEquals('upload: Not a POST request.', response.content)
    
    def test_upload_no_params(self):
        response = self.client.post('/recap/upload/')
        self.assertEquals("upload: No request.FILES attribute.", response.content)
    
    def test_upload_docket_no_court_param(self):
        del self.valid_params['court']
        response = self.client.post('/recap/upload/', self.valid_params)
        self.assertEquals("upload: No POST 'court' attribute.", response.content)
    
    def test_upload_docket_invalid_casenum_param(self):
        self.valid_params['casenum'] = 'garbage_data'
        response = self.client.post('/recap/upload/', self.valid_params)
        self.assertEquals("upload: 'casenum' invalid: garbage_data", response.content)
    
    def test_upload_docket_no_casenum_param(self):
        del self.valid_params['casenum']
        response = self.client.post('/recap/upload/', self.valid_params)
        self.assertEquals("upload: docket has no casenum.", response.content)
    
    def test_upload_docket_no_mimetype_param(self):
        del self.valid_params['mimetype']
        response = self.client.post('/recap/upload/', self.valid_params)
        self.assertEquals("upload: No POST 'mimetype' attribute.", response.content)
    
    def test_upload_docket_report(self):
        response = self.client.post('/recap/upload/', self.valid_params)
        output = simplejson.loads(response.content)
        self.assertEquals(3, len(output))
        self.assertEquals("DktRpt successfully parsed.", output['message'])
        # After upload, a pickled put should be created
        # If this fails, make sure you've created a picklejar directory
        self.assertEquals(1, PickledPut.objects.all().count())
        pp = PickledPut.objects.all()[0]
        self.assertEquals(1, pp.ready)
    
    def test_upload_docket_report_for_unlocked_bucket(self):
        # Setup - Upload a docket
        response = self.client.post('/recap/upload/', self.valid_params)
        # After upload, a pickled put should be created
        self.assertEquals(1, PickledPut.objects.all().count())

        #Do it again, to test whether merges are handled correctly
        response = self.client.post('/recap/upload/', self.valid_params)
        output = simplejson.loads(response.content)
        self.assertEquals("DktRpt successfully parsed.", output['message'])
        self.assertEquals(1, PickledPut.objects.all().count())
        pp = PickledPut.objects.all()[0]
        self.assertEquals(1, pp.ready)
    
    #TK: This case seems wrong, we discard the newer docket if an old docket
    # on the same case is being uploaded. Might be too edge casey to worry about
    # The function test behavior is the same as the one above, so going to leave it 
    # unimplemented for now
    def test_upload_docket_report_for_locked_bucket(self):
        pass
    
    def test_upload_document_without_url(self):
        del self.valid_params_pdf['url']
        response = self.client.post('/recap/upload/', self.valid_params_pdf)
        self.assertEquals('upload: pdf failed. no url supplied.', response.content)
    
    #TK: Handle this case better? Most likely isn't possible
    def test_upload_document_no_associated_document_with_docid(self):
        self.pdf_doc.delete()
        response = self.client.post('/recap/upload/', self.valid_params_pdf)
        self.assertEquals('upload: pdf ignored.', response.content)
    
    def test_upload_document_no_record_of_docid(self):
        self.pdf_doc.docid=99999
        self.pdf_doc.save()
        response = self.client.post('/recap/upload/', self.valid_params_pdf)
        self.assertEquals('upload: pdf ignored.', response.content)
    
    def test_upload_document_metadata_mismatch(self):
        self.valid_params_pdf['court'] = 'azb'
        response = self.client.post('/recap/upload/', self.valid_params_pdf)
        self.assertEquals('upload: pdf metadata mismatch.', response.content)
    
    def test_upload_document(self):
        response = self.client.post('/recap/upload/', self.valid_params_pdf)
        output = simplejson.loads(response.content)
        self.assertEquals('pdf uploaded.', output['message'])
        self.assertEquals(2, PickledPut.objects.all().count())
        self.pdf_doc = Document.objects.all()[0]
        self.assertTrue(self.pdf_doc.sha1 != None)
        self.assertEquals("5741373aff552f22fa2f14f2bd39fea4564aa49c", self.pdf_doc.sha1)
    
    def test_upload_document_no_sha1_difference(self):
        #set the sha1 to what we know it to be
        self.pdf_doc.sha1 = "5741373aff552f22fa2f14f2bd39fea4564aa49c"
        self.pdf_doc.save()
        response = self.client.post('/recap/upload/', self.valid_params_pdf)
        output = simplejson.loads(response.content)
        self.assertEquals('pdf uploaded.', output['message'])
        # we only upload a docket update if the doc is the same
        self.assertEquals(1, PickledPut.objects.all().count())
    
    # have to do some patching to get around the filename issue
    @patch('uploads.UploadHandler.is_doc1_html', Mock(return_value=True))
    @patch('uploads.UploadHandler.docid_from_url_name', Mock(return_value='9999999'))
    def test_upload_doc1_no_matching_docid(self):
        response = self.client.post('/recap/upload/', self.valid_params_doc1)
        self.assertEquals('upload: doc1 ignored.', response.content)
    
    # have to do some patching to get around the filename issue
    @patch('uploads.UploadHandler.is_doc1_html', Mock(return_value=True))
    @patch('uploads.UploadHandler.docid_from_url_name', Mock(return_value='123056'))
    def test_upload_doc1(self):
        response = self.client.post('/recap/upload/', self.valid_params_doc1)
        output = simplejson.loads(response.content)
        self.assertEquals('doc1 successfully parsed.', output['message'])
        self.assertTrue('cases' in output)




