FROM python:3.9

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY jwt_encode.py /action/jwt_encode.py

ENTRYPOINT ["python", "/action/jwt_encode.py"]