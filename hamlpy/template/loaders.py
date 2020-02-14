import os

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loaders import filesystem, app_directories

from hamlpy import HAML_EXTENSIONS, HAML_UNIT
from hamlpy.compiler import Compiler
from hamlpy.template.utils import get_django_template_loaders, components_save

# Get options from Django settings
options = {}

if hasattr(settings, 'HAMLPY_ATTR_WRAPPER'):
    options.update(attr_wrapper=settings.HAMLPY_ATTR_WRAPPER)

if hasattr(settings, 'HAMLPY_DJANGO_INLINE_STYLE'):
    options.update(django_inline_style=settings.HAMLPY_DJANGO_INLINE_STYLE)


def get_haml_loader(loader):


    # par = lambda d, edge="templates": par(dirname(d), n-1) if n else (d)
    root = lambda p, e: p if os.path.split(p)[-1] == e else root(os.path.dirname(p), e)

    class Loader(loader.Loader):
        def get_contents(self, origin):
            # Django>=1.9
            contents = super(Loader, self).get_contents(origin)

            print origin.template_name
            name, _extension = os.path.splitext(origin.template_name)
            # os.path.splitext always returns a period at the start of extension
            extension = _extension.lstrip('.')

            if extension in HAML_EXTENSIONS:
                compiler = Compiler(options=options)

                import re

##                from os.path import dirname
##
##                par = lambda d, n=1: par(dirname(d), n-1) if n else (d)

                if HAML_UNIT.ENABLE: contents = components_save(contents, origin).encode('utf-8')


                # remaining content (haml(html)

                reg = re.compile('([\t ]*)-(frag|unit) "([_\w]+)"')


##                for m in units:

                while True:

                    m = reg.search(contents)

                    if not m: break
                    else:

                        indent, unit_type, unit_name = m.groups() # indent = indent.replace('\t', ' '* 4)
                        unit_type = 'fragments' if unit_type == 'frag' else 'components'
                        unit_name = '.'.join((unit_name,  extension))

                        _root = root(origin.__str__(), 'templates')

                        unit_file = os.path.join(_root, unit_type, unit_name)

                        with open(unit_file, 'r') as reader: unit = reader.readlines()


                        first = [unit[0]]
                        second = [indent + line for line in unit[1:len(unit)]]

                        unit = ''.join(first + second)





##                      import io
##                      f = io.open("test", mode="r", encoding="utf-8")


                        # unit = '\n'.join([unit[0]]+[indent + line for line in unit[1:len(unit)]])




                        contents = contents[0:m.start()] + unit + contents[m.end(): m.endpos()]

#               now contents is full. Prepare it:



                tags = "(div|li|ul|h2|h3|main|button|link|script|form|label)"
                contents = re.sub(r"((\n|^)\s*)(?={}[\s\.\#\(])".format(tags), r"\1%", contents) #tags without %

                ## separate on lines: %main %section => %main \n %section
                contents = re.sub(r"(?<=\n)([\ \t]+)((%|\.)\w+[\ ])(%\S+)", r'\1\2\n\1\t\3', contents)

                contents = re.sub(r"~([\w\s\"\.]+)", r'{% \1 %}', contents)               # ~v => {% v %}

##                print contents

                r = compiler.process(contents)

                # save result
                html_file = str(origin).rsplit('.', 1)[0] + '.html'
                with open(html_file, 'w') as html:
                    html.write(r)

                return r

            return contents

        def load_template_source(self, template_name, *args, **kwargs):
            # Django<1.9
            name, _extension = os.path.splitext(template_name)
            # os.path.splitext always returns a period at the start of extension
            extension = _extension.lstrip('.')

            if extension in HAML_EXTENSIONS:
                try:
                    haml_source, template_path = super(Loader, self).load_template_source(
                        self._generate_template_name(name, extension), *args, **kwargs
                    )
                except TemplateDoesNotExist:  # pragma: no cover
                    pass
                else:
                    compiler = Compiler(options=options)
                    html = compiler.process(haml_source)

                    return html, template_path

            raise TemplateDoesNotExist(template_name)

        load_template_source.is_usable = True

        @staticmethod
        def _generate_template_name(name, extension="hamlpy"):
            return "%s.%s" % (name, extension)

    return Loader


haml_loaders = dict((name, get_haml_loader(loader)) for (name, loader) in get_django_template_loaders())

HamlPyFilesystemLoader = get_haml_loader(filesystem)
HamlPyAppDirectoriesLoader = get_haml_loader(app_directories)
