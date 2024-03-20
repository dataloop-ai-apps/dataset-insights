from concurrent.futures import ThreadPoolExecutor
import urllib.parse
import requests
import pydantic
import logging
import uvicorn
import tqdm

from dash import Dash, dcc, Input, Output, State  # Updated import for dash >= 2.0
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

import dtlpy as dl

from fastapi.middleware.wsgi import WSGIMiddleware
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse

from insights import Insights
from utils.styles import header_styles
import subprocess

logger = logging.getLogger('[INSIGHTS]')
logging.basicConfig(level='INFO')

load_figure_template(["cyborg", "darkly", "minty", "cerulean"])

port = 3000


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
            self.insights[dataset_id] = Insights(dataset_id=dataset_id, port=port)
        print(self.insights)
        return self.insights[dataset_id]


insights_handler = InsightsHandles()
app = FastAPI()

app_dash = Dash(__name__,
                external_stylesheets=[dbc.themes.MINTY],
                suppress_callback_exceptions=True,
                routes_pathname_prefix="/",
                requests_pathname_prefix="/dash/")
app_dash.layout = dbc.Container(
    children=[
        dcc.Location(id='url', refresh=False),
        dbc.Container(children=[dbc.Container(children=dbc.Container(children=f"Preparing")),
                                dbc.Container(children=dbc.Button(children="Run",
                                                                  id="run-button",
                                                                  style={'min-width': '110px'}))

                                ],
                      style=header_styles),
        dbc.Container(children=[
            dcc.Interval(id="progress-interval", n_intervals=0, interval=1 * 1000, disabled=True),
            dbc.Progress(id="progress-bar", value=0, max=100),
        ]), ])


# Callback to update the content of 'output-container' upon button clicks
@app_dash.callback(
    [
        Output("run-button", "disabled"),
        Output("run-button", "children"),
        Output("progress-interval", "disabled"),
        Output("progress-bar", "value"),
        Output("url", "refresh"),
        Output("url", "pathname"),

    ],
    [
        Input('run-button', 'n_clicks'),
        Input('progress-interval', 'n_intervals'),
        Input('url', 'pathname')
    ],
    [State('progress-interval', 'disabled')],

    prevent_initial_call=True
)
def handle_progress(n_clicks, n_intervals, pathname, interval_disabled):
    """
    Output order [
    :param n_clicks:
    :param n_intervals:
    :param pathname:
    :param interval_disabled:
    :return:
    """
    pathname = urllib.parse.unquote(pathname)
    print("n_clicks", n_clicks)
    print("n_intervals", n_intervals)
    print("pathname", pathname)
    print("interval_disabled", interval_disabled)

    disable_button = True
    button_text = "Run"
    disable_interval = True
    url_pathname = urllib.parse.urlparse(pathname).path
    url_refresh = False
    progress_val = 0
    if n_clicks is None:
        disable_button = False
        button_text = "Run"
        disable_interval = True
    else:
        insights = insights_handler.get(urllib.parse.urlparse(pathname).path.split('/')[-1])
        if interval_disabled is True:
            # start the run
            url = f'http://localhost:{port}{pathname}?force=true'
            print(f'calling ur;l: {url}')
            requests.get(url=url)
            disable_button = True
            button_text = "Fetching.."
            disable_interval = False
            progress_val = 0
            # url_refresh = True
            # url_pathname = urlparse(pathname).path + "?force=true"
        else:
            # running, update the progress
            print(progress_val)
            progress_val = insights.progress
            if progress_val >= 100:
                disable_interval = True
                disable_button = False
                button_text = "Run"
                progress_val = 100
                url_refresh = True
                url_pathname = urllib.parse.urlparse(pathname).path
            else:
                disable_interval = False
                disable_button = True
                button_text = "Fetching..."
    output = [disable_button, button_text, disable_interval, progress_val, url_refresh, url_pathname]
    print(f'sending event: {output}')
    return output

#
# app_dash.clientside_callback(
#     """function (select, id) {
#         if (select) {
#             console.log(select)
#         }
#         return ''
#     }""",
#     Output('111', 'children'),
#     Input('11', 'selectedData'),
#     State('11', 'id'),
#     prevent_initial_call=True
# )


class Settings(pydantic.BaseModel):
    theme: str


@app.post("/insights/settings/{dataset_id}")
async def set_settings(settings, dataset_id: str):
    insights: Insights = insights_handler.get(dataset_id=dataset_id)
    print(f'SETTINGS: body: {settings}')
    print(f'SETTINGS: body: {settings}')
    if settings.get('theme') == 'light':
        logger.info('SETTINGS: Changing theme to minty')
        app_dash.config.external_stylesheets = [dbc.themes.MINTY]
        insights.settings['theme'] = "minty"
    else:
        logger.info('SETTINGS: Changing theme to darkly')
        app_dash.config.external_stylesheets = [dbc.themes.DARKLY]
        insights.settings['theme'] = "darkly"

    return HTMLResponse('success', status_code=200)


@app.get("/insights/main")
async def read_index():
    # return loading html
    with open('src/loading.html') as f:
        content = f.read()
    return HTMLResponse(content, status_code=200)


@app.get("/insights")
def main():
    with open('src/index.html') as f:
        page = f.read()
    return HTMLResponse(page, status_code=200)


@app.get("/insights/build/{dataset_id}")
def update_dataset(dataset_id, force=False):
    force = force == 'true'
    insights: Insights = insights_handler.get(dataset_id=dataset_id)
    if insights.divs is None or force is True:
        logger.info(f'starting to build.. dataset: {dataset_id}, force: {force}')
        insights.run(force=force)
    app_dash.layout = insights.divs
    return HTMLResponse(requests.get(f'http://localhost:{port}/dash').content, status_code=200)


app.mount("/dash", WSGIMiddleware(app_dash.server))
app.mount("/assets", StaticFiles(directory="src"), name="static")

if __name__ == "__main__":
    dl.setenv('rc')
    d = dl.datasets.get(None, '5f4d13ba4a958a49a7747cd9')
    runner = Runner()
    # http://localhost:3003/insights/build/5f4d13ba4a958a49a7747cd9
