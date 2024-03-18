import io
import threading
from concurrent.futures import ThreadPoolExecutor
import dtlpy as dl
import numpy as np
import pandas as pd
import datetime
import logging
import pathlib
import json
import time
import tqdm
import os

logger = logging.getLogger('[DATA-EXPORTER]')


class Exporter:
    def __init__(self, dataset):
        self.dataset: dl.Dataset = dataset
        self.path = f'tmp/{self.dataset.id}/json'
        self._progress = 0

    def progress(self):
        return self._progress

    @staticmethod
    def change_iso_date_string(iso_datetime):
        # Parse the ISO 8601 string to a datetime object
        dt = datetime.datetime.fromisoformat(iso_datetime)
        # Format the datetime object to a more readable string
        readable_string = dt.strftime('%B %d, %Y %H:%M:%S')
        return readable_string

    def wait_for_command(self, command_id):
        timeout = 0
        max_sleep_time = 30
        backoff_factor = 1
        elapsed = 0
        start = time.time()
        if timeout is None or timeout <= 0:
            timeout = np.inf

        command = None
        num_tries = 1
        while elapsed < timeout:
            command = dl.commands.get(command_id=command_id)
            if not command.in_progress():
                break
            elapsed = time.time() - start
            sleep_time = np.min([timeout - elapsed, backoff_factor * (2 ** num_tries), max_sleep_time])
            self._progress = command.progress
            num_tries += 1
            logger.debug("Command {!r} is running for {:.2f}[s] and now Going to sleep {:.2f}[s]".format(command.id,
                                                                                                         elapsed,
                                                                                                         sleep_time))
            time.sleep(sleep_time)
        if command is None:
            raise ValueError('Nothing to wait for')
        if elapsed >= timeout:
            raise TimeoutError("command wait() got timeout. id: {!r}, status: {}, progress {}%".format(
                command.id, command.status, command.progress))
        if command.status != dl.CommandsStatus.SUCCESS:
            raise dl.exceptions.PlatformException(error='424',
                                                  message="Command {!r} {}: '{}'".format(command.id,
                                                                                         command.status,
                                                                                         command.error))

        command = self.wait_for_command(command_id=command.id)

        if 'outputItemId' not in command.spec:
            raise dl.exceptions.PlatformException(
                error='400',
                message="outputItemId key is missing in command id: {}".format(command_id))
        self.remove_active_exports()
        item_id = command.spec['outputItemId']
        annotation_zip_item = self.dataset.items.get(item_id=item_id)

        return annotation_zip_item

    def start_export(self):
        t = time.time()
        export_version = dl.ExportVersion.V1
        payload = dict()
        # if filters is not None:
        #     payload['itemsQuery'] = filters.prepare()
        payload['annotations'] = {
            "include": True,
            "convertSemantic": False
        }
        payload['exportVersion'] = export_version
        # if annotation_filters is not None:
        #     payload['annotationsQuery'] = annotation_filters.prepare()
        #     payload['annotations']['filter'] = filter_output_annotations

        success, response = self.dataset._client_api.gen_request(req_type='post',
                                                                 path='/datasets/{}/export'.format(self.dataset.id),
                                                                 json_req=payload,
                                                                 headers={'user_query': 'true'})
        if not success:
            raise dl.exceptions.PlatformException(response)

        # save command in json
        command = dl.Command.from_json(_json=response.json(),
                                       client_api=self.dataset._client_api)
        self.update_active_exports(command_id=command.id)

        return command.id

    def download_export_from_item(self, item):
        zip_path = item.download()
        export_date = self.change_iso_date_string(item.created_at[:-1])
        dl.miscellaneous.Zipping.unzip_directory(zip_filename=zip_path,
                                                 to_directory=self.path)
        os.remove(zip_path)
        return export_date

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
        df = pd.DataFrame(alls.values())
        # pd.concat({x: pd.Series(y) for x, y in d.items()}).reset_index()

        print(f'DataFrame load time: {(time.time() - t):.2f}[s]')
        print(f'num items: {self.dataset.items_count}')
        print(f'num annotations: {self.dataset.annotations_count}')
        print(f'num annotations: {df.shape[0]}')
        return df

    def update_active_exports(self, command_id):
        b_dataset = self.dataset.project.datasets._get_binaries_dataset()
        filters = dl.Filters(use_defaults=False)
        buffer = io.BytesIO()
        buffer.write(json.dumps({"commandId": command_id}).encode('utf-8'))
        buffer.name = "active_export.json"
        b_dataset.items.upload(local_path=buffer,
                               remote_path=f'/.dataloop/exports/{self.dataset.id}',
                               overwrite=True)

    def remove_active_exports(self):
        filters = dl.Filters(use_defaults=False)
        filters.add(field='dir', values=f'/.dataloop/exports/{self.dataset.id}/active_export.json')
        filters.page_size = 10
        b_dataset = self.dataset.project.datasets._get_binaries_dataset()
        items = b_dataset.items.list(filters=filters)
        if items.items_count != 0:
            items.items[0].delete()
        return True

    def check_active_exports(self):
        filters = dl.Filters(use_defaults=False)
        filters.add(field='dir', values=f'/.dataloop/exports/{self.dataset.id}/active_export.json')
        filters.page_size = 10
        b_dataset = self.dataset.project.datasets._get_binaries_dataset()
        items = b_dataset.items.list(filters=filters)
        if items.items_count != 0:
            with open(items.items[0].download(overwrite=True)) as f:
                export_data = json.load(f)
            return export_data['commandId']
        else:
            return None

    def find_last_export(self):
        filters = dl.Filters(use_defaults=False)
        filters.add(field='dir', values=f'/.dataloop/exports/{self.dataset.id}')
        filters.sort_by(field='createdAt', value=dl.FiltersOrderByDirection.DESCENDING)
        filters.page_size = 10
        b_dataset = self.dataset.project.datasets._get_binaries_dataset()
        items = b_dataset.items.list(filters=filters)
        if items.items_count != 0:
            return items.items[0]
        else:
            return None

    def create_html(self, df, export_date):
        divs = dbc.Container(
            children=[
                dbc.Container(children=[dbc.Container(children=dbc.Container(children=f"Last Updated: {export_date}")),
                                        dbc.Container(children=dbc.Button(children="Run",
                                                                          id="run-button",
                                                                          style={'min-width': '110px'}))

                                        ],
                              style=header_styles),
                dbc.Container(children=[
                    dcc.Interval(id="progress-interval", n_intervals=0, interval=1 * 1000, disabled=True),
                    dbc.Progress(id="progress-bar", value=0, max=100),
                ]),
                dbc.Container(children=[
                    dbc.Card(children=dcc.Graph(id='11',
                                                figure=self.gc.histogram_annotation_by_item(df=df,
                                                                                            settings=self.settings),
                                                style=graph_style),
                             style=card_style),
                    dbc.Card(children=dcc.Graph(id='12',
                                                style=graph_style,
                                                figure=self.gc.pie_annotation_type(df=df,
                                                                                   settings=self.settings)),
                             style=card_style)
                ],
                    style=container_style,
                ),
                dbc.Container(children=[
                    dbc.Card(children=dcc.Graph(id='21',
                                                style=graph_style,
                                                figure=self.gc.bar_annotations_labels(df=df,
                                                                                      settings=self.settings)),
                             style=card_style),
                    dbc.Card(children=dcc.Graph(id='22',
                                                style=graph_style,
                                                figure=self.gc.scatter_item_height_width(df=df,
                                                                                         settings=self.settings)),
                             style=card_style)
                ],
                    style=container_style,
                ),
                dbc.Container(children=[
                    dbc.Card(children=dcc.Graph(id='31',
                                                style=graph_style,
                                                figure=self.gc.pie_annotation_attributes(df=df,
                                                                                         settings=self.settings)),
                             style=card_style),
                    dbc.Card(children=dcc.Graph(id='32',
                                                style=graph_style,
                                                figure=self.gc.sunburst_annotation_attribute_by_label(
                                                    df=df, settings=self.settings)),
                             style=card_style)
                ],
                    style=container_style),
                dbc.Container(children=[dbc.Card(children=dcc.Graph(id='41',
                                                                    style=graph_style,
                                                                    figure=self.gc.heatmap_annotation_location(
                                                                        df=df,
                                                                        settings=self.settings)),
                                                 style=card_style),
                                        dbc.Card(children=dcc.Graph(id='42',
                                                                    style=graph_style,
                                                                    figure=self.gc.scatter_annotation_height_width(
                                                                        df=df,
                                                                        settings=self.settings)),
                                                 style=card_style)
                                        ],
                              style=container_style)
            ],
            style={'font-family': '"Open Sans", verdana, arial, sans-serif'},
            id='main-container')
        return divs


    def async_run_and_refresh(self):
        command_id = self.check_active_exports()
        if command_id is None:
            command_id = self.start_export()
        item = self.wait_for_command(command_id=command_id)
        export_date = self.download_export_from_item(item=item)
        df = self.build_dataframe()
        self.divs = self.create_html(df, export_date)

    def run(self, force):
        # first of all - show something
        item = self.find_last_export()
        if item is None:
            force = True
            export_date = "No existing export"
            df = pd.DataFrame()
        else:
            export_date = self.download_export_from_item(item=item)
            df = self.build_dataframe()

        if self.check_active_exports() is not None:
            force = True

        if force is True:
            thread = threading.Thread(target=self.async_run_and_refresh)
            thread.daemon = True
            thread.start()
        self.divs = self.create_html(df, export_date)
