from test_constants import *

from uploads.recap_config import config

from uploads.BeautifulSoup import BeautifulSoup,HTMLParseError, Tag, NavigableString
import uploads.ParsePacer as PP
import uploads.DocketXML as DocketXML
import re, os
#from lxml import etree

#from mock import patch, Mock

#from django.test.client import Client
#from django.utils import simplejson

#from uploads.models import Document, Uploader, BucketLock, PickledPut
#import uploads.InternetArchiveCommon as IACommon
#import uploads.InternetArchive as IA

import unittest
#import datetime
#import time

class TestParsePacer(unittest.TestCase):
  def setUp(self):
      pass


  def test_docket_output(self):
    docket_list = ["nysd.39589.html"]
    
    for filename in docket_list:
      court, casenum = filename.split(".")[:2]
      f = open("/".join([TEST_DOCKET_PATH, filename]))
      filebits = f.read()
      
      docket = PP.parse_dktrpt(filebits, court, casenum)

      docket_xml = docket.to_xml()
    
  def test_parse_dktrpt(self):
    test_dockets = ['mieb.600286.html']

    for filename in test_dockets:
      court, casenum = filename.split(".")[:2]
      f = open("/".join([BANK_TEST_DOCKET_PATH, filename]))
      filebits = f.read()
      
      docket = PP.parse_dktrpt(filebits, court, casenum)
    

  def test_all_bankruptcy_dockets_for_case_metadata(self):
    count =0
    no_assigned_to_dockets = ['njb.764045.html', 'flmb.923870.html']

    unknown_cases= []
    no_date_filed = []

    for filename in os.listdir(BANK_TEST_DOCKET_PATH):
       soup = _open_soup("/".join([BANK_TEST_DOCKET_PATH, filename]))

       court, casenum = filename.split(".")[:2]
       case_data = PP._get_case_metadata_from_dktrpt(soup, court)
	    
       try:
           print count, filename, court, casenum, case_data["docket_num"], case_data["case_name"],"::", case_data["assigned_to"]
       except KeyError:
	  pass
	    
       #self.assertTrue("date_case_filed" in case_data)
       self.assertTrue("docket_num" in case_data)
       self.assertTrue("case_name" in case_data)
       self.assertTrue("date_case_filed" in case_data)

       if filename not in no_assigned_to_dockets:
	    self.assertTrue("assigned_to" in case_data)
	    
       if "date_case_filed" not in case_data:
            no_date_filed.append(filename)

       if case_data["case_name"] == "Unknown Bankruptcy Case Title":
            unknown_cases.append( (filename, case_data["case_name"]))

       count+=1

    print "No Date filed:"
    for filename in no_date_filed:
	    print filename
	    
    print "\nUnknown casename cases:"
    for filename, name in unknown_cases:
       print filename, name
#	    self.assertNotEquals(case_data["case_name"],"Unknown Bankruptcy Case Title")

  def test_merge_dockets(self):
    no_parties_path = TEST_DOCKET_PATH + "noPartiesXML/"
    no_parties_list = ["cit7830", "cit7391", "caedSomeParties", "candSomeAttys"]
    no_parties_filebits = {}
    for xml in no_parties_list:
        f = open(no_parties_path + xml + ".xml")
	no_parties_filebits[xml] = f.read()
	f.close()
    docketfilebits = {}
     

    for docket in TEST_DOCKET_LIST:
	    f = open(TEST_DOCKET_PATH + docket + "docket.html")
	    docketfilebits[docket] = f.read()
	    f.close()

    # Test merging with no parties in original (olddocket)
    docket = PP.parse_dktrpt(docketfilebits["cit7830"],"cit", "7830")
    olddocket, err =  DocketXML.parse_xml_string(no_parties_filebits["cit7830"]) 

    # Sanity Check
    self.assertNotEquals([], docket.parties)
    self.assertEquals([], olddocket.parties)
    olddocket.merge_docket(docket)
    self.assertEquals(olddocket.parties, docket.parties)


    
    docket = PP.parse_dktrpt(docketfilebits["cit7391"],"cit", "7391")
    olddocket, err =  DocketXML.parse_xml_string(no_parties_filebits["cit7391"]) 

    # Sanity Check
    self.assertNotEquals([], docket.parties)
    self.assertEquals([], olddocket.parties)
    olddocket.merge_docket(docket)
    self.assertEquals(olddocket.parties, docket.parties)

    
    # Test merging with some parties in original (olddocket)
    docket = PP.parse_dktrpt(docketfilebits["caed"],"caed", "7830")
    olddocket, err =  DocketXML.parse_xml_string(no_parties_filebits["caedSomeParties"]) 
    # Sanity Check
    self.assertEquals(6, len(docket.parties))
    self.assertEquals(4, len(olddocket.parties))

    olddocket.merge_docket(docket)

    self.assertEquals(6, len(olddocket.parties))
    self.assertTrue(sorted(olddocket.parties) == sorted(docket.parties))

    # Test merging with same num of parties but different number of attorneys
    docket = PP.parse_dktrpt(docketfilebits["cand2"],"cand2", "7830")
    olddocket, err =  DocketXML.parse_xml_string(no_parties_filebits["candSomeAttys"]) 

    # Sanity
    self.assertEquals("James Brady", olddocket.parties[0]["name"])
    self.assertEquals(1, len(olddocket.parties[0]["attorneys"]))
    self.assertEquals(3, len(docket.parties[0]["attorneys"]))

    self.assertEquals(-1, olddocket.parties[0]["attorneys"][0]["attorney_role"].find("TERMINATED"))

    olddocket.merge_docket(docket)

    self.assertEquals(3, len(olddocket.parties[0]["attorneys"]))
    self.assertNotEquals(-1, olddocket.parties[0]["attorneys"][0]["attorney_role"].find("TERMINATED"))

