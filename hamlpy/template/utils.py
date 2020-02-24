import imp

from django.template import loaders

from warnings import warn

from django.core.urlresolvers import reverse
from django.conf import settings

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

def _extract_const_block(dct, s, _pattern = re.compile(r'/\*~const \w+\*/([\s\S]*?)/\*~\*/')):

    '''
    find blocks in component template `s` (/*~const block */ CONTENT /*~*/) - extract
    CONTENT inside components to dct and remove its from origin
    '''

    const_block = _pattern.search(s)

    mchs = re.finditer(r'{% url "(\w+)" %}', const_block)



    s = re.sub(_pattern, '', s)

    for b in _blocks:

        dct[b.group(1)] = dct.get(b.group(1),'') + '\n' + b.group(2)

    return s


haml = HamlComponent(contents, origin)
inline_ress = haml.package_ress()


class HamlComponent(object):

    __slots__ = (
        'raw_content',                          # raw content
        'origin',                               # origin path (this? or root?)          ?
        'content',                              # haml main (root) part of raw content
        'res_keeper',                           # resourse keeper in keeper mode
        'outside_ress',                         # res of inline resourse for aggregate insert into root_content
        'name',                                 # name of (page)fragment or component
        'app_path',                             # path to template dir (by app called this template)
        'type',                                 # type of root (or current) template
        'static_path',                          # path to static dir (by app called this template)
        'ress',                                 # dict of resourses by type looked as {'style':Res(),'js':Res(type,value)}

    )

    def __init__(self, contents, origin):
        self.raw_content = contents
        self.origin = origin.__str__()

        _multicontent = contents.split(HAML_UNIT.UNITS['js'])

        self.content = _multicontent[0]

        if len(_multicontent) > 1:
            other_content = _multicontent[1]


        self.res_keeper = {
            'blocks' : {}
        }
        self.outside_ress = {}

        _pathname_origin, _filename_origin = os.path.split(origin.__str__())         # [`.../templates/pages`, `tmpl.haml`]

        self.name = _filename_origin.rsplit('.',1)[0]                                # `tmpl` - name of main page
        self.app_path, self.type = _get_origin_type(_pathname_origin)                # type of root = (page|fragment|component)
                                                                                     # base_path - base path of app
        if other_content:
            _other_content = other_content.split(HAML_UNIT.UNITS['style'])

        self.static_path = os.path.join(base_path, 'static')

        _types = (2*('js',), ('style','css'))

        res = namedtuple('Res', ['type','value'])

        self.ress = {tip[0]: res(tip[1], v)  for tip, v in zip(types, _other_content)}

#        self.ress = {tip[0]: {'type':tip[1], 'value' : v}  for tip, v in zip(types, _other_content)}
#       {'style': {'type': 'css', 'value': 'style_content'}, 'js': {'type': 'js', 'value': 'js_content'}}


##        self.ress = dict(zip(_other_content, (2*('js',), ('style','css'))))          # # _content : ('js','js'), _content : ('style','..

        # self.script, self.style = self.ress

    def package_ress(self, component_type=None, frag_name=None):
        '''
        put resourses (js/css) to appropriate files (or to self.components_keeper if STYLE_PREPROCS
         has suitable flag w/o save to file)

        - and also extract -frag/-component resourses

        if component_type is None,
        '''
        for tip in self.ress:                                                   # tip => style|js

            current_res = self.ress[tip].value

            # <0.4ms for one replace
            current_res = self._extract_blocks(self.outside_ress, current_res)  # self.outside_ress - resourse that should be pasted inside `onload`, 'style' blocks into root template

            # compile static blocks inside the resourse
            current_res = self._restate_const_block(current_res)

            resourse_carrier = self._save_res(current_res,
                self.ress[tip].type, tip,
                inside_unit_type=component_type,
                inside_unit_name=frag_name)


            if resourse_carrier:
                res_type = self.ress[tip].type
                self.res_keeper[res_type] = self.res_keeper.get(res_type, '') + resourse_carrier

        if not frag_name: ress_to_header(self.outside_ress)                     # if root template (just for fragment, not pages) (for page by default recommend place to header directly)
        else: ress_to_unit(self.outside_ress)                                   # js need to be refresh in dom through createElement


    def ress_to_header(self, outside_ress):

        for blo in outside_ress:

            mch = re.search(r'(\s|\t)-block %s'%blo, self.content)                   # blo = links, onload etc

            if not mch:

                warn(blo+' block is undefined in root template %s'%origin.__str__())  # raise Exception(blo+' block is undefined in root template %s'%origin.__str__())

                content = re.sub(
                    r'(-extends "[\w\.]+")"', r'\1\n\t-block %s'%(blo, _indent_block(
                        r'\t', outside_ress[blo]
                    ),
                    content)
                )

            else:
                _blo = self._indent_block(mch.groups()[0]+' '*4, outside_ress[blo])

                content = re.sub(r'(\s|\t)(-block %s)'%blo, r'\1\2\n'+_blo, content)

