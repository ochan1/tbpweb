"""Settings for 3rd Party Apps used by tbpweb"""
import sys

from settings.base import CACHES

# Set up SASS (SCSS) compilation for django-compressor, with the "compass"
# library. Use SASS version 3.4.25 was deemed okay to upgrade to from 3.2.14
COMPRESS_PRECOMPILERS = (
    ('text/x-scss', 'sass _3.4.25_ --scss --compass {infile} {outfile}'),
)

# Use the "AbsoluteFilter" to change relative URLs to absolute URLs, and
# CSSMinFilter to minify the CSS
COMPRESS_CSS_FILTERS = [
    'compressor.filters.css_default.CssAbsoluteFilter',
    'compressor.filters.cssmin.CSSMinFilter'
]

# Make django-compressor store its output compressed files in the original
# location of the static files, rather than a subfolder
COMPRESS_OUTPUT_DIR = ''

# Set up a second local memory cache backend for Django Compressor. This is
# useful so that the default cache can be disabled during testing, while still
# allowing Django Compressor to use a cache.
CACHES['compressor'] = {
    'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    'LOCATION': 'compressor'
}

COMPRESS_CACHE_BACKEND = 'compressor'

# Set up aliases for easy-thumbnails
THUMBNAIL_ALIASES = {
    '': {
        'avatar': {
            'size': (40, 40),
            'autocrop': True,
            'crop': 'smart'
        },
        'candidateicon': {
            'size': (200, 200),
            'autocrop': True,
            'crop': 'smart'
        },
        'officericon': {
            'size': (150, 150),
            'autocrop': True,
            'crop': 'smart',
            'quality': 90
        }
    },
}


# Define the function that determines whether the Django Debug Toolbar should
# be shown
def show_toolbar(request):
    """Return True so that the Django Debug Toolbar is always shown.
    This function should only be used with dev!
    By default, the Debug Toolbar would only be shown when DEBUG=True and the
    request is from an IP listed in the INTERNAL_IPS setting.
    """
    return True