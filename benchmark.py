import os
import sys
import math
import time
from io import StringIO
from subprocess import getoutput
from typing import Tuple, List
from abc import ABC, abstractmethod
import numpy as np
import mpld3
import matplotlib.pyplot as plt
from mpld3._server import serve as mpld3_server


cname, sname, qos, qos_lim = None, None, None, None
client_demand = None
bandwidth = None
time_label = None
cname_map = {}
sname_map = {}

class IOFile():
    demand = 'data/demand.csv'
    qos = 'data/qos.csv'
    bandwidth = 'data/site_bandwidth.csv'
    config = 'data/config.ini'
    output = 'output/solution.txt'


class Plot(ABC):
    id_cnt = 0
    def __init__(self) -> None:
        plt.subplots(figsize=(8, 2))
        self.fig = plt.gcf()
        # self.fig, self.ax = plt.subplots(figsize=(15, 3))
    
    @abstractmethod
    def generate_figure(self): pass

class ServerSeriesPlot(Plot):  # x: time  y: many client bandwidth height. P.S. only for one server
    def __init__(self, s_idx: int) -> None:
        plt.subplots(1, 2, figsize=(10, 2))
        self.fig = plt.gcf()
        self.s_name = sname[s_idx]
        self.time = None
        self.y_accu = None
        self.labels = []
        self.bottom = []
        self.heights = []
    
    def add(self, label: str, y_height: int):  # client name, bw in every time for this client
        # plt.bar(self.time, bottom=self.y_accu, height=y_height, label=label)
        self.labels.append(label)       # list: each contains name of client
        self.heights.append(y_height)   # c_idx, t_idx
        self.y_accu += y_height         # t_idx, height for every time

    def add_idle_matrix(self, idle_series: np.ndarray, idx_series: np.ndarray, s_idx: int): # s_idx, t_idx
        plt.subplot(121)
        plt.title('idle situation, number is time index')
        plt.xlabel('bandwidth', labelpad=1.0)
        upper_bw = bandwidth[s_idx]
        idx = np.argsort(-idle_series)
        idle_series = idle_series[idx]
        idx_series = idx_series[idx]
        used_bw = upper_bw - idle_series
        idle_perc = idle_series / upper_bw
        arg = np.argsort(used_bw)
        plt.barh(len(arg), upper_bw, label='bandwidth upper limit', tick_label='upper bandwidth')
        tick_labels = [ f'95%+{i}' for i in range(1, len(arg)+1) ]
        plt.barh(np.arange(len(arg)), used_bw[arg], label='higher than 95%', tick_label=tick_labels)
        for x, y, label, perc in zip(   used_bw[arg], np.arange(len(arg)), 
                                        list(map(lambda x: str(x), idx_series[arg].tolist())), idle_perc):
            if perc > 0.35:
                plt.text(x, y, '   ' + label + f':   {(perc * 100):.2f}% idle', ha='left', va='center')
            else:
                plt.text(x, y, '   ' + label + f':   {(perc * 100):.2f}% idle', ha='right', va='center')
    
    def draw_95_at_left(self, height: int, idx: str):
        plt.barh(-1, height, label='95%', tick_label='95%')
        plt.text(height, -1, str(idx), ha='left', va='center')
        plt.yticks([])
        plt.legend()

    def plot(self, s_idx):
        idx = np.argsort(self.y_accu)
        sep_idx = int(len(idx) * 0.8)
        end_idx = int(math.ceil(len(idx) * 0.95)) 
        time_str = self.time[idx].tolist()
        time_str = [ str(i) for i in time_str]
        upper_bw = bandwidth[s_idx]
        idle = upper_bw - self.y_accu
        idle_perc = idle / upper_bw
        # self.draw_95_at_left(np.array(self.heights).sum(axis=0)[end_idx-1], time_str[end_idx-1])
        plt.subplot(121)
        plt.title('distribution that before 95%, number is time index')
        plt.ylabel('bandwidth', labelpad=0.5)
        for label, height in zip(self.labels, np.array(self.heights)[:, idx]):   # iterate for c_idx and sorted time
            plt.bar(self.time[sep_idx: end_idx], bottom=self.bottom[sep_idx: end_idx], height=height[sep_idx: end_idx], label=label)
            self.bottom += height
        for x, y, label in zip(self.time[sep_idx: end_idx], self.bottom[sep_idx: end_idx], time_str[sep_idx: end_idx]):
            if y / self.bottom[end_idx-1] < 0.95:
                plt.text(x, y, label, ha='center', va='bottom')
            else:
                plt.text(x, y, label, ha='center', va='top')
        plt.legend(loc=2, bbox_to_anchor=(0.97,1.0))
        self.plot_idle(idx, idle_perc, s_idx)
        del self.labels, self.bottom, self.heights, self.time, self.y_accu
    
    def plot_idle(self, idx: np.ndarray, idle_perc: np.ndarray, s_idx):
        plt.subplot(122)
        plt.title('idle situation, number is time index')
        plt.xlabel('bandwidth', labelpad=0)
        my_bottom = np.zeros(len(idx), dtype=np.int64) # sorted
        end_idx = int(math.ceil(len(idx) * 0.95)) 
        for c_name, height in zip(self.labels, np.array(self.heights)[:, idx]):
            plt.barh(self.time[end_idx-1:], height[end_idx-1:], left=my_bottom[end_idx-1:], label=c_name)
            my_bottom += height
        for x, y, t_idx, perc in zip(self.y_accu[idx][end_idx:], self.time[end_idx:], 
                                        idx[end_idx:], idle_perc[idx][end_idx:]):
            if perc > 0.35:
                plt.text(x, y, ' ' + str(t_idx) + f': {(perc * 100):.2f}% idle', ha='left', va='center')
            else:
                plt.text(x, y, ' ' + str(t_idx) + f': {(perc * 100):.2f}% idle', ha='right', va='center')
        if idle_perc[idx][end_idx-1] > 0.35:
            plt.text(self.y_accu[idx][end_idx-1], end_idx-1, str(idx[end_idx-1]) + ': pos at 95% data', ha='left', va='center')
        else:
            plt.text(self.y_accu[idx][end_idx-1], end_idx-1, str(idx[end_idx-1]) + ': pos at 95% data', ha='right', va='center')
        plt.barh(len(idx), bandwidth[s_idx], color='k', alpha=0.5)
        plt.text(bandwidth[s_idx] / 2, len(idx), 'bandwidth upper limit', ha='center', va='center')
        plt.yticks([])
        plt.xticks(rotation=-15) 
        # plt.legend()
    
    def add_client_time_series(self, matrix: np.ndarray, c_idx_list: List[int], s_idx: int):  # time * client  value: bandwidth
        self.time = np.arange(len(matrix))
        self.y_accu = np.zeros(len(matrix), dtype=np.int64)
        self.bottom = np.zeros(len(matrix), dtype=np.int64)
        for i, c_idx in enumerate(c_idx_list):
            c = cname[c_idx]
            value = matrix[:, i]
            self.add(c, value)  # client name, bw in every time for this client
        self.plot(s_idx)
    
    def generate_figure(self):
        id = Plot.id_cnt
        Plot.id_cnt += 1
        strio = StringIO()
        mpld3.save_json(self.fig, strio)
        json_str = strio.getvalue()
        html_content = f'<p>edge server name: {self.s_name}</p>\n<div id="fig{id}"></div>\n'
        js_content = f"j{id} = {json_str}; \n draw('fig{id}', j{id})"
        return html_content, js_content
        