##            _blo = _indent_block(mch.groups()[0]+' '*8, blo)
##            _blo = '\n\1    :javascript\n' + _blo

    def embed_components(self, reg = re.compile('([\t ]*)-(frag|unit) "([_\w]+)"')):

        contents = self.content
        contents, origin, extension ='haml'


        return self.content

    def _save_res(self, content, ext, content_type,
        inside_unit_type=None, inside_unit_name=None):
        '''
        save type

        base_name - base name of file (w/o extension) - usually consides with component name
        template_type - subdirectory for saving (`components`,`fragments`,`pages`)
        content_type - name of directory for saving (`style`,`js`)
        ext - extension for saving (`js`,`css`, `less`)
        optional - optional handle funcs for process (for example for less compile)

        '''

        static_path = self.static_path
        base_name = self.name
        template_type = self.type

        option = 'w' if inside_unit_name else 'a'
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
                    sub_compiler[0](content, cs_path+'.'+ext, option)                  # compile to finished file w/o middleware preprocessor saving
                    print 'save to %s by %s'%(style_flname, option)
        else:

            style_flname = cs_path + '.' + (sub_content or ext or content_type)
            with open(style_flname, option) as style_file: style_file.write(content)


    def _extract_blocks(outside_ress, static_content, _pattern = re.compile(r'/\*~block (\w+)\*/([\s\S]*?)/\*~\*/')):

        ''' status: -fixed -optimize !tested
        find blocks in static_content of component (/*~block NAME */ CONTENT /*~*/) - extract
        NAME and CONTENT inside components to outside_ress and remove its from origin
        '''

        _blocks = _pattern.finditer(static_content)

        static_content = re.sub(_pattern, '', static_content)

        for b in _blocks:

            # append key if none or append content to existed key in outside_ress
            # (key is existed block name in root template for appending b.group(2) to it)
            outside_ress[b.group(1)] = outside_ress.get(b.group(1),'') + '\n' + b.group(2)

        return static_content



    def _restate_const_block(sub_content, _pattern = re.compile(r'/\*~const \w+\*/([\s\S]*?)/\*~\*/')):

        ''' status: -fixed !optimize !tested
        find blocks in component template `sub_content` vs pattern (/*~const block */ CONTENT /*~*/)
        - compile CONTENT inside the `const block` to static condition end return sub_content
        with compiled block
        '''

        const_block = _pattern.search(sub_content)
        static_block = const_block.group()

        url_tags = re.finditer(r'{%\s*url [\'"]{1}(\w+)[\'"]{1}\s?(\d*)\s*%}', static_block)     # url
        for url_tag in url_tags:
            url_name, arg = url_tag.groups()
            url = reverse(url_name, args=[arg]) if arg else reverse(url_name)
            static_block = static_block.replace(url_tag.group(), url, 1)

        static = settings.STATIC_URL
        _static_block = re.sub(r"% *static ['\"]([\w\.\d\/\_]+)['\"] *%}", r"/%s/\1"%static, static_block)

        sub_content = sub_content.replace(static_block, _static_block)

        return sub_content

    def __indent_block(self, indnt, code):
        _code = code.splitlines()
        for line in _code:
            line = indnt + line
        return '\n'.join(_code)


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

    components_keeper = {
        'blocks' : {}
    }
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





    if not frag_name:



        for blo in outside_ress:
        # if root template (for fragment - page by default recommend place to header directly):


            mch = re.search(r'(\s|\t)-block %s'%blo, content)                   # blo = links, onload etc

            if not mch:
                raise Exception(blo+' block is undefined in root template %s'%origin.__str__())

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

                content = re.sub(r'(\s|\t)(-block links)',r'\1\2\n'+_blo, content)

    else:


        # if thrown by -frag or -unit tags: need insert into root (parent) page header (to -block links)
        for blo in outside_ress:
            # append to end each block
            # component_type()
            components_keeper['blocks'][blo]=(
                components_keeper['blocks'].get(blo, '') + '\n\n' + outside_ress[blo]
            )

    return (content.encode('utf-8'), components_keeper)





reg = re.compile('([\t ]*)-(frag|unit) "([_\w]+)"')
reg_prefix = r'\n(\s*\.)'

def embed_components(contents, origin, extension ='haml'):
    '''
    embed components to page:
        - insert haml/html component content to page
        - move component js-code to page js-code
        - move style code
    '''
    while True:

##      for m in units: - may so but by back direct in cycle!

        m = reg.search(contents)

        if not m: break
        else:

            indent, unit_type, _unit_name = m.groups() # indent = indent.replace('\t', ' '* 4)
            unit_type = 'fragments' if unit_type == 'frag' else 'components'
            unit_name = '.'.join((_unit_name,  extension))

            _root = root(origin.__str__(), 'templates')

            unit_file = os.path.join(_root, unit_type, unit_name)

            with open(unit_file, 'r') as reader: raw_unit = reader.read()

            print raw_unit

##            if HAML_UNIT.Autoprefix:
##                raw_unit = re.sub(reg_prefix, r'\n\1%s__'%_unit_name.replace('_',''), raw_unit)
##                print raw_unit
##
##            with open(r'C:\Users\admin\Desktop\log.txt', 'w') as p: p.write(raw_unit)

            unit, option = components_save(raw_unit, origin, unit_type, unit_name)      # get unit text

            blocks = option.pop('blocks', '')

            second = '\n'.join([str(indent) + line for line in unit.split('\n')])  # prepare for insert to parent tamplate

            unit = ''.join(second)                                                 # join lines to one monotext

            contents = contents[0:m.start()] + unit + contents[m.end(): m.endpos]   # insert to parent template (html/haml)

    return contents
