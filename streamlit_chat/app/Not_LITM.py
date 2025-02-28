from langchain_core.retrievers import BaseRetriever
#from pydantic import BaseModel
from langchain_community.document_transformers import (
    LongContextReorder
)
from database_connection import Database_connector
from embedder import Embedder

#class Not_LITM_retriever(BaseRetriever, BaseModel) questo da problemi con docker
class Not_LITM_retriever(BaseRetriever):
    #questo glielo passso quando lo invoco mettendo attributo=attributo_passato
    database_connection: Database_connector
    embedder: Embedder

    #quest metodo viene chiamato in automatico avendo il retriever
    def get_relevant_documents(self, query):
        query_vector=self.embedder.embed_query(query)
        retrieved_document=self.get_documents_by_semantic_search(query_vector)
        #st.write(retrieved_document)
        #Lost in the middle problem
        reordered_docs=self.__lost_in_middle_problem(retrieved_document)
        return reordered_docs
        
    def get_documents_by_semantic_search(self, query_vector):
        result =self.database_connection.get_retriever_by_semantic_search(query_vector)
        return result

    def __lost_in_middle_problem(delf, reranked_docs):
        reordering = LongContextReorder()
        reordered_docs = reordering.transform_documents(reranked_docs)
        return reordered_docs