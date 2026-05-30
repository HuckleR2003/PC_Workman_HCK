from setuptools import setup, find_packages

setup(
    name='pc_workman_hck',
    version='1.7.2',
    author='HCK_Labs',
    description='Educational system monitor and AI assistant for Windows',
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'psutil>=5.9.0',
        'gputil>=1.4.0',
        'matplotlib>=3.7.0',
        'pillow>=10.0.0',
        'pystray>=0.19.0',
        'pandas>=2.0.0',
        'numpy>=1.24.0',
        'requests>=2.28.0',
    ],
    entry_points={
        'console_scripts': [
            'pcworkman=startup:run_demo'
        ]
    },
    python_requires='>=3.8',
)
