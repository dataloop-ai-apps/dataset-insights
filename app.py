from fastapi.middleware.cors import CORSMiddleware
import json
from concurrent.futures import ThreadPoolExecutor
import requests
import pydantic
import logging
import uvicorn
import tqdm

from dash import Dash  # Updated import for dash >= 2.0
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template
import dash_html_components as html

import dtlpy as dl

from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from insights import Insights
from exporter import Exporter

logger = logging.getLogger('[INSIGHTS]')
logging.basicConfig(level='INFO')

load_figure_template(["cyborg", "darkly", "minty", "cerulean"])

port = 3004


class Runner(dl.BaseServiceRunner):
    def __init__(self):
        uvicorn.run("app:app",
                    host="0.0.0.0",
                    port=port,
                    timeout_keep_alive=60)

    @staticmethod
    def upload_taco():
        def upload_single(d, n):
            try:
                _ = d.items.upload(local_path=r'E:\taco\items\raw\*',
                                   local_annotations_path=r'E:\taco\json\raw',
                                   remote_path=f'/{n:03}')
            except Exception as e:
                print(e)
            finally:
                pbar.update()

        dl.setenv('rc')
        dataset = dl.datasets.get(dataset_id='65d62d986052ab7e8de1f1b4')
        pool = ThreadPoolExecutor(max_workers=8)
        pbar = tqdm.tqdm(total=100)
        for num in range(2, 100):
            print(f'/{num:03}')
            pool.submit(fn=upload_single, n=num, d=dataset)
            # break
        pool.shutdown()


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


class Settings(pydantic.BaseModel):
    theme: str


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


@app.post("/insights/settings")
async def set_settings(datasetId: str, isDark="false"):
    insights: Insights = insights_handler.get(dataset_id=datasetId)
    print(f'SETTINGS: body: {isDark}')
    print(f'SETTINGS: body: {isDark}')
    if isDark == "false":
        logger.info('SETTINGS: Changing theme to minty')
        app_dash.config.external_stylesheets = [dbc.themes.MINTY]
        insights.settings['theme'] = "minty"
    else:
        logger.info('SETTINGS: Changing theme to darkly')
        app_dash.config.external_stylesheets = [dbc.themes.DARKLY]
        insights.settings['theme'] = "darkly"

    return HTMLResponse('success', status_code=200)


@app.get("/insights/build")
def update_dataset(datasetId, itemId, theme):
    insights: Insights = insights_handler.get(dataset_id=datasetId)
    insights.run(export_item_id=itemId)
    app_dash.layout = html.Div(
        id='main-container',
        className=['scroll', 'reactive-scroll'],
        children=[
            insights.divs
        ],
        **{"data-theme": 'dark-mode' if theme == 'dark' else 'light-mode'}
    )

    print('layout', app_dash.layout)

    # app_dash.layout = insights.divs
    return HTMLResponse(requests.get(f'http://localhost:{port}/dash').content, status_code=200)


app.mount("/dash", WSGIMiddleware(app_dash.server))
app.mount("/assets", StaticFiles(directory="src"), name="static")

if __name__ == "__main__":
    dl.setenv('rc')
    d = dl.datasets.get(None, '5f4d13ba4a958a49a7747cd9')
    runner = Runner()
    # http://localhost:3003/insights/build/5f4d13ba4a958a49a7747cd9
