from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from sklearn.metrics.pairwise import cosine_similarity
from decorate_document import Document_decorator

class Cosine_chunker:
    
    def __init__(self, embedder, document_decorator):
        #create embedder object
        self.__embedder=embedder
        self.__document_decorator=document_decorator
        self.keyword=None
        self.sha1=None

    def get_document_chunks(self, document, pdf_title, file_path):
        # get_page_keyword --> used to add page keyword
        #self.keyword=self.__document_decorator.get_page_keyword(document)
        sentences=self.__create_document_chunks(document)
        # if there is only one chunk in the document
        if len(sentences)<=1:
            sentences[0]['section']=sentences[0]['sentence']
            document_chunks=sentences
        else: 
            distances, sentences = self.__calculate_cosine_distances(sentences)
            indexes_above_treshold_distance=self.__identify_indexes_above_treshold_distance(distances)
            document_chunks=self.__group_chunks(indexes_above_treshold_distance, sentences)
        # get_page_summary --> used to add summery 
        # get_answers_questions --> used to add questions answers
        # add_autoincrement_value --> no more used
        #document_chunks.append(self.__document_decorator.get_page_summary(document, title))
        #document_chunks.extend(self.get_answers_questions(document))
        #document_chunks=self.__document_decorator.add_autoincrement_value(document_chunks, self.vector_amount_in_db)
        document_chunks=self.__document_decorator.remove_index_and_simple_sentece_from_senteces(document_chunks)
        document_chunks=self.__document_decorator.add_metadata_pdf(document_chunks, pdf_title, file_path)
        return document_chunks
    

    def __create_document_chunks(self, document):
        #split document (based on length)
        docs_split=self.__split_document_by_recursive(document, 300, 50)
        string_text = [docs_split[i].page_content for i in range(len(docs_split))]
        sentences = [{'sentence': x, 'index' : i} for i, x in enumerate(string_text)]
        # the second argument indicates the number of sentences to combine before and after the current sentence
        sentences = self.__combine_sentences(sentences, 1)
        # emnedding
        sentences=self.__do_embedding(sentences)
        return sentences
    
    def __get_new_chunk(self, leng, document):
        splitted_chunks = []
        # get strings from documents
        string_text = [document[i].page_content for i in range(leng)]
        sentences = [{'sentence': x, 'index' : i} for i, x in enumerate(string_text)]
        sentences = [{'sentence': f"{x['sentence']}", 'index': x['index']} for x in sentences]
        # get sentence and combined_sentence
        for i in range(len(sentences)):
            combined_sentence = sentences[i]['sentence']
            sentences[i]['section'] = combined_sentence
        # get new embeddings for the new chunks
        sentences=self.__do_embedding(sentences)
        # add the new chunks to the list
        splitted_chunks.extend(sentences)
        return splitted_chunks
    
    def __do_embedding(self, sentences):
        embeddings=self.__embedder.do_embedding_sections(sentences)
        for i, sentence in enumerate(sentences):
            sentence['embedding'] = embeddings[i]
        return sentences

    #buffer size: number of sentence before and after the current one to be joined
    def __combine_sentences(self, sentences, buffer_size):
        for i in range(len(sentences)):
            # create a string for the joined sentences
            combined_sentence = ''
            # add sentences before the current one, based on the buffer size.
            for j in range(i - buffer_size, i):
                # check if the index j is not negative (avoid problem for the first sentence)
                if j >= 0:
                    combined_sentence += sentences[j]['sentence'] + ' '
            # add the current sentence
            combined_sentence += sentences[i]['sentence']

            # add sentences after the current one, based on the buffer size
            for j in range(i + 1, i + 1 + buffer_size):
                # check if the index j is within the range of the sentences list
                if j < len(sentences):
                    combined_sentence += ' ' + sentences[j]['sentence']
            # store the combined sentence in the current sentence dict
            sentences[i]['section'] = combined_sentence
        return sentences

    def __calculate_cosine_distances(self, sentences):
        distances = []
        for i in range(len(sentences) - 1):
            embedding_current = sentences[i]['embedding']
            embedding_next = sentences[i + 1]['embedding']
            # calculate cosine similarity
            similarity = cosine_similarity([embedding_current], [embedding_next])[0][0]
            # convert to cosine distance
            distance = 1 - similarity
            # append cosine distance to the list
            distances.append(distance)
            # store distance in the dictionary
            sentences[i]['distance_to_next'] = distance
        return distances, sentences

    def __identify_indexes_above_treshold_distance(self, distances, distance=0.95):
        # identify the outlier
        # higher distance --> less chunks
        # lower distance --> more chunks
        # Indexes of the chunks with cosine distance above treshold
        indices_above_thresh=[]
        for i, x in enumerate(distances):
            if (1-x)<(distance):
                indices_above_thresh.append(i)
        return indices_above_thresh
    

    def __group_chunks(self, indices, sentences):
        # initialize the start index
        start_index = 0
        # create a list to hold the grouped sentences
        chunks = []
        # iterate through the breakpoints to slice the sentences
        for index in indices:
            # the end index is the current breakpoint
            end_index = index
            # slice the sentence_dicts from the current start index to the end index
            group = sentences[start_index:end_index + 1]
            combined_text = ' '.join([repr(d['sentence']) for d in group])
            chunks.extend(self.__check_len([Document(page_content=combined_text)]))
            start_index = index + 1
        # the last group, if any sentences remain
        if start_index < len(sentences):
            combined_text = ' '.join([repr(d['sentence']) for d in sentences[start_index:]])
            chunks.extend(self.__check_len([Document(page_content=combined_text)]))
        return chunks
    
    def __check_len(self, document):
        # chek if the amount of token id above the limit
        if len(document[0].page_content)*0.75>1024:
            docs_split=self.__split_document_by_recursive(document, 1024, 50)
            # get new embeddings for the new chunks
            return self.__get_new_chunk(len(docs_split), docs_split)
        else:
            #st.write("Sotto i 1024")
            return self.__get_new_chunk(1, document)
    
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
            