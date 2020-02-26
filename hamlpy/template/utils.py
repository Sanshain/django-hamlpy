import imp

from django.template import loaders

from warnings import warn
from collections import namedtuple, defaultdict

from django.core.urlresolvers import reverse
from django.conf import settings

from os import listdir
from os.path import dirname, splitext

from hamlpy import HAML_UNIT
import os
import re

import pdb

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
root = lambda p, e, d=3: (
    p if os.path.split(p)[-1] == e else (
        root(os.path.dirname(p), e, d-1) if d>0 else None
    )
)


def _get_sub_content_type(content):
    '''
    just for css/less/sass/stylus
    '''
    for key in HAML_UNIT.STYLE_PREPROCS.keys():
        if key in content[0:content.find(' ')+1]:
            return key
    else:
        return None



res = namedtuple('Res', ['type','value'])

class HamlComponent(object):

    __slots__ = (
        'raw_content',                          # raw content
        'origin',                               # origin path (this? or root?)          ?
        'content',                              # haml main (root) part of raw content
        'res_keeper',                           # resourse keeper in keeper mode
        'outside_ress',                         # res of inline resourse for aggregate insert into root_content
        'name',                                 # name of root (page)fragment
        'app_path',                             # path to root dir app contained templates dir (by app called this template)
        'type',                                 # type of root template (page or fragment)
        'static_path',                          # path to static dir (by app called this template)
        'ress',                                 # dict of resourses by type looked as {'style':Res(),'js':Res(type,value)}
        'is_root',                              # define is current component is root or subcontent of root
        'save_flag',                            # flag for mode file write for embed_coponents (if once ont keeper then 'a')
        # if its subcontent (fragment or component) of root content (page or fargment):
        'component_type',                       # type of current component
        'frag_name',                            # name of current subelement
    )

    def __init__(self, origin, contents, component_type=None, frag_name=None):

        self.raw_content = contents
        self.origin = origin.__str__()

        self.component_type = component_type
        self.frag_name = frag_name
        self.is_root = False if frag_name else True

        _multicontent = contents.split(HAML_UNIT.UNITS['js'])

        self.content = _multicontent[0]

        other_content = _multicontent[1] if len(_multicontent) > 1 else None

        self.res_keeper = {}
        self.save_flag = { 'js':'w', 'css' : 'w' }                              # defaultdict(lambda x: 'w')
        self.outside_ress = {}

        _pathname_origin, _filename_origin = os.path.split(self.origin)         # [`.../templates/pages`, `tmpl.haml`]

        self.name = _filename_origin.rsplit('.',1)[0]                                # `tmpl` - name of main page
        self.app_path, self.type = _get_origin_type(_pathname_origin)                # type of root = (page|fragment|component)
        self.static_path = os.path.join(self.app_path, 'static')
        self.ress = {'style': res(type='css', value=''), 'js': res(type='js', value='')}

        if other_content:
            _other_content = other_content.split(HAML_UNIT.UNITS['style'])
            _types = (2*('js',), ('style','css'))
            self.ress = {tip[0]: res(tip[1], v)  for tip, v in zip(_types, _other_content)} # {'style': Res(type='css', value='style_content'), 'js': Res(type='js', value='js_content')}


    def package_ress(self, root_content = None):
        '''
        - put resourses (js/css) to appropriate files (or to self.components_keeper if STYLE_PREPROCS
        has suitable flag w/o save to file)

        - move to root_content blocks marked as inline blocks (look _extract_blocks() for more details)

            if component_type is None, means self is root component
        '''

        component_type = self.component_type
        frag_name = self.frag_name

        for tip in self.ress:                                                   # tip => style|js

            current_res = self.ress[tip].value

            # `onload`, 'style' blocks for inside to root template move to outside_ress
            current_res = self._extract_blocks(self.outside_ress, current_res, tip)  # <0.4ms for one replace

            current_res = self._restate_const_block(current_res)                # compile static blocks inside the resourse

            resourse_carrier = self._save_res(current_res,
                self.ress[tip].type, tip,
                inside_unit_type=component_type,
                inside_unit_name=frag_name)


            if resourse_carrier:                                                # if is compiled contents
                res_type = self.ress[tip].type                                  # js/css
                self.res_keeper[res_type] = self.res_keeper.get(res_type, '') + resourse_carrier
##                print 'wwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwwww'
            else:
                self.save_flag[self.ress[tip].type] = 'a'
