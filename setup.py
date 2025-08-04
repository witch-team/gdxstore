from setuptools import setup, find_packages

setup(
    name='gdxstore',
    version='0.1',
    description='A storage and version control tool for WITCH result files',
    author='Marco Gambarini',
    author_email='marco.gambarini@cmcc.it',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'gdxstore=source.gdxstore:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
    ],
)