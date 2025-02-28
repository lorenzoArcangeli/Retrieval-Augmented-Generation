from database_connection import Database_connector
from embedder import Embedder
from UI_chat import UIChat
from Not_LITM import Not_LITM_retriever


def UI_chat():
    #localhost --> runno in locale
    #qdrant --> se lo runno da dokcer compose 
    database_connection=Database_connector("qdrant", 6333)
    embedder= Embedder()
    database_connection.connect(embedder, collection_name="RAG")
    not_lost_in_the_middle_retriever=Not_LITM_retriever(database_connection=database_connection, embedder=embedder)
    chat=UIChat(not_lost_in_the_middle_retriever)
    chat.chat()

if __name__ == '__main__':
    UI_chat()