##                print 'aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa'
##                print self.ress[tip].type
##                print self.save_flag[self.ress[tip].type]

        # if is_root and type = page -> `style`,`onload`, script` to headers by ress_to_header
        if self.type == "pages":
            if self.is_root:
                self.content = self.ress_move_on_page()
            elif not self.is_root:
                # pass
                root_content = self.ress_move_on_page(root_content)

                # self.ress_to_keep(self.outside_ress, root_content)
        elif self.type == 'fragments' or self.type == 'components':

            self.outside_ress = self.prep_tags(self.outside_ress)                  # prepare: inside in tags script/style

            if self.is_root:
                self.content = self.ress_append(self.outside_ress)
            elif not self.is_root:
                root_content = self.ress_append(self.outside_ress, root_content)


        # js need to be refresh in dom through createElement

        return self.res_keeper if self.is_root else (self.res_keeper, root_content)

    def ress_append(self, outside_ress, _content=None):
        _content = _content or self.content

        outres = '\n'.join([outside_ress[blo].value for blo in outside_ress])

        _content = outres + _content

        return _content

    def prep_tags(self, outside_ress):
        for blo in outside_ress:
            tip = ':' + ('javascript' if outside_ress[blo].type == 'js' else 'stylus') + '\n'

            subcontent = '%s'%(
                tip,
                self.__indent_block('\t', outside_ress[blo].value) + '\n'
            )

##            subcontent = '<{0} id="{1}">\n{2}\n</{0}>'.format(
##                outside_ress[blo].type,
##                self.name + '_' + blo,
##                outside_ress[blo].value
##            )

            outside_ress[blo].value = subcontent

        return outside_ress





    def ress_move_on_page(self, content=None):
        """
        find blocks, specified in outside_ress, into self.content and
        inside its
        """
        outside_ress = self.outside_ress
        content = content or self.content

        for blo in outside_ress:

            mch = re.search(r'(\s|\t)-block %s'%blo, content)                   # blo = links, onload etc

            if not mch:

                warn(blo+' block is undefined in root template %s'%self.origin.__str__())  # raise Exception(blo+' block is undefined in root template %s'%origin.__str__())

                super_block = r'\t\t={ block.super }\n'
                content = re.sub(
                    r'(-extends "[\w\.]+")"', r'\1\n\t-block %s%s%s'%(
                        blo, super_block, __indent_block(r'\t\t', outside_ress[blo].value)
                    ),
                    content
                )

            else:
                _blo = self.__indent_block(mch.groups()[0]+' '*4, outside_ress[blo].value)

                # (\s|\t)-block \w+(([\s:]*={ *block.super *})|)        ={ *block.super *} - \2

                content = re.sub(r'(\s|\t)(-block %s)'%blo, r'\1\2\n'+_blo, content)

