from fastapi.middleware.cors import CORSMiddleware
import json
from concurrent.futures import ThreadPoolExecutor
import requests
import pydantic
import logging
import uvicorn
import tqdm

from dash import Dash, dcc, html, callback, Input, Output
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

import dtlpy as dl

from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from urllib.parse import urlparse

from insights import Insights
from exporter import Exporter

logger = logging.getLogger('[INSIGHTS]')
logging.basicConfig(level='INFO')

load_figure_template(["cyborg", "darkly", "minty", "cerulean"])

port = 3000


class Runner(dl.BaseServiceRunner):
    def __init__(self):
        uvicorn.run("app:app",
                    host="0.0.0.0",
                    port=port,
                    timeout_keep_alive=60
                    )


class InsightsHandles:
    def __init__(self):
        self.insights = dict()

    def get(self, dataset_id):
        if dataset_id not in self.insights:
            self.insights[dataset_id] = Insights(
                dataset_id=dataset_id)
        return self.insights[dataset_id]


class ExporterHandles:
    def __init__(self):
        self.exporters = dict()

    def get(self, dataset_id):
        if dataset_id not in self.exporters:
            self.exporters[dataset_id] = Exporter(dataset_id=dataset_id)
        return self.exporters[dataset_id]


insights_handler = InsightsHandles()
exporters_handler = ExporterHandles()

# Initialize FastAPI app
app = FastAPI()

origins = [
    "*",  # allow all
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app_dash = Dash(__name__,
                external_stylesheets=[dbc.themes.MINTY],
                suppress_callback_exceptions=True,
                routes_pathname_prefix="/",
                requests_pathname_prefix="/dash/")

app_dash.layout = html.Div([
    dcc.Location(id='url', refresh=False),
    html.Div(id='main-container')
])


@callback(Output('main-container', 'children'), [Input('url', 'pathname'),
                                                 Input('url', 'search')])
def display_page(pathname, search):
    if pathname == '/dash/datasets':
        query_params = urlparse(search).query
        query = dict(q.split('=') for q in query_params.split('&'))
        datasetId = query.get('id', None)
        if datasetId:
            try:
                insights: Insights = insights_handler.get(dataset_id=datasetId)
                content = html.Div(
                    className=['scroll', 'reactive-scroll'],
                    children=[dcc.Location(id='plots'),
                              *insights.divs])
            except:
                content = html.Div('No data found')
            return content

        else:
            return html.Div('No datasetId provided')

    else:
        return html.Div('No page found')


class Settings(pydantic.BaseModel):
    theme: str


@app.get("/export/status")
async def export_status(datasetId: str):
    """
    Get the export status for a specific dataset.

    Parameters:
    - datasetId (str): The ID of the dataset.

    Returns:
    - JSON response with export status, progress, export date, and export item ID.
    """
    exporter: Exporter = exporters_handler.get(dataset_id=datasetId)
    status = {
        'progress': 100 if exporter.status == 'ready' else int(exporter.progress),
        'exportDate': exporter.export_date,
        'status': exporter.status,
        'exportItemId': exporter.export_item_id
    }
    logger.info(f"Returning status: {status}")
    return HTMLResponse(json.dumps(status, indent=2), status_code=200)


@app.get("/export/run")
async def export_status(datasetId: str):
    """
    Start the export process for a specific dataset.

    Parameters:
    - datasetId (str): The ID of the dataset.

    Returns:
    - JSON response indicating that the export has started.
    """
    exporter: Exporter = exporters_handler.get(dataset_id=datasetId)
    exporter.status = "starting"
    exporter.progress = 0
    exporter.start_export()
    return HTMLResponse(json.dumps({'status': 'started'}), status_code=200)


@app.get("/build/status")
def build_status(datasetId):
    """
    Get the build status for insights of a specific dataset.

    Parameters:
    - datasetId (str): The ID of the dataset.

    Returns:
    - JSON response with the build status.
    """
    insights: Insights = insights_handler.get(dataset_id=datasetId)
    status = {
        'status': insights.build_status
    }
    logger.info(f"Returning status: {status}")
    return HTMLResponse(json.dumps(status, indent=2), status_code=200)


@app.get("/graph/build")
def update_dataset(datasetId, itemId):
    """
    Build the graphs for a specific dataset from exported item.

    Parameters:
    - datasetId (str): The ID of the dataset.
    - itemId (str): The ID of the exported item.

    Returns:
    - JSON response indicating that the build is ready.
    """
    insights: Insights = insights_handler.get(dataset_id=datasetId)
    insights.build_status = "building"
    insights.run(export_item_id=itemId)
    insights.build_status = "ready"
    return HTMLResponse(json.dumps({'status': 'ready'}), status_code=200)


# Mount the Dash app at the "/dash" endpoint
app.mount("/dash", WSGIMiddleware(app_dash.server))

# Mount static files of build insights at the "/insights" endpoint
app.mount("/insights", StaticFiles(directory="panels/insights",
          html=True), name='insights')
