from setuptools import setup, find_packages

setup(
    name="NotORM",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        'Momoko==2.1.0',
        'aiopg==0.7.0',
        'gnureadline==6.3.3',
        'ipython==3.0.0',
        'nose==1.3.7',
        'psycopg2==2.6.1',
        'readline==6.2.4.1',
        'requests==2.5.3',
        'six==1.9.0',
        'tornado==4.2.1',
        'gevent==1.1b1'
    ]
)
