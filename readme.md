# SLM CLI Agent
## Setup
### backend
```bash
conda create -n slmagent python=3.12
pip install ollama openai dotenv
```

Ollama is used to serve language model `qwen2.5-coder:1.5b`
```bash
# install ollama for your system.
ollama pull qwen2.5-coder:1.5b
ollam serve
```

Each slm can be run individually for testing. Run orchestrator.py to try agent.

start server:
```bash
# extra dependencies
pip install fastapi uvicorn[standard]
```
```bash
uvicorn server:app
```
use flag `--reload` for dev.

### frontend
Front end is implemented with `node.js`, install node.js and npm if you haven't.

```bash
cd ./cli-frontend
npm install
npm link # may require sudo
```

Then, you can run CLI anywhere with command `agent`.

undo linking:
```bash
npm unlink agent
```

## Examples
Successful interactions:
```
> 把当前时间输出到文本文件中
["查看当前时间", "推理出当前时间的字符串形式", "使用print()函数将当前时间写入txt文件"]
1. 查看当前时间
2. 推理出当前时间的字符串形式
3. 使用print()函数将当前时间写入txt文件
是否继续(y/n/r)? y
步骤1: 查看当前时间
['date']
➜ date
Tue Oct 28 07:47:03 PM CST 2025
 
步骤2: 推理出当前时间的字符串形式
2025-10-28T19:47:03+0800
步骤3: 使用print()函数将当前时间写入txt文件
["echo $(date) > current_time.txt"]
➜ echo $(date) > current_time.txt
```

```
> 在./hh中创建fibo.cpp,输出非比纳契数列100项
["执行命令: 在./hh目录下创建fibo.cpp文件", "文件编辑: 在./hh/fibo.cpp文件中写入斐波那契数列生成代码", "执行命令: 使用g++编译./hh/fibo.cpp为./hh/fibo", "执行命令: 运行./hh/fibo输出斐波那契数列前100项"]
1. 执行命令: 在./hh目录下创建fibo.cpp文件
2. 文件编辑: 在./hh/fibo.cpp文件中写入斐波那契数列生成代码
3. 执行命令: 使用g++编译./hh/fibo.cpp为./hh/fibo
4. 执行命令: 运行./hh/fibo输出斐波那契数列前100项
是否继续(y/n/r)? r
["执行命令: 在./hh目录下创建fibo.cpp文件", "综合推理: 推理出生成斐波那契数列前100项的C++代码", "文件编辑: 在./hh/fibo.cpp文件中写入上一步得到的代码", "执行命令: 使用g++编译./hh/fibo.cpp为./hh/fibo", "执行命令: 运行./hh/fibo程序输出斐波那契数列100项"]
1. 执行命令: 在./hh目录下创建fibo.cpp文件
2. 综合推理: 推理出生成斐波那契数列前100项的C++代码
3. 文件编辑: 在./hh/fibo.cpp文件中写入上一步得到的代码
4. 执行命令: 使用g++编译./hh/fibo.cpp为./hh/fibo
5. 执行命令: 运行./hh/fibo程序输出斐波那契数列100项
是否继续(y/n/r)? y
执行命令: 在./hh目录下创建fibo.cpp文件
➜ mkdir -p ./hh && touch ./hh/fibo.cpp 
 
综合推理: 推理出生成斐波那契数列前100项的C++代码
```cpp
#include <iostream>
#include <vector>

int main() {
    std::vector<long long> fib(100);
    fib[0] = 0;
    if (fib.size() > 1) fib[1] = 1;

    for (size_t i = 2; i < fib.size(); ++i) {
        fib[i] = fib[i - 1] + fib[i - 2];
    }

    for (const auto& num : fib) {
        std::cout << num << " ";
    }

    return 0;
}
\```
文件编辑: 在./hh/fibo.cpp文件中写入上一步得到的代码
编辑文件: ./hh/fibo.cpp
文件 ./hh/fibo.cpp 已成功更新。
执行命令: 使用g++编译./hh/fibo.cpp为./hh/fibo
➜ cd ./hh && g++ fibo.cpp -o fibo 
 
执行命令: 运行./hh/fibo程序输出斐波那契数列100项
➜ cd ./hh && g++ fibo.cpp -o fibo && ./fibo 
0 1 1 2 3 5 8 13 21 34 55 89 144 233 377 610 987 1597 2584 4181 6765 10946 17711 28657 46368 75025 121393 196418 317811 514229 832040 1346269 2178309 3524578 5702887 9227465 14930352 24157817 39088169 63245986 102334155 165580141 267914296 433494437 701408733 1134903170 1836311903 2971215073 4807526976 7778742049 12586269025 20365011074 32951280099 53316291173 86267571272 139583862445 225851433717 365435296162 591286729879 956722026041 1548008755920 2504730781961 4052739537881 6557470319842 10610209857723 17167680177565 27777890035288 44945570212853 72723460248141 117669030460994 190392490709135 308061521170129 498454011879264 806515533049393 1304969544928657 2111485077978050 3416454622906707 5527939700884757 8944394323791464 14472334024676221 23416728348467685 37889062373143906 61305790721611591 99194853094755497 160500643816367088 259695496911122585 420196140727489673 679891637638612258 1100087778366101931 1779979416004714189 2880067194370816120 4660046610375530309 7540113804746346429 -6246583658587674878 1293530146158671551 -4953053512429003327 -3659523366270331776 -8612576878699335103 6174643828739884737 -2437933049959450366  
```