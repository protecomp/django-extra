from django.conf import settings
from django.middleware.cache import UpdateCacheMiddleware, FetchFromCacheMiddleware
from django.utils.safestring import mark_safe

import re

_HTML_TYPES = ('text/html', 'application/xhtml+xml')

class CustomUpdateCacheMiddleware(UpdateCacheMiddleware):
    '''
    Parses certain (mostly analytics scripts related) cookies from
    request in order to solve cache issues. Due to the cookies
    the cache key for unchanged content differed so no cache hits were
    commited.
    '''

    STRIP_RE = re.compile(r'\b((_|ki|2c)[^=]+=.+?(?:; |$))')
    STRIP_CSRF_RE = re.compile(r'csrftoken=[ a-z0-9]*(; |$)')

    def process_request(self, request):               
        cookie = self.STRIP_RE.sub('', request.META.get('HTTP_COOKIE', ''))   
#        cookie = self.STRIP_CSRF_RE.sub('', cookie)
        request.META['HTTP_COOKIE'] = cookie                      

    def _should_update_cache(self, request, response):
        should = super(CustomUpdateCacheMiddleware, self)._should_update_cache(request, response)
        if should:
            response['X-Cache-Update'] = 'True'
        else:
            response['X-Cache-Update'] = 'False'
        return should

class CustomFetchFromCacheMiddleware(FetchFromCacheMiddleware):
    '''
    Adds informative headers about caching to the response
    '''
    def process_request(self, request):
        """
        Checks whether the page is already cached and returns the cached
        version if available.
        """
        response = super(CustomFetchFromCacheMiddleware, self).process_request(request)
        if response:
            response['X-Cache-Middleware'] = 'Hit'
        return response

    def process_response(self, request, response):
        if response.get('X-Cache-Middleware', '') == '':
            response['X-Cache-Middleware'] = 'Miss'
        return response

class CsrfTokenUpdaterMiddleware(object):
    '''
    Updates CSRF tokens to match the token contained in cookie. This way 
    pages can be safely cached. CsrfTokenUpdaterMiddleware should be run after the page is 
    feched from cache.

    Django 1.2
    '''

    CSRFTOKEN_RE = re.compile(r'csrfmiddlewaretoken[^>]*value=(?:\'|")([a-z0-9]+)(?:\'|")', re.IGNORECASE)

    def process_response(self, request, response):
        if response['Content-Type'].split(';')[0] in _HTML_TYPES:
            print "processing..."
            csrf_token = request.META.get("CSRF_COOKIE", None)
            print "Cookie: " + str(csrf_token)
            # If csrf_token is None, we have no token for this request, which probably
            # means that this is a response from a request middleware.
            if csrf_token is None:
                return response

            # Find the CSRF token used in cached content
            token_match = self.CSRFTOKEN_RE.search(response.content)
            if token_match: print "Match: " + token_match.group(1)
            if token_match and token_match.group(1) != csrf_token:
                print csrf_token
                # Replace all CSRF tokens on response
                response.content = mark_safe(response.content.replace(token_match.group(1), csrf_token))
                request.META["CSRF_COOKIE_USED"] = True

                # Since the content has been modified, any Etag will now be
                # incorrect.  We could recalculate, but only if we assume that
                # the Etag was set by CommonMiddleware. The safest thing is just
                # to delete. See bug #9163
                del response['ETag']
        return response

