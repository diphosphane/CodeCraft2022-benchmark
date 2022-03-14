# CodeCraft2022-benchmark - 华为CodeCraft2022 判题器  
A benchmark for Huawei CodeCraft 2022  
华为CodeCraft2022 判题器

This benchmark requires numpy.   
该判题器需要使用numpy

Usage: 用法
```bash 
python3 benchmark.py ['your_execution_command']
```
e.g. `python3 benchmark.py bin/CodeCraft-2022.exe`
例如，你可以这样使用 `python3 benchmark.py bin/CodeCraft-2022.exe`

The argument is optional.   
参数是可选项。 

You can specify your execution command, if not provided, this benbchmark will automatically execute `sh build_and_run.sh`.  
你可以指定你的执行命令，如果不提供，则将会使用默认的`sh build_and_run.sh`命令用于编译和判题。

Score is only for reference. Because the data we used online and offline is different, I can not sure the truth of this benchmark.  
分数仅供参考。因为线上线下使用的数据不同，因此我无法保证判题器分数的真实性。

This benchmark only tested on macOS, I cannot sure it will work on other system. This benchmark may have many bug, only for test usage.   
该判题器仅在macOS下测试过，我无法保证它能兼容其他系统，可能存在很多bug，仅做测试用途。

