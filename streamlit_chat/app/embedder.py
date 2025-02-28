import os
from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv


class Embedder:

    def __init__(self):
        load_dotenv()
        os.environ['OPENAI_API_KEY'] = os.getenv("OPEN_AOI_KEY")
        self.__oaiembeds = OpenAIEmbeddings(model="text-embedding-ada-002")

    def do_embedding(self, sentences):
        embeddings = self.__oaiembeds.embed_documents([x['combined_sentence'] for x in sentences])
        return embeddings
    
    def get_embedding_funciont(self):
        return self.__oaiembeds
    
    def do_embedding_sections(self, sections):
        embeddings = self.__oaiembeds.embed_documents([section['section'] for section in sections])
        return embeddings
    
    def embed_query(self, query):
        return self.__oaiembeds.embed_query(query)
    
    