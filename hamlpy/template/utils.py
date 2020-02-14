import imp

from django.template import loaders
from os import listdir
from os.path import dirname, splitext

from hamlpy import HAML_UNIT
import os
import re

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



# par = lambda d, edge="templates": par(dirname(d), n-1) if n else (d)
root = lambda p, e: p if os.path.split(p)[-1] == e else root(os.path.dirname(p), e)


def _get_sub_content_type(content):
    '''
    just for css/less/sass/stylus
    '''
    for key in HAML_UNIT.STYLE_PREPROCS.keys():
        if key in content[0:content.find(' ')+1]:
            return key
    else:
        return None


def _get_origin_type(pathname_origin):

    base_path, template_type = os.path.split(pathname_origin)

    if template_type in ('components', 'fragments', 'pages'): pass
    elif template_type == 'templates':  template_type = ''
    else: template_type = 'pages'

    return template_type


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

    sub_content = _get_sub_content_type(content)

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



def _template_partition(contents, origin, component_type, frag_name):


    '''
    divides sourse code (`contents`) to component parts and save it on each its dir

    contents - source file content
    origin - source path by object Origin
    component_type - name of container type where will be inserted the partition (usually pages or fragments)
    frag_name - component/fragment (not component container) name

        origin_name - origin component container name

    '''


    origin_name = origin.__str__().split(os.path.sep)[-1].split('.')[0]

    multi_content = contents.split(HAML_UNIT.UNITS['js'])

    haml_content = multi_content[0]
    other_content = multi_content[1] if len(multi_content) > 1 else None

    if not other_content: return haml_content


    multi_content = other_content.split(HAML_UNIT.UNITS['style'])

    js_content = '\n\n' + multi_content[0].strip()
    style_content = multi_content[1] if len(multi_content) > 1 else None


    # this files needs to be inserted its content to according js/less files

    # Find this files:

    _root = os.path.dirname( root(origin.__str__(), 'templates'))

    origin_type = _get_origin_type(str(origin))

    # js_file = os.path.join(_root, 'static', 'js', component_type, origin_name + '.js')

    js_file = os.path.sep.join([_root, 'static', 'js', origin_type, origin_name + '.js'])

    # js_content = '// %s: \n\n'%component_type + js_content if component_type else js_content

    with open(js_file, 'a+') as pen: pen.write(js_content)

    if style_content:

        sub_content = _get_sub_content_type(style_content)

        # _root, 'static', 'style', -> '../'
        _style_src = os.path.join('../', component_type, '%s.%s'%(frag_name, sub_content))

        # origin_type = _get_origin_type(os.path.dirname(str(origin)))

        _style_tgt = os.path.join(_root, 'static', 'style', origin_type, '%s.%s'%(origin_name, sub_content))

        _style = '@import "%s"'%_style_src.repalce('\\','/')

        print '++++++++++++++++++++++++++++++++++++++++++++++++++++++a'

        with open(_style_tgt, 'a+') as pen: pen.write(_style)


##    _get_sub_content_type(content)



    return haml_content


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



reg = re.compile('([\t ]*)-(frag|unit) "([_\w]+)"')

def embed_components(contents, origin, extension ='haml'):

    while True:

##      for m in units: - may so but by back direct in cycle!

        m = reg.search(contents)

        if not m: break
        else:

            indent, unit_type, unit_name = m.groups() # indent = indent.replace('\t', ' '* 4)
            unit_type = 'fragments' if unit_type == 'frag' else 'components'
            unit_name = '.'.join((unit_name,  extension))

            _root = root(origin.__str__(), 'templates')

            unit_file = os.path.join(_root, unit_type, unit_name)

            with open(unit_file, 'r') as reader: raw_unit = reader.read()

            unit = _template_partition(raw_unit, origin, unit_type, unit_name)

##            first = [unit[0].decode('utf-8')]
##            second = [indent + line.decode('utf-8') for line in unit[1:len(unit)]]

            #first = [unit[0]]
            second = '\n'.join([str(indent) + line for line in unit.split('\n')])

            unit = ''.join(second)


##          import io
##          f = io.open("test", mode="r", encoding="utf-8")

            contents = contents[0:m.start()] + unit + contents[m.end(): m.endpos]

    return contents
