import json
import dtlpy as dl


def clean():
    dpk = dl.dpks.get(dpk_name='dataset-insightss')
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

    try:
        app = project.apps.get(app_name=dpk.display_name)
        print(f'already installed, updating...')
        app.dpk_version = dpk.version
        app.update()
        print(f'update done. app id: {app.id}')
    except dl.exceptions.NotFound:
        print(f'installing ..')
        app = project.apps.install(dpk=dpk,
                                   app_name=dpk.display_name,
                                   scope='project')
        print(f'installed! app id: {app.id}')
    print(f'Done!')


if __name__ == "__main__":
    dl.setenv('prod')
    # project = dl.projects.get(project_name="DataloopTasks")
    project = dl.projects.get(project_id="f056db8b-01f7-4990-8ef0-c589d63a3673")
    # bump()
    with open('dataloop.json') as f:
        manifest = json.load(f)
    publish_and_install(manifest=manifest, project=project)
