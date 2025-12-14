from setuptools import setup, find_packages

setup(
    name='pc_workman_hck',
    version='1.3.3',
    author='HCK_Labs',
    description='Educational system monitor and AI assistant for Windows',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'psutil',
        'gputil'
    ],
    entry_points={
        'console_scripts': [
            'pcworkman=startup:run_demo'
        ]
    },
    python_requires='>=3.8',
)
