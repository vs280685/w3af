'''
base_consumer.py

Copyright 2012 Andres Riancho

This file is part of w3af, w3af.sourceforge.net .

w3af is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation version 2 of the License.

w3af is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with w3af; if not, write to the Free Software
Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

'''
import Queue

from multiprocessing.dummy import Process

from core.controllers.core_helpers.consumers.constants import POISON_PILL
from core.controllers.threads.threadpool import Pool


class BaseConsumer(Process):
    '''
    Consumer thread that takes fuzzable requests from a Queue that's populated
    by the crawl plugins and identified vulnerabilities by performing various
    requests.
    '''
    
    def __init__(self, consumer_plugins, w3af_core):
        '''
        @param in_queue: The input queue that will feed the base_consumer plugins
        @param base_consumer_plugins: Instances of base_consumer plugins in a list
        @param w3af_core: The w3af core that we'll use for status reporting
        '''
        super(BaseConsumer, self).__init__()
        
        self.in_queue = Queue.Queue()
        # See documentation in the property below
        self._out_queue = Queue.Queue()
        self._consumer_plugins = consumer_plugins
        self._w3af_core = w3af_core
        self._threadpool = Pool(10)
        self._tasks_in_progress_counter = 0
    
    def run(self):
        '''
        Consume the queue items, sending them to the plugins which are then going
        to find vulnerabilities, new URLs, etc.
        
        TODO: Report progress to w3afCore somehow.
        '''

        while True:
           
            work_unit = self.in_queue.get()

            if work_unit == POISON_PILL:
                
                # Close the pool and wait for everyone to finish
                self._threadpool.close()
                self._threadpool.join()
                
                self._teardown()
                self._task_done(None)
                
                # Finish this consumer and everyone consuming the output
                self._out_queue.put( POISON_PILL )
                self.in_queue.task_done()
                break
                
            else:
                
                self._consume(work_unit)
                self.in_queue.task_done()

    def _teardown(self):
        raise NotImplementedError

    def _consume(self, work_unit):
        raise NotImplementedError

    def _task_done(self, result):
        self._tasks_in_progress_counter -= 1
    
    def _add_task(self):
        self._tasks_in_progress_counter += 1
    
    def in_queue_put(self, work):
        if work is not None:
            self._add_task()
            return self.in_queue.put( work )
        
    def in_queue_put_iter(self, work_iter):
        if work_iter is not None:
            for work in work_iter:
                self._add_task()
                self.in_queue.put( work )
                    
    def has_pending_work(self):
        '''
        @return: True if the in_queue_size is != 0 OR if one of the pool workers
                 is still doing something that might impact on out_queue.
        '''
        if self.in_queue_size() > 0 \
        or self.out_queue.qsize() > 0:
            return True
        
        if self._tasks_in_progress_counter > 0:
            return True
        
        return False
    
    @property
    def out_queue(self):
        #
        #    This output queue can contain one of the following:
        #        * POISON_PILL
        #        * (plugin_name, fuzzable_request, AsyncResult)
        return self._out_queue
        
    def in_queue_size(self):
        return self.in_queue.qsize()

    def join(self):
        '''
        Poison the loop and wait for all queued work to finish this might take
        some time to process.
        '''
        self.in_queue.put( POISON_PILL )
        self.in_queue.join()

    def terminate(self):
        '''
        Remove all queued work from in_queue and poison the loop so the consumer
        exits. Should be very fast and called only if we don't care about the
        queued work anymore (ie. user clicked stop in the UI).
        '''
        while not self.in_queue.empty():
            self.in_queue.get()
            self.in_queue.task_done()
        
        self.in_queue.put( POISON_PILL )
        self.in_queue.join()

    def get_result(self, timeout=0.5):
        '''
        @return: The first result from the output Queue.
        '''
        return self._out_queue.get(timeout=timeout)
