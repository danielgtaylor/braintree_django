from distutils.core import setup

setup(
    name='django-braintree',
    version="1.3.2",
    description='Django app for interacting with the braintree API',
    author='Daniel Taylor',
    author_email='dan@programmer-art.org',
    url = "https://github.com/danielgtaylor/braintree_django",
    packages=[
        'django_braintree'
    ],
    classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Environment :: Web Environment",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Framework :: Django",
    ],
    install_requires = [
        'braintree>=2.8'
    ],
)

