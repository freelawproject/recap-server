import os

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
TEST_SUPPORT_PATH = os.path.join(CURRENT_PATH, "../../test_support/")
TEST_OPINION_PATH = TEST_SUPPORT_PATH + "testopinions/"
TEST_DOC1_PATH = TEST_SUPPORT_PATH + "testdoc1s/"
TEST_PDF_PATH = TEST_SUPPORT_PATH + "testpdfs/"
TEST_DOCKET_PATH  = TEST_SUPPORT_PATH + "testdockets/"
TEST_DOCUMENT_PATH = TEST_SUPPORT_PATH + "testdocuments/"
BANK_TEST_DOCKET_PATH = TEST_DOCKET_PATH + "bankruptcydockets/"

TEST_DOCKET_LIST = ["cacd", "deb", "almb", "almd", "alsd", "cit", "cit2", "cit7830", "cit7391", "cand", "cand2", "cand3", "caed", "ded", "flsb", "txed"] #akd doesn't parse

