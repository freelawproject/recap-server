
import re
import logging

from django.utils import simplejson

from MySQLdb import IntegrityError

from uploads.models import Document, PickledPut
import InternetArchive as IA
import InternetArchiveCommon as IACommon
import ParsePacer
import DocketXML
import DocumentManager
import BucketLockManager

from recap_config import config
from settings import ROOT_PATH
import os

def is_pdf(mimetype):
    return mimetype == "application/pdf"

def is_html(mimetype):
    return mimetype.find("text/html") >= 0

def is_doc1_path(path):
    """ Returns true if path is exactly a doc1 path.
          e.g. /doc1/1234567890
    """
    doc_re = re.compile(r'^/doc1/\d+$')
    return bool(doc_re.match(path))

def is_doc1_html(filename, mimetype, url, casenum):
    """ Returns true if the metadata indicates a doc1 HTML file. """
    return is_doc1_path(filename) and is_html(mimetype) \
        and url is None and casenum is None

def docid_from_url_name(name_from_url):
    """ Extract the docid from a PACER URL name. """

    t = name_from_url.split("/")
    name_from_url = t.pop()
    t = name_from_url.split("?")

    return ParsePacer.coerce_docid(t[0])


def handle_upload(filedata, court, casenum, mimetype, url):
    """ Main handler for uploaded data. """

    try:
        filename = filedata['filename']
        filebits = filedata['content']
    except KeyError:
        message = "No filedata 'filename' or 'content' attribute."
        logging.error("handle_upload: %s" % message)
        return "upload: %s" % message

    if is_pdf(mimetype):
        message = handle_pdf(filebits, court, url)

    elif is_doc1_html(filename, mimetype, url, casenum):
        message = handle_doc1(filebits, court, filename)

    elif is_html(mimetype):
        if casenum:
            message = handle_docket(filebits, court, casenum, filename)
        else:
            message = "docket has no casenum."
            logging.error("handle_upload: %s" % message)
            return "upload: %s" % message

    else:
        message = "couldn't recognize file type %s" % (mimetype)
        logging.error("handle_upload: %s" % message)
        return "upload: %s" % message

    return message


def handle_pdf(filebits, court, url):
    """ Write PDF file metadata into the database. """

    # Parse coerced docid out of url
    try:
        docid = docid_from_url_name(url)
    except AttributeError:
        logging.warning("handle_pdf: no url available to get docid")
        return "upload: pdf failed. no url supplied."

    # Lookup based on docid b/c it's the only metadata we have
    #  Document exists if we've previously parsed the case's docket
    query = Document.objects.filter(docid=docid)
    try:
        doc = query[0]
    except IndexError:
        logging.info("handle_pdf: haven't yet seen docket %s" % (url))
        return "upload: pdf ignored."
    else:
        # Sanity check
        if doc.court != court:
            logging.error("handle_pdf: court mismatch (%s, %s) %s" %
                          (court, doc.court, url))
            return "upload: pdf metadata mismatch."

        casenum = doc.casenum
        docnum = doc.docnum
        subdocnum = doc.subdocnum
        sha1 = doc.sha1

    # Docket with updated sha1, available, and upload_date
    docket = DocketXML.make_docket_for_pdf(filebits, court, casenum,
                                           docnum, subdocnum, available=0)
    DocumentManager.update_local_db(docket)

    if docket.get_document_sha1(docnum ,subdocnum) != sha1:

        # Upload the file -- either doesn't exist on IA or has different sha1

        # Gather all the additional metadata we have
        #   - from the docket we just made
        doc_meta = docket.get_document_metadict(docnum, subdocnum)
        #   - from the database, if available
        if doc.docid:
            doc_meta["pacer_doc_id"] = doc.docid
        if doc.de_seq_num:
            doc_meta["pacer_de_seq_num"] = doc.de_seq_num
        if doc.dm_id:
            doc_meta["pacer_dm_id"] = doc.dm_id

        # Push the file to IA
        IA.put_file(filebits, court, casenum, docnum, subdocnum, doc_meta)

    # Whether we uploaded the file, push the docket update to IA.
    do_me_up(docket)

    logging.info("handle_pdf: uploaded %s.%s.%s.%s.pdf" % (court, casenum,
                                                           docnum, subdocnum))
    message = "pdf uploaded."

    response = {}
    response["message"] = message
    jsonout = simplejson.dumps(response)

    return jsonout