#    print docket.to_xml()
#    print olddocket.to_xml()


  def test_bankruptcy_parties_info_from_dkrpt(self):
    bank_dockets_list = ["njb.658906", "mnb.325447", "mdb.532409", "nvb.242643", "mieb.600286", "mdb.541423"]

    bank_soups = {}
    for docket in bank_dockets_list:
        bank_soups[docket] = _open_soup(BANK_TEST_DOCKET_PATH + docket + ".html")

    # Normal bankruptcy proceedings
    parties = PP._get_parties_info_from_dkrpt(bank_soups["mdb.532409"], "mdb")
    self.assertEquals(len(parties), 3)
    self.assertEquals(parties[0]["name"], "Rodney K. Cunningham")
    self.assertEquals(parties[0]["type"], "Debtor")
    self.assertEquals(len(parties[0]["attorneys"]), 1)
    self.assertEquals(parties[0]["attorneys"][0]["attorney_name"], "Sopo Ngwa")
    self.assertEquals(parties[1]["name"], "Karen S. Cunningham")
    self.assertEquals(parties[1]["type"], "Debtor")
    self.assertEquals(len(parties[1]["attorneys"]), 1)
    self.assertEquals(parties[1]["attorneys"][0]["attorney_name"], "Sopo Ngwa")
    self.assertEquals(parties[2]["type"], "Trustee")
     
    parties = PP._get_parties_info_from_dkrpt(bank_soups["nvb.242643"], "nvb")
    self.assertEquals(len(parties), 4)
    self.assertEquals(parties[0]["name"], "PAUL OGALESCO")
    self.assertTrue("PRO SE" in parties[0]["attorneys"][0]["contact"])
    self.assertEquals(parties[0]["type"], "Debtor")
    self.assertEquals(len(parties[0]["attorneys"]), 1)
    self.assertEquals(parties[1]["name"], "RICK A. YARNALL")
    self.assertEquals(parties[1]["type"], "Trustee")
    self.assertTrue("TERMINATED" in parties[1]["extra_info"])

    # Adversary Proceeding type docket
    parties = PP._get_parties_info_from_dkrpt(bank_soups["njb.658906"], "njb")
    self.assertEquals(len(parties), 6)
    self.assertEquals(parties[0]["name"], "Richard A. Spair")
    self.assertEquals(parties[0]["type"], "Plaintiff")
    self.assertEquals(len(parties[0]["attorneys"]), 1)
    self.assertEquals(parties[0]["attorneys"][0]["attorney_name"], "Eugene D. Roth")
    self.assertEquals(parties[1]["attorneys"][1]["attorney_role"], "LEAD ATTORNEY")
    self.assertEquals(parties[3]["name"], "Albert Russo")
    self.assertEquals(parties[3]["type"], "Trustee")


    parties = PP._get_parties_info_from_dkrpt(bank_soups["mnb.325447"], "mnb")
    self.assertEquals(len(parties), 2)
    self.assertEquals(parties[0]["name"], "RANDALL L SEAVER")
    self.assertEquals(parties[0]["type"], "Plaintiff")
    self.assertEquals(parties[0]["extra_info"], "101 W. Burnsville Pkwy., Suite 201\nBurnsville, MN 55337")
    self.assertEquals(len(parties[0]["attorneys"]), 1)
    self.assertEquals(parties[0]["attorneys"][0]["attorney_name"], "Matthew R. Burton")
    
    parties = PP._get_parties_info_from_dkrpt(bank_soups["mieb.600286"], "mieb")
    

    miebfilebits = open(BANK_TEST_DOCKET_PATH+ "mieb.600286" + ".html").read()

    miebdocket = PP.parse_dktrpt(miebfilebits, "mieb", "600286")
    
    # mdb Adversary proceedings have slightly different formats, more similar to normal bank, but still different enough to crash parsepacer
    parties = PP._get_parties_info_from_dkrpt(bank_soups["mdb.541423"], "mdb")
    self.assertEquals(len(parties), 3)
    self.assertEquals(parties[0]["name"], "Metamorphix, Inc.")
    self.assertEquals(parties[0]["type"], "Plaintiff")
    self.assertEquals(parties[0]["extra_info"], "Metamorphix, Inc.\nAttn: Dr. Edwin Quattlebaum\n8000 Virginia Manor Road\nBeltsville, MD 20705")
    self.assertEquals(len(parties[0]["attorneys"]), 2)
    self.assertEquals(parties[0]["attorneys"][0]["attorney_name"], "Peter D. Guattery")
    self.assertEquals(parties[1]["name"], "Edwin Quattlebaum")
    self.assertEquals(parties[1]["type"], "Plaintiff")
    self.assertEquals(parties[2]["name"], "Theresa Brady")
    self.assertEquals(parties[2]["type"], "Defendant")


  def test_bankruptcy_relative_doc1_links(self):
    relfilebits = open(BANK_TEST_DOCKET_PATH+ "flsb.575106" + ".html").read()
    reldocket = PP.parse_dktrpt(relfilebits, "flsb", "575106")
    self.assertEquals(len(reldocket.documents), 20)
    document = reldocket.documents['1-0']
    self.assertEquals("1", document['doc_num'])
    self.assertEquals("0", document['attachment_num'])
    self.assertEquals("050020328570", document['pacer_doc_id'])
    self.assertEquals("2011-12-30", document['date_filed'])
    self.assertEquals("Chapter 7 Voluntary Petition . [Fee Amount $306] (Segaul, John) (Entered: 12/30/2011)", document['long_desc'])


  def test_all_bankruptcy_dktrpts_for_parties_basics(self):
    count =0

    no_parties_dockets = []
    one_parties_dockets = []

    for filename in os.listdir(BANK_TEST_DOCKET_PATH):
       court, casenum = filename.split(".")[:2]
       soup = _open_soup("/".join([BANK_TEST_DOCKET_PATH, filename]))

       parties = PP._get_parties_info_from_dkrpt(soup,court) 

       if len(parties)==0:
           no_parties_dockets.append(filename)
       if len(parties) == 1: 
	   one_parties_dockets.append(filename)

    print ""
    print "Dockets with no parties:"
    for filename in no_parties_dockets:
         print filename

    print "Dockets with only one party (possible error): "
    for filename in one_parties_dockets:
	 print filename

	  


  def test_get_parties_info_from_dkrpt(self): 
    testdockets = {}
    for docket in TEST_DOCKET_LIST:
	    testdockets[docket] = _open_soup(TEST_DOCKET_PATH + docket + "docket.html")

    parties = PP._get_parties_info_from_dkrpt(testdockets["txed"], "txed")
    self.assertEquals(len(parties), 14)
    self.assertEquals(parties[0]["name"], "AOL LLC")
    self.assertEquals(parties[0]["extra_info"], "TERMINATED: 03/26/2008")
    self.assertEquals(parties[2]["type"], "Mediator")
    self.assertEquals(parties[2]["name"], "James W. Knowles")

    parties = PP._get_parties_info_from_dkrpt(testdockets["deb"], "deb")

    self.assertEquals(len(parties), 9)
    self.assertEquals(parties[0]["name"], "American Business Financial Services, Inc., a Delaware Corporation")
    self.assertEquals(parties[0]["type"], "Debtor")
    self.assertEquals(len(parties[0]["attorneys"]), 9)
    self.assertEquals(parties[0]["attorneys"][0]["attorney_name"], "Bonnie Glantz Fatell")
    self.assertEquals(parties[0]["attorneys"][0]["attorney_role"], "TERMINATED: 04/11/2006")
    self.assertEquals(len(parties[1]["attorneys"]), 11)
    self.assertEquals(len(parties[1]["attorneys"]), 11)

    
    parties = PP._get_parties_info_from_dkrpt(testdockets["almb"], "almb")

    self.assertEquals(len(parties), 2)
    self.assertEquals(parties[0]["name"], "Ruthie Harris")
    # Should be no attorneys object
    self.assertEquals(parties[1].get("attorneys"), None)


    parties = PP._get_parties_info_from_dkrpt(testdockets["almd"], "almd")

    self.assertEquals(len(parties), 2)
    self.assertEquals(parties[0]["name"], "Joyce Efurd")
    self.assertEquals(parties[0]["type"], "Plaintiff")
    self.assertEquals(len(parties[0]["attorneys"]), 3)
    self.assertEquals(parties[0]["attorneys"][0]["attorney_name"], "Allen Durham Arnold")
    self.assertEquals(parties[0]["attorneys"][0]["attorney_role"], "LEAD ATTORNEY\nATTORNEY TO BE NOTICED")
    self.assertEquals(len(parties[1]["attorneys"]), 3)
    # Should be no extra_info
    self.assertEquals(parties[0].get("extra_info"), None)
    
    parties = PP._get_parties_info_from_dkrpt(testdockets["cit"], "cit")
    self.assertEquals(len(parties), 4)
    self.assertEquals(parties[0]["name"], "New Hampshire Ball Bearing, Inc.")
    self.assertEquals(parties[0]["type"], "Plaintiff")
    self.assertEquals(len(parties[0]["attorneys"]), 1)
    self.assertEquals(parties[0]["attorneys"][0]["attorney_name"], "Frank H. Morgan")
    self.assertEquals(parties[0]["attorneys"][0]["attorney_role"], "LEAD ATTORNEY\nATTORNEY TO BE NOTICED")
