FROM docker.io/dataloopai/dtlpy-agent:cpu.py3.10.opencv

USER root

# Install required packages
RUN apt-get update && apt-get install -y \
    software-properties-common \
    curl \
    nginx && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Install Node.js and npm using n
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g npm@latest && \
    npm install -g n && \
    n latest

# create open ssl
WORKDIR /tmp
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout local.dataloop.ai.key -out local.dataloop.ai.crt -subj "/CN=local.dataloop.ai"
RUN cp local.dataloop.ai.crt /etc/ssl/certs/ & cp local.dataloop.ai.key /etc/ssl/private/

WORKDIR /tmp/app
RUN pip install --user  \
    fastapi  \
    uvicorn  \
    plotly \
    dash \
    dash-bootstrap-components \
    dash_bootstrap_templates \
    pyarrow \
    fastparquet \
    https://storage.googleapis.com/dtlpy/single-export-be/dtlpy_exporter-0.1.1-py3-none-any.whl



# docker build -t gcr.io/viewo-g/piper/agent/local:0.0.1 -f ./Dockerfile .
# docker push gcr.io/viewo-g/piper/agent/jupyter-server:0.1.49

# docker run -p 3004:3000  -it -v E:\Applications\dataset-cleanup:/tmp/app gcr.io/viewo-g/piper/agent/local:0.0.1 bash
