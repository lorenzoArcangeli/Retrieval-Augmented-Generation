import streamlit as st
from langchain_openai import ChatOpenAI 
from langchain.llms import OpenAI
#from langchain.chat_models import ChatOpenAI # questo è deprecato
from langchain.chains import ConversationalRetrievalChain
from langchain_core.prompts import PromptTemplate
from langchain.chains.llm import LLMChain
from langchain.chains.combine_documents.stuff import StuffDocumentsChain
from streaming import StreamingStdOutCallbackHandlerCustom

class UIChat:

    def __init__(self, retriever):
        #is used to store question/answers to display
        if "history" not in st.session_state:
            st.session_state['history'] = []
            st.session_state['history'].append({"role": "assistant", "content": "Ciao! Sono l'assistente virtuale di Essenzia. Chiedimi qualcosa"})
        #is used to store chat history for the LLM since dict is not allowed
        if "chat_history" not in st.session_state:
            st.session_state['chat_history'] = []
        self.custom_output=StreamingStdOutCallbackHandlerCustom()
        self.__chain = self.__get_conversational_chain(retriever)
        
    def __get_stuff_chain(self):
        #questo è il template usato per dare effettivamente la riposta
        prompt_template = """You are the virtual assistan of an IT company called APRA. Give the answer in italian, not in english
            Use the following pieces of context to answer the question at the end. Please follow the following rules:
            1. If the question is to request sources, please only return the entire sources with no answer.

            2. If you don't know the answer, don't try to make up an answer. Just say **I can't find the final answer but you may want to check the following links** and add the sources of the context as a list. Based only on context sources, nothing more.
                The sources have a format like that: https://wikidoc.apra.it/essenzia/index.php?title=Page_title#Section_title. Show the entire sources NOT just the Section_title

            3. If you know the answer, usee the following pieces of context to answer the question at the end.
                First write the answer and then add the list of the sources that are **directly** used to derive the answer saying "you can find more informatation here: " in a new line. Exclude the titles that are irrelevant to the final answer. Give the answer in italian, not in english
                **IMPORTANT NOTE**: the most important aspect is the answer, soo focused on giving a **COMPLETE AND EXHAUSTIVE** answer and then add the sources. Usually chunks are part of a single web page
                The sources have a format like that: https://wikidoc.apra.it/essenzia/index.php?title=Page_title#Section_title. Show the entire sources not only the Section_title.

            {context}

            Question: {question}
            Helpful Answer:"""
        QA_CHAIN_PROMPT = PromptTemplate.from_template(prompt_template)
        llm_chat=ChatOpenAI(model="gpt-3.5-turbo",callbacks=[self.custom_output], streaming=True)
        llm_chain = LLMChain(llm=llm_chat, prompt=QA_CHAIN_PROMPT, verbose=False)
        
        #in questo template definsico che oltre al page_content, deve prendere anche il title (che si trova nei metadata)
        document_prompt = PromptTemplate(
            input_variables=["page_content", "source"],
            template="Context:\ncontent:{page_content}\source:{source}",
        )

        combine_docs_chain = StuffDocumentsChain(
            llm_chain=llm_chain,
            document_variable_name="context",
            document_prompt=document_prompt,
            callbacks=None,
        )
        return combine_docs_chain, llm_chat

    def __get_conversational_chain(self, retriever):
        combine_docs_chain, llm_chat=self.__get_stuff_chain()
        
        # template per crearea la domanda che verrà effettivamente usata a partire dalla domanda originale e della chata history
        template = """Given the following conversation and a follow up question, rephrase the follow up question to be a standalone question, in its original language.
            Chat History:
            {chat_history}
            Follow Up Input: {question}
            Standalone question:"""
        prompt = PromptTemplate.from_template(template)
        llm_chat_final=ChatOpenAI(model="gpt-3.5-turbo", callbacks=[self.custom_output], streaming=True)
        question_generator_chain = LLMChain(llm=llm_chat_final, prompt=prompt)
        
        chain = ConversationalRetrievalChain(
            combine_docs_chain=combine_docs_chain,
            retriever=retriever,
            question_generator=question_generator_chain,
        )
        return chain
    
    def __conversational_chat(self, query):
        result = self.__chain({"question": query, "chat_history": st.session_state['chat_history']})
        #LLM chat history
        st.session_state['chat_history'].append((query, result["answer"]))
        return result["answer"]

    def chat(self):
        #sidebar
        with st.sidebar:
            st.title('🤖💬 APRA Chatbot')
            st.write("Benvenuto nel nostro assistente virtuale! Sono qui per rispondere alle tue domande, risolvere problemi e offrirti supporto tecnico personalizzato. Digita semplicemente la tua richiesta e sarò felice di aiutarti nel miglior modo possibile.")

        #chat
        for message in st.session_state['history']:
            role = message["role"]
            if role == "user":
                with st.chat_message('user', avatar="https://cdn-icons-png.flaticon.com/512/5987/5987424.png"):
                    st.markdown(message['content'], unsafe_allow_html=True)
            else:
                with st.chat_message('assistant', avatar="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTYzs4aNNoy8aM6p0cArrghtTo4MqOaDk5otpXuGXN1eIxpT3EHhTyLvel0c-bx15oKb1o&usqp=CAU"):
                    st.markdown(message['content'], unsafe_allow_html=True)

        if prompt := st.chat_input("Domanda: "):
            st.session_state['history'].append({"role": "user", "content": prompt})
            with st.chat_message("user", avatar="https://cdn-icons-png.flaticon.com/512/5987/5987424.png"):
                st.markdown(prompt, unsafe_allow_html=True)
            with st.chat_message("assistant", avatar="https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTYzs4aNNoy8aM6p0cArrghtTo4MqOaDk5otpXuGXN1eIxpT3EHhTyLvel0c-bx15oKb1o&usqp=CAU"):
                self.custom_output.initialize_placeholder()
                message_placeholder = st.empty()
                #full_response=self.get_response(prompt)
                full_response= self.__conversational_chat(prompt)
                self.custom_output.remove_placeholder()
                message_placeholder.markdown(full_response, unsafe_allow_html=True)
            st.session_state['history'].append({"role": "assistant", "content": full_response})
