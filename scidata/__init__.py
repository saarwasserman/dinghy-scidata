# """init procedures for enire app
# """
# import os
# import subprocess
# import logging

# from .config import get_configuration

# logging.basicConfig(level=logging.INFO)

# logger = logging.getLogger(__file__)


# NBLADE_PACKAGE_DIRPATH = os.path.dirname(os.path.abspath(__file__))

# settings = get_configuration(os.getenv("APP_ENVIRONMENT", "development"))


# NEXUS_GLADIATOR_REPO = "gladiator"


# def shell(command, cwd=None, raise_exception=True, env=None):
#     """runs command in shell

#     Args:
#         command (str): will be executed in the shell

#     Returns:
#         str: standard output string of shell

#     Raises:
#         Exception: if shell command returned error_code != 0

#     """

#     logger.info("Executing: %s", command)
#     process = subprocess.Popen(command, stderr=subprocess.STDOUT,
#                                stdout=subprocess.PIPE, shell=True,
#                                cwd=cwd, env=env)

#     lines = []
#     for line in iter(process.stdout.readline, b''):
#         line = line.rstrip().decode('utf8')
#         logger.info(line)
#         lines.append(line)

#     process.communicate()
#     output = '\n'.join(lines)
#     if process.returncode and raise_exception:
#         raise Exception(f'Failed to run command \'{command}\'\nError code:'
#                         f'{process.returncode}\nContent: {output}')

#     return process.returncode, output
