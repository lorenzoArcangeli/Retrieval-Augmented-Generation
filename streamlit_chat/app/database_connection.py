from qdrant_client import QdrantClient,models
from langchain.vectorstores import Qdrant
from enum import Enum
from langchain.schema import Document

class Check_Page(Enum):
    NEED_MODIFY_EMBEDDING = 1
    NO_NEED = 2
    NEED_EMBEDDING=3

class Database_connector:

    def __init__(self, host, port):
        self.__host=host
        self.__port=port
        self.__qdrant_client=None
        self.__collection=None
        self.__db=None

    def connect(self, embedder, collection_name="RAG"):
        self.__qdrant_client= QdrantClient(host=str(self.__host), port=self.__port)
        self.__db=Qdrant(
            client=self.__qdrant_client, 
            collection_name=collection_name, 
            embeddings=embedder.get_embedding_funciont()
        )
        self.__qdrant_client.update_collection(
            collection_name=collection_name,
            optimizer_config=models.OptimizersConfigDiff(
                indexing_threshold=20000
            ),
            quantization_config=models.BinaryQuantization(
                binary=models.BinaryQuantizationConfig(always_ram=True),
            ),
        )

    def get_retriever_by_semantic_search(self, query):
        points=self.__qdrant_client.search(
            collection_name="RAG",
            query_vector=query,
            search_params=models.SearchParams(
                quantization=models.QuantizationSearchParams(
                    ignore=False,
                    rescore=True,
                    oversampling=2.0,
                )
            ),
            limit=15
        )
        documents = [Document(page_content=point.payload['page_content'], metadata=point.payload['metadata']) for point in points]
        return documents
        
    '''
    # non usato
    def get_document_based_on_keyword(self, keyword):
        keyword_where_condition=self.__get_multiple_where_condition(keyword)
        keyword_result=self.__collection.get(
            where=keyword_where_condition
        )
        # list of document
        return keyword_result
    '''

    '''
    def __get_multiple_where_condition(self, keyword):
        or_clause = []
        # insert string ad dictinary in the list
        for parola in lista_ricerche:
            or_clause.append({"contains": parola})
        # final dictionary
        where_clause = {"$or": or_clause}
    '''
    
    '''
    # non usato
    def remove_elements(self):
        numeri = [str(numero) for numero in range(17, 35)]
        self.__collection.delete(
            ids=numeri
        )
    '''
    '''
    prova per avere clause where composte
    where_clause = {
        "$or" : [
            {"contains" : "first_string"}, 
            {"contains" : "second_string"}, 
        ]
    }

    results = collection.query(
        query_texts="phone manufacturers", 
        n_results=5, 
        where = where_clause
    )
    '''
        
