# python 工具
需求： python3， pip

# 使用虚拟环境[推荐]

1. **创建虚拟环境**：

   ```
   python3 -m venv venv  # 创建一个名为 myenv 的虚拟环境
   ```

2. **激活虚拟环境**：

   ```
   source myenv/bin/activate
   ```

3. **安装 库**

   1. ```
      pip install pdf2docx
      ```

4. 运行程序

   1. ```
      python your_script.py
      ```

5. **退出虚拟环境**（完成后）：

   1. ```
      deactivate
      ```
## 依赖库管理

> - 简单项目：`requirements.txt`
> - 复杂项目：`pyproject.toml` + `poetry`
> - 团队协作：`Pipfile` + `pipenv`



**requirements.txt**

1. 本地安装依赖库

2. 生成依赖库文件

   1. ```
      pip freeze > requirements.txt
      ```

3. 从依赖库文件安装依赖

   1. pip install -r requirements.txt

# 目录
venv: python 虚拟环境
mirror_server: 流量镜像服务器
trans_mention.py : 转换mention为@用户名
myConvert.py: 转换pdf为docx
kaily.py:kaily 公式计算工具
CMCFear.py:CMC  Fear Index 计算工具
