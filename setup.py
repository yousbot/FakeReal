from setuptools import setup, find_packages

setup(
    name='seedpy',
    version='0.1.0',
    packages=find_packages(),
    install_requires=[
        'peewee',
        'Faker',
    ],
    author='Youssef Sbai Idrissi',
    author_email='sbaiidrissiyoussef@gmail.com',
    description='A Python library for seeding databases with test data."',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/yourusername/seedpy',
)
