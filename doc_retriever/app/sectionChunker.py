from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from decorate_document import Document_decorator
import re

class SectionChunker:
    
    def __init__(self, embedder):
        #create embedder object
        self.__embedder=embedder
        self.__document_decorator=Document_decorator(self.__embedder)
        self.keyword=None
        self.sha1=None

    def get_document_chunks(self, content, page_title, page_id, sha1):
        #st.write("First version of the document chunks")
        chunks=self.get_sections(content, page_title)
        chunks=self.embed_sections(chunks)
        chunks=self.__document_decorator.add_metadata_v2(chunks, "web", sha1,page_title, page_id)
        return chunks
    
    def get_document_chunks_v2(self, list_of_sections, page_title, page_id, sha1, logger):
        relevant_section_indeces=logger.get_relevant_section_of_a_page(list_of_sections)
        chunks=self.get_sections_v2(relevant_section_indeces, list_of_sections, page_title, logger, page_id )
        chunks=self.embed_sections(chunks)
        chunks=self.__document_decorator.add_metadata_v2(chunks, "web", sha1,page_title, page_id)
        return chunks
    
    def get_sections_v2(self, relevant_section_indeces, list_of_sections, page_title, logger, page_id):
        sections_info=[]
        for index in relevant_section_indeces:
          section_info=logger.get_section_content(page_id, index)
          sections_info.extend(self.check_len_v2([Document(page_content=section_info['parse']['wikitext']['*'])], 
                                                 list_of_sections['parse']['sections'][index-1]['anchor'], 
                                                 page_title,
                                                 list_of_sections['parse']['sections'][index-1]['line']))
        return sections_info

    def check_len_v2(self, document, anchor, page_title, line):
        # per ogni sezioni veririco se eccede nella lunghezza massima
        if len(document[0].page_content)*0.75>1024:
            # create chunks
            docs_split=self.__split_document_by_recursive(document, 1024, 50)
            # get new embeddings for the new chunks
            return self.__get_new_chunk_v2(docs_split, anchor, page_title, line)
        else:
            return self.__get_new_chunk_v2(document, anchor, page_title)
        
    
    def __get_new_chunk_v2(self, splitted_documents, anchor, page_title, line=""):
        sections=[]
        # se ci sono più sottosezioni indico che parte della sottosezione è
        # in ogni caso inserisco anche il titolo generale della pagine in cui si trova
        for index, doc in enumerate(splitted_documents):
            if index >= 1:
                modified_content=f"{page_title}{"\n"}{line}{" parte "}{str(index+1)}{"\n"}{doc.page_content}"
            else:
                modified_content=f"{page_title}{"\n"}{doc.page_content}"
            doc_section = {'section': modified_content,'anchor':anchor}
            sections.append(doc_section)
        return sections
    
    
    #I metodi non etichettati con v_2 indicano i metodi che NON si basano sulle sezioni prese tramite le API di mediawiki
    #alcune pagine infatti non hanno sezioni, ma solo tabelle, i cui identificativi delle righe sono identificate tramite [[]]
    def get_sections(self, content, page_title):
        # Find title
        sections = []
        sub_secions = re.findall(r'\[\[(.*?)\]\]', content)
        #se non ci sono sezioni all'interno della pagina
        if len(sub_secions)==0:
                sections.extend(self.check_len([Document(page_content=content)], page_title))
        else:
            # Dividi il contenuto in base alle sezioni
            for i in range(len(sub_secions)):
                start_section = content.find("[["+sub_secions[i]+"]]")
                if i < len(sub_secions) - 1:
                    end_section = content.find("[["+sub_secions[i+1]+"]]")
                #se è l'ultimo titolo basta prendere la lunghezza del chunk
                else:
                    end_section = len(content)
                #il -2 è per le [[ iniziali
                section_content = content[(start_section)-2:end_section-2]
                sections.extend(self.check_len([Document(page_content=section_content)], page_title))
        return sections
    
    # alcune pagine non hanno ne sezioni ne tabelle o hanno una formattazione particolari
    # vengono semplicemente splittate per carattere
    def unregular_page(self, page, page_title, sha1, page_id):
        document=[Document(page_content=page)]
        if len(document[0].page_content)*0.75>1024:
            # create chunks
            docs_split=self.__split_document_by_recursive(document, 1024, 50)
            # get new embeddings for the new chunks
            chunks= self.__get_new_chunk(docs_split, page_title)
        else:
            chunks= self.__get_new_chunk(document)
        chunks=self.embed_sections(chunks)
        chunks=self.__document_decorator.add_metadata_v2(chunks, "web", sha1,page_title, page_id)
        return chunks

    def check_len(self, document, page_title):
        if len(document[0].page_content)*0.75>1024:
            #Trovo il titolo della riga della tabella
            end_title = document[0].page_content.find('[[', document[0].page_content.find(']]') + 1)
            if end_title != -1:
                modified_document = document[0].page_content[:end_title] + " parte " +str(1) + document[0].page_content[end_title:]
            #questo else serve se non si hanno ne sezioni ne titoli ne tabelle
            else:
                modified_document=document[0].page_content
            # create chunks
            docs_split=self.__split_document_by_recursive([Document(page_content=modified_document)], 1024, 50)
            # get new embeddings for the new chunks
            return self.__get_new_chunk(docs_split, page_title)
        else:
            return self.__get_new_chunk(document)


    def __get_new_chunk(self, splitted_documents, title=""):
        sections=[]
        for index, doc in enumerate(splitted_documents):
            if index >= 1:
                modified_content=title+"parte "+str(index+1)+"\n"+doc.page_content
                doc_section = {'section': modified_content,
                               'anchor': ""}
            else:
                doc_section = {'section': title+"\n"+doc.page_content,
                               'anchor': ""}
            sections.append(doc_section)
        return sections
    
    def embed_sections(self, sections):
        embeddings=self.__embedder.do_embedding_sections(sections)
        for i, section in enumerate(sections):
            section['embedding'] = embeddings[i]
        return sections
    
    def __split_document_by_recursive(self, document, chunk_size, overlap):
        # create chunks
        text_splitter=RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=overlap,
            separators=[
            ".",
        ],
        )
        docs_split=text_splitter.split_documents(document)
        return docs_split
    

