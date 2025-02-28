from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams
from langchain.vectorstores import Qdrant
from qdrant_client.http.models import PointStruct
from qdrant_client.http import models
from enum import Enum
from dotenv import load_dotenv
import os



class Check_Page(Enum):
    NEED_MODIFY_EMBEDDING = 1
    NO_NEED = 2
    NEED_EMBEDDING=3

class Database_connector:

    def __init__(self, host, port):
        self.__host=host
        self.__port=port
        self.__qdrant_client=None
        self.__db=None

    def connect(self):
        self.__qdrant_client= QdrantClient(str(self.__host), port=int(self.__port))
    
    def create_collection(self, collection_name):
        self.__collection = self.__qdrant_client.create_collection(
            collection_name=collection_name,
             vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
        )


    def add_elements_to_collection(self, chunks, collection_name="RAG"):
        points=[]
        result = self.list_extract_from_dict(chunks)
        combined_sentences_list, combined_sentence_embeddings_list, uuid_list = result
        metadatas=self.get_metadata(chunks)
        for i, uuid in enumerate(uuid_list):
            points.append(PointStruct(id=uuid, vector=combined_sentence_embeddings_list[i],
                        #i metadata li uso per il retriever, quello che estrae è infatti un documento con il page_content e i metadata, se non trova il campo
                        #metadata come dict (con dentro il campo title) da errore. Il resto del payload lo uso come filtering
                          payload={
                                "page_content": combined_sentences_list[i],
                                "metadata":{
                                    'source': str(metadatas[i]['source'])
                                    },
                                "type": str(metadatas[i]['type']),
                                "sha1": str(metadatas[i]['sha1']),
                                "source": str(metadatas[i]['source']),
                                #nel caso dei pdf source e title hanno lo stesso valore
                                "title":str(metadatas[i]['title']),
                                #nel caso dei pdf id_page==id
                                "id_page": str(metadatas[i]['id']),
                                "id": str(uuid)
                          }))
            
        self.__qdrant_client.upsert(
            collection_name=collection_name,
            wait=True,
            points=points
        )
    
    def get_metadata(self, chunks):
        # extract metadata from chunks
        metadata_list = [] 
        for chunk in chunks:
            metadata = {
                'type': chunk['type'],
                'sha1': chunk['sha1'],
                'title': chunk['title'],
                'id':chunk['id'],
                'source':chunk['source']
            }
            metadata_list.append(metadata)
        return metadata_list
      
    def list_extract_from_dict(self, chunks):
        # extract lists from chunks
        combined_sentences_list = []
        combined_sentence_embeddings_list = []
        ids_list = []

        for chunk in chunks:
            # extract fields
            combined_sentences_list.append(chunk['section'])
            combined_sentence_embeddings_list.append(chunk['embedding'])
            ids_list.append(str(chunk['uuid']))

        return combined_sentences_list, combined_sentence_embeddings_list, ids_list
    
    def get_collection_info(self, collection_name="RAG"):
        return self.__qdrant_client.get_collection(collection_name=collection_name)
    
    def scroll_collection(self, collection_name="RAG"):
        result= self.__qdrant_client.scroll(collection_name=collection_name, limit=8000)
        records=result[0]
        metadatas=[]
        for record in records:
            metadatas.append(record.payload['metadata']['source'])

    def check_page_by_title(self, page_title, sha1):
        points=self.get_id_by_title(page_title)
        return self.checking_result(sha1, points)
    
    def get_id_by_title(self, title, collection_name="RAG"):
        result=self.__qdrant_client.scroll(
            collection_name=collection_name,
            limit=10000,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="title",
                        match=models.MatchValue(value=str(title)),
                    )   
                ]
            )
        )
        return result[0]
    
    def checking_result(self, sha1, points):
        if len(points)==0:
            return Check_Page.NEED_EMBEDDING, None
        else:
            for point in points:
                if point.payload['sha1']==str(sha1):
                    return Check_Page.NO_NEED, None
        uuids=[]
        for point in points:
            uuids.append(point.payload['id'])
        return Check_Page.NEED_MODIFY_EMBEDDING, uuids
    
    def get_id_by_id(self, id, collection_name="RAG"):
        result=self.__qdrant_client.scroll(
            collection_name=collection_name,
            limit=10000,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="id_page",
                        match=models.MatchValue(value=str(id)),
                    )   
                ]
            )
        )
        return result[0]

    def check_page_by_id(self, id, sha1):
        points=self.get_id_by_id(id)
        return self.checking_result(sha1, points)


    def check_pdf(self, pdf_path, title, decorator):
        points=self.get_id_by_title(title)
        pdf_sha1=decorator.compute_sha1(pdf_path)
        return self.checking_result(pdf_sha1, points)

    def modify_elements_of_collection(self, chunks, ids, collection_name="RAG"):
        self.__qdrant_client.delete(
            collection_name=collection_name,
            points_selector=models.PointIdsList(
                points=ids,
            )
        )
        self.add_elements_to_collection(chunks)


    #metodi per aggiornare i titoli dei pdf in modo da hostarli

    def update_pdf_metadata(self, collection_name="RAG"):
        load_dotenv()
        pdf_initial_path=os.getenv("PDF_HOST")
        result=self.__qdrant_client.scroll(
            collection_name=collection_name,
            limit=10000,
            scroll_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="type",
                        match=models.MatchValue(value="pdf"),
                    )   
                ]
            )
        )
        points=result[0]
        uuids=[]
        payloads=[]
        for point in points:
            url = str(point.payload['title'])
            last_index = url.rfind("/")
            file_name = pdf_initial_path+url[last_index + 1:].replace(" ", "_")
            print(file_name)
            point.payload['title']=file_name
            point.payload['source']=file_name
            point.payload['metadata']={
                                    'source': file_name
                                    }
            payloads.append(point.payload)
            uuids.append(point.payload['id'])
        self.update_payloads(uuids, payloads)
 
    def update_payloads(self, uuids, payloads, collection_name="RAG"):
        for i, uuid in enumerate(uuids):
            uuid_list=[]
            uuid_list.append(uuid)
            print(uuid_list)
            print(payloads[i])
            self.__qdrant_client.overwrite_payload(
                collection_name=collection_name,
                payload=payloads[i],
                points=uuid_list
            )
            