class PlotManager():
    html_template = """
    <h1> Each Server Time Series for Client</h1>
    <p>only show biggest 20%% client connection</p>
    %s

    <script>
    function mpld3_load_lib(url, callback){
    var s = document.createElement('script');
    s.src = url;
    s.async = true;
    s.onreadystatechange = s.onload = callback;
    s.onerror = function(){console.warn("failed to load library " + url);};
    document.getElementsByTagName("head")[0].appendChild(s);
    }

    function draw(id, json){
    if(typeof(mpld3) !== "undefined" && mpld3._mpld3IsLoaded){
        // already loaded: just create the figure
        !function(mpld3){
            mpld3.draw_figure(id, json);
        }(mpld3);
    }else if(typeof define === "function" && define.amd){
        // require.js is available: use it to load d3/mpld3
        require.config({paths: {d3: "https://d3js.org/d3.v5"}});
        require(["d3"], function(d3){
            window.d3 = d3;
            mpld3_load_lib("https://mpld3.github.io/js/mpld3.v0.5.7.js", function(){
                mpld3.draw_figure(id, json);
            });
        });
    }else{
        // require.js not available: dynamically load d3 & mpld3
        mpld3_load_lib("https://d3js.org/d3.v5.js", function(){
                mpld3_load_lib("https://mpld3.github.io/js/mpld3.v0.5.7.js", function(){
                    mpld3.draw_figure(id, json);
                })
                });
    }
    }

    %s
    </script>
    """
    def __init__(self) -> None:
        self.plots: List[Plot] = []
    
    def add_plot(self, plot: Plot):
        self.plots.append(plot)
    
    def show_webpage(self, prev_msg: str=''):
        web_element = prev_msg + '\n'
        js_obj = ''
        for p in self.plots:
            h, j = p.generate_figure()
            web_element += (h + '\n')
            js_obj += (j + '\n')
        mpld3_server(self.html_template % (web_element, js_obj))
    


