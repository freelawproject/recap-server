from test_constants import *

from uploads.recap_config import config

#from uploads.BeautifulSoup import BeautifulSoup,HTMLParseError, Tag, NavigableString
import uploads.ParsePacer as PP
#import uploads.DocketXML as DocketXML
#import re, os
#from lxml import etree

#from mock import patch, Mock

#from django.test.client import Client
#from django.utils import simplejson

#from uploads.models import Document, Uploader, BucketLock, PickledPut
#import uploads.InternetArchiveCommon as IACommon
#import uploads.InternetArchive as IA

import unittest
import datetime
#import time

class TestParseOpinions(unittest.TestCase):
  def test_parse_opinions(self):
    opinion_filelist = ["akd.1900", "akd.2010", "nysd.2009"]

    #test empty file
    filebits = open('/dev/null').read()
    dockets = PP.parse_opinions(filebits, 'test')
    self.assertEquals([], dockets)

    filebits = {}

    for opinion_file in opinion_filelist:
        f = open(TEST_OPINION_PATH + opinion_file + ".opinions.html")
        filebits[opinion_file] = f.read()
        f.close()
    
    #test valid opinion file with no entries
    dockets = PP.parse_opinions(filebits["akd.1900"], "akd")
    self.assertEquals([], dockets) 

    dockets = PP.parse_opinions(filebits["akd.2010"], "akd")
    self.assertEquals(78, len(dockets) ) # number of entries in the opinions table
    
    #check basic metadata
    self.assertEquals("akd", dockets[0].get_court())
    self.assertEquals("12460", dockets[0].get_casenum())
    casemeta = dockets[0].get_casemeta()
    self.assertEquals("Steffensen v. City of Fairbanks et al", casemeta['case_name'])
    self.assertEquals("4:09-cv-00004-RJB", casemeta['docket_num'])
    self.assertEquals("42:1983 Prisoner Civil Rights", casemeta["case_cause"])
    self.assertEquals("Civil Rights: Other", casemeta["nature_of_suit"])
    self.assertEquals(1, len(dockets[0].documents))

    document = dockets[0].documents['98-0']
    self.assertEquals("98", document['doc_num'])
    self.assertEquals("0", document['attachment_num'])
    self.assertEquals("563", document['pacer_de_seq_num'])
    self.assertEquals("602530", document['pacer_dm_id'])
    self.assertEquals("2010-01-05", document['date_filed'])
    self.assertEquals("Order Dismissing Case", document['long_desc'])


    self.assertEquals("akd", dockets[1].get_court())
    self.assertEquals("18239", dockets[1].get_casenum())
    casemeta = dockets[1].get_casemeta()
    self.assertEquals("Kahle v. Executive Force Australia PTY LTD", casemeta['case_name'])
    self.assertEquals("2:09-cv-00008-JWS", casemeta['docket_num'])
    self.assertEquals("28:1441 Petition for Removal- Personal Injury", casemeta["case_cause"])
    self.assertEquals("Personal Inj. Prod. Liability", casemeta["nature_of_suit"])
    self.assertEquals(1, len(dockets[1].documents))

    document = dockets[1].documents['27-0']
    self.assertEquals("27", document['doc_num'])
    self.assertEquals("0", document['attachment_num'])
    self.assertEquals("142", document['pacer_de_seq_num'])
    self.assertEquals("603861", document['pacer_dm_id'])
    self.assertEquals("2010-01-07", document['date_filed'])
    self.assertEquals("Order on Motion for Hearing, Order on Motion to Amend/Correct, Order on Motion to Remand to State Court, Order on Motion to Strike", document['long_desc'])

    self.assertEquals("akd", dockets[5].get_court())
    self.assertEquals("15580", dockets[5].get_casenum())
    casemeta = dockets[5].get_casemeta()
    self.assertEquals("USA v. Celestine et al", casemeta['case_name'])
    self.assertEquals("3:2009-cr-00065-HRH", casemeta['docket_num'])
    self.assertEquals(None, casemeta.get("case_cause"))
    self.assertEquals(None, casemeta.get("nature_of_suit"))
    self.assertEquals(1, len(dockets[5].documents))

    document = dockets[5].documents['135-0']
    self.assertEquals("135", document['doc_num'])
    self.assertEquals("0", document['attachment_num'])
    self.assertEquals("794", document['pacer_de_seq_num'])
    self.assertEquals("616260", document['pacer_dm_id'])
    self.assertEquals(datetime.date.today().isoformat(), document['date_filed'])
    self.assertEquals("Order on Motion for Bill of Particulars, Order on Motion for Joinder", document['long_desc'])

    #Sometimes the document url case id does not match the court case id
    #  In these cases we want to use the parent case number, but also have access to the child casenum
    self.assertEquals("akd", dockets[2].get_court())
    self.assertEquals("4655", dockets[2].get_casenum())
    casemeta = dockets[2].get_casemeta()
    self.assertEquals("USA v. Kott et al", casemeta['case_name'])
    self.assertEquals("3:2007-cr-00056-JWS", casemeta['docket_num'])
    self.assertEquals(1, len(dockets[2].documents))

    document = dockets[2].documents['429-0']
    self.assertEquals("429", document['doc_num'])
    self.assertEquals("0", document['attachment_num'])
    self.assertEquals("1946", document['pacer_de_seq_num'])
    self.assertEquals("606429", document['pacer_dm_id'])
    self.assertEquals("2010-01-13", document['date_filed'])
    self.assertEquals("Order on Motion to Dismiss", document['long_desc'])

    self.assertEquals("4656", document['casenum'])


    # Some dockets have a different linking format from akd. Let's test these out
    dockets = PP.parse_opinions(filebits["nysd.2009"], "nysd")
    self.assertEquals(5916, len(dockets) ) # number of entries in the opinions table

    
    self.assertEquals("nysd", dockets[0].get_court())
    self.assertEquals("53122", dockets[0].get_casenum())
    casemeta = dockets[0].get_casemeta()
    self.assertEquals("Kingsway Financial v. Pricewaterhouse, et al", casemeta['case_name'])
    self.assertEquals("1:03-cv-05560-RMB-HBP", casemeta['docket_num'])
    self.assertEquals("15:78m(a) Securities Exchange Act", casemeta["case_cause"])
    self.assertEquals("Securities/Commodities", casemeta["nature_of_suit"])
    self.assertEquals(1, len(dockets[0].documents))
    
    document = dockets[0].documents['380-0']
    self.assertEquals("380", document['doc_num'])
    self.assertEquals("0", document['attachment_num'])
    self.assertEquals("6095482", document['pacer_de_seq_num'])
    self.assertEquals("5453339", document['pacer_dm_id'])
    self.assertEquals("2009-01-05", document['date_filed'])
    self.assertEquals("Memorandum & Opinion", document['long_desc'])
    

    # Some sanity checks about iquery type opinion pages

    for docket in dockets:
        self.assertEquals(1, len(docket.documents))
        document = docket.documents.values()[0]
        casenum_diff = int(docket.get_casenum()) - int(document['casenum'])
        self.assertTrue(casenum_diff <= 0)



