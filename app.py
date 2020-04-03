import os
import shutil
import time


import click
import markdown
from jinja2 import Environment, PackageLoader, select_autoescape
from watchdog.observers import Observer
from watchdog.events import LoggingEventHandler
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper



class Event(LoggingEventHandler):
    def on_modified(self, event):
        builder()


def write_to_path(text, path):
    try:
        os.mkdir('/'.join(path.split('/')[:-1]))
    except FileExistsError:
        pass
    with open(path, 'w+') as stream:
        stream.write(text)


def page_to_html(page):
    if page == '':
        page = 'index'
    with open('assets/pages/' + page + '.md', 'r') as stream:
        return markdown.markdown(stream.read())


def builder():
    with open('options.yaml', 'r') as stream:
        options = load(stream, Loader=Loader)

    config = {}
    for k in options['project']:
        config[k] = options['project'][k]
    config['navbar_pages'] = options['navbar']
    config['marketing_ids'] = options['marketing']

    env = Environment(loader=PackageLoader(__name__, 'assets/templates'))

    # One-to-one blueprints
    o2o = options['blueprints']['o2o']
    for key in o2o:
        template = env.get_template(key + '.html')
        html = template.render(body=page_to_html(o2o[key]), **config)
        path = 'dist/' + o2o[key] + '/index.html'
        write_to_path(text=html, path=path)

    # One-to-many blueprints
    o2m = options['blueprints']['o2m']
    for key in o2m:
        template = env.get_template(key + '.html')
        for page in o2m[key]:
            html = template.render(body=page_to_html(page), **config)
            path = 'dist/' + page + '/index.html'
            write_to_path(text=html, path=path)

    # Collect static assets
    shutil.rmtree('dist/static')
    shutil.copytree(src='assets/static', dst='dist/static')


@click.group()
def cli():
    pass


@cli.command()
def build():
    builder()


@cli.command()
def watch():
    event_handler = Event()
    observer = Observer()
    observer.schedule(event_handler, './assets', recursive=True)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == '__main__':
    cli()