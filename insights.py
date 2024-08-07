from concurrent.futures import ThreadPoolExecutor
import dtlpy as dl
import pandas as pd
import traceback
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
        self.items_df = None
        self.annotations_df = None
        self.gc = GraphsCalculator()
        self.path = f'tmp/{self.dataset.id}/json'
        self.build_status = "ready"
        self.build_progress = 0

    def download_export_from_item(self, export_item_id):
        item = dl.items.get(item_id=export_item_id)
        zip_path = item.download()

        dl.miscellaneous.Zipping.unzip_directory(zip_filename=zip_path,
                                                 to_directory=self.path)
        os.remove(zip_path)

    def collect_single_json(self, path, pbar, items_dict, annotations_dict):
        item_id = ""
        try:
            with open(path) as f:
                data = json.load(f)
            item_id = data['id']
            collection = dl.AnnotationCollection.from_json_file(path)
            items_dict[item_id] = {
                'item_id': data['id'],
                'width': data.get('metadata', {}).get('system', {}).get('height', 0),
                'height': data.get('metadata', {}).get('system', {}).get('height', 0),
                'mimetype': data.get('metadata', {}).get('system', {}).get('mimetype', ''),
                'size': data.get('metadata', {}).get('system', {}).get('size', 0)
            }
            for annotation in collection:
                annotation: dl.Annotation
                try:
                    annotations_dict[annotation.id] = {
                        'item_id': item_id,
                        'type': annotation.type,
                        'annotation_id': annotation.id,
                        'label': annotation.label,
                        'top': annotation.top,
                        'left': annotation.left,
                        'bottom': annotation.bottom,
                        'right': annotation.right,
                        'annotation_height': annotation.bottom - annotation.top,
                        'annotation_width': annotation.right - annotation.left,
                        'attributes': None,
                    }
                except Exception:
                    logger.exception(f'failed in annotation: {annotation.id}')
        except Exception as e:
            logger.exception(f'failed in item: {item_id}')
        finally:
            pbar.update()
            self.build_progress = min(pbar.n / pbar.total, 0.99)

    def build_dataframe(self):
        json_files = list(pathlib.Path(self.path).rglob('*.json'))
        pool = ThreadPoolExecutor(max_workers=128)
        pbar = tqdm.tqdm(total=len(json_files))
        items_dict = dict()
        annotations_dict = dict()
        t = time.time()
        for filepath in json_files:
            pool.submit(self.collect_single_json,
                        path=filepath,
                        pbar=pbar,
                        items_dict=items_dict,
                        annotations_dict=annotations_dict)
        pool.shutdown()

        logger.info(f'files collection time: {(time.time() - t):.2f}[s]')
        t = time.time()
        self.items_df = pd.DataFrame(items_dict.values())
        self.annotations_df = pd.DataFrame(annotations_dict.values())
        for filepath in json_files:
            os.remove(filepath)
        logger.info(f'DataFrame load time: {(time.time() - t):.2f}[s]')
        logger.info(f'num dataset items: {self.dataset.items_count}')
        logger.info(f'num dataframe items: {self.items_df.shape[0]}')
        logger.info(f'num dataset annotations: {self.dataset.annotations_count}')
        logger.info(f'num dataframe annotations: {self.annotations_df.shape[0]}')

    def create_html(self):
        divs = [
            dbc.Container(className='card-container',
                          children=[
                              dbc.Card(children=dcc.Graph(id='graph-1-1',
                                                          figure=self.gc.histogram_annotation_by_item(
                                                              df=self.annotations_df,
                                                              settings=self.settings),
                                                          className="graph")),
                              dbc.Card(children=dcc.Graph(id='graph-1-2',
                                                          className="graph",
                                                          figure=self.gc.pie_annotation_type(df=self.annotations_df,
                                                                                             settings=self.settings)))
                          ]),
            dbc.Container(className='card-container',
                          children=[
                              dbc.Card(children=dcc.Graph(id='graph-2-1',
                                                          className="graph",
                                                          figure=self.gc.bar_annotations_labels(df=self.annotations_df,
                                                                                                settings=self.settings))),
                              dbc.Card(children=dcc.Graph(id='graph-2-2',
                                                          className="graph",
                                                          figure=self.gc.scatter_item_height_width(df=self.items_df,
                                                                                                   settings=self.settings)))
                          ]
                          ),
            # dbc.Container(className='card-container',
            #               children=[
            #                   dbc.Card(children=dcc.Graph(id='graph-3-1',
            #                                               className="graph",
            #                                               figure=self.gc.pie_annotation_attributes(
            #                                                   df=self.annotations_df,
            #                                                   settings=self.settings))),
            #                   dbc.Card(children=dcc.Graph(id='graph-3-2',
            #                                               className="graph",
            #                                               figure=self.gc.sunburst_annotation_attribute_by_label(
            #                                                   df=self.annotations_df,
            #                                                   settings=self.settings)))
            #               ], ),
            dbc.Container(className='card-container',
                          children=[
                              dbc.Card(children=dcc.Graph(id='graph-4-1',
                                                          className="graph",
                                                          figure=self.gc.heatmap_annotation_location(
                                                              annotations_df=self.annotations_df,
                                                              items_df=self.items_df,
                                                              settings=self.settings,
                                                          ))),
                              dbc.Card(children=dcc.Graph(id='graph-4-2',
                                                          className="graph",
                                                          figure=self.gc.scatter_annotation_height_width(
                                                              df=self.annotations_df,
                                                              settings=self.settings,
                                                              max_item_width=self.items_df['height'].max(),
                                                              max_item_height=self.items_df['height'].max(),
                                                          )))
                          ])
        ]

        return divs

    def get_parquet_files(self):
        json_item = dl.items.get(item_id=self.export_item_id)
        name, ext = os.path.splitext(json_item.name)
        first_path = f'/.dataloop/exports/insights_parquet/{json_item.dataset_id}/{name}-items.parquet'
        second_path = f'/.dataloop/exports/insights_parquet/{json_item.dataset_id}/{name}-annotations.parquet'
        filters = dl.Filters(use_defaults=False,
                             field='filename',
                             values=first_path)
        first_pages = json_item.dataset.items.list(filters=filters)
        filters = dl.Filters(use_defaults=False,
                             field='filename',
                             values=second_path)
        second_pages = json_item.dataset.items.list(filters=filters)
        if first_pages.items_count != 0 and second_pages.items_count != 0:
            logger.info('found parquet files! downloading existing dataframes')
            self.items_df = pd.read_parquet(first_pages.items[0].download(save_locally=False))
            self.annotations_df = pd.read_parquet(second_pages.items[0].download(save_locally=False))
            return True
        else:
            return False

    def set_parquet_files(self):
        json_item = dl.items.get(item_id=self.export_item_id)
        name, ext = os.path.splitext(json_item.name)
        self.items_df.to_parquet(f'{json_item.id}-items.parquet')
        remote_path = f'/.dataloop/exports/insights_parquet/{json_item.dataset_id}/{name}-items.parquet'
        json_item.dataset.items.upload(local_path=f'{json_item.id}-items.parquet',
                                       remote_path=os.path.dirname(remote_path),
                                       remote_name=os.path.basename(remote_path))
        remote_path = f'/.dataloop/exports/insights_parquet/{json_item.dataset_id}/{name}-annotations.parquet'
        self.annotations_df.to_parquet(f'{json_item.id}-annotations.parquet')
        json_item.dataset.items.upload(local_path=f'{json_item.id}-annotations.parquet',
                                       remote_path=os.path.dirname(remote_path),
                                       remote_name=os.path.basename(remote_path))

        # remove local files
        os.remove(f'{json_item.id}-items.parquet')
        os.remove(f'{json_item.id}-annotations.parquet')

    def run(self, export_item_id):
        if self.build_status not in ("failed", "ready"):
            return
        self.build_status = "started"
        self.build_progress = 0
        try:
            # first of all - show something
            if not self.export_item_id == export_item_id:
                self.export_item_id = export_item_id
                self.build_status = "downloading"
                if self.get_parquet_files() is not True:
                    self.download_export_from_item(export_item_id=self.export_item_id)
                    self.build_status = "building"
                    self.build_dataframe()
                    self.set_parquet_files()
                self.gc.clear()
                self.build_status = "creating"
                self.build_progress = 0.995
                self.divs = self.create_html()

            self.build_status = "ready"
            self.build_progress = 1
            self.items_df = None
            self.annotations_df = None
        except Exception as e:
            self.build_status = "failed"
            self.build_progress = traceback.format_exc()


if __name__ == "__main__":
    self = Insights(dataset_id='665b919f446301a86622d1a0')
    self.export_item_id = ''
    self.run('6660ab485e2fff2e70e3cda2')
