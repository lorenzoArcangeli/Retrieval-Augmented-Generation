from langchain_openai import ChatOpenAI
import uuid
import hashlib
from dotenv import load_dotenv
import os


class Document_decorator:

    def __init__(self, embedder):
        self.__embedder=embedder
        self.__llm=ChatOpenAI(model="gpt-3.5-turbo")
    
    def add_metadata_v2(self, sentences, type, sha1, title, id):
        for sentence in sentences:
            sentence['type']=type # web page or pdf
            new_uuid=uuid.uuid4()
            sentence['uuid']=str(new_uuid) # instead of using increment id
            sentence['sha1']=str(sha1) # used to check if the web page/pad has been changed
            source="https://wikidoc.apra.it/essenzia/index.php?title="+title+"#"+sentence['anchor']
            #funziona anche con " ", ma la formattazione visiva è meglio con "_"
            source=source.replace(" ","_")
            sentence['source']=str(source) # used to identify the we
            sentence['title']=str(title)
            sentence['id']=str(id)
        return sentences
    
    def compute_sha1(self, file_path):
        sha1 = hashlib.sha1()
        with open(file_path, 'rb') as file:
            while True:
                blocco = file.read(4096)  # Leggi il file a blocchi di 4 KB
                if not blocco:
                    break
                sha1.update(blocco)
        return sha1.hexdigest()
    
    def add_metadata_pdf(self, sentences, title, file_path, type="pdf"):
        load_dotenv()
        pdf_initial_path=os.getenv("PDF_HOST")
        for sentence in sentences:
            sentence['type']=type # web page or pdf
            new_uuid=uuid.uuid4()
            sentence['uuid']=str(new_uuid) # instead of using increment id
            sha1=self.compute_sha1(file_path)
            sentence['sha1']=str(sha1) # used to check if the web page/pad has been changed
            sentence['source']=str(pdf_initial_path+title) # used to identify the we
            sentence['title']=str(pdf_initial_path+title) # used to identify the we
            sentence['id']=str(new_uuid) # nel caso dei pdf l'id e l'uuid hanno lo stesso valore
        return sentences
    
    def remove_index_and_simple_sentece_from_senteces(self, sentences):
        for sentence in sentences:
            # Remove index and sentence field in the list of dictionary
            sentence.pop('index', None)
            sentence.pop('sentence')
        return sentences
    '''
    def get_page_summary(self, document, page_title):
        #get the summary for the entire page
        PROMPT = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """
                        Sei l'amministratore di un documento in cui sono presenti elementi che che parlano di un argomento simile.
                        Genera un riassunto dettagliato che informerà gli osservatori ciò di cui si parla nel documento.
                        La lunghezza limite del riassunto è di 3000 parole.

                        Un buon riassunto dice di cosa tratta il documento.

                        Ti verrà dato un documento. Questo documento ha bisogno di un riassunto.
                        
                        Esempio:
                        Input: Documento: Greg ama mangiare la pizza
                        Output: Questo documento contiene informazioni sui tipi di cibo che Greg ama mangiare.

                        Rispondi solo con il nuovo riassunto, nient'altro.
                        """,
                    ),
                    ("user", "Determina il rissunto del seguente documento:\n{proposition}"),
                ]
            )
        runnable = PROMPT | self.__llm

        new_chunk_summary = runnable.invoke({
                "proposition": document
        }).content
        
        summary_header="Quest è il riassunto generale della pagina web relativa a: "+page_title+"\n\n"
        final_summary=summary_header+new_chunk_summary
        summary = {}  # Initialize the summary dictionary
        summary['section']=final_summary
        summary_embedding=self.__embedder.do_embedding([summary])
        summary['embedding']=summary_embedding
        return summary

    def get_page_keyword(self, document):
        #get keyword for the entire page
        PROMPT = ChatPromptTemplate.from_messages(
                [
                    (
                        "system",
                        """
                        Sei l'amministratore di un documento in cui sono presenti elementi che che parlano di un argomento simile.
                        Genera delle parole chiavi che identificano di cosa si tratta all'interno del documento.
                        Genera il numero di parole chiavi che riteni opportune per identificare gli elementi chiave del documento.

                        Delle buone parole chiavi riescono a far capire agli osservatori di cosa parla il documento.

                        Ti verrà dato un documento. Questo documento ha bisogno di parole chiavi.

                        Rispondi solo con le parole chiavi, nient'altro. Non indicare il numero di parole chiavi
                        """,
                    ),
                    ("user", "Determina il rissunto del seguente documento:\n{proposition}"),
                ]
            )
        runnable = PROMPT | self.__llm

        new_chunk_keyword = runnable.invoke({
                "proposition": document
        }).content
        return new_chunk_keyword
    
    # metodo per testare l'estrazione di domande/rispsote
    def extract_questions_anwers_from_document(self, sentences):
        os.environ["OPENAI_API_MODEL"]="gpt-3.5-turbo"
        qa_transformer = DoctranQATransformer()
        questions_answars=[]
        for sentence in sentences:
            document_from_sentence=[Document(page_content=sentence['combined_sentence'])]
            interrogated_document=qa_transformer.transform_documents(document_from_sentence)
            question_answers=json.dumps(interrogated_document[0].metadata, indent=2)
            questions_answers_splitted=self.__split_question_anwer([Document(page_content=question_answers)])
            questions_answers_splitted_list_dict=[]
            for qas in questions_answers_splitted:
                #qasd={'combined_sentence': qas}
                qasd={'section': qas}
                qasd_emb=self.__embedder.do_embedding([qas])
                qasd['embedding']=qasd_emb
                questions_answers_splitted_list_dict.append(qasd)
            questions_answars.extend(questions_answers_splitted_list_dict)
#            st.write(questions_answars)
        return questions_answars
    
    def __split_question_anwer(self, answers_questions_document):
        #chek if amount of token id above the limit
        if len(answers_questions_document[0].page_content)*0.75>2000:
            #create chunks
            text_splitter=RecursiveCharacterTextSplitter(
                chunk_size=1024, chunk_overlap=50
            )
            docs_split=text_splitter.split_documents(answers_questions_document)
            #get new embeddings for the new chunks
            return [docs_split[i].page_content for i in range(len(docs_split))]
        else:
            return [answers_questions_document[0].page_content]
    '''