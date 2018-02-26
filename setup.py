# > python setup.py sdist upload

from setuptools import setup

def version():
    import re
    VERSION_FILE="imks/_version.py"
    VERSION_REGEX = r"^__version__ = ['\"]([^'\"]*)['\"]"
    with open(VERSION_FILE, "rt") as f:
        version_line = f.read()
        mo = re.search(VERSION_REGEX, version_line, re.M)
    if mo:
        return mo.group(1)
    else:
        raise RuntimeError("Unable to find version string in %s." % VERSION_FILE)

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='imks',
      version=version(),
      description='An ipython extension to make computations with units',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Framework :: IPython',
        'Topic :: Scientific/Engineering :: Physics'
      ],
      keywords='units physics calculator',
      url='https://github.com/astrozot/imks',
      author='Marco Lombardi',
      author_email='marco.lombardi@gmail.com',
      license='MIT',
      packages=['imks'],
      install_requires=[
          'ply',
          'unidecode',
          'lxml',
          # next two lines should be
          # 'ProxyTypes;python_version<"3.0"',
          # 'objproxies;python_version>"3.0"'
          # 'ProxyTypes'
          'objproxies'
        ],
      extras_require = {
        'numpy': ['numpy'],
        'mpmath': ['mpmath'],
        'uncertainties':  ['uncertainties'],
        'soerp': ['soerp'],
        'mcerp': ['mcerp']
      },
      tests_require=['nose'],
      test_suite='nose.collector',
      include_package_data=True,
      zip_safe=False)
