class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Add security headers
        response['X-Content-Type-Options'] = 'nosniff'
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response['Permissions-Policy'] = 'camera=(), microphone=(), geolocation=()'
        response['X-XSS-Protection'] = '1; mode=block'

        # Basic CSP policy - enhance as needed
        csp = "default-src 'self'; script-src 'self' https://js.stripe.com 'unsafe-inline'; " \
              "style-src 'self' 'unsafe-inline'; img-src 'self' data:; " \
              "connect-src 'self' https://api.stripe.com; " \
              "frame-src 'self' https://js.stripe.com https://hooks.stripe.com;"

        response['Content-Security-Policy'] = csp

        return response