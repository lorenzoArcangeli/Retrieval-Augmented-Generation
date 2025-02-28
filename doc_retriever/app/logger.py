import requests

class Logger:

    def __init__(self, username, password, baseurl):
        self.username=username
        self.password=password
        self.baseurl=baseurl
        self.__token=None
        self.__session=None
    
    def login(self):
        self.__session = requests.Session()

        # Get token
        parameters = {
            'action':"query",
            'meta':"tokens",
            'type':"login",
            'format':"json"
        }

        session_response = self.__session.get(url=self.baseurl, params=parameters)
        data = session_response.json()

        login_token = data['query']['tokens']['logintoken']
        login_parameters = {
            'action': "login",
            'lgname': self.username,
            'lgpassword': self.password,
            'lgtoken': login_token,
            'format': "json",
        }

        session_response = self.__session.post(self.baseurl, data=login_parameters)
        data = session_response.json()
        assert data['login']['result'] == 'Success'
        self.__token=login_token
    
    def complete_json_by_title(self, title):
        token=self.__token
        headers = {
            'Authorization': 'Bearer <{token}}>',
        }

        #the paramters are always the same except for the page title
        api_url = f"https://wikidoc.apra.it/essenzia/api.php?action=query&prop=revisions&titles={title}&rvslots=*&rvprop=timestamp|content|sha1&formatversion=2&format=json"
        response = self.__session.get(api_url, headers=headers)
        return response.json()
    
    def complete_json_by_id(self, id):
        token=self.__token
        headers = {
            'Authorization': 'Bearer <{token}}>',
        }

        #the paramters are always the same except for the page title
        api_url = f"https://wikidoc.apra.it/essenzia/api.php?action=query&prop=revisions&pageids={id}&rvslots=*&rvprop=timestamp|content|sha1&formatversion=2&format=json"
        response = self.__session.get(api_url, headers=headers)
        return response.json()
    
    def get_last_version(self, json):
        versions=json['query']['pages'][0]['revisions']
        last_version=versions[-1]
        return last_version
    
    #get all the website pages
    def get_pages(self): 
        token=self.__token
        headers = {
            'Authorization': 'Bearer <{token}}>',
        }
        #the paramters are always the same except for the page title
        api_url = f"https://wikidoc.apra.it/essenzia/api.php?action=query&list=allpages&aplimit=max&format=json"
        #api_url = f"https://wikidoc.apra.it/essenzia/api.php?action=query&list=allpages&aplimit=max&format=json&apcontinue=Versamenti_di_Produzione_/_Imbottigliamento"
        response = self.__session.get(api_url, headers=headers)
        result=response.json()
        with open("Page_titles.txt", 'a') as file:
            # Scrivi ogni stringa nella lista su una nuova riga
            for stringa in result['query']['allpages']:
                file.write(f"{stringa['title']}\n")

    # get last a version of sections
    def get_last_version_sections(self, page_id):
        token=self.__token
        headers = {
            'Authorization': 'Bearer <{token}}>',
        }

        #the paramters are always the same except for the page title
        api_url = f"https://wikidoc.apra.it/essenzia/api.php?action=query&prop=revisions&pageids={page_id}&rvslots=*&rvprop=sha1&formatversion=2&format=json"
        response = self.__session.get(api_url, headers=headers)
        json=response.json()
        versions=json['query']['pages'][0]['revisions']
        last_version=versions[-1]
        return last_version
    
    def get_sections_of_a_page_id(self, page_id):
        token=self.__token
        headers = {
            'Authorization': 'Bearer <{token}}>',
        }

        #the paramters are always the same except for the page title
        api_url = f"https://wikidoc.apra.it/essenzia/api.php?action=parse&format=json&pageid={page_id}&prop=sections&disabletoc=1"
        response = self.__session.get(api_url, headers=headers)
        return response.json()

    def get_relevant_section_of_a_page(self, page_sections_json):
        relevant_sections_index=[]
        start_relevant_index=0
        start_index_found=True
        end_relevant_index=0
        sections=page_sections_json['parse']['sections']
        pre_max_level=sections[0]['toclevel']
        sections_len=len(page_sections_json['parse']['sections'])

        for i in range(1,sections_len):
            current_max_level=sections[i]['toclevel']

            #START RELEVANT INDEX
            if (not start_index_found and current_max_level>pre_max_level):
                start_relevant_index, start_index_found=self.set_values(i, True)

            #END RELEVANT INDEX FIRST METHOD
            if (current_max_level>pre_max_level and start_index_found):
                end_relevant_index, start_index_found=self.set_values(i, False)

                #l'estremo alto è escludo dal range
                relevant_sections_index.extend(range(start_relevant_index + 1, end_relevant_index))

                #caso speciale nel cui si ha: 1, 2, 1 -->altrimenti il 2 non verebbe preso
                if (i+1)<(sections_len-1):
                    if sections[i+1]['toclevel'] < sections[i]['toclevel']:
                        relevant_sections_index.append(start_relevant_index+1)
                        
                        #il primo caso speciale, genera un altro caso speciale, ovvero se il secondo 1 di prima deve essere subito considerato
                        #se non deve essere considerato, viene già gestito dagli altri casi
                        if (i+2)<(sections_len-1):
                            if sections[i+1]['toclevel'] == sections[i+2]['toclevel']:
                                start_relevant_index, start_index_found=self.set_values(i+1, True)

                    # se il successivo è sullo stesso livello, devo considerare anche questo
                    elif sections[i+1]['toclevel'] == sections[i]['toclevel']:
                        start_relevant_index, start_index_found=self.set_values(i, True)

                #caso speciale in cui l'ultimo è l'unico elemento da aggiungere
                #devo fare questo controllo dato che la funzione range non inserire nessun indice se i 2 estremi sono uguali dato che
                #l'estremo superiore viene escluso
                elif start_relevant_index+1==end_relevant_index:
                    relevant_sections_index.append(start_relevant_index+1)

            #END RELEVANT INDEX SECOND METHOD
            if (current_max_level<pre_max_level and start_index_found):
                #in questo caso deve prendere anche l'ultimo indice della sezione
                end_relevant_index, start_index_found=self.set_values(i+1, False)
                #l'estremo alto è escludo dal range
                relevant_sections_index.extend(range(start_relevant_index + 1, end_relevant_index))

                # se il successivo è sullo stesso livello, devo considerare anche questo
                if (i+1)<(sections_len-1):
                    if sections[i+1]['toclevel'] == sections[i]['toclevel']:
                        start_relevant_index, start_index_found=self.set_values(i, True)

            pre_max_level=current_max_level

        #aggiungo gli elementi rimasti in attesa di essere aggiunti
        if start_index_found:
            relevant_sections_index.extend(range(start_relevant_index + 1, sections_len+1))

        return relevant_sections_index
    
    def set_values(self, index, boolean):
        return index, boolean
        
    def get_section_content(self, page_id, section_number):
        token=self.__token
        headers = {
            'Authorization': 'Bearer <{token}}>',
        }

        #the paramters are always the same except for the page title
        api_url = f"https://wikidoc.apra.it/essenzia/api.php?action=parse&format=json&pageid={page_id}&prop=wikitext&section={section_number}&disabletoc=1"
        response = self.__session.get(api_url, headers=headers)
        return response.json()
    
    

    #LINK PER ESTRARRE I NOMI DI TUTTE LE IMMAGINI
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=447.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Acconti_003.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Bil_65.JPG
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Carichi-Ins-Multiplo.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Consultazione_commessa.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Documento_carico.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Estratto_033.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=GiorniChiusuraCFf.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Imageufukfkf.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Listini_standard.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=OPA-DISTINTA-FANTASMA.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Percorso_voci_di_costi.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=RA_065.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Righe.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=Significato_pulsanti_Saiku.png
    #https://wikidoc.apra.it/essenzia/api.php?action=query&list=allimages&ailimit=max&format=json&aicontinue=VAR-NEW.png