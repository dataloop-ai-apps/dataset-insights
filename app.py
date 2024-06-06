import threading
import logging
import uvicorn
import json

import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
from dash import Dash, dcc, html

from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi import FastAPI, BackgroundTasks

import dtlpy as dl

from insights import Insights
from exporter import Exporter

logger = logging.getLogger('[INSIGHTS]')
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

app_dash = Dash(__name__,
                external_stylesheets=[dbc.themes.MINTY],
                suppress_callback_exceptions=True,
                routes_pathname_prefix="/",
                requests_pathname_prefix="/dash/")


class Runner(dl.BaseServiceRunner):
    def __init__(self):
        self.thread = threading.Thread(target=uvicorn.run,
                                       kwargs={'app': app,
                                               'host': "0.0.0.0",
                                               'port': port,
                                               'timeout_keep_alive': 60}
                                       )
        self.thread.daemon = True
        self.thread.start()


class InsightsHandles:
    def __init__(self):
        self.insights = dict()

    def get(self, dataset_id):
        if dataset_id not in self.insights:
            self.insights[dataset_id] = Insights(
                dataset_id=dataset_id)
        print(self.insights)
        return self.insights[dataset_id]


class ExporterHandles:
    def __init__(self):
        self.exporters = dict()

    def get(self, dataset_id):
        if dataset_id not in self.exporters:
            self.exporters[dataset_id] = Exporter(dataset_id=dataset_id)
        print(self.exporters)
        return self.exporters[dataset_id]


insights_handler = InsightsHandles()
exporters_handler = ExporterHandles()


def build_in_background(dataset_id, item_id):
    logger.info('inside background. stating...')
    insights: Insights = insights_handler.get(dataset_id=dataset_id)
    insights.run(export_item_id=item_id)
    app_dash.layout = dcc.Loading(children=html.Div(
        id='main-container',
        className=['scroll', 'reactive-scroll'],
        children=[dcc.Location(id='url'),
                  *insights.divs]))


@app.get("/export/status")
async def export_status(datasetId: str):
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
    exporter: Exporter = exporters_handler.get(dataset_id=datasetId)
    exporter.status = "starting"
    exporter.progress = 0
    exporter.start_export()
    return HTMLResponse(json.dumps({'status': 'started'}), status_code=200)


@app.get("/build/status")
async def build_status(datasetId):
    insights: Insights = insights_handler.get(dataset_id=datasetId)
    status = {
        'status': insights.build_status,
        'progress': insights.build_progress
    }
    logger.info(f"Returning status: {status}")
    return HTMLResponse(json.dumps(status, indent=2), status_code=200)


@app.get("/insights/build")
async def update_dataset(datasetId, itemId, background_tasks: BackgroundTasks):
    logger.info('starting insights build (insights.run) in background. get status from /insights/status page')
    background_tasks.add_task(build_in_background,
                              dataset_id=datasetId,
                              item_id=itemId)
    return HTMLResponse(json.dumps({'status': 'started'}), status_code=200)


app.mount("/dash", WSGIMiddleware(app_dash.server))
app.mount("/assets", StaticFiles(directory="src"), name="static")
app.mount("/insights", StaticFiles(directory="panels/insights", html=True), name='insights')
