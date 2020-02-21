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


def _extract_blocks(dct, s, _pattern = re.compile(r'/\*~block (\w+)\*/([\s\S]*?)/\*~\*/')):

    '''
    find blocks in component template `s` (/*~block NAME */ CONTENT /*~*/) - extract
    NAME and CONTENT inside components to dct and remove its from origin
    '''

    _blocks = _pattern.finditer(s)

    s = re.sub(_pattern, '', s)

    for b in _blocks:

        dct[b.group(1)] = dct.get(b.group(1),'') + '\n' + b.group(2)

    return s



def _get_origin_type(pathname_origin):

    base_path, template_type = os.path.split(pathname_origin)

    if template_type in ('components', 'fragments', 'pages'): pass
    elif template_type == 'templates':  template_type = ''
    else: template_type = 'pages'

    base_path = os.path.dirname(base_path) if template_type else base_path      # path of app (for ex - 'main')

    return base_path, template_type


def _type_save(content, static_path, base_name, template_type, content_type,
    ext, new=True, inside_unit_type=None, inside_unit_name=None):

    '''
    save type

    base_name - base name of file (w/o extension) - usually consides with component name
    template_type - subdirectory for saving (`components`,`fragments`,`pages`)
    content_type - name of directory for saving (`style`,`js`)
    ext - extension for saving (`js`,`css`, `less`)
    optional - optional handle funcs for process (for example for less compile)

    '''

    option = 'w' if new else 'a'

    ext = ext or content_type


    sub_content = _get_sub_content_type(content)
    sub_compiler = HAML_UNIT.STYLE_PREPROCS.get(sub_content, None)


    cs_path = os.path.join(static_path, content_type, template_type)
    if not os.path.exists(cs_path): os.makedirs(cs_path)
    cs_path = os.path.join(cs_path, base_name)

    if inside_unit_type:
        pp_path = os.path.join(static_path, content_type, inside_unit_type)
        if not os.path.exists(pp_path): os.makedirs(pp_path)

        pp_path = os.path.join(pp_path, inside_unit_name)
        content = '/*%s %s*/\n\n'%(inside_unit_type, inside_unit_name) + content
        print '----------------------------------------------------'

    else: pp_path = cs_path


    if sub_compiler:


        if hasattr(sub_compiler,'__call__'):                                    # just file to

            pp_flname = pp_path + '.' + sub_content
            with open(pp_flname, option) as pp_file: pp_file.write(content)        # save no-compile code to preprocesssor extension

            print '{} compile for {} {}: '.format(sub_content, content_type, '\"%s %s\"'%(base_name, template_type))

            print sub_compiler(cs_path+'.'+ext, option) # call func for compile to final file with appropriate extension (func self know where)


        elif type(sub_compiler) is tuple:

            if len(sub_compiler) > 1: return sub_compiler[0](content)           # turn compiled code (w/o saving somewhere)

            else:

                style_flname = cs_path + '.' + ext

                sub_compiler[0](content, style_flname, option)                  # compile to finished file w/o middleware preprocessor saving

                print 'save to %s by %s'%(style_flname, option)
    else:

        # for `'less' : None` in STYLE_PREPROCS will save to .*sub_content*.
        # It means less-file need compile by outer tool like gulp-watch

        style_flname = cs_path + '.' + (sub_content or ext or content_type)
        with open(style_flname, option) as style_file: style_file.write(content)




'''
for call for page:

    divides sourse code of pages(`contents`) to component parts and save it on each its dir,
    append to previous files

    @params:
        contents - source file content
        origin - source path by object Origin

for call for components:


    divides sourse code (`contents`) of component/fragment to component parts
    and append its parts to common files of parent pages/fragment OR save it on each it dirs -
    this options rely by func in HAML_UNIT.STYLE_PREPROCS

    like components_save? - join its to once func

    @params:
        contents - source file content
        origin - source path by object Origin
        component_type - name of container type where will be inserted the partition (usually pages or fragments)
        frag_name - component/fragment (not component container) name

        origin_name - origin component container name

'''
def components_save(contents, origin, component_type=None, frag_name=None):

    multi_content = contents.split(HAML_UNIT.UNITS['js'])

    content = multi_content[0]

    if len(multi_content) > 1: other_content = multi_content[1]
    else:
        return (content.encode('utf-8'), {})

    components_keeper = {}
    outside_ress = {}

    pathname_origin, filename_origin = os.path.split(origin.__str__())          # [`.../templates/pages`, `tmpl.haml`]
    base_name = filename_origin.rsplit('.',1)[0]                                # `tmpl` - name of main page


    base_path, template_type = _get_origin_type(pathname_origin)                # type of parent = (page|fragment|component)
                                                                                # base_path - base path of app

    other_content = other_content.split(HAML_UNIT.UNITS['style'])

    static_path = os.path.join(base_path, 'static')


    jcss_info = dict(zip(other_content, (2*('js',), ('style','css'))))          # _content : ('js','js'), _content : ('style','..

    inside_elem_flag = True if frag_name else False

    for _content in jcss_info:

        _content = _extract_blocks(outside_ress, _content)                      # <0.4ms for one replace

        res = _type_save(
            _content.strip(),                                                   # .encode('utf-8')
            static_path,
            base_name,
            template_type,
            *jcss_info[_content],
            new = not inside_elem_flag,
            inside_unit_type=component_type,
            inside_unit_name=frag_name)

        if res: components_keeper[jcss_info[_content][1]] += res                #

    def _indent_block(indnt, code):
        _code = code.splitlines()
        for line in _code:
            line = indnt + line
        return '\n'.join(_code)

    if frag_name:
        # if thrown by -frag or -unit tags: need insert into root (parent) page header (to -block links)



        for blo in outside_ress:

            mch = re.search(r'(\s|\t)-block %s'%blo, content)                   # blo = links, onload etc

            if not mch:
                raise Exception('links block undefined in root template %s'%origin.__str__())

                content = re.sub(
                    r'(-extends "[\w\.]+")"', r'\1\n\t-block %s'%(blo, _indent_block(
                        r'\t', outside_ress[blo]
                    ),
                    content)
                )
            else:
                _blo = _indent_block(mch.groups()[0]+' '*8, outside_ress[blo])

                # from django.core.urlresolvers import reverse



##            _blo = _indent_block(mch.groups()[0]+' '*8, blo)
##            _blo = '\n\1    :javascript\n' + _blo

                content = re.sub(r'(\s|\t)(-block links)',r'\1