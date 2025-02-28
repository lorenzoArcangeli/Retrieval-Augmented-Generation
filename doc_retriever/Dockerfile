FROM python:3.12.1
WORKDIR /app
COPY ./app .
#intsallo le dipendenze
RUN pip install -r requirements.txt
#è già di default 8501
EXPOSE 8502
# per runnare come seguibile
#ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]
ENTRYPOINT ["python", "app.py", "--server.port=8502", "--server.address=0.0.0.0"]