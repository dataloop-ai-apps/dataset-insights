import json
import logging
import threading
from urllib.parse import urlparse

import dash_bootstrap_components as dbc
import dtlpy as dl

import uvicorn
from exporter import Exporter
from dash import Dash, Input, Output, callback, dcc, html
from dash_bootstrap_templates import load_figure_template

from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles


logger = logging.getLogger('[INSIGHTS MAIN]')
logging.basicConfig(level='INFO')

load_figure_template(["cyborg", "darkly", "minty", "cerulean"])

port = 3000

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

app_dash = Dash(
    __name__,
    external_stylesheets=[dbc.themes.MINTY],
    suppress_callback_exceptions=True,
    routes_pathname_prefix="/",
    requests_pathname_prefix="/dash/",
)


app_dash.layout = html.Div(
    [dcc.Location(id='url', refresh=False), html.Div(id='main-container')]
)


@callback(
    Output('main-container', 'children'),
    [Input('url', 'pathname'), Input('url', 'search')],
)
def display_page(pathname, search):
    """
    Display the appropriate page content based on the given pathname and search query.

    Args:
        pathname (str): The path of the page to display.
        search (str): The search query string containing query parameters.

    Returns:
        html.Div: A Div containing the content to be displayed on the page.

    Raises:
        None: This function does not raise any exceptions explicitly.
    """
    if pathname == '/dash/datasets':
        query_params = urlparse(search).query
        query = dict(q.split('=') for q in query_params.split('&'))
        dataset_id = query.get('id', None)
        if dataset_id:
            try:
                exporter = Exporter(dataset_id=dataset_id)
                content = html.Div(
                    className=['scroll', 'reactive-scroll'],
                    children=[dcc.Location(id='plots'), *exporter.divs],
                )
            except Exception as e:
                logger.exception('failed to create exporter: %s', e)
                content = html.Div('No data found')
            return content

        else:
            return html.Div('No datasetId provided')

    else:
        return html.Div('No page found')


class Runner(dl.BaseServiceRunner):
    """
    Runner class that initializes and starts a background thread to run a Uvicorn server.

    Attributes:
        thread (threading.Thread): The thread that runs the Uvicorn server.

    Methods:
        __init__(): Initializes the Runner instance and starts the Uvicorn server in a background thread.
    """

    def __init__(self):
        self.thread = threading.Thread(
            target=uvicorn.run,
            kwargs={
                'app': app,
                'host': "0.0.0.0",
                'port': port,
                'timeout_keep_alive': 60,
            },
        )
        self.thread.daemon = True
        self.thread.start()


@app.get("/export/status")
async def export_status(datasetId: str):
    """
    Get the export status for a specific dataset.

    Parameters:
    - datasetId (str): The ID of the dataset.

    Returns:
    - JSON response with export status, progress, export date, and export item ID.
    """
    exporter: Exporter = Exporter(dataset_id=datasetId)
    status = {
        'progress': int(exporter.progress),
        'exportDate': exporter.last_update,
        'status': exporter.status.value,
    }
    logger.info("Returning status: %s", status)
    return HTMLResponse(json.dumps(status, indent=2), status_code=200)


@app.get("/export/run")
async def export_run(datasetId: str, cache: str, background_tasks: BackgroundTasks):
    """
    Start the export process for a specific dataset.

    Parameters:
    - datasetId (str): The ID of the dataset.

    Returns:
    - JSON response indicating that the export has started.
    """
    exporter: Exporter = Exporter(dataset_id=datasetId)
    exporter.progress = 0
    background_tasks.add_task(exporter.check_and_run, use_cache=cache)
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
    exporter: Exporter = Exporter(dataset_id=datasetId)
    status = {
        'status': exporter.build_status,
        'progress': exporter.build_progress,
    }
    logger.info("Returning status: %s", status)
    return HTMLResponse(json.dumps(status, indent=2), status_code=200)


# Mount the Dash app at the "/dash" endpoint
app.mount("/dash", WSGIMiddleware(app_dash.server))

# Mount static files of build insights at the "/insights" endpoint
app.mount(
    "/insights", StaticFiles(directory="panels/insights", html=True), name='insights'
)
