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
#import time


class TestThirdPartyViews(unittest.TestCase):
    # test lock
    def setUp(self):
        self.client = Client()
        self.uploader = Uploader(key='testkey', name='testuploader')
        self.uploader.save()

    def tearDown(self):
        Uploader.objects.all().delete()
        BucketLock.objects.all().delete()

    def test_lock_no_key(self):
        response = self.client.get('/recap/lock/', {'court' : 'nysd', 'casenum' : 1234})
        self.assertEquals("0<br>Missing arguments.", response.content)
        self.assertEquals(200, response.status_code)
    
    def test_lock_invalid_key(self):
        response = self.client.get('/recap/lock/', {'key' : 'invalid_key', 
                                                    'court' : 'nysd', 
                                                    'casenum' : 1234})
        self.assertEquals("0<br>Authentication failed.", response.content)
        self.assertEquals(200, response.status_code)
    
    def test_lock_valid_request(self):
        response = self.client.get('/recap/lock/', {'key' : self.uploader.key, 
                                                    'court' : 'nysd', 
                                                    'casenum' : 1234})
        created_lock = BucketLock.objects.all()[0]
        self.assertEquals("1<br>%s" % created_lock.nonce, response.content)
        self.assertEquals(200, response.status_code)
    
    def test_lock_already_locked_bucket_same_requester(self):
        #lock a case
        self.client.get('/recap/lock/', {'key' : self.uploader.key, 
                                                    'court' : 'nysd', 
                                                    'casenum' : 1234})
        
        created_lock = BucketLock.objects.all()[0]
        response = self.client.get('/recap/lock/', {'key' : self.uploader.key, 
                                                    'court' : 'nysd', 
                                                    'casenum' : 1234})
        self.assertEquals("1<br>%s" % created_lock.nonce, response.content)
        self.assertEquals(200, response.status_code)
    
    def test_lock_ready_but_not_processing(self):
        #lock a case
        self.client.get('/recap/lock/', {'key' : self.uploader.key, 
                                                    'court' : 'nysd', 
                                                    'casenum' : 1234})

        # unlock it, it should be marked ready for upload
        response = self.client.get('/recap/unlock/', {'key' : self.uploader.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 1234,
                                                    'modified' : 1,
                                                    'nononce' : 0})
        created_lock = BucketLock.objects.all()[0]
        self.assertEquals(1, created_lock.ready)
        self.assertEquals(0, created_lock.processing)
        
        #lock it again
        self.client.get('/recap/lock/', {'key' : self.uploader.key, 
                                                    'court' : 'nysd', 
                                                    'casenum' : 1234})
        
        created_lock = BucketLock.objects.all()[0]
        self.assertEquals(0, created_lock.ready)
        self.assertEquals(0, created_lock.processing)

    
    def test_lock_already_locked_bucket_different_requester(self):
        other_guy = Uploader(key='otherkey', name='imposter')
        other_guy.save()

        #lock a case
        self.client.get('/recap/lock/', {'key' : self.uploader.key, 
                                                    'court' : 'nysd', 
                                                    'casenum' : 1234})
        
        response = self.client.get('/recap/lock/', {'key' : other_guy.key, 
                                                    'court' : 'nysd', 
                                                    'casenum' : 1234})
        self.assertEquals("0<br>Locked by another user.", response.content)
        self.assertEquals(200, response.status_code)

    # test unlock
    def test_unlock_no_key(self):
        response = self.client.get('/recap/unlock/', {'court' : 'nysd', 'casenum' : 1234})
        self.assertEquals("0<br>Missing arguments.", response.content)
        self.assertEquals(200, response.status_code)
    
    def test_unlock_invalid_key(self):
        response = self.client.get('/recap/unlock/', {'key' : 'invalid_key',
                                                    'court' : 'nysd',
                                                    'casenum' : 1234,
                                                    'modified' : 1,
                                                    'nononce' : 0})
        self.assertEquals("0<br>Authentication failed.", response.content)
        self.assertEquals(200, response.status_code)
    
    def test_unlock_valid_nonexisting_lock(self):
        response = self.client.get('/recap/unlock/', {'key' : self.uploader.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 1234,
                                                    'modified' : 1,
                                                    'nononce' : 0})
        self.assertEquals('1', response.content)
        self.assertEquals(200, response.status_code)
    
    def test_unlock_valid_not_modified(self):
        #create a lock
        self.client.get('/recap/lock/', {'key' : self.uploader.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 1234})

        created_lock = BucketLock.objects.all()[0]
        self.assertNotEquals(None, created_lock)

        response = self.client.get('/recap/unlock/', {'key' : self.uploader.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 1234,
                                                    'modified' : 0,
                                                    'nononce' : 0})
        self.assertEquals('1', response.content)
        self.assertEquals(200, response.status_code)
        self.assertEquals(0, BucketLock.objects.count())
    
    def test_unlock_valid_modified(self):
        #create a lock
        self.client.get('/recap/lock/', {'key' : self.uploader.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 1234})

        created_lock = BucketLock.objects.all()[0]
        self.assertNotEquals(None, created_lock)

        response = self.client.get('/recap/unlock/', {'key' : self.uploader.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 1234,
                                                    'modified' : 1,
                                                    'nononce' : 0})
        self.assertEquals('1', response.content)
        self.assertEquals(200, response.status_code)
        self.assertEquals(1, BucketLock.objects.count())
        self.assertEquals(1, BucketLock.objects.all()[0].ready)

    def test_unlock_bucket_different_requester(self):
        other_guy = Uploader(key='otherkey', name='imposter')
        other_guy.save()

        #lock a case
        self.client.get('/recap/lock/', {'key' : self.uploader.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 1234})
        
        response = self.client.get('/recap/unlock/', {'key' : other_guy.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 1234,
                                                    'modified' : 1,
                                                    'nononce' : 0})
        self.assertEquals("0<br>Locked by another user.", response.content)
        self.assertEquals(200, response.status_code)

    # test querylocks
    def test_querylocks_no_key(self):
        response = self.client.get('/recap/querylocks/')
        self.assertEquals("0<br>Missing arguments.", response.content)
        self.assertEquals(200, response.status_code)
    
    def test_querylocks_invalid_key(self):
        response = self.client.get('/recap/querylocks/', {'key' : 'invalid_key'})
        self.assertEquals("0<br>Authentication failed.", response.content)
        self.assertEquals(200, response.status_code)
    
    def test_querylocks_valid_no_locks(self):
        response = self.client.get('/recap/querylocks/', {'key' : self.uploader.key})
        self.assertEquals("0<br>", response.content)
        self.assertEquals(200, response.status_code)
    
    def test_querylocks_valid_two_locks(self):
        response = self.client.get('/recap/lock/', {'key' : self.uploader.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 1234})
        response = self.client.get('/recap/lock/', {'key' : self.uploader.key,
                                                    'court' : 'nysd',
                                                    'casenum' : 5678})
        response = self.client.get('/recap/querylocks/', {'key' : self.uploader.key})
        #remainder of content is nonce and other case
        self.assertEquals("2<br>nysd,1234", response.content[0:14])
        self.assertEquals(200, response.status_code)

