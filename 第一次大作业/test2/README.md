# 问卷系统（阶段二）

## 文档

| 文档 | 内容 |
|------|------|
| [docs/SYSTEM.md](docs/SYSTEM.md) | 系统说明（定位、技术栈、架构、目录） |
| [docs/DATABASE.md](docs/DATABASE.md) | 数据库设计（集合、字段、索引） |
| [docs/API.md](docs/API.md) | API 说明 |
| [docs/LOGIC.md](docs/LOGIC.md) | 关键逻辑（跳转、校验、填写、统计） |
| [docs/QUESTION_BANK.md](docs/QUESTION_BANK.md) | 题库、版本、发布锁定与跨问卷统计规则 |
| [手工测试/手工测试流程与结果.md](手工测试/手工测试流程与结果.md) | **阶段二扩展**（题库、共享、版本、发布锁定、跨问卷统计） |
| [mongodb_schema_doc/](mongodb_schema_doc/) | 报告用完整 Schema 分文件 |


## 运行

- 进入项目目录
```bash
cd test2
```
- 创建虚拟环境并激活  
```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows 系统: .venv\Scripts\activate
```
- 安装依赖  
```bash
pip install -r requirements.txt  # 或 python -m pip install -r requirements.txt

```
- 拷贝环境变量模板并按需修改  
```bash
cp .env.example .env
# 按需修改 .env（MongoDB、SECRET_KEY 等）
```
- 启动服务  
```bash
python -m uvicorn app.main:app --reload --port 8000

```

浏览器访问 `http://127.0.0.1:8000/`（静态页）、API 文档 `http://127.0.0.1:8000/docs`。

- 登录注册
```markdown
点击右上角 `登录` 或 `注册` 按钮进行登录 / 注册
```

## 测试

```bash
pytest
```

无 MongoDB 时集成测试会自动跳过；单元测试不依赖数据库。

## 界面效果

- 大体界面与`阶段一`一致，`阶段二`详细界面见 [手工测试/手工测试流程与结果.md](手工测试/手工测试流程与结果.md)