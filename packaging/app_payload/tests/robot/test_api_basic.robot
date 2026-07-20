*** Settings ***
# Robot Framework — 星识 Star-Learn API 基础冒烟测试
#
# 本文件目的: 证明"我了解 Robot Framework 的基本语法 + 关键字驱动测试"
# 不是替代 pytest, 仅为岗位加分项提供 1 个能跑通的 .robot 示例。
#
# 覆盖维度:
#   - 健康检查 (静态页 200)
#   - 用户注册/登录 (含响应字段断言)
#   - 闪卡生成 (LLM 调用, 慢, 但不能崩)
#   - 画像接口 (不存在的 user_id 应优雅返回)
#   - 视频列表 (数组结构)
#   - 等价类: 正常 vs 短内容 flashcard
#
# 运行前提:
#   pip install robotframework robotframework-requests
#   uvicorn main:app --port 8000
#   robot tests/robot/test_api_basic.robot
#   或: robot --outputdir reports/robot tests/robot/

Documentation    星识 Star-Learn 后端 API 基础冒烟测试 — 覆盖健康检查/用户/闪卡/画像/视频 5 大类
Library          RequestsLibrary
Library          Collections
Library          String

*** Variables ***
# Base URL — 启动 uvicorn 时使用
${BASE_URL}        http://127.0.0.1:8000
# 用一个时间戳用户名, 避免重复跑时冲突
${TEST_USER}       robot_demo_${EMPTY}
# 测试用的 user_id, 注册成功后自动覆盖
${TEST_USER_ID}    1
# 闪卡测试用的长内容 (验证 LLM 正常路径)
${LONG_CONTENT}    Hadoop 是一个分布式系统基础架构, 包含 HDFS 分布式文件系统和 MapReduce 编程模型。HDFS 由 NameNode 管理元数据, DataNode 存储数据。MapReduce 分为 Map 和 Reduce 两个阶段。
# 闪卡测试用的短内容 (验证边界值)
${SHORT_CONTENT}   Hadoop

*** Keywords ***
建立 Session 并验证连通性
    [Documentation]    关键字: 创建 Session + 健康检查, 失败直接 Fatal Error
    Create Session    starlearn    ${BASE_URL}    timeout=10
    ${resp}    GET On Session    starlearn    /
    Status Should Be    200    ${resp}

生成唯一测试用户名
    [Documentation]    关键字: 用 epoch 时间戳生成不冲突的用户名
    ${stamp}    Get Time    epoch
    ${name}    Set Variable    robot_demo_${stamp}
    Set Test Variable    ${TEST_USER}    ${name}
    [Return]    ${name}

注册并提取 user_id
    [Documentation]    关键字: 用唯一用户名注册, 把响应里的 user_id 提取到 TEST_USER_ID
    ${name}    生成唯一测试用户名
    ${payload}    Create Dictionary    username=${name}    password=Robot@2026
    ${resp}    POST On Session    starlearn    /api/register    json=${payload}
    Status Should Be    200    ${resp}
    ${body}    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${body}    userId    msg=注册响应应包含 userId 字段
    ${uid}    Set Variable    ${body}[userId]
    Set Test Variable    ${TEST_USER_ID}    ${uid}
    [Return]    ${uid}

*** Test Cases ***
# ========== 健康检查 ==========

后端根路径应返回 200
    [Documentation]    等价类: 正常服务 → 根路径 200
    建立 Session 并验证连通性

登录页 HTML 可访问
    [Documentation]    验证静态页面服务正常
    ${resp}    GET On Session    starlearn    /login.html
    Status Should Be    200    ${resp}
    ${body}    Set Variable    ${resp.text}
    Should Contain    ${body}    <html    msg=登录页应返回 HTML 文档

# ========== 用户模块 ==========

注册新用户应返回 userId
    [Documentation]    场景: 用唯一用户名注册, 验证 userId 字段
    ${uid}    注册并提取 user_id
    Should Not Be Empty    ${uid}    msg=userId 不应为空
    Should Be True    ${uid} > 0    msg=userId 应为正整数

重复注册同一用户应失败
    [Documentation]    场景: 同名重复注册 → 期望非 200 (业务异常)
    ${name}    生成唯一测试用户名
    ${payload}    Create Dictionary    username=${name}    password=Robot@2026
    POST On Session    starlearn    /api/register    json=${payload}
    # 第二次注册同名应失败
    ${resp2}    POST On Session    starlearn    /api/register    json=${payload}    expected_status=any
    Should Not Be Equal As Numbers    200    ${resp2.status_code}    msg=重复注册应返回非 200

登录已注册用户应成功
    [Documentation]    场景: 用刚注册的账号登录
    ${name}    生成唯一测试用户名
    ${payload}    Create Dictionary    username=${name}    password=Robot@2026
    POST On Session    starlearn    /api/register    json=${payload}
    ${resp}    POST On Session    starlearn    /api/login    json=${payload}
    Status Should Be    200    ${resp}
    Dictionary Should Contain Key    ${resp.json()}    userId

# ========== 画像模块 ==========

获取不存在用户的画像应优雅返回
    [Documentation]    场景: 不存在的 user_id=999999999 → 期望 200 + 空对象/空列表
    ${resp}    GET On Session    starlearn    /api/profile/portrait/999999999
    Status Should Be    200    ${resp}
    ${body}    Set Variable    ${resp.json()}
    Dictionary Should Contain Key    ${body}    userId    msg=画像响应应至少含 userId 字段

# ========== 视频模块 ==========

本地视频列表应返回数组
    [Documentation]    场景: /api/local-videos → 200 + JSON 数组
    ${resp}    GET On Session    starlearn    /api/local-videos
    Status Should Be    200    ${resp}
    ${body}    Set Variable    ${resp.json()}
    ${is_array}    Evaluate    isinstance($body, list)
    Should Be True    ${is_array}    msg=视频列表应返回数组, 实际: ${body}

# ========== 闪卡模块 (LLM) ==========

生成闪卡-长内容应返回 flashcards 字段
    [Documentation]    场景: 正常长度内容 → LLM 应返回 flashcards (可能慢, 但不应崩)
    [Tags]    slow    ai
    ${uid}    注册并提取 user_id
    ${payload}    Create Dictionary    user_id=${uid}    course_id=bigdata    content=${LONG_CONTENT}    count=3
    ${resp}    POST On Session    starlearn    /api/v2/flashcard/generate    json=${payload}    timeout=60
    Status Should Be    200    ${resp}
    Dictionary Should Contain Key    ${resp.json()}    data    msg=闪卡响应应包含 data 字段
    Dictionary Should Contain Key    ${resp.json()}[data]    flashcards    msg=data 字段应包含 flashcards 子字段

生成闪卡-短内容边界值应不崩
    [Documentation]    边界值: 内容过短 → 期望不崩 (允许空 flashcards)
    [Tags]    ai
    ${uid}    注册并提取 user_id
    ${payload}    Create Dictionary    user_id=${uid}    course_id=bigdata    content=${SHORT_CONTENT}    count=3
    ${resp}    POST On Session    starlearn    /api/v2/flashcard/generate    json=${payload}    timeout=60    expected_status=any
    Should Be True    ${resp.status_code} < 500    msg=短内容请求不应返回 5xx, 实际 ${resp.status_code}

*** Keywords ***
# (测试用例内的 Setup/Teardown 可放这里, 当前用例复用 Session, 不需要)
