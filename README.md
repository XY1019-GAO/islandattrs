# islandattrs 岛屿属性计算工具包
**版本：0.1.2** 

岛屿生物地理学领域专业的岛屿地理属性计算工具包，完全符合学术规范，支持岛屿距离、邻近性、陆地占比等核心指标计算，内置71个群岛+7大洲+中国沿海岛屿的已计算结果，开箱即用。

## 功能特性
1. **专业属性计算**：支持DM(大陆距离)、SDM(踏脚石距离)、DN5(5近邻平均距离)、DNL(最近大岛距离)、NI(近邻指数)、B1/B3/B5(周边陆地占比)等10+核心指标
2. **双模式支持**：全岛屿计算模式、目标岛屿筛选模式，可灵活配置SDM/NI的计算范围
3. **内置数据集**：内置71个群岛+7大洲+中国沿海岛屿的已计算结果，支持唯一ID一键调取、关键词搜索
4. **高效计算**：基于空间索引优化，百万级岛屿也可快速计算，避免O(N²)复杂度
5. **多格式输出**：支持Excel/CSV/Shapefile格式输出，自动生成统计报告




## 安装方法
### 前置要求
- Python 3.9+
- Git
- Git LFS（用于大文件拉取）

## 安装方法
1.  克隆GitHub仓库（需安装Git）：
    ```bash
    git clone https://github.com/XY1019-GAO/islandattrs.git
    cd islandattrs
    ```
2.  安装依赖库：
    ```bash
    python -m pip install -r requirements.txt --user
    ```
3.  安装库（开发模式，修改代码后无需重新安装）：
    ```bash
    python -m pip install -e . --user
    ```
4.  验证安装成功
    ```bash
    python -c "import islandattrs; print(f'islandattrs v{islandattrs.__version__} 安装成功！')"
    ```
    预期输出：`islandattrs v0.1.2 安装成功！`


## 快速开始
### 1. 内置数据集调取
```python
import islandattrs

# 查看所有内置数据集
print(islandattrs.list_built_in_datasets())

# 加载群岛信息总表
info = islandattrs.load_archipelago_info()
print(info)

# 按ID加载已计算结果（ID=1）
data = islandattrs.load_built_in_dataset(1)
print(data.head())

# 按关键词搜索群岛，获取对应ID
result = islandattrs.search_archipelago_info("锡利群岛", search_column="Chinese_Name")
print(result)
# 用搜索到的ID加载结果
if len(result) > 0:
    arch_id = result['Archipelago_ID'].iloc[0]
    data = islandattrs.load_built_in_dataset(arch_id)
```

### 2. 包内示例数据计算
无需准备数据，直接运行测试脚本：
```bash
python islandattrs/tests/test_internal_calc.py
```

### 3. 本地数据计算
```python
import islandattrs

# 初始化计算器
calc = islandattrs.IslandAttributeCalculator(
    coastline_path="你的海岸线.shp",
    islands_path="你的岛屿.shp",
    target_file_path="你的目标岛屿.xlsx",
    output_dir="./output"
)

# 计算所有属性
calc.calculate_all_attributes()

# 保存结果
calc.save_results()
```

### 4. 命令行调用
```bash
# 目标岛屿模式，计算所有属性，SDM仅基于目标岛屿
islandattrs --islands 你的岛屿.shp --coastline 你的海岸线.shp --target-file 目标岛屿.xlsx --output ./output --all --sdm-target-only

# 查看所有命令参数
islandattrs -h
```

## 测试方法
### 测试1：内置数据集调取测试
```bash
python islandattrs/tests/test_built_in_datasets.py
```

### 测试2：包内数据计算测试
```bash
python islandattrs/tests/test_internal_calc.py
```

### 测试3：本地数据计算测试
```bash
# 先修改test_local_data.py中的本地路径，再运行
python islandattrs/tests/test_local_data.py
```

## 目录结构
```text
islandattrs/
├── islandattrs/              # 包核心目录
│   ├── __init__.py          # 包初始化
│   ├── core.py              # 核心计算代码
│   ├── data_loader.py       # 内置数据集加载
│   ├── data/                # 包内数据
│   │   ├── archipelago_info.xlsx  # 群岛信息总表
│   │   ├── test_data/       # 示例测试数据
│   │   └── built_in_results/ # 内置已计算结果
│   └── tests/               # 测试脚本
├── pyproject.toml           # 包配置
├── requirements.txt         # 依赖清单
├── README.md                # 说明文档
├── .gitignore               # Git忽略文件
└── LICENSE                  # 开源许可证
```

## 许可证
MIT License



## 版本说明
- 版本：0.1.2
- 作者：Gao xy
- 邮箱：gaoxy1019@163.com