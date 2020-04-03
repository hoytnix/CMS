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


def build_template(template_key, config, page_name):
    env = Environment(loader=PackageLoader(__name__, 'assets/templates'))
    template = env.get_template('{}.html'.format(template_key))

    try:
        config['body'] = markdown.markdown(open('assets/pages/{}.md'.format(page_name)).read())
    except:
        pass

    html = template.render(**config)

    if page_name == 'index':
        path = 'dist'
    else:
        path = 'dist/' + template_key
    try:
        os.mkdir(path)
    except FileExistsError:
        pass

    with open(path + '/index.html', 'w+') as stream:
        stream.write(html)


def builder():
    with open('options.yaml', 'r') as stream:
        options = load(stream, Loader=Loader)

    config = {}
    for k in options['project']:
        config[k] = options['project'][k]
    config['navbar_pages'] = options['navbar']
    config['marketing_ids'] = options['marketing']

    blueprints = options['blueprints']
    for template_key in blueprints:
        template_options = blueprints[template_key]

        # one-to-one
        if type(template_options) is dict: 
            for option in template_options:
                config[option] = template_options[option]
            build_template(template_key, config, template_key)
        # one-to-many
        else:
            for page in template_options:
                page_name = [x for x in page.keys()][0]
                page_options = page[page_name]
                try:
                    for option in page_options:
                        config[option] = page_options[option]
                except:
                    pass # no options to pass
                build_template(template_key, config, page_name)

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