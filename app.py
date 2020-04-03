import os
import shutil
import time


import click
import markdown
from jinja2 import Environment, PackageLoader, BaseLoader
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from yaml import load, dump

try:
    from yaml import CLoader as Loader, CDumper as Dumper
except ImportError:
    from yaml import Loader, Dumper



class Watcher:
    DIRECTORY_TO_WATCH = "./assets"

    def __init__(self):
        self.observer = Observer()

    def run(self):
        event_handler = Handler()
        self.observer.schedule(event_handler, self.DIRECTORY_TO_WATCH, recursive=True)
        self.observer.start()
        try:
            while True:
                time.sleep(5)
        except KeyboardInterrupt:
            self.observer.stop()
        self.observer.join()


class Handler(FileSystemEventHandler):

    @staticmethod
    def on_any_event(event):
        if event.is_directory:
            return None

        elif event.event_type == 'created':
            # Take any action here when a file is first created.
            print("Received created event - %s." % event.src_path)

        elif event.event_type == 'modified':
            # Taken any action here when a file is modified.
            print("Received modified event - %s." % event.src_path)

        builder()


def build_template(template_key, config, page_name):
    env = Environment(loader=PackageLoader(__name__, 'assets/templates'))
    template = env.get_template('{}.html'.format(template_key))

    try:
        config['body'] = Environment(loader=BaseLoader).from_string(markdown.markdown(open('assets/pages/{}.md'.format(page_name)).read())).render(**config)
    except:
        pass

    html = template.render(**config)

    path = 'dist' if page_name == 'index' else 'dist/{}'.format(page_name)
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

    with open(path + '/index.html', 'w+') as stream:
        stream.write(html)


def builder():
    with open('app.yaml', 'r') as stream:
        o = load(stream, Loader=Loader)
        app_config = o['app']
        blueprints = o['blueprints']

    for template_key in blueprints:
        template_options = blueprints[template_key]

        # one-to-one
        if type(template_options) is dict:
            build_template(template_key, {**app_config, **template_options}, template_key)
        # one-to-many
        else:
            for page in template_options:
                page_name = [x for x in page.keys()][0]
                page_options = page[page_name] or {}
                build_template(template_key, {**app_config, **page_options}, page_name)

    # Collect static assets
    try:
        shutil.rmtree('dist/static')
    except:
        pass
    shutil.copytree(src='assets/static', dst='dist/static')


@click.group()
def cli():
    pass


@cli.command()
def build():
    builder()


@cli.command()
def watch():
    w = Watcher()
    w.run()


if __name__ == '__main__':
    cli()