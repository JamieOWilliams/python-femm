import setuptools

with open('README.md', 'r') as f:
    long_description = f.read()

setuptools.setup(
    name='python-femm',
    version='0.0.1',
    author='Jamie Williams',
    author_email='jw17202@bristol.ac.uk',
    description='A Python framework for FEMM 4.2',
    long_description=long_description,
    long_description_content_type='text/markdown',
    packages=setuptools.find_packages(),
    entry_points={'console_scripts': [
        'python-femm = python_femm.core.manage:execute_from_command_line',
    ]},
    install_requires=[
        'pypiwin32',
        'numpy',
    ],
)