#    self.assertEquals(parties[2]["name"], "United States Customs and Border Protection")
    self.assertEquals(len(parties[2]["attorneys"]), 1)
    
    # This document has no parties, but it shouldn't break anything when doing that
    parties = PP._get_parties_info_from_dkrpt(testdockets["cit2"], "cit")
    self.assertEquals(len(parties), 0)

    """ this docket doesn't work - errors in creating beautiful soup
    parties = PP._get_parties_info_from_dkrpt(testdockets["akd"], "akd")
    print_parties(parties)
    self.assertEquals(len(parties), 4)
    self.assertEquals(parties[0]["name"], "West American Insurance Company")
    self.assertEquals(parties[0]["type"], "Plaintiff")
    self.assertEquals(len(parties[0]["attorneys"]), 1)
    self.assertEquals(parties[0]["attorneys"][0]["attorney_name"], "Brewster H. Jamieson")
    self.assertEquals(parties[0]["attorneys"][0]["attorney_role"], "LEAD ATTORNEY\nATTORNEY TO BE NOTICED")
    self.assertEquals(len(parties[1]["attorneys"]), 0)
    """
    parties = PP._get_parties_info_from_dkrpt(testdockets["cand"], "cand")
    self.assertEquals(len(parties), 3)
    self.assertEquals(parties[0]["name"], "John Michael Balbo")
    self.assertEquals(parties[0]["type"], "Petitioner")
    self.assertTrue("PRO SE" in parties[0]["attorneys"][0]["contact"])
    self.assertEquals(len(parties[0]["attorneys"]), 1)
    self.assertEquals(parties[1]["extra_info"], "Secretary CDCR")

    parties = PP._get_parties_info_from_dkrpt(testdockets["cand2"], "cand")
    self.assertEquals(len(parties), 4)
    self.assertEquals(parties[0]["name"], "James Brady")
    self.assertEquals(parties[0]["type"], "Plaintiff")
    self.assertEquals(parties[1]["name"], "Sarah Cavanagh")
    self.assertEquals(parties[1]["type"], "Plaintiff" )
    self.assertEquals(parties[1]["extra_info"], "individually and on behalf of all others similarly situated" )
    self.assertEquals(len(parties[0]["attorneys"]), 3)
    self.assertEquals(parties[2]["name"], "Deloitte & Touche LLP")
    self.assertEquals(parties[2]["extra_info"], "a limited liability partnership")
    self.assertEquals(parties[3]["name"], "Deloitte Tax LLP")
    self.assertEquals(parties[3]["extra_info"], "TERMINATED: 08/14/2008")


    # There is extra metadata in this one that doesn't appear in others - Pending courts, highest offense level, disposition, etc, not collecting those currently
   # parties = PP._get_parties_info_from_dkrpt(testdockets["cand3"], "cand")
   # self.assertEquals(len(parties), 2)
   # self.assertEquals(len(parties[0]["attorneys"]), 1)
   # self.assertEquals(parties[0]["name"], "Gustavo Alfaro-Medina")

    parties = PP._get_parties_info_from_dkrpt(testdockets["caed"], "caed")
    self.assertEquals(len(parties), 6)
    self.assertEquals(len(parties[0]["attorneys"]), 1)
    self.assertEquals(parties[0]["name"], "Corey Mitchell")
    self.assertEquals(parties[1]["extra_info"], "Correctional Officer")

    parties = PP._get_parties_info_from_dkrpt(testdockets["ded"], "ded")
    self.assertEquals(len(parties), 4)
    self.assertEquals(len(parties[0]["attorneys"]), 2)
    self.assertEquals(parties[0]["name"], "Cubist Pharmaceuticals Inc.")

    parties = PP._get_parties_info_from_dkrpt(testdockets["cacd"], "cacd")
    self.assertEquals(len(parties), 18)
    self.assertEquals(len(parties[0]["attorneys"]), 2)
    self.assertEquals(parties[0]["name"], "LA Printex Industries Inc")


  # Some dockets use multiple separate tables for parties, not just one table
  def test_get_parties_info_from_dkrpt_multiple_tables(self): 
    the_soup = _open_soup(TEST_DOCKET_PATH + "mad.137971.html")
    parties = PP._get_parties_info_from_dkrpt(the_soup, "mad")
    self.assertEquals(len(parties), 4)
    
    self.assertEquals(parties[0]["name"], "Aaron Swartz")
    self.assertEquals(parties[0]["extra_info"], "TERMINATED: 01/14/2013")
    self.assertEquals(len(parties[0]["attorneys"]), 6)

    self.assertEquals(parties[1]["name"], "Massachusetts Institute of Technology")
    self.assertEquals(len(parties[1]["attorneys"]), 2)
    self.assertEquals(parties[1]["type"], "Interested Party")

    self.assertEquals(parties[2]["name"], "JSTOR")
    self.assertEquals(len(parties[2]["attorneys"]), 1)
    self.assertEquals(parties[2]["type"], "Interested Party")
    
    self.assertEquals(parties[3]["name"], "USA")
    self.assertEquals(len(parties[3]["attorneys"]), 3)
    self.assertEquals(parties[3]["type"], "Plaintiff")
    self.assertEquals(parties[3]["attorneys"][0]["attorney_name"], "Jack W. Pirozzolo")
    self.assertEquals(parties[3]["attorneys"][1]["attorney_name"], "Scott Garland")
    self.assertEquals(parties[3]["attorneys"][2]["attorney_name"], "Stephen P. Heymann")


