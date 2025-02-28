from dotenv import load_dotenv
from logger import Logger
import os
from database_connection import Database_connector, Check_Page
from embedder import Embedder
from sectionChunker import SectionChunker
import sched, time
from pdf_formatter import PDF_formatter
from cosine_chunker import Cosine_chunker
from decorate_document import Document_decorator
import os
import glob
import shutil

def add_list_of_pages_check_sha1(page_titles, page_ids):
    index = 0
    for page_title in page_titles:
        embedding_phase(page_ids[index], page_title)
        index += 1
        time.sleep(1)
    embed_pdf()

def embedding_phase(page_id_by_index, page_title):
    page_json = logger.complete_json_by_id(page_id_by_index)
    last_version = logger.get_last_version(page_json)

    #same pages do not have content. Theese may cause an error
    if len(last_version['slots']['main']['content']) > 0:
        #check if the page is already present
        need_embedding, ids = database_connection.check_page_by_id(page_id_by_index, last_version['sha1'])
        if need_embedding != Check_Page.NO_NEED:
            #Page that do not respect the standard format
            if int(page_id_by_index)==int(8179) or int(page_id_by_index)==int(8365) or int(page_id_by_index)==int(8517):
                chunks=chunker.unregular_page(last_version['slots']['main']['content'], "ACCISE Webservices", last_version['sha1'], page_id_by_index)

            else:
                sections=logger.get_sections_of_a_page_id(page_id_by_index)
                #check if the page has section
                if len(sections['parse']['sections'])==0:
                    chunks = chunker.get_document_chunks(last_version['slots']['main']['content'], page_title, page_id_by_index, last_version['sha1'])
                else:
                    sha1=logger.get_last_version_sections(page_id_by_index)['sha1']
                    chunks=chunker.get_document_chunks_v2(sections, page_title, page_id_by_index, sha1, logger)
    
            if need_embedding == Check_Page.NEED_EMBEDDING:
                database_connection.add_elements_to_collection(chunks)
            else:
                database_connection.modify_elements_of_collection(chunks, ids)

def embed_pdf():
    formatter=PDF_formatter()
    document_decorator=Document_decorator(embedder)
    cosine_chunker=Cosine_chunker(embedder, document_decorator)
    folder_path = os.path.abspath("PDFs")
    new_folder_path=folder_path+"\\"+"elab"
    pdf_file = glob.glob(os.path.join(folder_path, '*.pdf'))

    for file in pdf_file:
        full_path=folder_path+"\\"+os.path.basename(file)
        #check if the pdf is already present
        need_embedding, ids = database_connection.check_pdf(full_path, os.path.basename(file), document_decorator)
        if need_embedding!=Check_Page.NO_NEED:
            document=formatter.get_formatted_content(full_path)
            chunks=cosine_chunker.get_document_chunks(document, os.path.basename(file), full_path)
            if need_embedding == Check_Page.NEED_EMBEDDING:
                database_connection.add_elements_to_collection(chunks)
            else:
                database_connection.modify_elements_of_collection(chunks, ids)
        old_file_path = os.path.join(folder_path, file)
        new_file_path = os.path.join(new_folder_path, os.path.basename(file))
        shutil.move(full_path, new_file_path)


def schedule_repeated_event(scheduler, interval, action, arguments=()):
    scheduler.enter(interval, 1, action, arguments)
    #re-schedule the event
    scheduler.enter(int(os.getenv("INTERVAL")), 1, schedule_repeated_event, (scheduler, interval, action, arguments))

def get_titles_and_ids():
    with open("Page_titles.txt", 'r') as file:
        # Read all the ids
        titles = file.readlines()
    with open("Page_ids.txt", 'r') as file:
        # Read all the titles
        ids = file.readlines()
    correct_titles = [line.strip() for line in titles]
    correct_ids = [line.strip() for line in ids]
    return correct_titles, correct_ids

if __name__ == '__main__':
    time.sleep(10)
    load_dotenv()
    logger = Logger(str(os.getenv("USERNAME_APRA")), str(os.getenv( "PASSWORD")), "https://wikidoc.apra.it/essenzia/api.php")
    logger.login()
    #localhost -->run in local
    #qdrant --> run using docker 
    database_connection=Database_connector("qdrant", 6333)
    database_connection.connect()
    embedder = Embedder()
    #read the ids/titles from file
    correct_titles, correct_ids=get_titles_and_ids()
    chunker = SectionChunker(embedder)
    formatter=PDF_formatter()
    document_decorator=Document_decorator(embedder)
    cosine_chunker=Cosine_chunker(embedder, document_decorator)
    my_scheduler = sched.scheduler(time.time, time.sleep)
    # Schedule the initial event
    schedule_repeated_event(my_scheduler, 0, add_list_of_pages_check_sha1, (correct_titles, correct_ids))
    # Run the scheduler
    my_scheduler.run()