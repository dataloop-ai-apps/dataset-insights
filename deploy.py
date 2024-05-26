import subprocess
import json
import time

import dtlpy as dl


def clean():
    dpk = dl.dpks.get(dpk_name='dataset-insights')
    filters = dl.Filters(field='dpkName', values=dpk.name, resource='apps')

    for app in dl.apps.list(filters=filters).all():
        print(app.name, app.project.name, app.scope)
        app.uninstall()

    [i.delete() for i in list(dpk.revisions.all())]


def publish_and_install(project, manifest):
    env = dl.environment()
    app_name = manifest['name']
    app_version = manifest['version']
    print(f'Publishing and installing {app_name} {app_version} to project {project.name} in {env}')

    # publish dpk to app store
    dpk = project.dpks.publish(ignore_max_file_size=True)
    print(f'published successfully! dpk name: {dpk.name}, version: {dpk.version}, dpk id: {dpk.id}')
    filters = dl.Filters(field='dpkName', values=dpk.name, resource='apps')

    for app in dl.apps.list(filters=filters).all():
        print(app.name, app.project.name, app.scope)
        if app.dpk_version != dpk.version:
            app.dpk_version = dpk.version
            app.update()
            print(f'update done. app id: {app.id}')
    print(f'Done!')


if __name__ == "__main__":
    dl.setenv('rc')
    project = dl.projects.get(project_name="COCO ors")
    # project = dl.projects.get(project_id="2bb16c5f-081f-4afb-91e0-78699c1b3476")
    # bump()
    with open('dataloop.json') as f:
        manifest = json.load(f)
    publish_and_install(manifest=manifest, project=project)