##            _blo = _indent_block(mch.groups()[0]+' '*8, blo)
##            _blo = '\n\1    :javascript\n' + _blo

        return content


    def ress_to_keep(self, outside_ress, content=None):
        '''
        Obsolete
        '''
        # called jaust by `haml_root -> embed_components -> haml_init -> package_ress -> ress_to_unit`

        # if thrown by -frag or -unit tags: need insert into root (parent) page header (to -block links)
        for blo in outside_ress:
            # append to end each block
            # component_type()
            pdb.set_trace()

            self.res_keeper['blocks'][blo]=(
                self.res_keeper['blocks'].get(blo, '') + '\n\n' + outside_ress[blo].value
            )


    def embed_components(self, reg = re.compile('([\t ]*)-(frag|unit) "([_\w]+)"')):
        """
        parse (frag|unit) tags in template and replace its on its content
        """
        contents = self.content
        extension ='haml'

        while True:

            component = reg.search(contents)

            if not component: break
            else:

                _indent, _unit_type, _unit_name = component.groups();

                unit_indn = _indent.replace('\t', ' '* 4)
                unit_type = 'fragments' if _unit_type == 'frag' else 'components'
                unit_name = '.'.join((_unit_name,  extension))

                templates_path = root(self.origin, 'templates')

                unit_file = os.path.join(templates_path, unit_type, unit_name)

                with open(unit_file, 'r') as reader: raw_unit = reader.read()

                haml_component = HamlComponent(self.origin, raw_unit, unit_type, unit_name)
                ress_keeper, contents = haml_component.package_ress(contents)



                for frag_block in ress_keeper:                                  # js/css
                    self.res_keeper[frag_block] = self.res_keeper.get('frag_block','') + ress_keeper[frag_block]
                for frag_block in self.res_keeper:
                    _dir = 'style' if frag_block == 'css' else 'style'
                    tgt = os.path.join(self.static_path, _dir, '.'.join(self.name, frag_block))
                    with open(tgt, self.save_flag[frag_block]) as pen: pen.write(self.res_keeper[frag_block])

                unit = '\n'.join([str(unit_indn) + line for line in haml_component.content.split('\n')])

                contents = contents.replace('%s-%s "%s"'%(_indent, _unit_type, _unit_name), unit, 1)

                ## next case need recalc contents len before and after `ress_keeper, contents = haml_component.package_ress(contents)`
                ## and will work just for add in header (before -frag/unit tag). Too tricky
                # start, end, endpos = component.start(), component.end(), component.endpos
                # contents = contents[0:start] + unit + contents[end: endpos]

        return contents









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

        option = 'a' if inside_unit_name else 'w'                               # option for saving to common root file
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
            scontent = '/*%s %s*/\n\n'%(inside_unit_type, inside_unit_name)
            content = str(scontent) + content                                            # .decode('utf-8')
            print scontent
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
                    print 'save to %s by %s'%(cs_path+'.'+ext, option)
        else:

            style_flname = cs_path + '.' + (sub_content or ext or content_type)
            _content = content.encode('utf-8') if type(content) is not str else content
            with open(style_flname, option) as style_file: style_file.write(_content)



    def _extract_blocks(self, outside_ress, static_content, tip, _pattern = re.compile(r'/\*~block (\w+)\*/([\s\S]*?)/\*~\*/')):

        ''' status: -fixed -optimize !tested
        find blocks in static_content of component (/*~block NAME */ CONTENT /*~*/) - extract
        NAME and CONTENT inside components to outside_ress and remove its from origin
        '''



        _blocks = _pattern.finditer(static_content)

        static_content = re.sub(_pattern, '', static_content)

        for b in _blocks:

            # append key if none or append content to existed key in outside_ress
            # (key is existed block name in root template for appending b.group(2) to it)

            outside_ress[b.group(1)] = res(
                tip,
                outside_ress[b.group(1)].value if b.group(1) in outside_ress else '' + '\n' + b.group(2)
            )

##            outside_ress[b.group(1)] = outside_ress.get(b.group(1), '') + '\n' + b.group(2)


        return static_content                                                   #, b.group(2)



    def _restate_const_block(self, sub_content, _pattern = re.compile(r'/\*~const \w+\*/([\s\S]*?)/\*~\*/')):

        ''' status: -fixed !optimize !tested
        find block in component template `sub_content` vs pattern (/*~const block */ CONTENT /*~*/)
        - compile CONTENT inside the `const block` to static condition end return sub_content
        with compiled block. Otherwise just return sub_content
        '''

        const_block = _pattern.search(sub_content)

        print '_______******************************************'

        if const_block:

            static_block = const_block.group()

            url_tags = re.finditer(r'{%\s*url [\'"]{1}(\w+)[\'"]{1}\s?(\d*)\s*%}', static_block)     # url

            _static_block = static_block

            for url_tag in url_tags:
                url_name, arg = url_tag.groups()

                url = str(reverse(url_name, args=[arg]) if arg else reverse(url_name))
                _static_block = _static_block.replace(url_tag.group(), url, 1)

            static = settings.STATIC_URL
            _static_block = re.sub(r"{% *static ['\"]([\w\.\d\/\_]+)['\"] *%}", r"%s\1"%static, _static_block)

            # pdb.set_trace()

            # sub_content = sub_content.decode('utf-8') if sub_content is str else sub_content
            sub_content = sub_content.replace(static_block, _static_block)

        return sub_content

    def __indent_block(self, indnt, code):
        _code = code.splitlines()
        for i, line in enumerate(_code):
            _code[i] = indnt + line
        return '\n'.join(_code)




def _get_origin_type(pathname_origin):

    base_path, template_type = os.path.split(pathname_origin)

    if template_type in ('components', 'fragments', 'pages'): pass
    elif template_type == 'templates':  template_type = ''
    else: template_type = 'pages'

    base_path = os.path.dirname(base_path) if template_type else base_path      # path of app (for ex - 'main')

    return base_path, template_type





