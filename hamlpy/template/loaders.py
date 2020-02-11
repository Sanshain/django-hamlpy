import os

from django.conf import settings
from django.template import TemplateDoesNotExist
from django.template.loaders import filesystem, app_directories

from hamlpy import HAML_EXTENSIONS, HAML_UNIT
from hamlpy.compiler import Compiler
from hamlpy.template.utils import get_django_template_loaders

# Get options from Django settings
options = {}

if hasattr(settings, 'HAMLPY_ATTR_WRAPPER'):
    options.update(attr_wrapper=settings.HAMLPY_ATTR_WRAPPER)

if hasattr(settings, 'HAMLPY_DJANGO_INLINE_STYLE'):
    options.update(django_inline_style=settings.HAMLPY_DJANGO_INLINE_STYLE)


def get_haml_loader(loader):
    class Loader(loader.Loader):
        def get_contents(self, origin):
            # Django>=1.9
            contents = super(Loader, self).get_contents(origin)
            name, _extension = os.path.splitext(origin.template_name)
            # os.path.splitext always returns a period at the start of extension
            extension = _extension.lstrip('.')

            if extension in HAML_EXTENSIONS:
                compiler = Compiler(options=options)

                import re

                from os.path import dirname

                par = lambda d, n=1: par(dirname(d), n-1) if n else (d)

                if HAML_UNIT.ENABLE:
                    multi_content = contents.split(HAML_UNIT.UNITS['js'])
                    contents = multi_content[0]

                    jcs_content = multi_content[1] if len(multi_content) > 1 else ''

                    print 'origin: ' + str(origin)

                    pathname_origin, filename_origin = os.path.split(origin.__str__()) # [`/templates/pages`, `tmpl.haml`]
                    base_name = filename_origin.rsplit('.',1)[0]                       # `tmpl`

                    print 'pathname_origin%s'%pathname_origin

                    base_path, template_type = os.path.split(pathname_origin)          # [`/templates`,`pages`]

                    if template_type in ('components', 'fragments', 'pages'): pass
                    elif template_type == 'templates':  template_type = ''
                    else:                                                           # other pathes
                        template_type = 'pages'

                    print '1:%s'%base_path

                    if template_type:
                        base_path = os.path.dirname(base_path)                   # path of app (for ex - 'main')


                    print '2:%s'%base_path




##                    print par(origin.__str__(), 3)
##                    print os.path.abspath('')

                    if jcs_content:

                        # static_path = os.path.join(par(base_path.__str__(), 3), 'static')

                        static_path = os.path.join(base_path, 'static')

                        jcs_content = jcs_content.split(HAML_UNIT.UNITS['style'])

                        js_content = jcs_content[0]

                        cs_content = jcs_content[1] if len(jcs_content) > 1 else ''

                        if js_content:

                            # js_path = os.path.join(par(base_path.__str__(), 3), 'js', template_type)

                            js_path = os.path.join(static_path, 'js', template_type)

                            if not os.path.exists(js_path): os.makedirs(js_path)

                            js_flname = os.path.join(js_path, base_name + '.js')

                            with open(js_flname, 'w') as js_file: js_file.write(js_content.encode('utf-8'))

                        if cs_content:

                            # cs_path = os.path.join(par(base_path.__str__(), 3), 'style', template_type)

                            cs_path = os.path.join(static_path, 'style', template_type)

                            if not os.path.exists(cs_path): os.makedirs(cs_path)

                            style_flname = os.path.join(cs_path, base_name + '.css')

                            with open(style_flname, 'w') as style_file: style_file.write(cs_content.encode('utf-8'))


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
