import os
import shutil
import time
import hashlib


import click
import markdown
from csscompressor import compress as csscompress
from htmlmin import minify as htmlminify
from jinja2 import Environment, PackageLoader, BaseLoader
from slimit import minify as jsminify
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from webptools import webplib as webp
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
    
    if page_name.split('/').__len__() == 2:
        try:
            os.mkdir('/'.join(path.split('/')[:-1]))
        except FileExistsError:
            pass

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
        models = o['models']

    # Build static pages
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

    # Build modeled pages
    for model_key in models:
        model = models[model_key]
        for template in model['templates']:
            template_key = [x for x in template][0]
            if type(template[template_key]) is str: # list views
                template_item = None
                template_path = template[template_key]

                build_template(template_key, {**app_config, **model}, template_path)
            else: # detail views
                template_item = [x for x in template[template_key]][0]
                template_glob = template[template_key][template_item]

                if template_glob.endswith('*'):
                    for item in model['items']:
                        page_name = [x for x in item][0]
                        template_path = template_glob.replace('*', page_name)
                        build_template(template_key, {**app_config, **item}, template_path)

                if template_glob.endswith('[*]'):
                    kvs = {}
                    for item in model['items']:
                        page_name = [x for x in item][0]
                        for k in item[page_name][template_item]:
                            if not k in kvs:
                                kvs[k] = []
                            kvs[k].append(page_name)
                    for k in kvs:
                        template_path = template_glob.replace('[*]', k)
                        build_template(template_key, {**app_config, **model, **{'kvs': kvs[k]}}, template_path)

    # Minify Images
    os.system("imagemin --plugin=pngquant assets/static/img/*.png --out-dir=assets/static/img/min")
    os.system("imagemin --plugin=mozjpeg assets/static/img/*.jpeg --out-dir=assets/static/img/min")
    os.system("imagemin --plugin=mozjpeg assets/static/img/*.jpg --out-dir=assets/static/img/min")
    os.system("imagemin --plugin=gifsicle assets/static/img/*.gif --out-dir=assets/static/img/min")
    #os.system("imagemin --plugin=svgo assets/static/img/*.svg --out-dir=assets/static/img/min")

    for (root, dirs, files) in os.walk('assets/static/img'):
        for file in files:
            old_fp = root + '/' + file
            raw_fp = root + '/raw/' + file
            webp_fp = root + '/webp/' + '.'.join(file.split('.')[:-1]) + '.webp'

            shutil.move(old_fp, raw_fp)
            
            if not os.path.exists(webp_fp):
                webp.cwebp(raw_fp, webp_fp, "-q 80")
        break

    # Collect static assets
    try:
        shutil.rmtree('dist/static')
    except:
        pass
    shutil.copytree(src='assets/static', dst='dist/static')

    # CSS Minification
    static_cache = {}
    for (root, dirs, files) in os.walk('dist/static/css'):
        for file in files:
            with open(root + '/' + file, 'r') as stream:
                css = csscompress(stream.read())
                m = hashlib.md5()
                m.update(str.encode(css))
                hashsum = m.hexdigest()
                new_file = "{}.{}.css".format(".".join(file.split('.')[:-1]), hashsum)
                with open('dist/static/css/' + new_file, 'w+') as stream:
                    stream.write(css)
                static_cache[file] = new_file
            os.remove(root + '/' + file)
        break

    # JS Minification
    for (root, dirs, files) in os.walk('dist/static/js'):
        for file in files:
            with open(root + '/' + file, 'r') as stream:
                js = jsminify(stream.read(), mangle=False)
                m = hashlib.md5()
                m.update(str.encode(js))
                hashsum = m.hexdigest()
                new_file = "{}.{}.js".format(".".join(file.split('.')[:-1]), hashsum)
                with open('dist/static/js/' + new_file, 'w+') as stream:
                    stream.write(js)
                static_cache[file] = new_file
            os.remove(root + '/' + file)
        break

    # Cache Busting
    for (root, dirs, files) in os.walk('dist'):
        for file in files:
            if file.endswith('html'):
                fp = root + '/' + file
                html = open(fp, 'r').read()
                for key in static_cache:
                    html = html.replace(key, static_cache[key])
                html = htmlminify(html, remove_comments=True)
                with open(fp, 'w+') as stream:
                    stream.write(html)


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