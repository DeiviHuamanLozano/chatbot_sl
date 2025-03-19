FROM python:3.8.16-bullseye

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    make \
    automake \
    gcc \
    g++ \
    subversion \
    python3-dev \
    streamripper \
    ffmpeg \
    curl \
    gnupg \
    apt-transport-https

# Instalar controlador MS ODBC SQL Server
RUN curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add - && \
    curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list && \
    apt-get update && \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
RUN pip install pyodbc

RUN pip list

COPY . .

EXPOSE 8001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--reload"]
# CMD ["/bin/bash"]
# CMD ["fastapi", "run", "main.py", "--host", "0.0.0.0", "--port", "8001"]
# uvicorn main:app --host 0.0.0.0 --port 8001 --reload
