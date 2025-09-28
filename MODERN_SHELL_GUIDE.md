# 现代Shell语法系统

## 概述

现代Shell语法系统为nex AI Assistant项目提供了一套全新的命令行交互体验，融合了函数式编程和面向对象特性，使文件系统操作更加直观和强大。

## 特性

- **面向对象的文件/系统操作**：将文件、目录、进程抽象为对象
- **函数式编程支持**：map、filter、reduce等高阶函数
- **管道数据处理**：支持类似Unix管道的数据流处理
- **类型安全**：强类型系统确保操作的正确性
- **智能补全**：与AI助手集成的智能命令补全

## 基本语法

### 变量声明
```shell
let name = "John"
let age = 25
let pi = 3.14159
let active = true
```

### 对象操作

#### 文件对象
```shell
# 创建文件对象
let file = File("data.txt")

# 访问属性
file.name           # 文件名
file.size           # 文件大小
file.modified       # 修改时间
file.exists         # 是否存在

# 调用方法
file.read()         # 读取内容
file.lines()        # 按行读取
file.write("content")  # 写入内容
file.copy("backup.txt")  # 复制文件
```

#### 目录对象
```shell
# 创建目录对象
let dir = Dir("/home/user")

# 访问属性
dir.files           # 文件列表
dir.subdirs         # 子目录列表
dir.exists          # 是否存在

# 调用方法
dir.create()        # 创建目录
dir.find("*.py")    # 查找文件
```

#### 系统对象
```shell
# 系统信息
System.cpu.usage        # CPU使用率
System.memory.free      # 可用内存
System.disk.usage       # 磁盘使用情况

# 进程管理
System.processes()      # 获取进程列表
```

### 函数式编程

#### 高阶函数
```shell
# map - 映射操作
let numbers = [1, 2, 3, 4, 5]
let doubled = numbers.map(x => x * 2)  # [2, 4, 6, 8, 10]

# filter - 过滤操作
let evens = numbers.filter(x => x % 2 == 0)  # [2, 4]

# reduce - 归约操作
let sum = numbers.reduce((a, b) => a + b)  # 15
```

#### 内置函数
```shell
range(10)               # [0, 1, 2, ..., 9]
range(1, 6)            # [1, 2, 3, 4, 5]
sum([1, 2, 3, 4, 5])   # 15
len([1, 2, 3])         # 3
max([3, 1, 4, 1, 5])   # 5
```

### 管道操作
```shell
# 数据管道
[1, 2, 3, 4, 5] 
| map(x => x * 2) 
| filter(x => x > 5)
| sum()  # 18

# 文件处理管道
File("log.txt")
| lines()
| filter(line => line.contains("ERROR"))
| count()
```

## 实用示例

### 文件系统操作

#### 查找大文件
```shell
Dir("/var/log")
  .files
  .filter(f => f.size > 100MB)
  .sort(f => f.size)
  .map(f => (f.name, f.size))
```

#### 统计代码行数
```shell
Files("*.py")
  .map(f => f.lines().count())
  .sum()
```

#### 批量文件处理
```shell
Files("*.txt")
  .forEach(f => {
    let backup = f.name.replace(".txt", ".bak")
    f.copy(backup)
  })
```

### 系统监控

#### 查找高CPU进程
```shell
Processes()
  .filter(p => p.cpu > 80)
  .map(p => (p.name, p.pid, p.cpu))
  .forEach(info => print(f"High CPU: {info}"))
```

#### 磁盘清理
```shell
Dir("/tmp")
  .files
  .filter(f => f.age > 7.days && f.size > 0)
  .forEach(f => f.delete())
```

### 数据分析

#### 日志分析
```shell
File("/var/log/app.log")
  .lines()
  .filter(line => line.contains("ERROR"))
  .map(line => line.split(" ")[0])  # 提取时间戳
  .groupBy(timestamp => timestamp.substring(0, 10))  # 按日期分组
  .map((date, errors) => (date, errors.count()))
```

#### JSON数据处理
```shell
File("data.json")
  .read()
  .JSON.parse()
  .get("users")
  .filter(user => user.age > 18)
  .map(user => user.name)
  .join(", ")
```

## 高级特性

### 函数定义
```shell
fn findLargeFiles(dir: Dir, threshold: Size) -> List<File> {
    return dir.files.filter(f => f.size > threshold)
}

# 使用函数
findLargeFiles(Dir("/var/log"), 10MB)
```

### 条件语句
```shell
if (System.cpu.usage > 90) {
    print("⚠️ CPU使用率过高")
    # 可以在这里执行清理操作
}
```

### 错误处理
```shell
try {
    let content = File("important.txt").read()
    print(content.lines().count())
} catch (error: FileNotFound) {
    print("文件未找到: " + error.filename)
}
```

## 在nex中使用

### 启动现代Shell
```shell
# 在nex CLI中使用现代Shell语法
/msh let x = File("test.txt").size
/msh Files("*.py").map(f => f.lines().count()).sum()
```

### 多行输入
现代Shell支持多行输入模式，适合复杂的脚本：

```shell
/msh fn analyzeProject() {
  let pyFiles = Files("*.py")
  let totalLines = pyFiles.map(f => f.lines().count()).sum()
  let avgSize = pyFiles.map(f => f.size).reduce((a,b) => a+b) / pyFiles.count()
  
  print(f"Python files: {pyFiles.count()}")
  print(f"Total lines: {totalLines}")
  print(f"Average size: {avgSize} bytes")
}
# 输入'end'执行
```

### 获取帮助
```shell
/msh help        # 显示帮助
/msh examples    # 显示示例
```

## 性能特性

- **懒计算**：流处理采用懒计算，节省内存
- **并行处理**：支持并行map和filter操作
- **缓存优化**：文件状态信息自动缓存
- **智能类型推断**：减少不必要的类型转换

## 扩展性

### 自定义对象
```shell
class LogAnalyzer {
    constructor(logDir: Dir) {
        this.logDir = logDir
    }
    
    fn findErrors() -> List<String> {
        return this.logDir.files
            .filter(f => f.ext == "log")
            .flatMap(f => f.lines())
            .filter(line => line.matches(/ERROR|FAIL/))
    }
}
```

### 自定义函数
通过Python API可以注册自定义函数：

```python
from ui.cli.modern_shell.functions import register_function

def custom_hash(text):
    import hashlib
    return hashlib.md5(text.encode()).hexdigest()

register_function("md5", custom_hash)
```

## 与AI助手集成

现代Shell与nex的AI助手深度集成：

- **智能补全**：AI根据上下文提供命令补全建议
- **命令解释**：AI可以解释复杂命令的含义
- **错误修复**：AI可以建议如何修复语法错误
- **最佳实践**：AI提供代码优化建议

## 兼容性

现代Shell与传统shell命令兼容：

```shell
# 可以混合使用
/msh Files("*.py").count()  # 现代Shell语法
/bash ls -la *.py          # 传统shell命令
```

这使得用户可以渐进式地采用新语法，无需完全替换现有工作流程。