def handle_docket(filebits, court, casenum, filename):
    ''' Parse HistDocQry and DktRpt HTML files for metadata.'''

    #TK: Remove ^.* from regex when upgrading test client
    histdocqry_re = re.compile(r"HistDocQry_?\d*\.html$")
    dktrpt_re = re.compile(r".*DktRpt_?\d*\.html$")

    if histdocqry_re.match(filename):
        return handle_histdocqry(filebits, court, casenum)
    elif dktrpt_re.match(filename):
        return handle_dktrpt(filebits, court, casenum)

    message = "unrecognized docket file."
    logging.error("handle_docket: %s %s" % (message, filename))
    return "upload: %s" % (message)


def handle_dktrpt(filebits, court, casenum):

    if config['DUMP_DOCKETS'] and re.search(config['DUMP_DOCKETS_COURT_REGEX'], court):
        logging.info("handle_dktrpt: Dumping docket %s.%s for debugging" % (court, casenum))
        _dump_docket_for_debugging(filebits,court,casenum)

    docket = ParsePacer.parse_dktrpt(filebits, court, casenum)

    if not docket:
        return "upload: could not parse docket."

    # Merge the docket with IA
    do_me_up(docket)

    # Update the local DB
    DocumentManager.update_local_db(docket)

    response = {"cases": _get_cases_dict(casenum, docket),
                "documents": _get_documents_dict(court, casenum),
                "message":"DktRpt successfully parsed."}
    message = simplejson.dumps(response)

    return message

def handle_histdocqry(filebits, court, casenum):

    docket = ParsePacer.parse_histdocqry(filebits, court, casenum)

    if not docket:
        return "upload: could not parse docket."

    # Merge the docket with IA
    do_me_up(docket)

    # Update the local DB
    DocumentManager.update_local_db(docket)

    response = {"cases": _get_cases_dict(casenum, docket),
                "documents": _get_documents_dict(court, casenum),
                "message": "HistDocQry successfully parsed."}

    message = simplejson.dumps(response)

    return message


def handle_doc1(filebits, court, filename):
    """ Write HTML (doc1) file metadata into the database. """

    uncoerced_docid = docid_from_url_name(filename)
    main_docid = ParsePacer.coerce_docid(uncoerced_docid)

    query = Document.objects.filter(docid=main_docid)

    try:
        main_doc = query[0]
    except IndexError:
        logging.info("handle_doc1: unknown docid %s" % (main_docid))
        return "upload: doc1 ignored."
    else:
        casenum = main_doc.casenum
        main_docnum = main_doc.docnum

        # Sanity check
        if court != main_doc.court:
            logging.error("handle_doc1: court mismatch (%s, %s) %s" %
                          (court, main_doc.court, main_docid))
            return "upload: doc1 metadata mismatch."

    docket = ParsePacer.parse_doc1(filebits, court, casenum, main_docnum)

    if docket:
        # Merge the docket with IA
        do_me_up(docket)
         # Update the local DB
        DocumentManager.update_local_db(docket)

    response = {"cases": _get_cases_dict(casenum, docket),
                "documents": _get_documents_dict(court, casenum),
                "message": "doc1 successfully parsed."}
    message = simplejson.dumps(response)
    return message

