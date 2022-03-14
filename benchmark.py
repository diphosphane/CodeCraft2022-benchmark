from typing import Tuple, List
import os
import sys
import math
import time
import numpy as np

class IOFile():
    demand = 'data/demand.csv'
    qos = 'data/qos.csv'
    bandwidth = 'data/site_bandwidth.csv'
    config = 'data/config.ini'
    output = 'output/solution.txt'

def err_print(msg):
    print('ERROR  ' * 10)
    print(msg)
    print('ERROR  ' * 10)
    exit(1)

def out_print(msg):
    print('RESULT  ' * 10)
    print(msg)
    print('RESULT  ' * 10)


cname, sname, qos, qos_lim = None, None, None, None
client_demand = None
bandwidth = None
time_label = None
cname_map = {}
sname_map = {}

def read_demand() -> Tuple[List[str], List[int]]:
    fname = IOFile.demand
    with open(fname) as f:
        data = f.read().splitlines()
    client_name = data[0].split(',')[1:]
    client_demand = []
    time_label = []
    for each in data[1:]:
        d = each.split(',')
        time_label.append(d[0])
        client_demand.append(list(map(int, d[1:])))
    return time_label, client_name, client_demand

def read_server_bandwidth() -> Tuple[List[str], List[int]]:
    fname = IOFile.bandwidth
    with open(fname) as f:
        data = f.read().splitlines()
    server_name = []
    server_bandwidth = []
    for each in data[1:]:
        a, b = each.split(',')
        server_name.append(a)
        server_bandwidth.append(int(b))
    return server_name, server_bandwidth

def read_qos() -> Tuple[List[str], List[str], List[List[int]]]:
    fname = IOFile.qos
    with open(fname) as f:
        data = f.read().splitlines()
    client_name = data[0].split(',')[1:]
    server_name = []
    qos_array = []
    for each in data[1:]:
        d = each.split(',')
        server_name.append(d[0])
        qos_array.append(list(map(int, d[1:])))
    return client_name, server_name, qos_array

def read_qos_limit() -> int:
    fname = IOFile.config
    with open(fname) as f:
        data = f.read().splitlines()
    qos_lim = int(data[1].split('=')[1])
    return qos_lim

def validate_file_exist():
    if not os.path.exists(IOFile.output):
        if os.path.exists('/' + IOFile.output):
            IOFile.output = '/' + IOFile.output
        else:
            err_print('can not find solution.txt in ./output/ or /output/')
    if not os.path.exists(IOFile.demand):
        if os.path.exists('/' + IOFile.demand):
            IOFile.demand = '/' + IOFile.demand
            IOFile.qos = '/' + IOFile.qos
            IOFile.bandwidth = '/' + IOFile.bandwidth
            IOFile.config = '/' + IOFile.config
        else:
            err_print('can not find input file in ./data/ or /data/')

def get_input_data():
    global cname, sname, qos, qos_lim, bandwidth, client_demand, time_label
    cname, sname, qos = read_qos()
    for idx, name in enumerate(cname):
        cname_map[name] = idx
    for idx, name in enumerate(sname):
        sname_map[name] = idx
    qos = np.array(qos)
    time_label, client_name, client_demand = read_demand()
    client_idx_list = []
    for c in cname:
        idx = client_name.index(c)
        client_idx_list.append(idx)
    client_demand = np.array(client_demand)[:, client_idx_list]
    server_name, server_bandwidth = read_server_bandwidth()
    bandwidth = []
    for s in sname:
        idx = server_name.index(s)
        bandwidth.append(server_bandwidth[idx])
    qos_lim = read_qos_limit()
    bandwidth = np.array(bandwidth)


class Output():
    def __init__(self) -> None:
        self.server_history_bandwidth = []
        # self.server_history_bandwidth = [ [] for _ in range(len(client_demand)) ]
        self.max = len(cname)
        self.reset()

    def reset(self):
        self.client_outputed = [ False for _ in range(len(cname)) ]
        self.server_used_bandwidth = np.zeros(len(sname), dtype=np.int64)
        self.count = 0
    
    def dispatch_server(self, c_idx: int, s_idx: int, res: int):
        self.server_used_bandwidth[s_idx] += res
        if self.server_used_bandwidth[s_idx] > bandwidth[s_idx]:
            err_print(f'bandwidth overflow at server {sname[s_idx]} \t {self.count}th line time: {time_label[self.count]}')
        if qos[s_idx, c_idx] > qos_lim:
            err_print(f'qos larger than qos limit \t edge node: {sname[s_idx]} \t client node: {cname[c_idx]} \t {self.count}th line time: {time_label[self.count]}')
    
    def read_one_line(self, line: str):
        try:
            c, remain = line.strip().split(':')
            c_idx = cname_map[c]
            if self.client_outputed[c_idx]:
                err_print(  f'output format error: the same client node "{c}" appears in the same time \n' \
                            f'or output is not complete in the {self.count}th line time: {time_label[self.count]}')
            else:
                self.client_outputed[c_idx] = True
                self.count += 1
            dispatchs = remain[1: -1].split(',')
            if len(dispatchs) == 2:
                s, res = dispatchs
                s_idx = sname_map[s]
                res = int(res)
                self.dispatch_server(c_idx, s_idx, res)
                self.check_time_step_finished()
                return
            dispatchs = remain[1: -1].split('>,<')
            for d_str in dispatchs:
                s, res = d_str.split(',')
                s_idx = sname_map[s]
                res = int(res)
                self.dispatch_server(c_idx, s_idx, res)
                self.check_time_step_finished()
        except:
            err_print('output format error')
    
    def check_time_step_finished(self):
        if self.count == self.max:
            self.server_history_bandwidth.append(self.server_used_bandwidth)
            self.reset()

    def read_file(self, output_file_name: str):
        with open(output_file_name) as f:
            lines = f.read().splitlines()
        for l in lines:
            self.read_one_line(l)
    
    def calc_score_1(self):
        if self.count not in [0, self.max]:
            err_print('output is not complete in the last time step')
        time_cnt = len(time_label)
        idx = math.ceil(time_cnt * 0.95) - 1
        server_history = np.array(self.server_history_bandwidth)
        server_history.sort(axis=0)
        score = server_history[idx].sum()
        print(f'final score 1: {score}')

    def calc_score_2(self):
        if self.count not in [0, self.max]:
            err_print('output is not complete in the last time step')
        time_cnt = len(time_label)
        server_history = np.array(self.server_history_bandwidth)  # time * server_bandwidth
        non_zero = server_history > 0
        non_zero_count = non_zero.sum(axis=0)  # for each server
        zero_count = np.ones(len(sname), dtype=np.int64) * time_cnt - non_zero_count
        idx = zero_count + np.ceil(non_zero_count * 0.95).astype('int64') - 1
        server_history.sort(axis=0)
        score = server_history[idx, np.arange(len(idx))].sum()
        print(f'final score 2: {score}')

def gauge_time(args):
    start_time = time.time()
    os.system(' '.join(args))
    end_time = time.time()
    print(f'compile and run time: {(end_time - start_time):.4f}')

if __name__ == '__main__':
    validate_file_exist()
    get_input_data()
    if len(sys.argv) == 1:
        gauge_time('sh build_and_run.sh')
    else:
        gauge_time(sys.argv[1:])
    output_scorer = Output()
    output_scorer.read_file(IOFile.output)
    output_scorer.calc_score_1()
    output_scorer.calc_score_2()