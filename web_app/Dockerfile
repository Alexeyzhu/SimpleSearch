FROM python:3.7
COPY . /web_app
WORKDIR /web_app
RUN pip install -r requirements.txt
RUN pip install pymongo
CMD python app.py
