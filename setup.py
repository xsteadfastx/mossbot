from setuptools import setup

setup(
    name='mossbot',
    version='0.0.0',
    py_modules=['mossbot'],
    include_package_data=True,
    install_requires=[
        'Click>=6.0.0',
        'matrix_client'
    ],
    dependency_links=[
        'git+https://github.com/matrix-org/matrix-python-sdk.git#egg=matrix_client'
    ],
)