def do_me_up(docket):
    ''' Download, merge and update the docket with IA. '''
    # Pickle this object for do_me_up by the cron process.

    court = docket.get_court()
    casenum = docket.get_casenum()

    docketname = IACommon.get_docketxml_name(court, casenum)

    # Check if this docket is already scheduled to be processed.
    query = PickledPut.objects.filter(filename=docketname)

    try:
        ppentry = query[0]
    except IndexError:
        # Not already scheduled, so schedule it now.
        ppentry = PickledPut(filename=docketname, docket=1)

        try:
            ppentry.save()
        except IntegrityError:
            # Try again.
            do_me_up(docket)
        else:
            # Pickle this object.
            pickle_success, msg = IA.pickle_object(docket, docketname)

            if pickle_success:
                # Ready for processing.
                ppentry.ready = 1
                ppentry.save()

                logging.info("do_me_up: ready. %s" % (docketname))
            else:
                # Pickle failed, remove from DB.
                ppentry.delete()
                logging.error("do_me_up: %s %s" % (msg, docketname))

    else:
        # Already scheduled.
        # If there is a lock for this case, it's being uploaded. Don't merge now
        locked = BucketLockManager.lock_exists(court, casenum)
        if ppentry.ready and not locked:
            # Docket is waiting to be processed by cron job.

            # Revert state back to 'not ready' so we can do local merge.
            ppentry.ready = 0
            ppentry.save()

            # Fetch and unpickle the waiting docket.
            prev_docket, unpickle_msg = IA.unpickle_object(docketname)

            if prev_docket:

                # Do the local merge.
                prev_docket.merge_docket(docket)

                # Pickle it back
                pickle_success, pickle_msg = \
                    IA.pickle_object(prev_docket, docketname)

                if pickle_success:
                    # Merged and ready.
                    ppentry.ready = 1
                    ppentry.save()
                    logging.info("do_me_up: merged and ready. %s" %(docketname))
                else:
                    # Re-pickle failed, delete.
                    ppentry.delete()
                    logging.error("do_me_up: re-%s %s" % (pickle_msg,
                                                          docketname))

            else:
                # Unpickle failed
                ppentry.delete()
                IA.delete_pickle(docketname)
                logging.error("do_me_up: %s %s" % (unpickle_msg, docketname))


        # Ignore if in any of the other three possible state...
        #   because another cron job is already doing work on this entity
        # Don't delete DB entry or pickle file.
        elif ppentry.ready and locked:
            pass
            #logging.debug("do_me_up: %s discarded, processing conflict." %
            #              (docketname))
        elif not ppentry.ready and not locked:
            pass
            #logging.debug("do_me_up: %s discarded, preparation conflict." %
            #              (docketname))
        else:
            logging.error("do_me_up: %s discarded, inconsistent state." %
                          (docketname))

def _get_cases_dict(casenum, docket):
    """ Create a dict containing the info for the case specified """
    cases = {}
    cases[casenum] = {}
    try:
        docketnum = docket.casemeta["docket_num"]
    except (KeyError, AttributeError):
        docketnum = ""

    cases[casenum]["officialcasenum"] = docketnum

    return cases

def _get_documents_dict(court, casenum):
    """ Create a dict containing the info for the docs specified """
    documents = {}

    query = Document.objects.filter(court=court, casenum=int(casenum))
    if query:
        for document in query:
            if document.docid:
                docmeta = {"casenum": document.casenum,
                           "docnum": document.docnum,
                           "subdocnum": document.subdocnum}

                if document.available:
                    docmeta.update({"filename": IACommon.get_pdf_url(document.court,
                                                 document.casenum,
                                                 document.docnum,
                                                 document.subdocnum),
                                    "timestamp": document.lastdate.strftime("%m/%d/%y")})
                documents[document.docid] = docmeta
    return documents

def _dump_docket_for_debugging(filebits, court, casenum):

    docketdump_dir = ROOT_PATH + '/debugdockets/'

    if len(os.listdir(docketdump_dir)) > config['MAX_NUM_DUMP_DOCKETS']:
        return


    dumpfilename = ".".join([court, casenum, "html"])

    f = open( docketdump_dir + dumpfilename, 'w')
    f.write(filebits)
    f.close()

