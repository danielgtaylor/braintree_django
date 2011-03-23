import braintree

from django.conf import settings

if not hasattr(braintree.Configuration, "merchant_id"):
    braintree.Configuration.configure(
        getattr(settings, "BRAINTREE_ENV", braintree.Environment.Sandbox),
        getattr(settings, "BRAINTREE_MERCHANT", ""),
        getattr(settings, "BRAINTREE_PUBLIC_KEY", ""),
        getattr(settings, "BRAINTREE_PRIVATE_KEY", ""),
    )
    
    if getattr(settings, "BRAINTREE_UNSAFE_SSL", False):
        braintree.Configuration.use_unsafe_ssl = True
