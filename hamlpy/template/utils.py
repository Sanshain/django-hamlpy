import imp

from django.template import loaders
from os import listdir
from os.path import dirname, splitext

from hamlpy import HAML_UNIT
import os

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


def _type_save(content, static_path, base_name, template_type, content_type,
    ext, optional=None):

    '''
    save type

    template_type - subdirectory for saving (`components`,`fragments`,`pages`)
    content_type - name of directory for saving (`style`,`js`)
    ext - extension for saving (`js`,`css`, `less`)
    optional - optional handle funcs for process (for example for less compile)

    '''

    cs_path = os.path.join(static_path, content_type, template_type)

    if not os.path.exists(cs_path): os.makedirs(cs_path)

    sub_content = None

    for key in HAML_UNIT.STYLE_PREPROCS.keys():
        if key in content[0:content.find(' ')+1]: sub_content = key


    sub_compiler = HAML_UNIT.STYLE_PREPROCS.get(sub_content, None)

    if sub_compiler:

        if hasattr(sub_compiler,'__call__'):

            pp_flname = os.path.join(cs_path, base_name + '.' + sub_content or content_type)

            print 'sub_content ' + sub_content

            with open(pp_flname, 'w') as pp_file: pp_file.write(content)

            print '{} compile for {} {}: '.format(sub_content, content_type, '\"%s %s\"'%(base_name, template_type))

            print sub_compiler(pp_flname.replace('.%s'%sub_content, '.%s'%sub_content))


        elif type(sub_compiler) is tuple:

            style_flname = os.path.join(cs_path, base_name + '.' + ext or content_type)

            sub_compiler[0](content, style_flname)


    else:

        # for `'less' : None` in STYLE_PREPROCS will save to .*sub_content*.
        # It means less-file need compile by outer tool like gulp-watch

        style_flname = os.path.join(cs_path, base_name + '.' + (sub_content or ext or content_type))

        with open(style_flname, 'w') as style_file: style_file.write(content)


def components_save(contents, origin):

    '''
    divides sourse code (`contents`) to component parts and save it on each its dir

    contents - source file content
    origin - source path by object Origin

    '''

    multi_content = contents.split(HAML_UNIT.UNITS['js'])

    content = multi_content[0]

    if len(multi_content) > 1: jcs_content = multi_content[1]
    else:
        return content

    pathname_origin, filename_origin = os.path.split(origin.__str__())          # [`.../templates/pages`, `tmpl.haml`]
    base_name = filename_origin.rsplit('.',1)[0]                                # `tmpl`

    base_path, template_type = os.path.split(pathname_origin)                   # [`.../templates`,`pages`]

    if template_type in ('components', 'fragments', 'pages'): pass
    elif template_type == 'templates':  template_type = ''
    else: template_type = 'pages'

    base_path = os.path.dirname(base_path) if template_type else base_path      # path of app (for ex - 'main')

    if jcs_content:

        jcs_content = jcs_content.split(HAML_UNIT.UNITS['style'])

        static_path = os.path.join(base_path, 'static')


        types = (2*('js',), ('style','css'))

        dct = dict(zip(jcs_content, types))

        for _content in dct:

            _type_save(
                _content.encode('utf-8').strip(),
                static_path,
                base_name,
                template_type,
                *dct[_content])


    return content


    print "less compiled to {}".format(tgt)