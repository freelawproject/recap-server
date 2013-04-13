# Run tests by doing 'python manage.py test' in the recap-server directory
# Note that some tests in TestParsePacer take a long time, you may want to comment it
# out from this file while actively developing. Alternatively, refactor those tests
# so they don't take so long.

from test_parse_pacer import TestParsePacer
from test_views import TestViews
from test_upload_view import TestUploadView
from test_query_cases_view import TestQueryCasesView
from test_third_party_views import TestThirdPartyViews
from test_query_view import TestQueryView
from test_add_doc_meta_view import TestAddDocMetaView
from test_parse_opinions import TestParseOpinions

#from test_pacer_client import TestPacerClient
#from test_opinions_downloader import TestOpinionsDownloader
#from test_ia_uploader import TestIAUploader
from test_docket_xml import TestDocketXml
from test_document_manager import TestDocumentManager
