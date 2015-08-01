# notorm
Not a traditional Python ORM

This project goes along with a talk being given at pyOhio 2015.
 
Requires Python >= 3.4.

## Installation
    git clone git@github.com:subssn21/notorm.git
    cd notorm
    psql postgres -c "CREATE ROLE dbuser LOGIN SUPERUSER CREATEDB VALID UNTIL 'infinity';"
    psql dbuser -c "create database notorm_example;"
    psql dbuser -d notorm_example -f notormexample.sql
    virtualenv-3.4 --python=python3 ~/notormvenv
    source ~/notormvenv/bin/activate
    python3 setup.py develop

## Running the examples
    cd examples/tornadoasyncio
    python3 tornadoasyncio.py
    
Open `localhost:8888' in a browser.