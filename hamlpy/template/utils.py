import imp

from django.template import loaders
from os import listdir
from os.path import dirname, splitext

MODULE_EXTENSIONS = tuple([suffix[0] for suffix in imp.get_suffixes()])


def get_django_template_loaders():
    return [(loader.__name__.rsplit('.', 1)[1], loader)
            for loader in get_submodules(loaders) if hasattr(loader, 'Loader')]


def get_submodules(package):
    submodules = ("%s.%s" % (package.__name__, module) for module in package_contents(package))
    return [__import__(module, {}, {}, [module.rsplit(".", 1)[-1]]) for module in submodules]


def package_contents(package):
    package_path = dirname(loaders.__file__)
    contents = set([splitext(module)[0] for module in listdir(package_path) if module.endswith(MODULE_EXTENSIONS)])
    return contents



def convert(contents, origin):


    multi_content = contents.split(HAML_UNIT.UNITS['js'])
    contents = multi_content[0]

    jcs_content = multi_content[1] if len(multi_content) > 1 else ''

    print 'origin: ' + str(origin)

    pathname_origin, filename_origin = os.path.split(origin.__str__()) # [`/templates/pages`, `tmpl.haml`]
    base_name = filename_origin.rsplit('.',1)[0]                       # `tmpl`



    base_path, template_type = os.path.split(pathname_origin)          # [`/templates`,`pages`]

    if template_type in ('components', 'fragments', 'pages'): pass
    elif template_type == 'templates':  template_type = ''
    else:                                                           # other pathes
        template_type = 'pages'

    if template_type:
        base_path = os.path.dirname(base_path)                   # path of app (for ex - 'main')


    if jcs_content:



        static_path = os.path.join(base_path, 'static')

        jcs_content = jcs_content.split(HAML_UNIT.UNITS['style'])

        js_content = jcs_content[0]

        cs_content = jcs_content[1] if len(jcs_content) > 1 else ''

        if js_content:

            js_path = os.path.join(static_path, 'js', template_type)

            if not os.path.exists(js_path): os.makedirs(js_path)

            js_flname = os.path.join(js_path, base_name + '.js')

            with open(js_flname, 'w') as js_file: js_file.write(js_content.encode('utf-8'))

        if cs_content:

            cs_path = os.path.join(static_path, 'style', template_type)

            if not os.path.exists(cs_path): os.makedirs(cs_path)

            style_flname = os.path.join(cs_path, base_name + '.css')

            with open(style_flname, 'w') as style_file: style_file.write(cs_content.encode('utf-8'))

