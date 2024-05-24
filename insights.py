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
        self.divs = list()
        self.df = None
        self.gc = GraphsCalculator()
        self.path = f'tmp/{self.dataset.id}/json'
        self.build_status = "building"

    def download_export_from_item(self, export_item_id):
        item = dl.items.get(item_id=export_item_id)
        zip_path = item.download()

        dl.miscellaneous.Zipping.unzip_directory(zip_filename=zip_path,
                                                 to_directory=self.path)
        os.remove(zip_path)

    def build_dataframe(self):
        json_files = list(pathlib.Path(self.path).rglob('*.json'))

        def collect_single(path):
            singles = dict()
            try:
                with open(path) as f:
                    data = json.load(f)
                item_id = data['id']
                height = data.get('metadata', {}).get(
                    'system', {}).get('height', 0)
                width = data.get('metadata', {}).get(
                    'system', {}).get('height', 0)
                mimetype = data.get('metadata', {}).get(
                    'system', {}).get('mimetype', '')
                for annotation in data['annotations']:
                    if annotation['type'] != 'box':
                        continue
                    top = annotation['coordinates'][0]['y']
                    left = annotation['coordinates'][0]['x']
                    bottom = annotation['coordinates'][1]['y']
                    right = annotation['coordinates'][1]['x']
                    singles[annotation['id']] = {
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
                if len(singles) == 0:
                    singles[item_id] = {
                        'item_id': item_id,
                        'type': 'NA',
                        'annotation_id': 'NA',
                        'label': 'NA',
                        'top': 0,
                        'left': 0,
                        'bottom': 0,
                        'right': 0,
                        'annotation_height': 0,
                        'annotation_width': 0,
                        'attributes': 'NA',
                        'width': width,
                        'height': height,
                        'mimetype': mimetype
                    }
                alls.update(singles)
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

        print(f'DataFrame load time: {(time.time() - t):.2f}[s]')
        print(f'num items: {self.dataset.items_count}')
        print(f'num annotations: {self.dataset.annotations_count}')
        print(f'num annotations: {self.df.shape[0]}')

    def create_html(self):
        divs = [
            dbc.Container(className='card-container',
                          children=[
                              dbc.Card(children=dcc.Graph(id='graph-1-1',
                                                          figure=self.gc.histogram_annotation_by_item(df=self.df,
                                                                                                      settings=self.settings),
                                                          className="graph")),
                              dbc.Card(children=dcc.Graph(id='graph-1-2',
                                                          className="graph",
                                                          figure=self.gc.pie_annotation_type(df=self.df,
                                                                                             settings=self.settings)))
                          ]),
            dbc.Container(className='card-container',
                          children=[
                              dbc.Card(children=dcc.Graph(id='graph-2-1',
                                                          className="graph",
                                                          figure=self.gc.bar_annotations_labels(df=self.df,
                                                                                                settings=self.settings))),
                              dbc.Card(children=dcc.Graph(id='graph-2-2',
                                                          className="graph",
                                                          figure=self.gc.scatter_item_height_width(df=self.df,
                                                                                                   settings=self.settings)))
                          ]
                          ),
            dbc.Container(className='card-container',
                          children=[
                              dbc.Card(children=dcc.Graph(id='graph-3-1',
                                                          className="graph",
                                                          figure=self.gc.pie_annotation_attributes(df=self.df,
                                                                                                   settings=self.settings))),
                              dbc.Card(children=dcc.Graph(id='graph-3-2',
                                                          className="graph",
                                                          figure=self.gc.sunburst_annotation_attribute_by_label(
                                                              df=self.df, settings=self.settings)))
                          ], ),
            dbc.Container(className='card-container',
                          children=[
                              dbc.Card(children=dcc.Graph(id='graph-4-1',
                                                          className="graph",
                                                          figure=self.gc.heatmap_annotation_location(df=self.df,
                                                                                                     settings=self.settings))),
                              dbc.Card(children=dcc.Graph(id='graph-4-2',
                                                          className="graph",
                                                          figure=self.gc.scatter_annotation_height_width(
                                                              df=self.df,
                                                              settings=self.settings)))
                          ])
        ]
        # ))
        return divs

    def run(self, export_item_id):
        # first of all - show something
        if not self.export_item_id == export_item_id:
            self.export_item_id = export_item_id
            self.download_export_from_item(export_item_id=self.export_item_id)
            self.build_dataframe()
            self.gc.clear()
        self.divs = self.create_html()