def err_print(msg, original_line=None):
    print('ERROR  ' * 10)
    print(msg)
    if original_line:
        print(original_line)
    print('ERROR  ' * 10)
    exit(1)

def out_print(msg):
    print('RESULT  ' * 10)
    print(msg)
    print('RESULT  ' * 10)

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


class OutputAnalyser():
    def __init__(self) -> None:
        self._author = getoutput('echo $USER').strip() == 'daniel'
        self.server_history_bandwidth = []
        self.max = len(cname)
        self.curr_time_step = -1
        self.record = np.zeros((len(time_label), len(sname), len(cname)), dtype=np.int32)
        self.reset()
        self.webpage_info_init()

    def reset(self):
        self.client_outputed = [ False for _ in range(len(cname)) ]
        self.server_used_bandwidth = np.zeros(len(sname), dtype=np.int64)
        self.count = 0
        self.curr_time_step += 1
    
    def webpage_info_init(self):
        self.score1 = 0
        self.score2 = 0
        self._fig_id_list = []
        self._fig_json_list = []
    
    def _analyse_server_history_and_plot(self):
        conn_matrix = self.record.sum(axis=0) > 0  # server, client
        for s_idx, one_server_to_client in enumerate(conn_matrix):
            if one_server_to_client.sum() == 0: continue
            plot = ServerSeriesPlot(s_idx)
            # plot.add_idle_matrix(self.idle_matrix[s_idx], self.idle_matrix_t_idx_arr[s_idx], s_idx)
            c_idx_avail_list = []
            for c_idx, client in enumerate(one_server_to_client):
                if client: c_idx_avail_list.append(c_idx)
            plot.add_client_time_series(self.record[:, s_idx, c_idx_avail_list], c_idx_avail_list, s_idx)
            self.plot_manager.add_plot(plot)
    
    def empty_analyse(self):
        pos_96 = np.ceil(len(time_label) * 0.95 ).astype('int32')
        res_t_for_server = self.record.sum(axis=-1).T # s_idx, t_idx
        t_idx_arr_for_server = []
        for t_series in res_t_for_server:
            idxs = np.argpartition(t_series, pos_96)[pos_96:]
            t_idx_arr_for_server.append(idxs)
        idle_matrix = [] # s_idx, t_idx
        for s_idx, t_idx_arr in enumerate(t_idx_arr_for_server):
            used_bw = res_t_for_server[s_idx][t_idx_arr]
            upper_bw = bandwidth[s_idx]
            idle_bw = upper_bw - used_bw
            # idle_perc = idle_bw / upper_bw
            idle_matrix.append(idle_bw)
        idle_matrix = np.array(idle_matrix)
        self.idle_matrix_t_idx_arr = np.array(t_idx_arr_for_server) # s_idx, t_idx
        self.idle_matrix = idle_matrix
        idle_perc = idle_matrix.mean(axis=-1) / upper_bw
        print(f'server mean idle percent at > 95%: \n {idle_perc}')

    def output_result(self):
        self.calc_score_1()
        if self._author:
            self.calc_score_2()
        if self._author:
            score_msg = f'<p>score1: {self.score1}</p> <p>score2: {self.score2}</p>'
        else:
            score_msg = f'<p>score: {self.score1}</p>'
        self.empty_analyse()
        inp = input('generate plot through webpage? y/[n] (default is n):')
        if inp.strip().lower() == 'n' or inp.strip() == '':
            return
        elif inp.strip().lower() == 'y':
            self.plot_manager = PlotManager()
            self._analyse_server_history_and_plot()
            self.plot_manager.show_webpage(score_msg)
            return 
        else:
            print('input error, will not plot figure')


    def dispatch_server(self, c_idx: int, s_idx: int, res: int):
        self.record[self.curr_time_step, s_idx, c_idx] += res
        self.server_used_bandwidth[s_idx] += res
        if self.server_used_bandwidth[s_idx] > bandwidth[s_idx]:
            err_print(  f'bandwidth overflow at server {sname[s_idx]} (index: {s_idx}) \n'\
                        f'{self.count}th line \t time: {time_label[self.curr_time_step]} (index: {self.curr_time_step})',
                        self._curr_read_line)
        if qos[s_idx, c_idx] >= qos_lim:
            err_print(  f'qos larger or equal than qos limit \n'\
                        f'server edge node: {sname[s_idx]} (index: {s_idx}) \t client node: {cname[c_idx]} (index: {c_idx}) \t' \
                        f'{self.count}th line time: {time_label[self.curr_time_step]} (index: {self.curr_time_step})', 
                        self._curr_read_line)
    
    def read_one_line(self, line: str):
        # client node process
        try:
            c, remain = line.strip().split(':')
        except:
            err_print('output format error', line)
        c_idx = cname_map.get(c)
        if c_idx is None:
            err_print(f'not exists client node: {c}', line)
        if self.client_outputed[c_idx]:
            err_print(  f'output format error: the same client node "{c}" appears in the same time \n' \
                        f'or output is not complete in the {self.count}th line time: {time_label[self.count]} \n', line)
        else:
            self.client_outputed[c_idx] = True
            self.count += 1
        # server node process
        if remain.strip() == '':
            if client_demand[self.curr_time_step, c_idx] != 0:
                err_print(f'bandwidth of {cname[c_idx]} is not 0, but did not dispatch edge server')
            self._check_time_step_finished()
            return
        dispatchs = remain[1: -1].split(',')
        if len(dispatchs) == 1:
            err_print('output format error', line)
        if len(dispatchs) == 2:
            s, res = dispatchs
            self._process_server_res(c_idx, s, res, line)
            if int(res) != client_demand[self.curr_time_step, c_idx]:
                err_print(f'bandwidth of {cname[c_idx]} is not satisfied', line)
            self._check_time_step_finished()
            return
        dispatchs = remain[1: -1].split('>,<')
        if len(dispatchs) == 1:
            err_print('output format error', line)
        res_accum = 0
        for d_str in dispatchs:
            s, res = d_str.split(',')
            self._process_server_res(c_idx, s, res, line)
            res_accum += int(res)
        if res_accum != client_demand[self.curr_time_step, c_idx]:
            err_print(f'bandwidth accumulation of {cname[c_idx]} is not satisfied', line)
        self._check_time_step_finished()
    
    def _process_server_res(self, c_idx: int, server_name: str, res_str: str, line: str):
        s_idx = sname_map.get(server_name) # s_idx = sname_map[s]
        if s_idx is None:
            err_print(f'not exists edge node: {server_name}', line)
        try: 
            res = int(res_str)
            if res <= 0:
                err_print(  f'dispatch lower than 0 value at time {time_label[self._curr_line_idx]} (index: {self._curr_line_idx}), '\
                            f'server {server_name} (index: {s_idx}), client {cname[c_idx]} (index: {c_idx})', line)
        except: 
            err_print(f'fail in parsing bandwidth: {res}', line)
        self.dispatch_server(c_idx, s_idx, res)
    
    def _check_time_step_finished(self):
        if self.count == self.max:
            self.server_history_bandwidth.append(self.server_used_bandwidth)
            self.reset()
    
    def read_file(self, output_file_name: str):
        with open(output_file_name) as f:
            lines = f.read().splitlines()
        for l_idx, l in enumerate(lines):
            self._curr_read_line = l
            self._curr_line_idx = l_idx
            self.read_one_line(l)
        if self.curr_time_step != len(time_label):
            err_print('not all time step is printed')
    
    def calc_score_1(self):
        if self.count not in [0, self.max]:
            err_print('output is not complete in the last time step')
        time_cnt = len(time_label)
        idx = math.ceil(time_cnt * 0.95) - 1
        server_history = np.array(self.server_history_bandwidth)
        server_history.sort(axis=0)
        score = server_history[idx].sum()
        # print('largest: \n', server_history[-1], '\n')
        self.score1 = score
        if self._author:
            print(f'final score 1: {score}')
        else:
            print(f'final score: {score}')
        print(f'separate cost: {server_history[idx]}')

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
        self.score2 = score
        print(f'final score 2: {score}')
        print(f'separate cost: {server_history[idx, np.arange(len(idx))]}')

def gauge_time(args):
    start_time = time.time()
    if type(args) is str:
        os.system(args)
    else: 
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
    analyser = OutputAnalyser()
    analyser.read_file(IOFile.output)
    analyser.output_result()

