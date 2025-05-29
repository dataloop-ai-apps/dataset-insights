FROM docker.io/dataloopai/dtlpy-agent:cpu.py3.10.opencv

USER 1000
ENV HOME=/tmp
RUN pip install --user  \
    fastapi  \
    uvicorn  \
    plotly \
    dash \
    dash-bootstrap-components \
    dash_bootstrap_templates \
    pyarrow \
    fastparquet \
    https://storage.googleapis.com/dtlpy/single-export-be/dtlpy_exporter-0.1.6-py3-none-any.whl



# docker build --no-cache -t gcr.io/viewo-g/piper/agent/runner/cpu/dataset-insights:0.2.7 -f Dockerfile .
# docker push gcr.io/viewo-g/piper/agent/runner/cpu/dataset-insights:0.2.7