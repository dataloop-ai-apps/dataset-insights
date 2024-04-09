import dtlpy as dl
import numpy as np
import threading
import datetime
import logging
import json
import time
import io

from dash_bootstrap_templates import load_figure_template

logger = logging.getLogger('[EXPORTER]')
logging.basicConfig(level='INFO')

load_figure_template(["cyborg", "darkly", "minty", "cerulean"])


class Exporter:
    def __init__(self, dataset_id):
        self.dataset_id = dataset_id
        self.dataset = dl.datasets.get(dataset_id=self.dataset_id)
        self.path = f'tmp/{self.dataset.id}/json'

        # status
        self.export_date = ""
        self.progress = 0
        self.status = "loading"
        self.export_item_id = ""
        # start
        self.load()

    def refresh(self):
        item: dl.Item = self.find_last_export()
        if item is not None:
            self.status = "ready"
            self.progress = 0
            self.export_date = self.change_iso_date_string(item.created_at[:-1])
            self.export_item_id = item.id

    def load(self):
        self.refresh()
        # check for active exports:
        command_id = self.check_active_exports()
        if command_id is not None:
            self.wait_for_command(command_id=command_id)
            self.refresh()
        if command_id is None and self.export_item_id == "":
            logger.warning("No active exports found")
            self.start_export()

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
        self.status = 'running'
        while elapsed < timeout:
            command = dl.commands.get(command_id=command_id)
            if not command.in_progress():
                break
            elapsed = time.time() - start
            sleep_time = np.min([timeout - elapsed, backoff_factor * (2 ** num_tries), max_sleep_time])
            self.progress = np.minimum(command.progress, 90)
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

        if 'outputItemId' not in command.spec:
            raise dl.exceptions.PlatformException(
                error='400',
                message="outputItemId key is missing in command id: {}".format(command_id))
        self.remove_active_exports()
        item_id = command.spec['outputItemId']
        annotation_zip_item = self.dataset.items.get(item_id=item_id)
        self.progress = 100
        self.status = 'ready'
        self.export_item_id = item_id
        self.export_date = self.change_iso_date_string(annotation_zip_item.created_at[:-1])
        return annotation_zip_item

    def start_export(self):
        export_version = dl.ExportVersion.V1
        payload = dict()
        payload['annotations'] = {
            "include": True,
            "convertSemantic": False
        }
        payload['exportVersion'] = export_version

        success, response = dl.client_api.gen_request(req_type='post',
                                                      path='/datasets/{}/export'.format(self.dataset.id),
                                                      json_req=payload,
                                                      headers={'user_query': 'true'})
        if not success:
            raise dl.exceptions.PlatformException(response)

        # save command in json
        command = dl.Command.from_json(_json=response.json(),
                                       client_api=dl.client_api)
        self.update_active_exports(command_id=command.id)

        thread = threading.Thread(target=self.wait_for_command, kwargs={"command_id": command.id})
        thread.daemon = True
        thread.start()
        return command.id

    def update_active_exports(self, command_id):
        b_dataset = self.dataset.project.datasets._get_binaries_dataset()
        buffer = io.BytesIO()
        buffer.write(json.dumps({"commandId": command_id}).encode('utf-8'))
        buffer.name = "active_export.json"
        logger.info(f"Uploading active_export.json to /.dataloop/exports{self.dataset.id}")
        b_dataset.items.upload(local_path=buffer,
                               remote_path=f'/.dataloop/exports/{self.dataset.id}',
                               overwrite=True)

    def remove_active_exports(self):
        filters = dl.Filters(use_defaults=False)
        filters.add(field='filename', values=f'/.dataloop/exports/{self.dataset.id}/active_export.json')
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
