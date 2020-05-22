FROM python:3

WORKDIR /usr/src/app

COPY source/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY source/main.py .

CMD [ "python", "./main.py" ]