def _open_soup(filename):
    f = open(filename)
    filebits = f.read()

    try:
        the_soup = BeautifulSoup(filebits, convertEntities="html")
    except TypeError:
        # Catch bug in BeautifulSoup: tries to concat 'str' and 'NoneType' 
        #  when unicode coercion fails.
        message = "DktRpt BeautifulSoup error %s.%s" % \
            (court, casenum)
        logging.warning(message)
        
        filename = "%s.%s.dktrpt" % (court, casenum)
        try:
            error_to_file(filebits, filename)
        except NameError:
            pass
        
        return None

    except HTMLParseError:
        # Adjust for malformed HTML.  Wow, PACER.

        # Strip out broken links from DktRpt pages
        badre = re.compile("<A HREF=\/cgi-bin\/.*\.pl[^>]*</A>")
        filebits = badre.sub('', filebits)

        filebits = filebits.replace("&#037; 20", 
                                    "&#037;20")
        filebits = filebits.replace(" name=send_to_file<HR><CENTER>", 
                                    " name=send_to_file><HR><CENTER>")

	bad_end_tag_re = re.compile("</font color=.*>")

	filebits = bad_end_tag_re.sub("</font>", filebits)
        try:
            the_soup = BeautifulSoup(filebits, convertEntities="html")
        except HTMLParseError, err:

            message = "DktRpt parse error. %s %s line: %s char: %s." % \
                (filename, err.msg, err.lineno, err.offset)
            print message

	    print court
        
            return None

    return the_soup

