import time

import click
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


def builder():
    with open('options.yaml', 'r') as stream:
        options = load(stream, Loader=Loader)

    env = Environment(
        loader=PackageLoader(__name__, 'assets/templates'),
        autoescape=select_autoescape(['html', 'xml'])
    )
    template = env.get_template('index.html')
    print(template.render(**{'foo':'bar'}))


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