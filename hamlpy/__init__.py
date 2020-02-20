from django.apps import AppConfig

__version__ = '1.2'

HAML_EXTENSIONS = ('haml', 'hamlpy')

class HAML_UNIT:
    ENABLE = False

try:

    from django.conf import settings
    if hasattr(settings, 'LIGHT_UNITS'):

        HAML_UNIT.ENABLE = True

        HAML_UNIT.Mono = True

        HAML_UNIT.UNITS = settings.LIGHT_UNITS

        HAML_UNIT.STYLE_PREPROCS = (
            settings.STYLE_PREPROCS if hasattr(settings, 'STYLE_PREPROCS') else []
        )

        print 'init HAML_UNIT'

except Exception as e:
    print 'except HAML_UNIT'
    print HAML_UNIT.ENABLE
    print 'except HAML_UNIT'
    print e.message



import os
print os.path.abspath('')



class Config(AppConfig):
    name = 'hamlpy'

    def ready(self):
        # patch Django's templatize method
        from .template import templatize  # noqa


default_app_config = 'hamlpy.Config'
