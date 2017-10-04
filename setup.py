from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='imks',
      version='3.0.1',
      description='An ipython extension to make computations with units',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.6',
        'Framework :: IPython',
        'Topic :: Scientific/Engineering :: Physics'
      ],
      keywords='units physics calculator',
      url='http://www.marcolombardi.org',
      author='Marco Lombardi',
      author_email='marco.lombardi@gmail.com',
      license='MIT',
      packages=['imks'],
      install_requires=[
          'ply',
          'unidecode',
          'lxml'
        ],
      extras_require = {
        'mpmath': ['mpmath'],
        'uncertainties':  ['uncertainties'],
        'soerp': ['soerp'],
        'mcerp': ['mcerp']
      },
      test_suite='nose.collector',
      tests_require=['nose'],
      include_package_data=True,
      zip_safe=False)
