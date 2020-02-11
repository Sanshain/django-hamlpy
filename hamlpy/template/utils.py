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


def type_save(content, template_type, content_type, ext, optional=None):

    '''
    save type

    template_type - subdirectory for saving (`components`,`fragments`,`pages`)
    content_type - name of directory for saving (`style`,`js`)
    ext - extension for saving (`js`,`css`, `less`)
    optional - optional handle funcs for process (for example for less compile)

    '''

    cs_path = os.path.join(static_path, content_type, template_type)

    if not os.path.exists(cs_path): os.makedirs(cs_path)

    style_flname = os.path.join(cs_path, base_name + '.' + ext or content_type)

    with open(style_flname, 'w') as style_file: style_file.write(cs_content.encode('utf-8'))


def convert(contents, origin):


    multi_content = contents.split(HAML_UNIT.UNITS['js'])
    content = multi_content[0]

    if len(multi_content) > 1: jcs_content = multi_content[1]
    else:
        return content



    print 'origin: ' + str(origin)

    pathname_origin, filename_origin = os.path.split(origin.__str__())          # [`/templates/pages`, `tmpl.haml`]
    base_name = filename_origin.rsplit('.',1)[0]                                # `tmpl`



    base_path, template_type = os.path.split(pathname_origin)                   # [`/templates`,`pages`]

    if template_type in ('components', 'fragments', 'pages'): pass
    elif template_type == 'templates':  template_type = ''
    else:                                                                       # other pathes
        template_type = 'pages'

    if template_type:
        base_path = os.path.dirname(base_path)                   # path of app (for ex - 'main')


    if jcs_content:



        static_path = os.path.join(base_path, 'static')

        jcs_content = jcs_content.split(HAML_UNIT.UNITS['style'])


        types = (2*('js',), ('style','css'))

        dct = dict(zip(jcs_content, types))

        for _content in dct:

            type_save(_content, template_type, *dct[_content])





        js_content = jcs_content[0]

        cs_content = jcs_content[1] if len(jcs_content) > 1 else ''

        if js_content: type_save(cs_content, template_type, 'js')

        if cs_content: type_save(cs_content, template_type, 'style','css')

    return content