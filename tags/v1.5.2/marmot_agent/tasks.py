# -*- coding: utf-8 -*-
import urllib
import logging


logger = logging.Logger('marmot-agent')


class TaskBase(object):
    def __init__(self, name, identifier, priority):
        self.name = name
        self.identifier = identifier
        self.priority = int(priority) if int(priority) in range(1, 4) else 2

    def do(self):
        raise NotImplementedError


class TaskDeploy(TaskBase):
    def __init__(self, name, identifier, priority, file_url, file_dest_path):
        super(TaskDeploy, self).__init__(name, identifier, priority)
        self._file_url = file_url
        self._file_dest_path = file_dest_path

    def download_file(self):
        logger.info('Starting to download file: %s - %s ...' % (self._file_url, self._file_dest_path))
        try:
            urllib.urlretrieve(self._file_url, self._file_dest_path)
        except IOError as e:
            logger.error('Download file fail: %s' % self._file_url)
            return
        logger.info('Success to download file: %s - %s ...' % (self._file_url, self._file_dest_path))
        return self._file_dest_path

    def run_sub_process(self):
        pass

    def do(self):
        self.download_file()
        self.run_sub_process()


class TaskCustomScript(TaskBase):
    def __init__(self, name, identifier, priority, script_url):
        super(TaskCustomScript, self).__init__(name, identifier, priority)
        self._script_url = script_url
        self._script_path = ''

    def download_script(self):
        logger.info('Starting to download script: %s - %s ...' % self._script_url)
        try:
            urllib.urlretrieve(self._script_url, self._script_path).read()
        except IOError:
            logger.error('Download script fail: %s' % self._script_url)
            return
        logger.error('Success script fail: %s' % self._script_url)
        return self._script_path

    def run_script(self):
        pass

    def do(self):
        self.download_script()
        self.run_script()
