// ============================================
// 玄武·AI 结对编程舱 - JavaScript
// ============================================

// 章节分类定义
const chapters = [
    { id: 'ch1', name: 'Python基础', icon: '🐍', topics: ['变量与数据类型', '运算符', '控制流程'] },
    { id: 'ch2', name: '数据结构', icon: '📦', topics: ['列表List', '字典Dict', '集合Set', '元组Tuple'] },
    { id: 'ch3', name: '函数', icon: '⚙️', topics: ['函数定义', '参数传递', '返回值', '作用域'] },
    { id: 'ch4', name: '面向对象', icon: '🏗️', topics: ['类与对象', '继承', '封装', '多态'] },
    { id: 'ch5', name: '文件与异常', icon: '📁', topics: ['文件读写', '异常处理', '上下文管理器'] },
    { id: 'ch6', name: '模块与包', icon: '📚', topics: ['导入模块', '标准库', '第三方包'] },
    { id: 'ch7', name: '数据结构与算法', icon: '🧮', topics: ['排序算法', '查找算法', '递归', '动态规划'] },
    { id: 'ch8', name: '数据库', icon: '🗄️', topics: ['SQL基础', '数据库连接', 'CRUD操作'] },
];

// 示例代码问题库（每题3+错误，更长的代码）
const codeProblems = [
    // ========== 第一章：Python基础 ==========
    {
        id: 101,
        chapter: 'ch1',
        topic: '变量与数据类型',
        title: '综合变量赋值问题',
        language: 'python',
        difficulty: 'easy',
        code: `"""
用户管理系统 - 变量与数据类型综合练习
这个程序尝试创建一个简单的用户信息管理系统
但存在多个变量相关的错误
"""

# 导入需要的模块
import json

# 定义用户信息
user_name = "张三"
user_age = 25
user_score = 95.5
user_active = True

# 错误1：使用保留字作为变量名
str = "用户字符串"
int = 42
list = [1, 2, 3]

# 打印用户信息
print("用户名称:", user_name)
print("用户年龄:", user_age)

# 错误2：类型混用导致拼接错误
print("用户信息: " + user_name + " 年龄 " + user_age)  # TypeError: cannot concatenate str and int

# 错误3：字符串和数字直接拼接
message = "用户的总分数是" + user_score  # TypeError: unsupported operand type(s) for +: 'str' and 'float'

# 尝试访问保留字命名的变量
print("保留字str:", str)
print("保留字int:", int)
print("保留字list:", list)

# 错误4：未定义的变量
print("用户等级:", user_level)  # NameError: name 'user_level' is not defined

# 错误5：使用了未初始化的变量
result = total + 100  # NameError: name 'total' is not defined

print("程序执行完毕")`,
        errorLine: 24,
        errorType: 'TypeError',
        errorMsg: "cannot concatenate str and int - 字符串和整数不能直接拼接"
    },
    {
        id: 102,
        chapter: 'ch1',
        topic: '控制流程',
        title: '成绩判定与流程控制综合问题',
        language: 'python',
        difficulty: 'medium',
        code: `"""
学生成绩管理系统
根据学生分数计算等级和统计信息
存在多个流程控制相关的错误
"""

def calculate_grade(score):
    """根据分数计算等级"""
    if score >= 90:
        grade = "A"
    elif score >= 80:
        grade = "B"
    elif score >= 70:
        grade = "C"
    elif score >= 60:
        grade = "D"
    # 错误1：缺少 else 分支处理不及格情况
    # 当 score < 60 时，grade 变量不会被赋值
    return grade

def validate_score(score):
    """验证分数是否合法"""
    if score < 0:
        raise ValueError("分数不能为负数")
    if score > 100:
        raise ValueError("分数不能超过100")
    return True

def process_student_data():
    """处理学生数据"""
    students = [
        {"name": "小明", "score": 85},
        {"name": "小红", "score": 92},
        {"name": "小李", "score": 45},
        {"name": "小王", "score": 78},
        {"name": "小张", "score": 55},
    ]

    results = []
    for student in students:
        name = student["name"]
        score = student["score"]

        # 错误2：缩进错误 - if 块未正确缩进
        try:
        validate_score(score)
        except ValueError as e:
            print(f"数据验证失败: {e}")
            continue

        # 错误3：在循环中修改变量但未正确更新
        grade = calculate_grade(score)
        if score < 60:
            status = "不及格"
        # 错误4：缺少完整的条件分支

        results.append({
            "name": name,
            "score": score,
            "grade": grade
        })

    return results

def print_statistics(results):
    """打印统计信息"""
    total_students = len(results)
    total_score = sum(student["score"] for student in results)
    average = total_score / total_students

    print(f"学生总数: {total_students}")
    print(f"平均分: {average}")

    # 错误5：尝试访问可能不存在的键
    excellent_count = len([s for s in results if s["grade"] == "A"])
    print(f"优秀人数: {excellent_count}")

    # 错误6：使用了未定义的变量
    print(f"最高分学生: {top_student}")  # NameError

# 主程序
if __name__ == "__main__":
    results = process_student_data()

    for result in results:
        print(f"{result['name']}: 分数={result['score']}, 等级={result['grade']}")

    print_statistics(results)`,
        errorLine: 24,
        errorType: 'IndentationError',
        errorMsg: "expected an indented block - if 语句需要正确缩进"
    },
    {
        id: 103,
        chapter: 'ch1',
        topic: '运算符',
        title: '运算符综合应用错误',
        language: 'python',
        difficulty: 'easy',
        code: `"""
计算器程序 - 运算符练习
实现基本的数学运算
存在多个运算符使用错误
"""

def basic_calculator(a, b, operation):
    """简单的计算器函数"""
    result = 0

    if operation == "add":
        result = a + b
    elif operation == "subtract":
        result = a - b
    elif operation == "multiply":
        result = a * b
    elif operation == "divide":
        if b != 0:
            result = a / b
        else:
            print("错误：除数不能为零")

    # 错误1：赋值运算符使用错误
    if operation == "power":
        result = a ^ 2  # ^ 是位运算符，不是幂运算符！应该用 **

    # 错误2：比较运算符写成赋值
    if operation == "mod":
        result = a = b % a  # 应该是 a % b，不是 a = b % a

    # 错误3：逻辑运算符使用错误
    if operation == "check":
        # 错误地使用 and 作为变量赋值
        result = a and b  # 这不是比较，而是短路求值
        # 正确应该是 a == b 来比较是否相等

    # 错误4：混淆 // 和 /
    if operation == "floor_div":
        result = a // b  # 地板除
        # 如果需要精确除法，应该用 /

    return result

def complex_calculation(x, y, z):
    """复杂的数学计算"""
    # 错误5：运算符优先级错误
    result = x + y * z  # 先算乘法，应该加括号 (x + y) * z
    # 或者明确写成 x + (y * z)

    # 错误6：位运算误用
    result2 = x & y  # 位与，不是逻辑与
    result3 = x | z  # 位或，不是逻辑或

    # 错误7：增量赋值写成赋值
    counter = 0
    counter = counter + 1  # 正确
    # 错误写法：counter += counter  # 这会让counter翻倍

    return result, result2, result3

def comparison_test():
    """比较运算测试"""
    a = 10
    b = 20
    c = 10

    # 错误8：== 和 = 混淆
    if a = b:  # SyntaxError: 不能用赋值运算符做比较
        print("a等于b")

    # 错误9：is 比较用于数值
    if a is 10:  # is 用于比较对象身份，不是值
        print("a是10")

    # 错误10：链式比较省略运算符
    if a < b > c:  # 这会被解析为 (a < b) and (b > c)
        print("成立")

    return True

# 测试代码
if __name__ == "__main__":
    print("=== 基本计算器测试 ===")
    print(f"加法: {basic_calculator(10, 5, 'add')}")
    print(f"幂运算(错误): {basic_calculator(3, 2, 'power')}")

    print("\\n=== 复杂计算测试 ===")
    complex_calculation(2, 3, 4)

    print("\\n=== 比较测试 ===")
    comparison_test()`,
        errorLine: 34,
        errorType: 'SyntaxError',
        errorMsg: "cannot assign to expression - 不能用赋值运算符进行比较"
    },
    {
        id: 104,
        chapter: 'ch1',
        topic: '控制流程',
        title: '循环与条件综合问题',
        language: 'python',
        difficulty: 'medium',
        code: `"""
数据处理程序 - 循环与条件综合练习
处理一批销售数据，找出异常值
存在多个循环和条件判断错误
"""

def process_sales_data(sales_records):
    """处理销售记录"""
    results = []
    total = 0
    count = 0

    for record in sales_records:
        # 提取数据
        product = record["product"]
        price = record["price"]
        quantity = record["quantity"]

        # 错误1：在循环中修改列表导致迭代问题
        if price < 0:
            sales_records.remove(record)  # 不应在遍历时修改列表

        # 计算小计
        subtotal = price * quantity

        # 错误2：条件判断逻辑错误
        if price > 0 and quantity > 0
            total += subtotal
            count += 1

        # 错误3：elif 和 if 混用导致逻辑错误
        if subtotal > 1000:
            discount = 0.1
        elif subtotal > 500:
            discount = 0.05
        elif subtotal > 100:
            discount = 0.02
        # 错误：缺少 else 分支处理小金额

        results.append({
            "product": product,
            "subtotal": subtotal,
            "discount": discount if 'discount' in locals() else 0
        })

    return results, total, count

def find_anomalies(data):
    """查找异常数据"""
    values = [d["subtotal"] for d in data]

    # 错误4：使用未初始化的变量
    for i in range(len(values)):
        if values[i] > threshold:  # NameError: name 'threshold' is not defined
            print(f"发现异常值: {values[i]}")

    # 错误5：循环变量作用域问题
    for i in range(10):
        pass
    print(i)  # 能访问到最后的 i 值，但逻辑上可能不是预期的

    # 错误6：while 循环条件写错
    index = 0
    while index < len(values) {
        print(values[index])
        index += 1
    # 错误：缺少闭合大括号，且条件可能导致无限循环

def validate_data(data):
    """验证数据完整性"""
    required_fields = ["product", "price", "quantity"]

    for record in data:
        # 错误7：遍历字典键时的逻辑错误
        for field in required_fields:
            if field not in record:
                # 没有正确处理缺失字段的情况
                pass

        # 错误8：条件判断使用 or 而不是 and
        if "price" not in record or "quantity" not in record:
            print("数据不完整")
            continue

        # 错误9：数值比较使用字符串方法
        if record.price > 0:  # 应该用 record["price"]，不能用 record.price
            print(f"有效数据: {record}")

def main():
    """主函数"""
    sales_data = [
        {"product": "苹果", "price": 5, "quantity": 100},
        {"product": "香蕉", "price": 3, "quantity": 50},
        {"product": "橙子", "price": -10, "quantity": 30},  # 异常价格
        {"product": "葡萄", "price": 15, "quantity": 20},
        {"product": "西瓜", "price": 8, "quantity": 0},    # 异常数量
    ]

    results, total, count = process_sales_data(sales_data)
    print(f"总销售额: {total}, 商品种类: {count}")

    find_anomalies(results)
    validate_data(results)

if __name__ == "__main__":
    main()`,
        errorLine: 28,
        errorType: 'SyntaxError',
        errorMsg: "expected ':' - if 语句条件后需要冒号"
    },
    {
        id: 105,
        chapter: 'ch1',
        topic: '数据类型转换',
        title: '数据类型转换综合问题',
        language: 'python',
        difficulty: 'medium',
        code: `"""
数据转换程序 - 类型转换练习
处理用户输入的各种数据并进行转换
存在多个类型转换相关错误
"""

def process_user_input():
    """处理用户输入数据"""
    # 模拟用户输入
    user_inputs = ["123", "45.67", "hello", "True", "None", "100"]

    results = []

    for input_str in user_inputs:
        # 错误1：直接将字符串转为数字而不检查
        num = int(input_str)  # ValueError: invalid literal for int()
        results.append(num)

    return results

def format_output():
    """格式化输出各种类型"""
    numbers = [1, 2, 3, 4, 5]
    text = "hello"
    flag = True
    value = None

    # 错误2：字符串和数字拼接
    output = "数字: " + numbers  # TypeError: can only concatenate str to list
    output2 = "文本: " + text + " 数量: " + len(numbers)  # TypeError: cannot concatenate str and int

    # 错误3：布尔值和字符串混用
    output3 = "是否启用: " + flag  # TypeError: can only concatenate str to bool

    # 错误4：None 值参与运算
    output4 = "值: " + value  # TypeError: can only concatenate str to NoneType

    # 错误5：列表和元组混淆
    mixed = list((1, 2, 3))  # 应该用 tuple() 转换
    mixed2 = tuple([1, 2, 3])  # 这个是对的

    # 错误6：字典键类型错误
    data = {
        "name": "张三",
        123: "数字键",  # 字典键可以是数字，但可能导致类型混淆
        ["list"]:"列表键"  # TypeError: unhashable type: 'list' - 列表不能作为字典键
    }

def convert_data():
    """数据类型转换函数"""
    # 错误7：float 转 int 丢失精度
    original = 3.141592653589793
    converted = int(original)  # 结果是 3，丢失了小数部分

    # 错误8：字符串转列表
    s = "hello"
    lst = list(s)  # ['h', 'e', 'l', 'l', 'o'] - 这个是对的
    # 但如果想要 ['hello'] 应该用 [s]

    # 错误9：dict 转字符串
    d = {"a": 1, "b": 2}
    s = str(d)  # "{'a': 1, 'b': 2}" - 这是字符串，不是字典

    # 错误10：eval 安全性问题（这里只是演示，应该避免使用）
    user_input = "1 + 2 * 3"
    result = eval(user_input)  # 返回 7，但 eval 是危险的

    # 错误11：json.loads 需要字符串，不是字典
    data_dict = {"name": "test"}
    # json_str = json.loads(data_dict)  # TypeError: expected str, bytes or os.PathLike object

    return converted

def type_checking():
    """类型检查"""
    value = "123"

    # 错误12：isinstance 使用不当
    if isinstance(value, str):
        # 错误：应该用 int() 转换，不是 str()
        num = str(value)  # 已经是字符串了，这没有意义
        print(f"转换后的值: {num}")

    # 错误13：类型注解使用错误
    def process(x: int, y: int) -> int:
        return x + y

    result = process("1", "2")  # 类型注解只是提示，不会强制检查
    # 返回 "12" 而不是 3

    return result

if __name__ == "__main__":
    print("=== 处理输入 ===")
    try:
        results = process_user_input()
        print(results)
    except ValueError as e:
        print(f"转换错误: {e}")

    print("\\n=== 格式化输出 ===")
    format_output()

    print("\\n=== 类型转换 ===")
    convert_data()`,
        errorLine: 18,
        errorType: 'ValueError',
        errorMsg: "invalid literal for int() with base 10: 'hello' - 无法将非数字字符串转换为整数"
    },
    // ========== 第二章：数据结构 ==========
    {
        id: 201,
        chapter: 'ch2',
        topic: '列表List',
        title: '列表操作综合问题',
        language: 'python',
        difficulty: 'medium',
        code: `"""
任务管理器 - 列表操作综合练习
管理待办事项列表，支持添加、删除、排序等操作
存在多个列表操作相关错误
"""

def task_manager():
    """任务管理器主函数"""
    tasks = []
    completed = []

    # 初始任务列表
    tasks = ["完成报告", "发送邮件", "开会讨论", "整理文件"]

    # 错误1：索引越界
    first_task = tasks[10]  # IndexError: list index out of range
    print(f"第一个任务: {first_task}")

    # 错误2：在遍历列表时修改列表
    for task in tasks:
        if "邮件" in task:
            tasks.remove(task)  # 可能导致跳过某些元素

    # 错误3：列表切片使用错误
    remaining = tasks[10:20]  # 不会报错，但返回空列表或部分元素
    # 正确做法是先检查长度

    # 错误4：使用 + 连接列表和字符串
    all_items = tasks + " | "  # TypeError: can only concatenate list to list
    # 正确应该用 " | ".join(tasks)

    # 错误5：pop 操作不检查空列表
    while len(tasks) > 0:
        task = tasks.pop()  # 最后元素
    # 如果列表为空会抛出 IndexError

    # 重新填充任务
    tasks = ["完成报告", "发送邮件", "开会讨论", "整理文件", "回复消息"]

    # 错误6：排序函数使用错误
    tasks.sort(key=len, reverse)  # 缺少括号，应该是 reverse=False
    # 或者 tasks.sort(key=len, reverse=True)

    # 错误7：复制列表引用而不是副本
    tasks_backup = tasks  # 这里是引用，不是副本
    tasks.clear()  # 这会清空 tasks_backup！

    # 错误8：insert 位置错误
    tasks = ["a", "b", "c"]
    tasks.insert(10, "d")  # 不会报错，但插入到错误的位置

    # 错误9：extend 和 append 混淆
    list1 = [1, 2, 3]
    list1.append([4, 5])  # 结果是 [1, 2, 3, [4, 5]]，不是 [1, 2, 3, 4, 5]
    # 应该用 list1.extend([4, 5])

    # 错误10：count 参数错误
    list2 = [1, 2, 2, 3, 2, 4, 2]
    two_count = list2.count()  # TypeError: count expected 1 argument

    return tasks

def process_data():
    """数据处理函数"""
    data = [10, 20, 30, 40, 50]

    # 错误11：索引使用负数错误
    last = data[-1]  # 这是正确的
    second_last = data[-2]  # 也是正确的
    # 但如果列表为空会报错

    # 错误12：列表推导式语法错误
    squares = [x**2 for x in range(10) if x % 2 == 0]  # 这个是对的
    # 但如果写成 [x**2 for x in range(10) if x % 2 == 0 if x > 5] 可能逻辑错误

    # 错误13：enumerate 使用不当
    for i, item in data:
        print(f"{i}: {item}")  # 错误：enumerate 需要两个变量
    # 正确是 for i, item in enumerate(data):

    # 错误14：zip 不等长列表
    list1 = [1, 2, 3, 4, 5]
    list2 = ['a', 'b', 'c']
    zipped = zip(list1, list2)  # 只会保留最短的长度
    # 结果是 [(1, 'a'), (2, 'b'), (3, 'c')]

    # 错误15：解包赋值数量不匹配
    a, b, c = [1, 2]  # ValueError: not enough values to unpack

def main():
    """主函数"""
    result = task_manager()
    print(f"最终任务列表: {result}")

    process_data()

if __name__ == "__main__":
    main()`,
        errorLine: 16,
        errorType: 'IndexError',
        errorMsg: "list index out of range - 列表索引超出范围"
    },
    {
        id: 202,
        chapter: 'ch2',
        topic: '字典Dict',
        title: '字典操作综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
配置管理系统 - 字典操作综合练习
管理系统配置信息，支持读写、更新等操作
存在多个字典操作相关错误
"""

def config_manager():
    """配置管理器"""
    config = {
        "database": {
            "host": "localhost",
            "port": 3306,
            "name": "myapp"
        },
        "cache": {
            "enabled": True,
            "ttl": 3600
        },
        "logging": {
            "level": "INFO",
            "file": "app.log"
        }
    }

    # 错误1：访问不存在的键
    debug_mode = config["debug"]  # KeyError: 'debug'
    # 应该用 config.get("debug", False)

    # 错误2：直接修改嵌套字典
    config["database"]["port"] = 3307  # 这个本身没问题
    # 但如果 config["database"] 不存在会报错

    # 错误3：setdefault 使用不当
    config.setdefault("debug", False)  # 正确用法
    # 但如果写成 config["debug"].setdefault(...) 而 debug 不是字典会报错

    # 错误4：键类型错误
    config[123] = "数字键"  # 可以，但不推荐
    config[["list", "key"]] = "列表键"  # TypeError: unhashable type: 'list'

    # 错误5：更新字典覆盖问题
    defaults = {"theme": "light", "language": "zh"}
    user_prefs = {"theme": "dark"}
    config.update(user_prefs)  # 这会更新，但可能会丢失 defaults 中的其他键
    # 正确应该用 {**defaults, **user_prefs}

    return config

def process_user_data():
    """处理用户数据"""
    users = [
        {"id": 1, "name": "张三", "age": 25},
        {"id": 2, "name": "李四", "age": 30},
        {"id": 3, "name": "王五", "age": 28}
    ]

    # 错误6：字典列表查找错误
    user_dict = {u["id"]: u for u in users}  # 正确
    target_id = 5
    target = user_dict[target_id]  # KeyError: 5 不存在
    # 应该用 user_dict.get(target_id) 或先检查

    # 错误7：字典键不存在时创建
    stats = {}
    for user in users:
        stats[user["name"]]["count"] += 1  # KeyError: '张三' 键不存在
    # 正确应该先初始化或用 defaultdict

    # 错误8：del 删除不存在的键
    if "temp" in stats:
        del stats["temp"]  # 可能 key 不存在
    # 或者 del stats["nonexistent"]  # KeyError

    # 错误9：字典合并使用 + 运算符
    dict1 = {"a": 1, "b": 2}
    dict2 = {"c": 3, "d": 4}
    merged = dict1 + dict2  # TypeError: unsupported operand type(s) for +: 'dict' and 'dict'
    # 应该用 {**dict1, **dict2} 或 dict1 | dict2

    # 错误10：values() 和 keys() 使用错误
    keys = config.keys()
    values = config.values()
    # 如果直接遍历 keys() 并修改 dict 会出问题

def nested_dict_access():
    """嵌套字典访问"""
    data = {
        "level1": {
            "level2": {
                "level3": {
                    "value": 100
                }
            }
        }
    }

    # 错误11：多层访问不检查中间层
    deep_value = data["level1"]["level2"]["level3"]["value"]  # 可能中间键不存在
    # 正确应该逐层检查或用 get

    # 错误12：setdefault 嵌套使用
    data.setdefault("level1", {}).setdefault("level2", {})["level3"] = "new"
    # 如果 level1 已存在但不是字典会报错

    # 错误13：copy 和 deepcopy 混淆
    import copy
    nested = {"a": {"b": [1, 2, 3]}}
    shallow = nested.copy()  # 浅拷贝
    deep = copy.deepcopy(nested)  # 深拷贝
    # 修改 shallow["a"]["b"] 会影响 nested

def main():
    """主函数"""
    config = config_manager()
    print(f"配置: {config}")

    process_user_data()

if __name__ == "__main__":
    main()`,
        errorLine: 18,
        errorType: 'KeyError',
        errorMsg: "'debug' - 字典中不存在该键"
    },
    {
        id: 203,
        chapter: 'ch2',
        topic: '集合Set',
        title: '集合操作综合问题',
        language: 'python',
        difficulty: 'medium',
        code: `"""
标签系统 - 集合操作练习
管理文章标签，支持添加、删除、交集、并集等操作
存在多个集合操作相关错误
"""

def tag_manager():
    """标签管理器"""
    # 初始标签
    tech_tags = {"Python", "Java", "Go", "Rust"}
    backend_tags = {"Java", "Go", "Node.js", "C#"}

    # 错误1：尝试用 + 合并集合
    all_tags = tech_tags + backend_tags  # TypeError: unsupported operand type(s) for +: 'set' and 'set'
    # 应该用 tech_tags | backend_tags

    # 错误2：尝试用索引访问集合元素
    first_tag = tech_tags[0]  # TypeError: 'set' object is not subscriptable
    # 集合是无序的，不能用索引

    # 错误3：尝试用 extend 添加多个元素
    tech_tags.extend(["Ruby", "Swift"])  # AttributeError: 'set' object has no attribute 'extend'
    # 应该用 update 方法

    # 错误4：集合运算结果没有赋值
    common = tech_tags.intersection(backend_tags)
    # 错误：直接写 tech_tags.intersection(backend_tags) 不会修改原集合
    # 应该用 tech_tags &= backend_tags 或重新赋值

    # 错误5：difference 和 symmetric_difference 混淆
    only_tech = tech_tags.difference(backend_tags)  # tech 有 backend 没有的
    # 如果想要互相都没有的，应该用 symmetric_difference

    # 错误6：isdisjoint 判断错误
    if tech_tags.isdisjoint(backend_tags):  # False，因为有交集
        print("没有交集")
    else:
        print("有交集")

    return tech_tags

def process_tags():
    """处理标签数据"""
    # 错误7：集合中添加可变对象
    tag_groups = [
        {"name": "编程语言", "tags": {"Python", "Java"}},
        {"name": "框架", "tags": {"Django", "Spring"}},
    ]
    # tag_groups[0]["tags"].add(["Flask"])  # TypeError: unhashable type: 'list'

    # 错误8：集合推导式语法错误
    squares = {x**2 for x in "hello"}  # 正确，但结果是 {64, 1, 36, 100, 97}
    # 如果想要保留每个字符，应该用其他方式

    # 错误9：frozenset 和 set 混淆
    mutable_set = {1, 2, 3}
    mutable_set.add(4)  # 正确
    # frozen = frozenset({1, 2, 3})
    # frozen.add(4)  # AttributeError: 'frozenset' object has no attribute 'add'

    # 错误10：集合比较操作符误用
    a = {1, 2, 3}
    b = {2, 3, 4}
    # a < b  # 判断是否为真子集，这里是 False
    # a < {1, 2, 3}  # False，{1,2,3} 不是 {1,2,3} 的真子集

    # 错误11：in 操作符在嵌套集合中使用
    nested = {{1, 2}, {3, 4}}  # TypeError: unhashable type: 'set'
    # 集合不能包含集合，因为集合必须是可哈希的

def set_operations_demo():
    """集合运算演示"""
    set1 = {1, 2, 3, 4, 5}
    set2 = {4, 5, 6, 7, 8}

    # 错误12：运算符优先级错误
    result = set1 | set2 & set1  # 等于 set1 | (set2 & set1)，而不是 (set1 | set2) & set1
    # 正确应该用括号明确

    # 错误13：update 和 union 混淆
    set1.update({6, 7})  # 修改原集合
    # set1.union({6, 7})  # 返回新集合，原集合不变

    # 错误14：pop 行为不确定
    s = {1, 2, 3}
    elem = s.pop()  # 随机删除并返回一个元素，但顺序不确定
    # 在某些场景下可能导致问题

    # 错误15：clear 清空后继续使用
    temp_set = {1, 2, 3}
    temp_set.clear()
    if 1 in temp_set:  # False
        print("存在")  # 不会执行

def main():
    """主函数"""
    result = tag_manager()
    print(f"技术标签: {result}")

    process_tags()
    set_operations_demo()

if __name__ == "__main__":
    main()`,
        errorLine: 14,
        errorType: 'TypeError',
        errorMsg: "unsupported operand type(s) for +: 'set' and 'set' - 集合不支持 + 运算符合并，应该用 | 或 union()"
    },
    {
        id: 204,
        chapter: 'ch2',
        topic: '元组Tuple',
        title: '元组操作综合问题',
        language: 'python',
        difficulty: 'medium',
        code: `"""
数据记录系统 - 元组操作练习
使用元组存储固定格式的记录数据
存在多个元组操作相关错误
"""

def record_system():
    """记录系统"""
    # 错误1：尝试修改元组元素
    point = (10, 20)
    point[0] = 15  # TypeError: 'tuple' object does not support item assignment

    # 错误2：元组包含可变对象可修改
    nested = (1, 2, [3, 4, 5])
    nested[2].append(6)  # 不会报错，但可能导致意外行为
    # nested 变成 (1, 2, [3, 4, 5, 6])

    # 错误3：混淆列表和元组的创建方式
    list1 = [1, 2, 3]  # 列表
    tuple1 = (1, 2, 3)  # 元组
    # 如果只有一个元素
    single_list = [42]  # 列表
    single_tuple = (42,)  # 元组，必须有逗号

    # 错误4：元组解包数量不匹配
    coordinates = (100, 200, 300)
    x, y = coordinates  # ValueError: too many values to unpack

    # 错误5：元组不支持 append 等操作
    data = (1, 2, 3)
    data.append(4)  # AttributeError: 'tuple' object has no attribute 'append'
    # 元组是不可变的

    # 错误6：namedtuple 定义和使用错误
    from collections import namedtuple
    Point = namedtuple('Point', ['x', 'y'])
    p = Point(10, 20)
    # 访问方式
    print(p.x, p.y)  # 正确
    # print(p[0], p[1])  # 也可以，但索引容易出错

    return nested

def process_records():
    """处理记录数据"""
    # 错误7：元组作为字典键时的误用
    cache = {}
    key1 = (1, 2, 3)
    key2 = [1, 2, 3]  # 列表不能作为字典键
    # cache[key2] = "value"  # TypeError: unhashable type: 'list'

    # 错误8：元组比较时的行为
    t1 = (1, 2, 3)
    t2 = (1, 3, 2)
    # t1 < t2  # True，因为从第一个元素开始比较，2 < 3

    t3 = (1, 2, 100)
    t4 = (1, 2, 99)
    # t3 > t4  # True，因为前两个相等，100 > 99

    # 错误9：元组切片赋值
    t = (1, 2, 3, 4, 5)
    # t[1:3] = (10, 20)  # TypeError: 'tuple' object does not support item assignment

    # 错误10：函数返回元组时误用
    def get_stats():
        return [10, 20, 30]  # 返回列表

    result = get_stats()
    # if result[0] > result[1] > result[2]:  # 链式比较
    #     print("递减")

def tuple_packing():
    """元组打包"""
    # 正确用法
    person = "张三", 25, "北京"  # 隐式打包

    # 错误11：tuple 函数参数误用
    s = "hello"
    # tuple(s)  # ('h', 'e', 'l', 'l', 'o') - 正确
    # tuple(123)  # TypeError: cannot convert to tuple

    # 错误12：元组相乘操作误解
    t = (1, 2)
    t2 = t * 3  # (1, 2, 1, 2, 1, 2) - 重复，不是乘法
    # 如果想要数值乘积应该先转型

    # 错误13：交换变量使用元组
    a = 10
    b = 20
    # 正确方式
    a, b = b, a  # 交换
    # 错误方式
    # a = b  # 先赋值会丢失 a 的值
    # b = a  # 再赋值没有意义

def main():
    """主函数"""
    result = record_system()
    print(f"记录: {result}")

    process_records()
    tuple_packing()

if __name__ == "__main__":
    main()`,
        errorLine: 10,
        errorType: 'TypeError',
        errorMsg: "'tuple' object does not support item assignment - 元组是不可变的，不能直接修改元素"
    },
    // ========== 第三章：函数 ==========
    {
        id: 301,
        chapter: 'ch3',
        topic: '函数定义',
        title: '函数定义综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
计算器模块 - 函数定义综合练习
实现各种数学计算函数
存在多个函数定义相关错误
"""

# 错误1：默认参数使用可变对象
def add_item_to_list(item, items_list=[]):  # 危险！默认参数在定义时只求值一次
    items_list.append(item)
    return items_list

result1 = add_item_to_list("apple")
result2 = add_item_to_list("banana")
# result1 和 result2 都是 ['apple', 'banana']，因为共享同一个列表！

# 错误2：参数顺序错误
def create_user(name, age, is_active=True):
    return {"name": name, "age": age, "active": is_active}

user = create_user(age=25, "小明")  # SyntaxError: positional argument follows keyword argument

# 错误3：缺少 return 语句
def calculate_sum(numbers):
    total = sum(numbers)
    # 没有 return 语句，默认返回 None

# 错误4：return 语句位置错误
def find_max(numbers):
    for n in numbers:
        if n > 0:
            return n  # 提前返回
    # 如果没有正数，函数结束没有 return，也返回 None

# 错误5：函数名使用保留字
# def import():  # SyntaxError: invalid syntax
#     pass

# 错误6：函数内部定义函数参数错误
def outer():
    def inner(x, y):
        return x + y
    # 错误：inner 函数定义后立即调用
    result = inner(1, 2, 3)  # TypeError: inner() takes 2 positional arguments but 3 were given

def process_data():
    """处理数据的函数"""
    # 错误7：lambda 函数赋值给可变对象
    # f = lambda x: x ** 2
    # f[0] = 10  # TypeError: 'function' object does not support item assignment

    # 错误8：递归深度问题
    def factorial(n):
        if n <= 1:
            return 1
        return n * factorial(n)  # 错误！应该是 factorial(n-1)

    # 错误9：函数默认返回值问题
    def check_positive(numbers):
        for n in numbers:
            if n < 0:
                return False
        # 没有 return True，所以返回 None

    # 错误10：类型注解使用错误
    def add(a: int, b: int) -> int:
        return a + b

    result = add("1", "2")  # 类型注解不会强制检查，会返回 "12"

def validate_input():
    """验证输入参数"""
    # 错误11：缺少参数验证
    def divide(a, b):
        return a / b  # 如果 b 是 0 会抛出 ZeroDivisionError

    # 错误12：*args 和 **kwargs 使用错误
    def func(*args, *kwargs):  # SyntaxError: cannot use bare *args with *
        pass
    # 正确是 func(*args, **kwargs)

    # 错误13：函数参数解包错误
    def greet(greeting, name):
        return f"{greeting}, {name}!"

    args = ["Hello"]  # 只有一个参数
    # greet(*args)  # TypeError: greet() missing 1 required positional argument

def main():
    """主函数"""
    # 测试默认参数问题
    print(add_item_to_list("first"))
    print(add_item_to_list("second"))  # 会显示共享问题

    # 测试用户创建
    # user = create_user("小明", age=25)  # 这会报错

    print("程序执行完毕")

if __name__ == "__main__":
    main()`,
        errorLine: 15,
        errorType: 'TypeError',
        errorMsg: "positional argument follows keyword argument - 位置参数不能跟在关键字参数后面"
    },
    {
        id: 302,
        chapter: 'ch3',
        topic: '作用域',
        title: '作用域与闭包综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
数据分析模块 - 作用域与闭包练习
实现数据分析函数，涉及变量作用域问题
存在多个作用域相关错误
"""

# 错误1：在函数内修改全局变量
total = 0

def add_to_total(value):
    total = total + value  # UnboundLocalError: local variable 'total' referenced before assignment
    # 正确应该用 global total 声明

def counter():
    """计数器函数"""
    count = 0

    def increment():
        count += 1  # UnboundLocalError: local variable 'count' referenced before assignment
        # count 是 increment 的局部变量，但 += 相当于 count = count + 1
        # Python 认为这是对局部变量的赋值，所以报错了
        return count

    return increment

# 错误2：闭包中的晚期绑定
def create_multipliers():
    multipliers = []
    for i in range(5):
        def multiplier(x):
            return x * i  # 所有函数都引用同一个 i
        multipliers.append(multiplier)
    return multipliers

# 调用时会发现所有乘数都乘以 4（i 的最终值）

# 错误3：全局变量与局部变量同名
value = 100

def process():
    value = 200  # 这创建了新的局部变量，不会修改全局变量
    print(f"局部 value: {value}")

# 错误4：nonlocal 声明位置错误
def outer():
    x = 10

    def inner():
        nonlocal y  # SyntaxError: no binding for nonlocal 'y'
        y = 20

    inner()
    # print(y)  # y 不在 outer 的作用域内

# 错误5：循环中的函数引用循环变量
funcs = []
for j in range(3):
    def f():
        return j  # 所有函数都返回 2（j 的最终值）
    funcs.append(f)

# 错误6：类属性与局部变量混淆
class Calculator:
    result = 0

    def add(self, value):
        result = result + value  # UnboundLocalError: 局部 result 未初始化
        # 正确应该用 self.result

def scope_demo():
    """作用域演示"""
    x = 10

    def inner():
        # 错误7：在内部函数中引用外部不存在的变量
        # y = x + z  # NameError: name 'z' is not defined
        pass

    # 错误8：在循环后引用循环变量
    for i in range(3):
        pass
    # print(i)  # 能访问到 i=2，但逻辑上可能不是预期的

def closure_issue():
    """闭包问题"""
    # 错误9：错误地使用闭包
    def make_printer(msg):
        def printer():
            print(msg)  # 正确，msg 是外层函数的局部变量
        return printer

    # 错误10：闭包修改外部变量
    def outer2():
        count = 0

        def inner2():
            count = count + 1  # 错误，应该用 nonlocal
            return count

        return inner2

def main():
    """主函数"""
    # 测试作用域问题
    print(f"全局 total: {total}")
    # add_to_total(10)  # 会报错

    # 测试闭包
    funcs = create_multipliers()
    # for f in funcs:
    #     print(f(2))  # 会打印 4, 4, 4, 4, 4

    print("程序执行完毕")

if __name__ == "__main__":
    main()`,
        errorLine: 8,
        errorType: 'UnboundLocalError',
        errorMsg: "local variable 'total' referenced before assignment - 在赋值前引用了局部变量，需要先用 global 声明"
    },
    {
        id: 303,
        chapter: 'ch3',
        topic: '返回值',
        title: '返回值与异常处理综合问题',
        language: 'python',
        difficulty: 'medium',
        code: `"""
数据处理模块 - 返回值与异常处理练习
处理各种数据并返回结果
存在多个返回值和异常处理相关错误
"""

# 错误1：函数缺少返回值
def find_element(items, target):
    """查找元素位置"""
    for i, item in enumerate(items):
        if item == target:
            return i
    # 没有 return，所以返回 None

result = find_element([1, 2, 3, 4, 5], 3)
if result:  # 如果找不到会进入这个分支，因为 result 是 None
    print(f"找到，位置: {result}")
else:
    print("没找到")  # 这不会打印，因为 enumerate 从 0 开始，result=2 是真值

# 错误2：多个 return 语句路径
def process_value(value):
    if value > 0:
        return "正数"
    elif value < 0:
        return "负数"
    # 缺少 return None 分支，如果传入 0 会返回 None

# 错误3：try-except 中丢失异常信息
def divide(a, b):
    try:
        return a / b
    except:
        pass  # 错误：捕获所有异常但什么都不做，丢失了错误信息

# 错误4：except 顺序错误
def handle_errors():
    try:
        result = int("abc")
    except Exception as e:
        print(f"Exception: {e}")
    except ValueError as e:  # 这个永远不会执行，因为已经被 Exception 捕获了
        print(f"ValueError: {e}")

# 错误5：裸 except 子句
def bare_except():
    try:
        x = 1 / 0
    except:  # 捕获所有异常，包括 KeyboardInterrupt, SystemExit 等
        print("出错了")

# 错误6：finally 中的 return 覆盖异常
def finally_return():
    try:
        raise ValueError("错误")
    except:
        return "caught"
    finally:
        return "finally"  # 这个会覆盖 except 中的 return

# 错误7：异常处理后继续执行
def continue_after_error():
    try:
        result = 10 / 0
    except ZeroDivisionError:
        print("除数为零")
    # 错误：没有重新抛出异常，程序可能继续执行产生错误结果
    print(f"结果: {result}")  # result 未定义

def validate_data():
    """数据验证"""
    # 错误8：验证函数返回值检查不当
    def validate_age(age):
        if age < 0:
            raise ValueError("年龄不能为负")
        return True

    # if validate_age(-5):  # 会抛出异常而不是返回 False
    #     print("有效")

    # 错误9：finally 块中的异常
    def finally_exception():
        try:
            return 1
        finally:
            raise Exception("finally 中的异常")  # 这个会覆盖原来的返回值

def main():
    """主函数"""
    # 测试返回值
    result = find_element([1, 2, 3], 10)
    print(f"查找结果: {result}")

    # 测试异常处理
    divide(10, 0)

    print("程序执行完毕")

if __name__ == "__main__":
    main()`,
        errorLine: 20,
        errorType: 'NoneType',
        errorMsg: "returned None instead of a value when element not found"
    },
    {
        id: 304,
        chapter: 'ch3',
        topic: '参数传递',
        title: '参数传递与返回值综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
排序模块 - 参数传递练习
实现各种排序算法
存在多个参数传递相关错误
"""

# 错误1：默认参数使用可变对象
def add_to_history(item, history=[]):  # 危险！
    history.append(item)
    return history

# 错误2：修改传入的可变参数
def remove_duplicates(items):
    """错误：直接修改原列表"""
    unique = list(set(items))  # 创建新列表
    items.clear()  # 清空原列表
    items.extend(unique)  # 这会修改传入的原始列表

original = [1, 2, 2, 3, 3, 4]
# remove_duplicates(original)  # original 被修改了

# 错误3：函数返回局部变量
def create_list():
    """错误：返回局部列表的引用"""
    result = []
    return result  # 正确，但如果是 [] 直接返回可能有可变默认参数问题

# 错误4：参数解包错误
def greet(greeting, name):
    return f"{greeting}, {name}!"

args = ["Hello"]  # 只有一个参数
# greet(*args)  # TypeError: missing 1 required argument

# 错误5：关键字参数与位置参数混用错误
# greet(greeting="Hi", "World")  # SyntaxError: positional argument follows keyword argument

# 错误6：参数类型注解不会强制转换
def add(a: int, b: int) -> int:
    return a + b

# result = add("1", "2")  # 返回 "12" 而不是 3

# 错误7：*args 和 **kwargs 使用不当
def log_message(*args, **kwargs):
    print(args, kwargs)

# log_message("msg", "extra", key="value")  # 正确
# log_message(*["msg", "extra"], **{"key": "value"})  # 正确

def bubble_sort(items):
    """冒泡排序"""
    n = len(items)
    for i in range(n):
        for j in range(0, n - i - 1):
            if items[j] > items[j + 1]:
                # 交换
                items[j], items[j + 1] = items[j + 1], items[j]  # 这个修改了原列表

    return items

# 错误8：返回值与修改混淆
def sort_copy(items):
    """返回排序副本"""
    sorted_items = items.copy()
    sorted_items.sort()  # 正确：修改副本，不影响原列表
    return sorted_items

# 错误9：key 参数使用错误
def custom_sort():
    data = [("apple", 3), ("banana", 1), ("cherry", 2)]
    # 按数量排序
    data.sort(key=lambda x: x[1])  # 正确
    # 如果写成 data.sort(lambda x: x[1])  # 错误：缺少 key=

def main():
    """主函数"""
    # 测试默认参数问题
    h1 = add_to_history("first")
    h2 = add_to_history("second")
    # print(h1, h2)  # 会显示共享问题

    # 测试排序
    numbers = [64, 34, 25, 12, 22, 11, 90]
    # bubble_sort(numbers)  # 会修改原列表

    print("程序执行完毕")

if __name__ == "__main__":
    main()`,
        errorLine: 19,
        errorType: 'TypeError',
        errorMsg: "missing 1 required positional argument - 参数解包后参数数量不匹配"
    },
    // ========== 第四章：面向对象 ==========
    {
        id: 401,
        chapter: 'ch4',
        topic: '类与对象',
        title: '类定义与对象创建综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
学生管理系统 - 类与对象练习
实现学生和课程管理类
存在多个类定义相关错误
"""

class Student:
    """学生类"""

    # 错误1：类属性与实例属性混淆
    school_name = "清华大学"  # 类属性

    def __init__(self, name, age, student_id):
        self.name = name
        self.age = age
        self.student_id = student_id
        self.courses = []

    def add_course(self, course):
        """添加选课"""
        self.courses.append(course)

    def get_info(self):
        """获取学生信息"""
        return f"{self.name}, {self.age}, {self.student_id}"

    # 错误2：实例方法中访问类属性未使用 self
    def print_school(self):
        print(f"学校: {school_name}")  # NameError: name 'school_name' is not defined

    # 错误3：类方法与实例方法混淆
    @classmethod
    def create_default(cls):
        """创建默认学生"""
        return cls("默认学生", 0, "000000")  # 正确

    @staticmethod
    def validate_id(id):
        """验证学号"""
        if len(id) != 6:
            return False
        return id.isdigit()

def student_manager():
    """学生管理器"""
    # 错误4：创建对象参数不匹配
    s1 = Student("张三", 25)  # TypeError: __init__() missing 1 required positional argument: 'student_id'

    # 错误5：类属性与实例属性访问混淆
    s2 = Student("李四", 20, "123456")
    print(f"学生姓名: {s2.name}")  # 实例属性
    print(f"学校名称: {s2.school_name}")  # 类属性
    # 如果修改
    s2.school_name = "北京大学"  # 这会创建实例属性，不会修改类属性
    # Student.school_name 仍然是 "清华大学"

    # 错误6：私有属性访问
    class PrivateStudent:
        def __init__(self, name):
            self.__name = name  # 私有属性

        def get_name(self):
            return self.__name

    ps = PrivateStudent("王五")
    # print(ps.__name)  # AttributeError: 'PrivateStudent' object has no attribute '__name'
    print(ps.get_name())  # 正确方式

    # 错误7：类方法与静态方法调用
    Student.create_default()  # 类方法调用，OK
    # Student.get_info()  # 实例方法不能这样直接调用，需要实例化

def class_relationships():
    """类之间的关系"""
    # 错误8：继承与组合混淆
    class Course:
        def __init__(self, name):
            self.name = name

    class StudentWithCourse:
        def __init__(self, name):
            self.name = name
            self.course = Course(name)  # 组合
            # 如果 Course 需要更多初始化信息，这里会很复杂

    # 错误9：类变量共享问题
    class Counter:
        count = 0  # 类变量

        def __init__(self):
            self.count += 1  # 这会创建实例变量，不会影响类变量

    c1 = Counter()
    c2 = Counter()
    # print(f"Counter.count = {Counter.count}")  # 0
    # print(f"c1.count = {c1.count}, c2.count = {c2.count}")  # 1, 1

def main():
    """主函数"""
    s = Student("小明", 18, "123456")
    print(s.get_info())

    student_manager()

if __name__ == "__main__":
    main()`,
        errorLine: 31,
        errorType: 'NameError',
        errorMsg: "name 'school_name' is not defined - 在实例方法中访问类属性需要用 self.school_name 或 self.__class__.school_name"
    },
    {
        id: 402,
        chapter: 'ch4',
        topic: '继承',
        title: '继承与多态综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
图形系统 - 继承练习
实现各种图形类，展示继承关系
存在多个继承相关错误
"""

class Shape:
    """图形基类"""

    def __init__(self, color="black"):
        self.color = color

    def area(self):
        raise NotImplementedError("子类必须实现 area 方法")

    def perimeter(self):
        raise NotImplementedError("子类必须实现 perimeter 方法")

class Rectangle(Shape):
    """矩形类"""

    def __init__(self, width, height, color="black"):
        super().__init__(color)  # 调用父类构造方法
        self.width = width
        self.height = height

    def area(self):
        return self.width * self.height

    def perimeter(self):
        return 2 * (self.width + self.height)

class Square(Rectangle):
    """正方形类"""
    # 错误1：方法签名不匹配父类
    def __init__(self, side, color="black"):
        super().__init__(side, side, color)  # 正确
        # 如果写成 super().__init__(side, color) 会出错

    def set_size(self, size):
        """设置边长"""
        self.width = size
        self.height = size

class Circle(Shape):
    """圆形类"""

    def __init__(self, radius, color="black"):
        super().__init__(color)
        self.radius = radius

    def area(self):
        return 3.14 * self.radius ** 2

    # 错误2：子类添加了父类没有的方法参数
    def calculate_volume(self, height):  # 这是新方法，不算重写
        return self.area() * height

def polymorphism_demo():
    """多态演示"""
    shapes = [
        Rectangle(5, 3),
        Square(4),
        Circle(2)
    ]

    # 错误3：类型检查不当
    for shape in shapes:
        # 错误方式
        if isinstance(shape, Rectangle) and not isinstance(shape, Square):
            print(f"矩形面积: {shape.area()}")
        # 正确方式：直接调用多态方法
        print(f"面积: {shape.area()}")

    # 错误4：强制类型转换
    rect = Rectangle(4, 5)
    # square = rect  # 这只是引用赋值，不是类型转换
    # square.side  # AttributeError

def inheritance_issues():
    """继承问题"""
    # 错误5：菱形继承问题
    class A:
        def hello(self):
            print("A")

    class B(A):
        def hello(self):
            print("B")

    class C(A):
        def hello(self):
            print("C")

    class D(B, C):
        pass

    d = D()
    d.hello()  # 打印 B，因为 MRO 的顺序是 D -> B -> C -> A

    # 错误6：super() 调用顺序错误
    class Base:
        def __init__(self):
            print("Base init")

    class Child(Base):
        def __init__(self):
            super().__init__()  # 正确
            print("Child init")

    # 错误7：父类方法参数不匹配
    class Parent:
        def greet(self, name):
            return f"Hello, {name}"

    class Child2(Parent):
        def greet(self):  # 缺少 name 参数
            return f"Hi"

def main():
    """主函数"""
    r = Rectangle(5, 3)
    print(f"矩形面积: {r.area()}")

    s = Square(4)
    print(f"正方形面积: {s.area()}")

    polymorphism_demo()

if __name__ == "__main__":
    main()`,
        errorLine: 54,
        errorType: 'AttributeError',
        errorMsg: "'Rectangle' object has no attribute 'side' - 不能直接访问父类不存在的属性"
    },
    // ========== 第五章：文件与异常 ==========
    {
        id: 501,
        chapter: 'ch5',
        topic: '文件读写',
        title: '文件操作综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
日志系统 - 文件操作练习
实现日志写入和读取功能
存在多个文件操作相关错误
"""

import json

def write_log():
    """写入日志"""
    # 错误1：文件路径问题
    # with open("log.txt", "w") as f:  # 使用相对路径，可能不在预期位置
    #     f.write("Log entry")

    # 错误2：未指定编码
    # with open("data.txt", "w") as f:
    #     f.write("中文内容")  # 在 Windows 上可能出错

    # 错误3：文件写入后未关闭
    f = open("temp.txt", "w")
    f.write("temp data")
    # 如果这里发生异常，文件不会关闭

    # 错误4：写入模式覆盖
    # with open("config.json", "w") as f:
    #     f.write("new content")  # 会清空原有内容

    # 错误5：二进制模式误用
    # with open("text.txt", "wb") as f:  # 二进制模式不能写字符串
    #     f.write("text")

def read_log():
    """读取日志"""
    # 错误6：读取不存在的文件
    # with open("nonexistent.txt", "r") as f:  # FileNotFoundError
    #     content = f.read()

    # 错误7：编码问题
    # with open("data.txt", "r") as f:  # 可能没有指定编码
    #     content = f.read()

    # 错误8：文件读取模式错误
    # with open("text.txt", "w") as f:  # 写模式不能读
    #     content = f.read()

    # 错误9：读取后未检查内容
    with open("temp.txt", "r") as f:
        content = f.read()
        # 错误：没有检查 content 是否为空

    # 错误10：json.load 需要文件对象
    with open("temp.json", "w") as f:
        json.dump({"key": "value"}, f)

    with open("temp.json", "r") as f:
        # data = json.loads(f)  # TypeError: the JSON object must be str, not 'TextIOWrapper'
        data = json.load(f)  # 正确：load 接受文件对象

def file_operations():
    """文件操作函数"""
    # 错误11：同时读写未正确处理位置
    with open("data.txt", "r+") as f:
        content = f.read()  # 读取后位置在文件末尾
        f.write("more data")  # 写在末尾
        # 如果想从开头覆盖，需要 seek(0)

    # 错误12：read/readline/readlines 混淆
    with open("temp.txt", "r") as f:
        # content = f.read()  # 读取全部
        # line = f.readline()  # 读取一行
        # lines = f.readlines()  # 读取所有行到列表
        pass

    # 错误13：文件指针位置错误
    with open("temp.txt", "r") as f:
        f.seek(10)  # 跳到第10个字节
        content = f.read()  # 从第10个字节开始读

def context_manager():
    """上下文管理器"""
    # 错误14：未使用 with 语句
    f = open("temp.txt", "r")
    try:
        data = f.read()
    finally:
        f.close()  # 应该用 with 语句更安全

    # 错误15：try-except 中打开文件失败
    try:
        with open("missing.txt", "r") as f:
            data = f.read()
    except FileNotFoundError:
        print("文件不存在")
        # 没有处理其他可能的异常

def main():
    """主函数"""
    write_log()
    read_log()
    print("程序执行完毕")

if __name__ == "__main__":
    main()`,
        errorLine: 28,
        errorType: 'FileNotFoundError',
        errorMsg: "[Errno 2] No such file or directory: 'temp.txt' - 文件不存在"
    },
    {
        id: 502,
        chapter: 'ch5',
        topic: '异常处理',
        title: '异常处理综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
数据验证模块 - 异常处理练习
实现数据验证和错误处理
存在多个异常处理相关错误
"""

def validate_input():
    """验证输入"""
    user_input = "abc"

    # 错误1：裸 except 捕获所有异常
    try:
        number = int(user_input)
    except:  # 捕获所有异常，太宽泛
        print("转换失败")

    # 错误2：异常类型顺序错误
    try:
        result = 10 / 0
    except Exception as e:
        print(f"Exception: {e}")
    except ZeroDivisionError:  # 永远不会执行，因为已经被 Exception 捕获
        print("除数为零")

    # 错误3：捕获异常后未处理
    try:
        data = {"key": "value"}
        value = data["missing_key"]
    except KeyError:
        pass  # 静默忽略错误，可能导致后续问题

    # 错误4：异常信息丢失
    try:
        x = 1 / 0
    except:
        # 没有记录异常信息
        print("出错了")  # 不知道具体什么错误

    # 错误5：except 表达式错误
    try:
        pass
    except Exception as:  # SyntaxError: invalid syntax
        pass

def process_data():
    """处理数据"""
    # 错误6：finally 中的 return 覆盖异常
    try:
        raise ValueError("错误")
    except:
        return "caught"
    finally:
        return "finally"  # 这个 return 会覆盖 except 的 return

    # 错误7：嵌套 try-except 问题
    try:
        try:
            x = 1 / 0
        except ZeroDivisionError:
            # 处理内部异常
            raise ValueError("内部错误")  # 重新抛出异常
    except ValueError as e:
        print(f"外部捕获: {e}")

def raise_exceptions():
    """异常抛出"""
    # 错误8：异常类定义错误
    # class MyException(Exception
    #     pass

    # 错误9：raise 不带参数在非异常块中
    try:
        raise ValueError("error")
    except ValueError:
        # 在 except 块外使用 raise
        pass
    # raise  # SyntaxError: No active exception to re-raise

    # 错误10：异常链丢失
    try:
        x = int("abc")
    except ValueError:
        # 丢失了原始异常信息
        raise RuntimeError("新的错误")  # 没有使用 from

def exception_hierarchy():
    """异常层次"""
    # 错误11：混淆异常类与实例
    try:
        raise ValueError  # 正确：抛出类
    except ValueError as e:
        print(e)

    # 错误12：自定义异常继承错误
    # class MyError(Exception):  # 应该继承适当的异常类
    #     pass

    # 错误13：异常捕获过于具体
    try:
        x = 1 / 0
    except FloatingPointError:  # 实际上浮点运算不抛这个异常
        pass

def main():
    """主函数"""
    validate_input()
    print("程序执行完毕")

if __name__ == "__main__":
    main()`,
        errorLine: 24,
        errorType: 'TypeError',
        errorMsg: "catching classes that don't inherit from BaseException - 异常类必须继承自 BaseException"
    },
    // ========== 第六章：模块与包 ==========
    {
        id: 601,
        chapter: 'ch6',
        topic: '导入模块',
        title: '模块导入综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
配置管理模块 - 模块导入练习
导入和使用各种模块
存在多个模块导入相关错误
"""

# 错误1：循环导入
# module_a.py 中 from module_b import func_b
# module_b.py 中 from module_a import func_a
# 这会导致 ImportError

# 错误2：导入不存在的模块
# import non_existent_module  # ModuleNotFoundError

# 错误3：导入模块成员拼写错误
import json
# data = json.dump({"a": 1})  # AttributeError: 'dump' is for writing, should use 'dumps'
# 应该用 json.dumps()

# 错误4：from ... import 拼写错误
# from json import loadd  # ImportError: cannot import name 'loadd'

# 错误5：导入顺序问题
# 应该先导入标准库，再导入第三方库，最后导入本地模块

def module_usage():
    """模块使用"""
    # 错误6：模块成员访问错误
    import os
    # os.pwd()  # AttributeError: 'module' object has no attribute 'pwd'
    # 应该是 os.getcwd()

    # 错误7：相对导入在主模块中使用
    # from . import module  # SyntaxError: attempted relative import with no known parent package

    # 错误8：导入后未使用
    import math
    # import datetime  # 导入了但没使用

    # 错误9：别名使用错误
    import json as json_data
    # data = json.loads('{}')  # NameError: name 'json' is not defined
    data = json_data.loads('{}')  # 正确

def import_variants():
    """导入变体"""
    # 错误10：* 导入污染命名空间
    # from os import *  # 导入了所有，可能覆盖内置函数

    # 错误11：同时导入和使用问题
    # import os, sys, json
    # sys.exit()  # OK
    # os.getcwd()  # OK
    # json.loads('{}')  # OK

    # 错误12：导入的模块被修改
    import os
    # os.name = "posix"  # 不应该修改导入的模块

def module_attributes():
    """模块属性"""
    import math

    # 错误13：__all__ 列表使用错误
    # 如果模块定义了 __all__，则 from module import * 只导入列出的名称

    # 错误14：模块路径问题
    # import sys
    # sys.path.append("/path/to/module")  # 添加搜索路径
    # 但这种方式是临时的

def main():
    """主函数"""
    module_usage()
    import_variants()
    print("程序执行完毕")

if __name__ == "__main__":
    main()`,
        errorLine: 26,
        errorType: 'AttributeError',
        errorMsg: "'module' object has no attribute 'pwd' - os 模块没有 pwd 属性，应该是 getcwd()"
    },
    // ========== 第七章：数据结构与算法 ==========
    {
        id: 701,
        chapter: 'ch7',
        topic: '排序算法',
        title: '排序算法综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
排序算法实现 - 综合练习
实现各种排序算法
存在多个算法实现错误
"""

def bubble_sort(arr):
    """冒泡排序"""
    n = len(arr)
    for i in range(n):
        swapped = False
        for j in range(0, n - i - 1):
            if arr[j] > arr[j + 1]:
                # 交换
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
                swapped = True
        # 错误1：没有提前结束优化
        if not swapped:  # 这个是对的，但如果漏写就会多做无用比较
            break
    return arr

def quick_sort(arr):
    """快速排序"""
    if len(arr) <= 1:
        return arr

    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]

    # 错误2：递归忘记返回
    # return quick_sort(left) + middle + quick_sort(right)
    # 如果没有 return，结果是 None

    # 错误3：基准值选择不当
    # 如果数组已经有序，选取第一个或最后一个元素会导致最坏情况

    return quick_sort(left) + middle + quick_sort(right)

def merge_sort(arr):
    """归并排序"""
    if len(arr) <= 1:
        return arr

    mid = len(arr) // 2
    left = merge_sort(arr[:mid])
    right = merge_sort(arr[mid:])

    # 合并两个有序数组
    result = []
    i = j = 0
    while i < len(left) and j < len(right):
        if left[i] <= right[j]:
            result.append(left[i])
            i += 1
        else:
            result.append(right[j])
            j += 1

    # 错误4：遗漏剩余元素
    result.extend(left[i:])
    result.extend(right[j:])  # 这个是对的

    # 错误5：如果遗漏这行，就会丢失部分元素
    # result.extend(right[j:])  # 如果被注释掉会出错

    return result

def insertion_sort(arr):
    """插入排序"""
    for i in range(1, len(arr)):
        key = arr[i]
        j = i - 1
        # 将元素向右移动
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j -= 1
        arr[j + 1] = key
    return arr

def selection_sort(arr):
    """选择排序"""
    n = len(arr)
    for i in range(n):
        # 错误6：找最小值索引
        min_idx = i
        for j in range(i + 1, n):
            if arr[j] < arr[min_idx]:
                min_idx = j
        # 交换
        arr[i], arr[min_idx] = arr[min_idx], arr[i]
    return arr

def heap_sort(arr):
    """堆排序"""
    n = len(arr)

    # 构建最大堆
    for i in range(n // 2 - 1, -1, -1):
        # 错误7：堆化函数不完整
        pass  # 缺少 heapify 实现

    # 逐个提取元素
    for i in range(n - 1, 0, -1):
        arr[0], arr[i] = arr[i], arr[0]  # 交换
        # 错误8：没有对新的根节点进行堆化

def test_sorting():
    """测试排序"""
    test_cases = [
        [64, 34, 25, 12, 22, 11, 90],
        [5, 4, 3, 2, 1],
        [1, 2, 3, 4, 5],
        [],
        [1],
    ]

    for arr in test_cases:
        original = arr.copy()
        # result = bubble_sort(arr.copy())
        # result = quick_sort(arr.copy())
        # result = merge_sort(arr.copy())
        # print(f"{original} -> {result}")

def main():
    """主函数"""
    test_sorting()
    print("排序算法测试完成")

if __name__ == "__main__":
    main()`,
        errorLine: 39,
        errorType: 'RecursionError',
        errorMsg: "maximum recursion depth exceeded - 递归调用没有返回，导致无限递归"
    },
    {
        id: 702,
        chapter: 'ch7',
        topic: '递归',
        title: '递归算法综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
递归算法实现 - 综合练习
实现各种递归算法
存在多个递归相关错误
"""

def fibonacci(n):
    """计算斐波那契数列"""
    if n <= 1:
        return n
    # 错误1：没有使用记忆化，导致大量重复计算
    return fibonacci(n - 1) + fibonacci(n - 2)

def factorial(n):
    """计算阶乘"""
    if n <= 1:
        return 1
    # 错误2：没有终止条件检查
    # 如果 n 是负数会无限递归
    return n * factorial(n - 1)

def sum_listRecursive(lst):
    """递归求和"""
    if len(lst) == 0:
        return 0
    # 错误3：递归调用位置错误
    return sum_listRecursive(lst) + lst[0]  # 应该传 lst[1:]

def binary_search_recursive(arr, target, low, high):
    """二分查找递归版"""
    if low > high:
        return -1

    mid = (low + high) // 2

    # 错误4：条件判断不完整
    if arr[mid] == target:
        return mid
    elif arr[mid] < target:
        # 错误5：递归调用参数错误
        return binary_search_recursive(arr, target, mid, high)  # 应该是 mid + 1
    else:
        return binary_search_recursive(arr, target, low, mid - 1)

def power(base, exp):
    """计算幂"""
    # 错误6：递归终止条件错误
    if exp == 0:
        return 1
    # 如果 exp 是负数，会无限递归
    return base * power(base, exp - 1)

def reverse_string(s):
    """反转字符串"""
    if len(s) <= 1:
        return s
    # 错误7：切片位置错误
    return reverse_string(s[1:]) + s[0]  # 正确

def is_palindrome(s):
    """判断回文"""
    if len(s) <= 1:
        return True

    # 错误8：递归比较不完整
    if s[0] != s[-1]:
        return False
    # 缺少对中间部分的递归检查
    return is_palindrome(s[1:-1])  # 这个是对的

def tree_sum(root):
    """二叉树求和"""
    if root is None:
        return 0
    # 错误9：递归返回结果未合并
    tree_sum(root.left)  # 没有接收返回值
    tree_sum(root.right)  # 没有接收返回值
    return root.val  # 缺少左右子树的和

def count_stairs(n):
    """爬楼梯问题"""
    if n <= 2:
        return n
    # 错误10：状态转移方程错误
    return count_stairs(n - 1) + count_stairs(n - 2) + count_stairs(n - 3)
    # 爬楼梯每次只能走1步或2步，应该是 + count_stairs(n-2)
    # 只有走到第3步时才能一次走3步

def test_recursion():
    """测试递归"""
    # 测试斐波那契
    # for i in range(10):
    #     print(f"F({i}) = {fibonacci(i)}")  # 会很慢，没有记忆化

    # 测试二分查找
    arr = [1, 3, 5, 7, 9, 11, 13]
    # result = binary_search_recursive(arr, 7, 0, len(arr) - 1)
    # print(f"Found at index: {result}")

    print("递归测试完成")

def main():
    """主函数"""
    test_recursion()

if __name__ == "__main__":
    main()`,
        errorLine: 12,
        errorType: 'RecursionError',
        errorMsg: "maximum recursion depth exceeded - 斐波那契递归没有记忆化，导致指数级时间复杂度"
    },
    // ========== 第八章：数据库 ==========
    {
        id: 801,
        chapter: 'ch8',
        topic: 'SQL基础',
        title: 'SQL操作综合问题',
        language: 'python',
        difficulty: 'hard',
        code: `"""
数据库操作模块 - 综合练习
实现数据库 CRUD 操作
存在多个数据库操作相关错误
"""

import sqlite3

def create_table():
    """创建表"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()

    # 错误1：SQL 语法错误
    # cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT, age INTEGER)")  # 正确
    # 常见错误：字段定义缺少逗号、拼写错误等

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            name TEXT,
            age INTEGER,
            email TEXT
        )
    """)

    # 错误2：提交事务
    conn.commit()  # 需要提交
    conn.close()

def insert_data():
    """插入数据"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()

    # 错误3：SQL 注入漏洞
    name = "张三"
    age = 25
    # 错误写法：用 f-string 拼接 SQL
    # sql = f"INSERT INTO users (name, age) VALUES ('{name}', {age})"
    # 如果 name = "'; DROP TABLE users; --" 就会造成严重问题

    # 正确写法：使用参数化查询
    sql = "INSERT INTO users (name, age) VALUES (?, ?)"
    cursor.execute(sql, (name, age))

    # 错误4：忘记提交事务
    # cursor.execute("INSERT INTO users (name, age) VALUES ('李四', 30)")
    # conn.commit()  # 如果注释掉，数据不会真正写入

    conn.commit()
    conn.close()

def query_data():
    """查询数据"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()

    # 错误5：查询所有列但不处理结果
    cursor.execute("SELECT * FROM users")
    # rows = cursor.fetchall()  # 忘记 fetchall

    # 错误6：fetchone 和 fetchall 混淆
    cursor.execute("SELECT * FROM users")
    # row = cursor.fetchone()  # 只获取一条
    # rows = cursor.fetchall()  # 获取所有

    # 错误7：SQL WHERE 子句错误
    # cursor.execute("SELECT * FROM users WHERE id = '1'")  # 字符串引号问题
    cursor.execute("SELECT * FROM users WHERE id = ?", (1,))  # 正确

    # 错误8：LIKE 查询语法错误
    cursor.execute("SELECT * FROM users WHERE name LIKE '%张%'")  # 正确
    # 如果写成 WHERE name LIKE '张%' 就会漏掉中间的情况

    conn.close()

def update_data():
    """更新数据"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()

    # 错误9：UPDATE 缺少 WHERE
    # cursor.execute("UPDATE users SET age = 30")  # 会更新所有记录！

    # 正确写法
    cursor.execute("UPDATE users SET age = ? WHERE id = ?", (30, 1))

    # 错误10：DELETE 缺少 WHERE
    # cursor.execute("DELETE FROM users")  # 会删除所有记录！

    # 正确写法
    cursor.execute("DELETE FROM users WHERE id = ?", (1,))

    conn.commit()
    conn.close()

def transaction_demo():
    """事务演示"""
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()

    # 错误11：事务回滚不正确
    try:
        cursor.execute("INSERT INTO users (name, age) VALUES ('王五', 35)")
        cursor.execute("INSERT INTO users (name, age) VALUES ('赵六', 40)")
        # 错误：如果第二个失败，第一个也不会回滚
        conn.commit()
    except:
        # 回滚放在 except 中是正确的
        conn.rollback()

    conn.close()

def connection_management():
    """连接管理"""
    # 错误12：连接未关闭
    conn = sqlite3.connect('test.db')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users")
    # 如果函数在这里结束，连接可能不会正确关闭
    # 应该用 with 语句或 try-finally

    # 错误13：多次打开连接
    conn1 = sqlite3.connect('test.db')
    conn2 = sqlite3.connect('test.db')
    # 两个连接可能看到不同的数据状态

    conn1.close()
    conn2.close()

def main():
    """主函数"""
    create_table()
    insert_data()
    query_data()
    update_data()
    print("数据库操作完成")

if __name__ == "__main__":
    main()`,
        errorLine: 54,
        errorType: 'sqlite3.OperationalError',
        errorMsg: "no such table: users - 表不存在，可能是创建表时出错或未正确提交"
    },
];

// 学情状态管理
let learningState = {
    currentChapter: 'ch1',
    completedTopics: {},
    problemHistory: [],
    correctCount: 0,
    wrongCount: 0,
    masteryLevel: {},
};

// 难度等级配置
const difficultyConfig = {
    easy: { color: 'green', label: '简单', icon: '⭐' },
    medium: { color: 'yellow', label: '中等', icon: '⭐⭐' },
    hard: { color: 'red', label: '困难', icon: '⭐⭐⭐' }
};

// 全局状态
let state = {
    currentProblem: null,
    currentCode: '',
    messages: [],
    isTyping: false,
    isAIThinking: false,
    cpuUsage: 12,
    tokenCount: 0,
    sessionId: null,
    studentId: 'anonymous',
    courseId: 'bigdata',
    contextId: null,
    interactionCount: 0,
    socraticPassRate: 0.0,
    userAvatar: null
};

// DOM 缓存
let domCache = {};

// ============================================
// 初始化
// ============================================
function initDOMCache() {
    domCache = {
        modal: document.getElementById('ide-modal'),
        editorContent: document.getElementById('editor-content'),
        messageContainer: document.getElementById('message-container'),
        diffContainer: document.getElementById('diff-container'),
        submitInput: document.getElementById('submit-input'),
        sendBtn: document.getElementById('send-btn'),
        terminalCpu: document.getElementById('terminal-cpu'),
        terminalToken: document.getElementById('terminal-token'),
        problemSelect: document.getElementById('problem-select'),
        statusBadge: document.getElementById('status-badge'),
        codeInput: document.getElementById('code-input'),
        errorCount: document.getElementById('error-count'),
        titleDisplay: document.getElementById('problem-title'),
        chapterSelect: document.getElementById('chapter-select'),
        chapterName: document.getElementById('chapter-name'),
        progressBar: document.getElementById('progress-bar'),
        progressText: document.getElementById('progress-text'),
        statsCorrect: document.getElementById('stats-correct'),
        statsWrong: document.getElementById('stats-wrong'),
        masteryDisplay: document.getElementById('mastery-display'),
        topicSelect: document.getElementById('topic-select'),
        codeEditor: document.getElementById('code-editor'),
        codeLoading: document.getElementById('code-loading'),
        loadingProgress: document.getElementById('loading-progress'),
        reviewBtn: document.getElementById('review-btn')
    };
}

function init() {
    initDOMCache();
    loadLearningState();
    renderChapterSelect();
    updateStats();
    updateMasteryDisplay();
    initEventListeners();
    initKeyboardShortcuts();
    startTokenSimulation();
    initSession();
    // 默认调用 AI 生成个性化题目
    initAIPoweredStart();
    loadUserAvatar();
}

// ============================================
// 学情状态管理
// ============================================
function loadLearningState() {
    try {
        const saved = localStorage.getItem('starlearn_coding_state');
        if (saved) {
            learningState = { ...learningState, ...JSON.parse(saved) };
        }
    } catch (e) {
        console.log('学情状态加载失败，使用默认状态');
    }
}

function saveLearningState() {
    try {
        localStorage.setItem('starlearn_coding_state', JSON.stringify(learningState));
    } catch (e) {
        console.log('学情状态保存失败');
    }
}

function updateLearningState(problemId, isCorrect) {
    const problem = codeProblems.find(p => p.id === problemId);
    if (!problem) return;

    if (isCorrect) {
        learningState.correctCount++;
    } else {
        learningState.wrongCount++;
    }

    learningState.problemHistory.push({
        problemId,
        chapter: problem.chapter,
        topic: problem.topic,
        isCorrect,
        timestamp: Date.now()
    });

    const key = `${problem.chapter}:${problem.topic}`;
    if (!learningState.masteryLevel[key]) {
        learningState.masteryLevel[key] = { correct: 0, total: 0 };
    }
    learningState.masteryLevel[key].total++;
    if (isCorrect) {
        learningState.masteryLevel[key].correct++;
    }

    saveLearningState();
}

function getTopicMastery(chapter, topic) {
    const key = `${chapter}:${topic}`;
    const mastery = learningState.masteryLevel[key];
    if (!mastery || mastery.total === 0) return 0;
    return Math.round((mastery.correct / mastery.total) * 100);
}

function getChapterMastery(chapterId) {
    const chapter = chapters.find(c => c.id === chapterId);
    if (!chapter) return 0;

    let totalCorrect = 0;
    let totalProblems = 0;

    chapter.topics.forEach(topic => {
        const mastery = learningState.masteryLevel[`${chapterId}:${topic}`];
        if (mastery) {
            totalCorrect += mastery.correct;
            totalProblems += mastery.total;
        }
    });

    if (totalProblems === 0) return 0;
    return Math.round((totalCorrect / totalProblems) * 100);
}

function updateStats() {
    if (domCache.statsCorrect) {
        domCache.statsCorrect.textContent = learningState.correctCount;
    }
    if (domCache.statsWrong) {
        domCache.statsWrong.textContent = learningState.wrongCount;
    }
}

function updateMasteryDisplay() {
    if (!domCache.masteryDisplay) return;

    const currentChapter = learningState.currentChapter;
    const mastery = getChapterMastery(currentChapter);

    domCache.masteryDisplay.innerHTML = `
        <div class="flex items-center gap-2">
            <span>掌握度</span>
            <div class="w-24 h-2 bg-gray-700 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-green-500 to-emerald-400 transition-all duration-500" style="width: ${mastery}%"></div>
            </div>
            <span class="text-sm ${mastery >= 80 ? 'text-green-400' : mastery >= 50 ? 'text-yellow-400' : 'text-red-400'}">${mastery}%</span>
        </div>
    `;
}

// ============================================
// 章节和题目选择
// ============================================
function renderChapterSelect() {
    if (!domCache.chapterSelect) return;

    domCache.chapterSelect.innerHTML = chapters.map(ch => {
        const mastery = getChapterMastery(ch.id);
        return `<option value="${ch.id}">${ch.icon} ${ch.name} (${mastery}%)</option>`;
    }).join('');

    domCache.chapterSelect.value = learningState.currentChapter;
    updateChapterInfo();
}

function updateChapterInfo() {
    const chapterId = domCache.chapterSelect?.value || learningState.currentChapter;
    const chapter = chapters.find(c => c.id === chapterId);
    if (!chapter) return;

    learningState.currentChapter = chapterId;

    if (domCache.chapterName) {
        domCache.chapterName.textContent = `${chapter.icon} ${chapter.name}`;
    }

    if (domCache.topicSelect) {
        domCache.topicSelect.innerHTML = '<option value="all">全部知识点</option>' +
            chapter.topics.map(t => `<option value="${t}">${t}</option>`).join('');
    }

    const totalProblems = codeProblems.filter(p => p.chapter === chapterId).length;
    const chapterProblems = codeProblems.filter(p => p.chapter === chapterId && p.errorLine !== null);
    const doneProblems = learningState.problemHistory.filter(h => h.chapter === chapterId).length;

    if (domCache.progressBar) {
        const progress = totalProblems > 0 ? Math.round((doneProblems / totalProblems) * 100) : 0;
        domCache.progressBar.style.width = `${progress}%`;
    }

    if (domCache.progressText) {
        domCache.progressText.textContent = `${doneProblems}/${totalProblems} 题目已完成`;
    }

    updateMasteryDisplay();
}

function getRecommendedProblem() {
    const chapterId = learningState.currentChapter;
    const topic = domCache.topicSelect?.value;

    let candidates = codeProblems.filter(p => p.chapter === chapterId && p.errorLine !== null);

    if (topic && topic !== 'all') {
        candidates = candidates.filter(p => p.topic === topic);
    }

    if (candidates.length === 0) {
        candidates = codeProblems.filter(p => p.chapter === chapterId && p.errorLine !== null);
    }

    candidates.sort((a, b) => {
        const masteryA = getTopicMastery(a.chapter, a.topic);
        const masteryB = getTopicMastery(b.chapter, b.topic);
        return masteryA - masteryB;
    });

    const lowestMastery = getTopicMastery(candidates[0]?.chapter, candidates[0]?.topic);
    const lowMasteryProblems = candidates.filter(p => {
        const m = getTopicMastery(p.chapter, p.topic);
        return m <= lowestMastery + 10;
    });

    const randomIndex = Math.floor(Math.random() * Math.min(lowMasteryProblems.length, 3));
    return lowMasteryProblems[randomIndex] || candidates[0];
}

// ============================================
// AI 生成个性化题目
// ============================================
let isGeneratingProblem = false;
let generatedProblems = []; // 缓存 AI 生成的题目

async function generateAIPoweredProblem() {
    if (isGeneratingProblem) {
        return null;
    }

    const chapterId = learningState.currentChapter;
    const chapter = chapters.find(c => c.id === chapterId);
    const topic = domCache.topicSelect?.value;

    if (!chapter) {
        return null;
    }

    // 获取薄弱知识点
    const weakTopics = getWeakTopics(chapterId);
    const currentMastery = getChapterMastery(chapterId);

    // 根据掌握度调整难度
    let difficulty = 'medium';
    if (currentMastery < 30) {
        difficulty = 'easy';
    } else if (currentMastery > 70) {
        difficulty = 'hard';
    }

    isGeneratingProblem = true;
    updateAIStatus('生成题目中...', true);
    showCodeLoading();

    try {
        const response = await fetch('/api/v2/coding-problem/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                student_id: state.studentId,
                course_id: state.courseId,
                chapter: chapterId,
                topic: topic || chapter.topics[0],
                difficulty: difficulty,
                weak_topics: weakTopics,
                learning_history: learningState.problemHistory.slice(-10),
                current_mastery: currentMastery
            })
        });

        if (!response.ok) {
            throw new Error(`API 错误: ${response.status}`);
        }

        const result = await response.json();

        if (result.success && result.problem) {
            const problem = result.problem;
            // 添加到生成题目缓存
            generatedProblems.push(problem);
            isGeneratingProblem = false;
            updateAIStatus('诊断中', false);
            return problem;
        } else {
            throw new Error(result.error || '生成失败');
        }
    } catch (error) {
        console.error('AI 题目生成失败:', error);
        isGeneratingProblem = false;
        updateAIStatus('诊断中', false);
        return null;
    }
}

// 页面加载时默认调用 AI 生成第一道题目
async function initAIPoweredStart() {
    const problem = await generateAIPoweredProblem();
    if (problem) {
        loadAIGeneratedProblem(problem);
    } else {
        // AI 生成失败时显示提示
        showAIGenerationError();
    }
}

function showAIGenerationError() {
    if (domCache.messageContainer) {
        domCache.messageContainer.innerHTML = `
            <div class="flex flex-col items-center justify-center h-full text-center p-8">
                <div class="text-4xl mb-4">🤖</div>
                <div class="text-lg text-gray-300 mb-2">AI 题目生成服务</div>
                <div class="text-sm text-gray-500 mb-4">
                    暂时无法生成个性化题目<br>
                    请检查网络连接或稍后再试
                </div>
                <button onclick="retryAIGeneration()" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm transition">
                    重新生成
                </button>
            </div>
        `;
    }
}

window.retryAIGeneration = function() {
    initAIPoweredStart();
};

function getWeakTopics(chapterId) {
    // 从学习历史中找出薄弱知识点
    const chapterHistory = learningState.problemHistory.filter(h => h.chapter === chapterId);
    const topicStats = {};

    chapterHistory.forEach(record => {
        if (!topicStats[record.topic]) {
            topicStats[record.topic] = { correct: 0, wrong: 0 };
        }
        if (record.isCorrect) {
            topicStats[record.topic].correct++;
        } else {
            topicStats[record.topic].wrong++;
        }
    });

    // 找出正确率低于50%的知识点
    const weakTopics = [];
    for (const [topic, stats] of Object.entries(topicStats)) {
        const total = stats.correct + stats.wrong;
        if (total >= 2 && stats.correct / total < 0.5) {
            weakTopics.push(topic);
        }
    }

    return weakTopics.slice(0, 3);
}

// ============================================
// 用户头像同步
// ============================================
function loadUserAvatar() {
    try {
        const user = JSON.parse(localStorage.getItem('starlearn_user') || 'null');
        state.userAvatar = user?.avatar || null;
    } catch (e) {
        state.userAvatar = null;
    }
}

function getUserAvatarHtml() {
    if (state.userAvatar) {
        return `<img src="${state.userAvatar}" alt="用户头像" class="w-8 h-8 rounded-full object-cover">`;
    }
    return '👤';
}

// ============================================
// 会话初始化
// ============================================
function initSession() {
    state.sessionId = Date.now().toString(36) + Math.random().toString(36).substr(2);
    state.contextId = 'pair-prog-' + state.sessionId;
    state.tokenCount = 0;
    state.interactionCount = 0;
    state.socraticPassRate = 0.0;
    setInterval(updateCPUDisplay, 3000);
}

// ============================================
// 问题加载
// ============================================
function loadProblem(problemId) {
    const problem = codeProblems.find(p => p.id === problemId);
    if (!problem) {
        const recommended = getRecommendedProblem();
        if (recommended) {
            loadProblemById(recommended.id);
        }
        return;
    }
    loadProblemById(problem.id);
}

function loadProblemById(problemId) {
    const problem = codeProblems.find(p => p.id === problemId);
    if (!problem) return;

    state.currentProblem = problem;
    state.currentCode = problem.code;
    state.messages = [];

    if (domCache.titleDisplay) {
        const diff = difficultyConfig[problem.difficulty] || difficultyConfig.medium;
        domCache.titleDisplay.innerHTML = `
            <span class="inline-flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-[10px] bg-${diff.color}-500/20 text-${diff.color}-400">${diff.icon} ${diff.label}</span>
                <span>${problem.title}</span>
            </span>
        `;
    }

    if (domCache.errorCount) {
        domCache.errorCount.textContent = problem.errorLine ? '1 Error' : '0 Errors';
        domCache.errorCount.className = problem.errorLine
            ? 'px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-[11px]'
            : 'px-2 py-0.5 rounded bg-green-500/20 text-green-400 text-[11px]';
    }

    if (domCache.messageContainer) {
        domCache.messageContainer.innerHTML = '';
    }

    renderCode();

    setTimeout(() => {
        const topicMastery = getTopicMastery(problem.chapter, problem.topic);
        const greeting = `你好！我是你的 AI 编程导师 👋

我们正在学习「${problem.topic}」这个知识点。
当前这个知识点的掌握度是 ${topicMastery}%。

我注意到你正在查看「${problem.title}」这道题。
${problem.errorLine ? `代码中存在一个错误，试着找出来吧！` : `这是一个经典场景，看看代码有什么特点？`}

不要担心说错——结对编程的意义就在于一起思考、一起探索。`;
        addAIMessage(greeting);
    }, 500);
}

// ============================================
// 代码渲染
// ============================================
function renderCode() {
    const container = domCache.editorContent;
    const code = state.currentCode;
    if (!container || !code) return;

    const lines = code.split('\n');
    container.innerHTML = '';

    lines.forEach((line, index) => {
        const lineNum = index + 1;
        const isError = state.currentProblem?.errorLine === lineNum;

        const lineEl = document.createElement('div');
        lineEl.className = `flex text-[13px] leading-6 ${isError ? 'error-line' : ''} group`;

        const gutterEl = document.createElement('div');
        gutterEl.className = `w-12 text-right pr-4 flex-shrink-0 select-none font-mono flex items-center justify-end gap-1 ${isError ? 'text-red-400' : 'text-[#858585]'}`;

        if (isError) {
            gutterEl.innerHTML = `
                <span class="error-gutter-marker">
                    ⚠️
                    <div class="error-tooltip">
                        <div class="font-semibold text-red-400 mb-1">${state.currentProblem.errorType}</div>
                        <div>${state.currentProblem.errorMsg}</div>
                    </div>
                </span>
            `;
        } else {
            gutterEl.textContent = lineNum;
        }

        const codeEl = document.createElement('div');
        codeEl.className = 'flex-1 pl-2 pr-4';

        if (line.trim() === '') {
            codeEl.innerHTML = '&nbsp;';
        } else if (isError) {
            codeEl.innerHTML = `<span class="wavy-underline text-red-300">${escapeHtml(highlightSyntax(line))}</span>`;
        } else {
            codeEl.innerHTML = highlightSyntax(line);
        }

        const foldEl = document.createElement('div');
        foldEl.className = 'w-6 text-center text-[#808080] cursor-pointer hover:text-[#c6c6c6] flex-shrink-0 opacity-0 group-hover:opacity-100 transition-opacity';
        foldEl.textContent = '▶';

        lineEl.appendChild(gutterEl);
        lineEl.appendChild(codeEl);
        lineEl.appendChild(foldEl);

        container.appendChild(lineEl);
    });
}

function highlightSyntax(code) {
    let result = escapeHtml(code);
    result = result.replace(/#.*$/, '<span class="syntax-comment">$&</span>');
    result = result.replace(/"([^"]*)"/g, '<span class="syntax-string">"$1"</span>');
    result = result.replace(/'([^']*)'/g, '<span class="syntax-string">\'$1\'</span>');
    result = result.replace(/\b(\d+)\b/g, '<span class="syntax-number">$1</span>');
    result = result.replace(/\b(List|int|str|Dict|bool|None)\b/g, '<span class="syntax-type">$1</span>');
    result = result.replace(/\b(import|from|def|return|if|elif|else|while|for|in|not|and|or|with|as|class|try|except|finally|raise|lambda|yield|global|nonlocal|pass|break|continue)\b/g, '<span class="syntax-keyword">$1</span>');
    result = result.replace(/\b(print|len|range|str|int|list|dict|set|tuple|open|json\.load|json\.dump|append|extend|items|keys|values)\b(?=\()/g, '<span class="syntax-function">$1</span>');
    return result;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ============================================
// 消息系统
// ============================================
function addMessage(type, content) {
    const container = domCache.messageContainer;
    if (!container) return;

    const msgEl = document.createElement('div');
    msgEl.className = `flex gap-3 ${type === 'user' ? 'justify-end' : ''} mb-4`;

    if (type === 'ai') {
        msgEl.innerHTML = `
            <div class="message-avatar ai">🤖</div>
            <div class="message-card ai-message flex-1">
                <div class="text-[11px] text-indigo-400 mb-1">AI 导师 · ${getTimeString()}</div>
                <div class="text-[13px] leading-relaxed ai-message-content">${content}</div>
            </div>
        `;
    } else {
        msgEl.innerHTML = `
            <div class="message-card user-message">
                <div class="text-[11px] text-gray-400 mb-1">你 · ${getTimeString()}</div>
                <div class="text-[13px] leading-relaxed">${escapeHtml(content)}</div>
            </div>
            <div class="message-avatar user">${getUserAvatarHtml()}</div>
        `;
    }

    container.appendChild(msgEl);
    container.scrollTop = container.scrollHeight;

    return msgEl;
}

function addAIMessage(content) {
    const msgEl = addMessage('ai', '');
    const contentEl = msgEl.querySelector('.ai-message-content');
    typeText(contentEl, content);
}

function typeText(element, text, speed = 20) {
    state.isTyping = true;
    updateAIStatus('思考中...', true);

    let index = 0;
    element.innerHTML = '<span class="typing-cursor"></span>';

    function type() {
        if (index < text.length) {
            const char = text[index];
            if (char === '\n') {
                element.innerHTML = element.innerHTML.replace('<span class="typing-cursor"></span>', '<br><span class="typing-cursor"></span>');
            } else {
                element.innerHTML = text.substring(0, index + 1).replace(/\n/g, '<br>') + '<span class="typing-cursor"></span>';
            }
            index++;
            setTimeout(type, speed);
        } else {
            element.innerHTML = text.replace(/\n/g, '<br>');
            state.isTyping = false;
            updateAIStatus('诊断中', false);
        }
    }

    type();
}

function getTimeString() {
    const now = new Date();
    return `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
}

// ============================================
// AI 状态
// ============================================
function updateAIStatus(text, thinking) {
    if (!domCache.statusBadge) return;

    const dot = domCache.statusBadge.querySelector('.status-dot');
    const label = domCache.statusBadge.querySelector('.status-text');

    if (dot) {
        dot.style.animation = thinking ? 'pulse-status 0.5s ease-in-out infinite' : 'pulse-status 1.5s ease-in-out infinite';
    }
    if (label) {
        label.textContent = text;
    }
}

// ============================================
// 发送消息到 AI
// ============================================
async function sendMessage() {
    const input = domCache.submitInput;
    if (!input) return;

    const content = input.value.trim();
    if (!content || state.isTyping) return;

    addMessage('user', content);
    state.messages.push({ type: 'user', content });
    input.value = '';

    updateAIStatus('思考中...', true);

    try {
        await callAI(content);
    } catch (error) {
        console.error('AI API 调用失败:', error);
        addAIMessage('抱歉，AI 服务暂时不可用。请稍后再试。');
    }
}

// ============================================
// AI API 调用
// ============================================
async function callAI(userMessage) {
    const payload = {
        student_id: state.studentId,
        course_id: state.courseId,
        user_input: buildSocraticPrompt(userMessage),
        context_id: state.contextId,
        current_profile: {
            knowledgeBase: 'Python 基础',
            codeSkill: '中级',
            learningGoal: '提升编程思维',
            cognitiveStyle: '实践型',
            weakness: state.currentProblem?.topic || '作用域问题',
            focusLevel: '高专注'
        },
        current_path: [
            { topic: state.currentProblem?.topic || '代码调试', status: 'current' }
        ],
        interaction_count: state.interactionCount,
        code_practice_time: Math.floor(Date.now() / 1000) % 86400,
        socratic_pass_rate: state.socraticPassRate
    };

    const response = await fetch('/api/v2/chat/stream', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        throw new Error(`API 错误: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let fullContent = '';
    let displayedContent = '';
    let typingQueue = [];
    let isTypingActive = false;
    const TYPING_SPEED = 80;

    const msgEl = addMessage('ai', '');
    const contentEl = msgEl.querySelector('.ai-message-content');
    contentEl.innerHTML = '<span class="typing-cursor"></span>';

    state.isTyping = true;
    updateAIStatus('思考中...', true);

    function startTypingEffect() {
        if (typingQueue.length === 0) return;
        if (!state.isTyping) {
            displayedContent = fullContent;
            contentEl.innerHTML = formatSocraticResponse(displayedContent) + '<span class="typing-cursor"></span>';
            return;
        }

        if (!isTypingActive) {
            isTypingActive = true;
            function typeNext() {
                if (typingQueue.length === 0) {
                    isTypingActive = false;
                    return;
                }
                const char = typingQueue.shift();
                displayedContent += char;
                contentEl.innerHTML = formatSocraticResponse(displayedContent) + '<span class="typing-cursor"></span>';
                domCache.messageContainer.scrollTop = domCache.messageContainer.scrollHeight;
                setTimeout(typeNext, TYPING_SPEED);
            }
            typeNext();
        }
    }

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
            if (line.startsWith('data: ')) {
                const data = line.slice(6);
                if (data === '[DONE]') {
                    continue;
                }
                try {
                    const event = JSON.parse(data);
                    if (event.type === 'content_chunk' && event.content) {
                        fullContent += event.content;
                        for (const char of event.content) {
                            typingQueue.push(char);
                        }
                        startTypingEffect();
                    } else if (event.type === 'complete') {
                        state.isTyping = false;
                        state.interactionCount++;
                        updateAIStatus('诊断中', false);
                    }
                } catch (e) {
                    // 忽略解析错误
                }
            }
        }
    }

    while (typingQueue.length > 0 && state.isTyping) {
        await new Promise(resolve => setTimeout(resolve, 50));
    }

    displayedContent = fullContent;
    contentEl.innerHTML = formatSocraticResponse(fullContent);
    state.isTyping = false;
    updateAIStatus('诊断中', false);

    state.messages.push({ type: 'ai', content: fullContent });
    state.tokenCount += Math.ceil(fullContent.length / 4);
    updateTokenDisplay();
}

// ============================================
// 构建苏格拉底式提示
// ============================================
function buildSocraticPrompt(userMessage) {
    const problem = state.currentProblem;
    const codeContext = problem ? `
当前代码问题：${problem.title}
知识点：${problem.topic}
章节：${chapters.find(c => c.id === problem.chapter)?.name || ''}
难度：${difficultyConfig[problem.difficulty]?.label || '中等'}
错误行：第 ${problem.errorLine || '无'} 行
错误类型：${problem.errorType || '无'}
错误信息：${problem.errorMsg || '无'}

代码内容：
\`\`\`${problem.language}
${problem.code}
\`\`\`
` : '';

    const lowerMsg = userMessage.toLowerCase();
    let socraticPrompt = '';

    if (lowerMsg.includes('错误') || lowerMsg.includes('报错') || lowerMsg.includes('error') || lowerMsg.includes('有问题') || lowerMsg.includes('找不')) {
        socraticPrompt = `学生注意到了代码中的错误："${userMessage}"

作为苏格拉底式导师，请引导学生自己发现问题：

1. 先不要直接指出错误，而是引导学生关注可疑的代码行
2. 询问学生："你观察到第 ${problem?.errorLine || '相关'} 行有什么问题？"
3. 询问学生："这个错误的类型是什么？想想可能是什么原因导致的？"
4. 引导学生自己发现并修正错误
5. 最后给出提示而非答案

保持对话简洁，每次只问一个问题。用中文回复。`;
    } else if (lowerMsg.includes('为什么') || lowerMsg.includes('why')) {
        socraticPrompt = `学生提问："${userMessage}"

作为苏格拉底式导师，引导学生深入思考：

1. 引导学生解释他们对这个问题的理解
2. 追问："你能想到这种情况会在什么时候发生吗？"
3. 帮助学生建立因果关系
4. 必要时用简单类比解释

保持对话简洁，每次只问一个问题。用中文回复。`;
    } else if (lowerMsg.includes('怎么改') || lowerMsg.includes('怎么修') || lowerMsg.includes('如何解决') || lowerMsg.includes('fix') || lowerMsg.includes('修正')) {
        socraticPrompt = `学生问如何修复错误："${userMessage}"

作为苏格拉底式导师，引导学生自己想出解决方案：

1. 先让学生解释他们打算怎么做
2. 追问学生思考解决步骤
3. 引导学生自己说出解决方案
4. 如果学生卡住了，给出方向性提示而非答案

关键：不要直接给答案！让学生通过思考自己找到答案。

保持对话简洁，每次只问一个问题。用中文回复。`;
    } else if (lowerMsg.includes('不懂') || lowerMsg.includes('不理解') || lowerMsg.includes('不明白')) {
        socraticPrompt = `学生表示不理解："${userMessage}"

作为苏格拉底式导师，换一种方式解释：

1. 用日常生活中的类比来解释抽象概念
2. 将复杂问题分解成小步骤
3. 每解释一步就确认学生是否理解

保持对话简洁，每次只问一个问题。用中文回复。`;
    } else if (lowerMsg.includes('明白了') || lowerMsg.includes('懂了') || lowerMsg.includes('理解了')) {
        socraticPrompt = `学生表示理解了："${userMessage}"

作为苏格拉底式导师：
1. 肯定学生的理解
2. 让学生用自己的话复述一遍（检验真正理解）
3. 询问能否应用到其他场景
4. 鼓励学生继续探索

保持对话简洁。用中文回复。`;
    } else {
        socraticPrompt = `学生说："${userMessage}"

当前代码问题：${problem?.title || '一般编程问题'}
知识点：${problem?.topic || '编程基础'}

作为苏格拉底式导师：
1. 先理解学生的问题或困惑
2. 通过提问引导学生思考，而不是直接给答案
3. 每次只问一个引导性问题
4. 鼓励学生自己发现问题

保持对话简洁，每次只问一个问题。用中文回复。`;
    }

    return `你是「玄武·AI结对编程舱」的苏格拉底式编程导师。

角色设定：
- 你是一个启发式编程导师，而不是答案机器
- 你的目标是引导学生自己思考，自己发现问题
- 当学生犯错时，不要直接指出，而是通过提问让他们自己发现
- 用简洁的语言，每次只问一个问题
- 多用类比和图示来解释抽象概念

${codeContext}

${socraticPrompt}

记住：最好的教学不是告诉答案，而是引导思考。`;
}

// ============================================
// 格式化苏格拉底回复
// ============================================
function formatSocraticResponse(text) {
    let formatted = escapeHtml(text);
    formatted = formatted.replace(/\n/g, '<br>');
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    formatted = formatted.replace(/\*(.*?)\*/g, '<em>$1</em>');
    return formatted;
}

// ============================================
// Token 模拟
// ============================================
function startTokenSimulation() {}

function updateTokenDisplay() {
    if (domCache.terminalToken) {
        domCache.terminalToken.innerHTML = `
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
            </svg>
            <span>AI: ${state.tokenCount}</span>
        `;
    }
}

function updateCPUDisplay() {
    if (domCache.terminalCpu) {
        state.cpuUsage = Math.floor(Math.random() * 30) + 10;
        domCache.terminalCpu.innerHTML = `
            <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"/>
            </svg>
            <span>CPU: ${state.cpuUsage}%</span>
        `;
    }
}

// ============================================
// 键盘快捷键
// ============================================
function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            e.preventDefault();
            sendMessage();
        }

        if (domCache.modal && !domCache.modal.classList.contains('hidden')) {
            if (e.altKey && e.key === 'ArrowLeft') {
                e.preventDefault();
                prevProblem();
            } else if (e.altKey && e.key === 'ArrowRight') {
                e.preventDefault();
                nextProblem();
            } else if (e.altKey && e.key === 'ArrowUp') {
                e.preventDefault();
                recommendProblem();
            }
        }
    });
}

function prevProblem() {
    // 使用 AI 生成新的上一题
    recommendProblem();
}

function nextProblem() {
    // 使用 AI 生成新的下一题
    recommendProblem();
}

async function recommendProblem() {
    // 默认使用 AI 生成个性化题目
    const aiProblem = await generateAIPoweredProblem();
    if (aiProblem) {
        loadAIGeneratedProblem(aiProblem);
    } else {
        // AI 生成失败时显示错误
        showAIGenerationError();
    }
}

function loadAIGeneratedProblem(problem) {
    state.currentProblem = problem;
    state.currentCode = problem.code;
    state.messages = [];

    // 隐藏 loading，显示编辑器
    hideCodeLoading();

    if (domCache.titleDisplay) {
        const diff = difficultyConfig[problem.difficulty] || difficultyConfig.medium;
        domCache.titleDisplay.innerHTML = `
            <span class="inline-flex items-center gap-2">
                <span class="px-2 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-400">✨ AI生成</span>
                <span class="px-2 py-0.5 rounded text-[10px] bg-${diff.color}-500/20 text-${diff.color}-400">${diff.icon} ${diff.label}</span>
                <span>${problem.title}</span>
            </span>
        `;
    }

    // 计算错误数量（从 allErrors 或 code 中的 # 错误X 标注）
    let errorCount = 0;
    if (problem.allErrors && problem.allErrors.length > 0) {
        errorCount = problem.allErrors.length;
    } else {
        const matches = problem.code.match(/# 错误\d+/g);
        errorCount = matches ? matches.length : 0;
    }

    if (domCache.errorCount) {
        domCache.errorCount.textContent = errorCount > 0 ? `${errorCount}+ Errors` : '0 Errors';
        domCache.errorCount.className = errorCount > 0
            ? 'px-2 py-0.5 rounded bg-red-500/20 text-red-400 text-[11px]'
            : 'px-2 py-0.5 rounded bg-green-500/20 text-green-400 text-[11px]';
    }

    if (domCache.messageContainer) {
        domCache.messageContainer.innerHTML = '';
    }

    // 使用打字机效果显示代码
    typeCodeToEditor(problem.code, () => {
        // 代码显示完成后显示 AI 问候
        const greeting = `你好！我是你的 AI 编程导师 👋

✨ 这是一道我为你量身定制的题目！

当前知识点：${problem.topic}
目标难度：${difficultyConfig[problem.difficulty]?.label || '中等'}

题目要求：
1. 代码中存在至少 ${errorCount} 个错误
2. 你可以直接修改代码中的错误
3. 改好后点击「AI批阅」让我来检查
4. 或者与我交流你的发现

不要担心说错——结对编程的意义就在于一起思考、一起探索。`;
        addAIMessage(greeting);
    });
}

// ============================================
// 代码打字机效果
// ============================================
let currentTypingMessage = null;

function typeCodeToEditor(code, callback) {
    const editor = domCache.codeEditor;
    if (!editor) return;

    editor.value = '';
    const TYPING_SPEED = 3; // 每个字符的延迟（毫秒）

    let index = 0;

    // 在右侧显示"代码加载中"消息
    if (domCache.messageContainer) {
        currentTypingMessage = document.createElement('div');
        currentTypingMessage.className = 'flex gap-3 mb-4';
        currentTypingMessage.innerHTML = `
            <div class="message-avatar ai">🤖</div>
            <div class="message-card ai-message flex-1">
                <div class="text-[11px] text-indigo-400 mb-1">AI 导师 · ${getTimeString()}</div>
                <div class="text-[13px] leading-relaxed ai-message-content">
                    代码加载中...
                    <span class="typing-cursor"></span>
                </div>
            </div>
        `;
        domCache.messageContainer.appendChild(currentTypingMessage);
        domCache.messageContainer.scrollTop = domCache.messageContainer.scrollHeight;
    }

    function updateLoadingMessage() {
        // 更新加载进度
        const progress = Math.round((index / code.length) * 100);
        if (currentTypingMessage) {
            const content = currentTypingMessage.querySelector('.ai-message-content');
            if (content) {
                content.innerHTML = `📝 代码加载中 ${progress}%... <span class="typing-cursor"></span>`;
            }
        }
    }

    function typeChar() {
        if (index < code.length) {
            const char = code[index];
            if (char === '\n') {
                editor.value += '\n';
            } else {
                editor.value += char;
            }
            index++;

            // 滚动到底部
            editor.scrollTop = editor.scrollHeight;

            // 每隔一段时间更新进度
            if (index % 50 === 0) {
                updateLoadingMessage();
            }

            setTimeout(typeChar, TYPING_SPEED);
        } else {
            // 打字完成
            if (currentTypingMessage) {
                currentTypingMessage.remove();
                currentTypingMessage = null;
            }
            if (callback) callback();
        }
    }

    typeChar();
}

// ============================================
// 代码加载 UI
// ============================================
let loadingProgress = 0;
let loadingInterval = null;
let loadingMessage = null;

function showCodeLoading() {
    if (domCache.codeLoading) {
        domCache.codeLoading.classList.remove('hidden');
        domCache.codeLoading.style.display = 'flex';
    }
    if (domCache.codeEditor) {
        domCache.codeEditor.style.display = 'none';
    }
    const wrapper = document.getElementById('code-editor-wrapper');
    if (wrapper) {
        wrapper.style.display = 'none';
    }

    // 在右侧聊天框显示消息
    if (domCache.messageContainer) {
        domCache.messageContainer.innerHTML = `
            <div class="flex gap-3 mb-4">
                <div class="message-avatar ai">🤖</div>
                <div class="message-card ai-message flex-1">
                    <div class="text-[11px] text-indigo-400 mb-1">AI 导师 · ${getTimeString()}</div>
                    <div class="text-[13px] leading-relaxed">
                        <span class="animate-pulse">✨</span> 正在为你生成个性化题目...
                        <br><span class="text-gray-500 text-[11px]">根据你的学习情况定制中</span>
                    </div>
                </div>
            </div>
        `;
    }

    // 启动进度条动画
    loadingProgress = 0;
    if (domCache.loadingProgress) {
        domCache.loadingProgress.style.width = '0%';
    }
    loadingInterval = setInterval(() => {
        loadingProgress += Math.random() * 10;
        if (loadingProgress > 85) loadingProgress = 85;
        if (domCache.loadingProgress) {
            domCache.loadingProgress.style.width = loadingProgress + '%';
        }
    }, 300);
}

function hideCodeLoading() {
    if (domCache.codeLoading) {
        domCache.codeLoading.classList.add('hidden');
        domCache.codeLoading.style.display = 'none';
    }
    if (domCache.codeEditor) {
        domCache.codeEditor.style.display = 'block';
    }
    const wrapper = document.getElementById('code-editor-wrapper');
    if (wrapper) {
        wrapper.style.display = 'block';
    }
    if (loadingInterval) {
        clearInterval(loadingInterval);
        loadingInterval = null;
    }
    if (domCache.loadingProgress) {
        domCache.loadingProgress.style.width = '100%';
    }
}

// ============================================
// AI 批阅功能
// ============================================
let isReviewing = false;

async function submitForReview() {
    if (isReviewing) return;
    if (!domCache.codeEditor) return;

    const userCode = domCache.codeEditor.value.trim();
    if (!userCode) {
        addAIMessage('请先在代码框中输入或修改代码，再提交批阅。');
        return;
    }

    const problem = state.currentProblem;
    if (!problem) return;

    isReviewing = true;

    // 禁用批阅按钮
    if (domCache.reviewBtn) {
        domCache.reviewBtn.disabled = true;
        domCache.reviewBtn.innerHTML = '<span class="animate-spin">⏳</span><span>批阅中...</span>';
    }

    updateAIStatus('批阅中...', true);

    // 清空消息并显示批阅报告
    if (domCache.messageContainer) {
        domCache.messageContainer.innerHTML = `
            <div class="flex flex-col items-center justify-center p-4">
                <div class="text-3xl mb-2 animate-pulse">🔍</div>
                <div class="text-gray-300">AI 正在批阅你的代码...</div>
            </div>
        `;
    }

    try {
        const response = await fetch('/api/v2/code/review', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                student_id: state.studentId,
                original_code: problem.code,
                user_code: userCode,
                problem_id: problem.id,
                topic: problem.topic,
                difficulty: problem.difficulty
            })
        });

        if (!response.ok) {
            throw new Error(`API 错误: ${response.status}`);
        }

        const result = await response.json();

        if (result.success && result.report) {
            displayReviewReport(result.report);
        } else {
            throw new Error(result.error || '批阅失败');
        }
    } catch (error) {
        console.error('AI 批阅失败:', error);
        if (domCache.messageContainer) {
            domCache.messageContainer.innerHTML = `
                <div class="flex flex-col items-center justify-center p-4">
                    <div class="text-3xl mb-2">❌</div>
                    <div class="text-gray-300">批阅失败</div>
                    <div class="text-gray-500 text-sm mt-1">${error.message}</div>
                    <button onclick="submitForReview()" class="mt-3 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm transition">
                        重新批阅
                    </button>
                </div>
            `;
        }
    } finally {
        isReviewing = false;
        if (domCache.reviewBtn) {
            domCache.reviewBtn.disabled = false;
            domCache.reviewBtn.innerHTML = '<span>🔍</span><span>AI批阅</span>';
        }
        updateAIStatus('诊断中', false);
    }
}

function displayReviewReport(report) {
    if (!domCache.messageContainer) return;

    const { correct_items, wrong_items, summary } = report;

    let html = `
        <div class="review-report">
            <div class="text-lg font-semibold mb-4 text-indigo-300">📋 AI 批阅报告</div>
    `;

    // 正确的项目
    if (correct_items && correct_items.length > 0) {
        html += `<div class="mb-4">
            <div class="text-sm text-green-400 font-medium mb-2">✓ 已改正 (${correct_items.length})</div>
        `;
        correct_items.forEach(item => {
            html += `
                <div class="review-item correct">
                    <span class="text-green-400 text-lg">✓</span>
                    <div class="review-item-info">
                        <div class="review-item-line">第 ${item.line} 行</div>
                        <div class="review-item-content">${item.description}</div>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }

    // 错误的项目
    if (wrong_items && wrong_items.length > 0) {
        html += `<div class="mb-4">
            <div class="text-sm text-red-400 font-medium mb-2">✗ 还需修改 (${wrong_items.length})</div>
        `;
        wrong_items.forEach(item => {
            html += `
                <div class="review-item wrong">
                    <span class="text-red-400 text-lg">✗</span>
                    <div class="review-item-info">
                        <div class="review-item-line">第 ${item.line} 行</div>
                        <div class="review-item-content">${item.description}</div>
                        ${item.suggestion ? `<div class="text-yellow-400 text-xs mt-1">💡 建议: ${item.suggestion}</div>` : ''}
                    </div>
                </div>
            `;
        });
        html += `</div>`;
    }

    // 总结
    html += `
        <div class="review-summary">
            <div>
                <span class="review-correct">✓ ${summary?.correct_count || 0}</span>
                <span class="text-gray-500 mx-2">/</span>
                <span class="review-wrong">✗ ${summary?.wrong_count || 0}</span>
            </div>
            <div class="text-sm">
                <span class="${summary?.passed ? 'text-green-400' : 'text-yellow-400'}">
                    ${summary?.passed ? '🎉 全部正确！' : '⏳ 继续加油！'}
                </span>
            </div>
        </div>
    </div>`;

    // 添加鼓励消息
    let encouragement = '';
    if (summary?.passed) {
        encouragement = `🎉 太棒了！你已经找到了所有的错误并改正！

继续挑战下一道题目，或者与苏格拉底导师探讨更多问题吧！`;
    } else if ((summary?.correct_count || 0) > (summary?.wrong_count || 0)) {
        encouragement = `👍 做得不错！你已经改正了大部分错误。

看看"还需修改"的部分，仔细思考一下问题的根源。如果需要帮助，可以问我！`;
    } else {
        encouragement = `💪 别灰心！编程就是不断试错的过程。

看看"还需修改"的部分，我给你一些提示：
1. 仔细阅读错误信息
2. 想想这类问题的常见原因
3. 不要只看表面，要理解深层逻辑`;
    }

    domCache.messageContainer.innerHTML = html;

    // 添加鼓励消息
    setTimeout(() => {
        addAIMessage(encouragement);
    }, 500);
}

// ============================================
// 事件监听
// ============================================
function initEventListeners() {
    if (domCache.sendBtn) {
        domCache.sendBtn.addEventListener('click', sendMessage);
    }

    if (domCache.submitInput) {
        domCache.submitInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
    }

    if (domCache.chapterSelect) {
        domCache.chapterSelect.addEventListener('change', (e) => {
            updateChapterInfo();
            // 默认使用 AI 生成题目
            recommendProblem();
        });
    }

    if (domCache.topicSelect) {
        domCache.topicSelect.addEventListener('change', (e) => {
            // 默认使用 AI 生成题目
            recommendProblem();
        });
    }

    if (domCache.problemSelect) {
        domCache.problemSelect.addEventListener('change', (e) => {
            loadProblem(parseInt(e.target.value));
        });
    }

    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('fold-indicator') || e.target.textContent === '▶') {
            const line = e.target.closest('.flex');
            if (line) {
                const isCollapsed = line.classList.contains('collapsed');
                if (isCollapsed) {
                    line.classList.remove('collapsed');
                    e.target.textContent = '▶';
                } else {
                    line.classList.add('collapsed');
                    e.target.textContent = '▼';
                }
            }
        }
    });
}

// 页面加载完成后初始化
document.addEventListener('DOMContentLoaded', init);
