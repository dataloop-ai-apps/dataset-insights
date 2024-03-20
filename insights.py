from concurrent.futures import ThreadPoolExecutor
import dtlpy as dl
import numpy as np
import pandas as pd
import logging
import pathlib
import json
import time
import tqdm
import os

from dash import dcc
import dash_bootstrap_components as dbc
from dash_bootstrap_templates import load_figure_template

from utils.styles import container_style, graph_style, card_style, header_styles
from utils.generate_graphs import GraphsCalculator

logger = logging.getLogger('[INSIGHTS]')
logging.basicConfig(level='INFO')

load_figure_template(["cyborg", "darkly", "minty", "cerulean"])


class Insights:
    def __init__(self, dataset_id):
        super(Insights, self).__init__()
        self.dataset_id = dataset_id
        self.export_item_id = ''
        self.dataset = dl.datasets.get(dataset_id=self.dataset_id)
        # self.settings = {"theme": "minty"}
        self.settings = {"theme": "darkly"}
        self.divs = None
        self.df = None
        self.gc = GraphsCalculator()
        self.path = f'tmp/{self.dataset.id}/json'

    def download_export_from_item(self, export_item_id):
        item = dl.items.get(item_id=export_item_id)
        zip_path = item.download()

        dl.miscellaneous.Zipping.unzip_directory(zip_filename=zip_path,
                                                 to_directory=self.path)
        os.remove(zip_path)

    def build_dataframe(self):
        print('datasettttt', self.dataset.id)
        json_files = list(pathlib.Path(self.path).rglob('*.json'))

        def collect_single(path):
            try:
                with open(path) as f:
                    data = json.load(f)
                item_id = data['id']
                height = data.get('metadata', {}).get('system', {}).get('height', 0)
                width = data.get('metadata', {}).get('system', {}).get('height', 0)
                mimetype = data.get('metadata', {}).get('system', {}).get('mimetype', '')
                for annotation in data['annotations']:
                    if annotation['type'] != 'box':
                        continue
                    top = annotation['coordinates'][0]['y']
                    left = annotation['coordinates'][0]['x']
                    bottom = annotation['coordinates'][1]['y']
                    right = annotation['coordinates'][1]['x']
                    alls[annotation['id']] = {
                        'item_id': item_id,
                        'type': annotation['type'],
                        'annotation_id': annotation['id'],
                        'label': annotation['label'],
                        'top': top,
                        'left': left,
                        'bottom': bottom,
                        'right': right,
                        'annotation_height': bottom - top,
                        'annotation_width': right - left,
                        'attributes': np.random.choice(['red', 'blue', 'gold'], p=[0.7, 0.2, 0.1]),
                        'width': width,
                        'height': height,
                        'mimetype': mimetype
                    }
            except Exception as e:
                print(e)
            finally:
                pbar.update()

        pool = ThreadPoolExecutor(max_workers=128)
        pbar = tqdm.tqdm(total=len(json_files))
        alls = dict()
        t = time.time()
        for filepath in json_files:
            pool.submit(collect_single, path=filepath)
        pool.shutdown()
        print(f'files collection time: {(time.time() - t):.2f}[s]')
        t = time.time()
        self.df = pd.DataFrame(alls.values())
        # pd.concat({x: pd.Series(y) for x, y in d.items()}).reset_index()

        print(f'DataFrame load time: {(time.time() - t):.2f}[s]')
        print(f'num items: {self.dataset.items_count}')
        print(f'num annotations: {self.dataset.annotations_count}')
        print(f'num annotations: {self.df.shape[0]}')

    def create_html(self):
        divs = dbc.Container(
            style={'font-family': '"Open Sans", verdana, arial, sans-serif'},
            id='main-container',
            children=[
                dcc.Location(id='url'),
                dbc.Container(
                    children=[
                    dbc.Card(children=dcc.Graph(id='11',
                                                figure=self.gc.histogram_annotation_by_item(df=self.df,
                                                                                            settings=self.settings),
                                                className="graph",
                                                style=graph_style),
                             style=card_style),
                    dbc.Card(children=dcc.Graph(id='12',
                                                style=graph_style,
                                                className="graph",

                                                figure=self.gc.pie_annotation_type(df=self.df,
                                                                                   settings=self.settings)),
                             style=card_style)
                ],
                    style=container_style,
                ),
                dbc.Container(children=[
                    dbc.Card(children=dcc.Graph(id='21',
                                                style=graph_style,
                                                className="graph",

                                                figure=self.gc.bar_annotations_labels(df=self.df,
                                                                                      settings=self.settings)),
                             style=card_style),
                    dbc.Card(children=dcc.Graph(id='22',
                                                style=graph_style,
                                                className="graph",

                                                figure=self.gc.scatter_item_height_width(df=self.df,
                                                                                         settings=self.settings)),
                             style=card_style)
                ],
                    style=container_style,
                ),
                dbc.Container(children=[
                    dbc.Card(children=dcc.Graph(id='31',
                                                className="graph",

                                                style=graph_style,
                                                figure=self.gc.pie_annotation_attributes(df=self.df,
                                                                                         settings=self.settings)),
                             style=card_style),
                    dbc.Card(children=dcc.Graph(id='32',
                                                className="graph",

                                                style=graph_style,
                                                figure=self.gc.sunburst_annotation_attribute_by_label(
                                                    df=self.df, settings=self.settings)),
                             style=card_style)
                ],
                    style=container_style),
                dbc.Container(children=[
                    dbc.Card(children=dcc.Graph(id='41',
                                                className="graph",

                                                style=graph_style,
                                                figure=self.gc.heatmap_annotation_location(
                                                    df=self.df,
                                                    settings=self.settings)),
                             style=card_style),
                    dbc.Card(children=dcc.Graph(id='42',
                                                className="graph",

                                                style=graph_style,
                                                figure=self.gc.scatter_annotation_height_width(
                                                    df=self.df,
                                                    settings=self.settings)),
                             style=card_style)
                ],
                    style=container_style)
            ]
        )
        return divs

    def run(self, export_item_id):
        # first of all - show something
        if self.export_item_id == export_item_id:
            # same export - no need to build everything
            ...
        else:
            self.export_item_id = export_item_id
            self.download_export_from_item(export_item_id=self.export_item_id)
            self.build_dataframe()
            self.gc.clear()
        self.divs = self.create_html()
