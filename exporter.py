import os
import time
import traceback
import logging
from enum import Enum

import dash_bootstrap_components as dbc
import dtlpy as dl
import pandas as pd
import tqdm


from dash import dcc
from dtlpy_exporter import ExportBase

from utils.generate_graphs import GraphsCalculator

logger = logging.getLogger('[INSIGHTS]')
logging.basicConfig(level='INFO')


class BuildStatus(str, Enum):
    """
    Enum class representing the various statuses of a build process.

    Attributes:
        READY (str): The build is ready to start.
        STARTED (str): The build has started.
        DOWNLOADING (str): The build is in the process of downloading resources.
        BUILDING (str): The build is in the process of being built.
        CREATING (str): The build is in the process of creating resources.
        FAILED (str): The build has failed.
    """

    READY = "ready"
    STARTED = "started"
    DOWNLOADING = "downloading"
    BUILDING = "building"
    CREATING = "creating"
    FAILED = "failed"


class Exporter(ExportBase):
    """
    A class used to export dataset insights and generate visualizations.

    Attributes
    ----------
    default_graph_config : dict
        Configuration for Plotly graphs.
    settings : dict
        Settings for the visualizations.
    divs : list
        List of HTML div elements containing the graphs.
    items_df : pd.DataFrame
        DataFrame containing item metadata.
    annotations_df : pd.DataFrame
        DataFrame containing annotation metadata.
    gc : GraphsCalculator
        Instance of GraphsCalculator to generate graphs.
    path : str
        Path to save temporary JSON files.
    build_status : str
        Status of the build process.
    build_progress : float
        Progress of the build process.

    Methods
    -------
    build_dataframe():
        Builds DataFrames from the downloaded data.
    create_html():
        Creates HTML div elements containing the graphs.
    get_parquet_files():
        Checks for existing Parquet files and loads them if available.
    set_parquet_files():
        Saves the DataFrames as Parquet files and uploads them.
    process_data():
        Processes the data, builds DataFrames, saves Parquet files, and creates HTML divs.
    """

    def __init__(self, dataset_id):
        super().__init__(dataset_id)
        if not hasattr(self, 'default_graph_config'):
            self.default_graph_config = {
                'displaylogo': False,  # Hide Plotly logo
                'modeBarButtonsToRemove': ['toImage'],  # Remove the download button
            }
            self.settings = {"theme": "darkly"}
            self.divs = list()
            self.items_df = None
            self.annotations_df = None
            self.gc = GraphsCalculator()
            self.path = f'tmp/{self.dataset.id}/json'
            self.build_status = BuildStatus.READY
            self.build_progress = 0

    def build_dataframe(self):
        """
        Builds dataframes for items and annotations from the downloaded data.

        This method processes the downloaded data to create two pandas DataFrames:
        one for items and one for annotations. It uses a progress bar to track the
        progress of the data processing.

        Attributes:
            self.download_data (list): List of downloaded data items.
            self.build_progress (float): Progress of the dataframe building process.
            self.items_df (pd.DataFrame): DataFrame containing item information.
            self.annotations_df (pd.DataFrame): DataFrame containing annotation information.

        Raises:
            Exception: If there is an error processing an item or annotation, it logs the exception.

        Logs:
            Logs the time taken to collect files and load DataFrames.
            Logs the number of items and annotations in the dataset and DataFrames.
        """
        pbar = tqdm.tqdm(total=len(self.download_data))
        items_dict = dict()
        annotations_dict = dict()
        t = time.time()
        for data in self.download_data:
            item_id = data['id']
            try:
                items_dict[item_id] = {
                    'item_id': data['id'],
                    'width': data.get('metadata', {})
                    .get('system', {})
                    .get('height', 0),
                    'height': data.get('metadata', {})
                    .get('system', {})
                    .get('height', 0),
                    'mimetype': data.get('metadata', {})
                    .get('system', {})
                    .get('mimetype', ''),
                    'size': data.get('metadata', {}).get('system', {}).get('size', 0),
                }
                collection = dl.AnnotationCollection.from_json(data['annotations'])
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
                    except (KeyError, TypeError, ValueError):
                        logger.exception('failed in annotation: %s', annotation.id)
            except (KeyError, TypeError, ValueError):
                logger.exception('failed in item: %s', item_id)
            finally:
                pbar.update()
                self.build_progress = min(pbar.n / pbar.total, 0.99)

        logger.info('files collection time: %.2f[s]', time.time() - t)
        t = time.time()
        self.items_df = pd.DataFrame(items_dict.values())
        self.annotations_df = pd.DataFrame(annotations_dict.values())
        logger.info('DataFrame load time: %.2f[s]', time.time() - t)
        logger.info('num dataset items: %d', self.dataset.items_count)
        logger.info('num dataframe items: %d', self.items_df.shape[0])
        logger.info('num dataset annotations: %d', self.dataset.annotations_count)
        logger.info('num dataframe annotations: %d', self.annotations_df.shape[0])

    def create_html(self):
        """
        Creates a list of Dash Bootstrap Components (dbc) Containers, each containing
        dbc Cards with Plotly Dash Graphs. The graphs are generated using various
        methods from the `gc` (graph creator) object, which visualize different aspects
        of the data stored in `annotations_df` and `items_df`.

        Returns:
            list: A list of dbc.Container objects, each containing dbc.Card components
                  with dcc.Graph elements.
        """
        divs = [
            dbc.Container(
                className='card-container',
                children=[
                    dbc.Card(
                        children=dcc.Graph(
                            id='graph-1-1',
                            figure=self.gc.histogram_annotation_by_item(
                                df=self.annotations_df, settings=self.settings
                            ),
                            className="graph",
                            config=self.default_graph_config,
                        )
                    ),
                    dbc.Card(
                        children=dcc.Graph(
                            id='graph-1-2',
                            className="graph",
                            figure=self.gc.pie_annotation_type(
                                df=self.annotations_df, settings=self.settings
                            ),
                            config=self.default_graph_config,
                        )
                    ),
                ],
            ),
            dbc.Container(
                className='card-container',
                children=[
                    dbc.Card(
                        children=dcc.Graph(
                            id='graph-2-1',
                            className="graph",
                            figure=self.gc.bar_annotations_labels(
                                df=self.annotations_df, settings=self.settings
                            ),
                            config=self.default_graph_config,
                        )
                    ),
                    dbc.Card(
                        children=dcc.Graph(
                            id='graph-2-2',
                            className="graph",
                            figure=self.gc.scatter_item_height_width(
                                df=self.items_df, settings=self.settings
                            ),
                            config=self.default_graph_config,
                        )
                    ),
                ],
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
            dbc.Container(
                className='card-container',
                children=[
                    dbc.Card(
                        children=dcc.Graph(
                            id='graph-4-1',
                            className="graph",
                            figure=self.gc.heatmap_annotation_location(
                                annotations_df=self.annotations_df,
                                items_df=self.items_df,
                                settings=self.settings,
                            ),
                            config=self.default_graph_config,
                        )
                    ),
                    dbc.Card(
                        children=dcc.Graph(
                            id='graph-4-2',
                            className="graph",
                            figure=self.gc.scatter_annotation_height_width(
                                df=self.annotations_df,
                                settings=self.settings,
                                max_item_width=self.items_df['height'].max(),
                                max_item_height=self.items_df['height'].max(),
                            ),
                            config=self.default_graph_config,
                        )
                    ),
                ],
            ),
        ]

        return divs

    def get_parquet_files(self):
        """
        Retrieves parquet files for items and annotations from a dataset.

        This method checks for the existence of parquet files for items and annotations
        in a specified dataset. If both files are found, they are downloaded and loaded
        into pandas DataFrames.

        Returns:
            bool: True if both parquet files are found and successfully loaded, False otherwise.
        """
        json_item = dl.items.get(item_id=self.output_item_ids[0])
        name, _ = os.path.splitext(json_item.name)
        first_path = f'/.dataloop/exports/insights_parquet/{json_item.dataset_id}/{name}-items.parquet'
        second_path = f'/.dataloop/exports/insights_parquet/{json_item.dataset_id}/{name}-annotations.parquet'
        filters = dl.Filters(use_defaults=False, field='filename', values=first_path)
        first_pages = json_item.dataset.items.list(filters=filters)
        filters = dl.Filters(use_defaults=False, field='filename', values=second_path)
        second_pages = json_item.dataset.items.list(filters=filters)
        if first_pages.items_count != 0 and second_pages.items_count != 0:
            logger.info('found parquet files! downloading existing dataframes')
            self.items_df = pd.read_parquet(
                first_pages.items[0].download(save_locally=False)
            )
            self.annotations_df = pd.read_parquet(
                second_pages.items[0].download(save_locally=False)
            )
            return True
        else:
            return False

    def set_parquet_files(self):
        """
        Converts items and annotations DataFrames to Parquet files, uploads them to a remote path, and removes the local files.

        This method performs the following steps:
        1. Retrieves the first output item using its ID.
        2. Extracts the name of the item (without extension).
        3. Converts the items DataFrame to a Parquet file and saves it locally.
        4. Constructs the remote path for the items Parquet file.
        5. Uploads the items Parquet file to the remote path.
        6. Constructs the remote path for the annotations Parquet file.
        7. Converts the annotations DataFrame to a Parquet file and saves it locally.
        8. Uploads the annotations Parquet file to the remote path.
        9. Removes the local Parquet files.

        Raises:
            Any exceptions raised by the underlying methods for file operations and uploads.
        """
        json_item = dl.items.get(item_id=self.output_item_ids[0])
        name, _ = os.path.splitext(json_item.name)
        self.items_df.to_parquet(f'{json_item.id}-items.parquet')
        remote_path = f'/.dataloop/exports/insights_parquet/{json_item.dataset_id}/{name}-items.parquet'
        json_item.dataset.items.upload(
            local_path=f'{json_item.id}-items.parquet',
            remote_path=os.path.dirname(remote_path),
            remote_name=os.path.basename(remote_path),
        )
        remote_path = f'/.dataloop/exports/insights_parquet/{json_item.dataset_id}/{name}-annotations.parquet'
        self.annotations_df.to_parquet(f'{json_item.id}-annotations.parquet')
        json_item.dataset.items.upload(
            local_path=f'{json_item.id}-annotations.parquet',
            remote_path=os.path.dirname(remote_path),
            remote_name=os.path.basename(remote_path),
        )

        # remove local files
        os.remove(f'{json_item.id}-items.parquet')
        os.remove(f'{json_item.id}-annotations.parquet')

    def process_data(self, **kwargs):
        """
        Processes the data by performing several steps including downloading, building,
        and creating HTML. Updates the build status and progress throughout the process.

        Steps:
        1. Sets initial progress and status.
        2. Attempts to download parquet files.
        3. If parquet files are not available, builds the dataframe and sets parquet files.
        4. Clears garbage collection.
        5. Creates HTML from the data.
        6. Updates the build status to ready and resets dataframes.

        Attributes:
            progress (int): Initial progress set to 100.
            build_status (str): Status of the build process.
            build_progress (float): Progress of the build process.
            divs (list): HTML divisions created from the data.
            items_df (DataFrame): DataFrame containing items data.
            annotations_df (DataFrame): DataFrame containing annotations data.

        Exceptions:
            Catches any exception during the process and updates the build status to "failed"
            and sets the build progress to the exception traceback.
        """
        self.progress = 100
        self.build_status = BuildStatus.STARTED
        self.build_progress = 0
        try:
            self.build_status = BuildStatus.DOWNLOADING
            if self.get_parquet_files() is not True:

                self.build_status = BuildStatus.BUILDING
                self.build_dataframe()
                self.set_parquet_files()
            self.gc.clear()
            self.build_status = BuildStatus.CREATING
            self.build_progress = 0.995
            self.divs = self.create_html()

            self.build_status = BuildStatus.READY
            self.build_progress = 1
            self.items_df = None
            self.annotations_df = None
        except Exception as e:
            self.build_status = BuildStatus.FAILED
            self.build_progress = traceback.format_exc()
            logger.exception('failed to process data: %s', e)
