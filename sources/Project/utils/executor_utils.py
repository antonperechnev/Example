from concurrent.futures import ThreadPoolExecutor, as_completed
import math
from typing import Any, Callable
import logging


class Executor:
    """
    class help remove duplicates from parsers functions
    """
    def __init__(self, func: Callable, workers_count: int = 2, to_iterate: Any = 'None'):
        """
        :param workers_count: num of workers that can execute task
        :param func: name of function without call that need execute
        :param to_iterate: iterable structure
        """
        self.workers = workers_count
        self.executable_func = func
        self.iterate_ds = to_iterate

    def _dict_create(self, executor, kwargs):
        step = math.ceil(len(self.iterate_ds) / self.workers)
        futures_dict = {
                executor.submit(
                    self.executable_func, self.iterate_ds[step * number: step * number + step], **kwargs
                ): number
                for number in range(self.workers)
            }
        return futures_dict

    def start(self, kwargs: dict):
        """
        start executor loop
        :parameter kwargs: dict for keyword params in function
        :return: future result or exception message
        """
        with ThreadPoolExecutor(max_workers=self.workers) as executor:

            futures_dict = self._dict_create(executor, kwargs)

            for future in as_completed(futures_dict):
                try:
                    future.result()
                except Exception as exception:
                    logging.exception(f'Caught an error in executor - {exception}')

    def start_accumulation_request(self):
        """
        method return list with data that threads collect
        :return: future result or exception message
        """
        data = []
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures_dict = self._dict_create(executor, {})
            print(futures_dict)
            for future in as_completed(futures_dict):
                try:
                    data.extend(future.result())
                except Exception as exception:
                    print(exception, future)
        return data

    def start_concurrent_request(self, request_info: list) -> list:
        """
        method start threads to faster take info from resource
        :param request_info: request params
        :return:
        """
        tmp = []
        with ThreadPoolExecutor(max_workers=len(request_info)) as executor:
            futures_dict = {
                executor.submit(self.executable_func, **info): info
                for info in request_info
            }
            for future in as_completed(futures_dict):
                try:
                    tmp.append((futures_dict[future], future.result()))
                except Exception as exception:
                    print(exception, future)
        return tmp
