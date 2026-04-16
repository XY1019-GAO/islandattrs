# islandattrs 岛屿属性计算工具包
**版本：0.1.2** 

岛屿生物地理学领域专业的岛屿地理属性计算工具包，完全符合学术规范，支持岛屿距离、邻近性、陆地占比等核心指标计算，内置71个群岛+7大洲+中国沿海岛屿的已计算结果，开箱即用。
# 版本信息
- 最新版本：0.1.2
- GitHub 托管地址：https://github.com/XY1019-GAO/islandattrs.git
- 开源协议：MIT License

## 功能特性
1. **专业属性计算**：支持DM(大陆距离)、SDM(踏脚石距离)、DN5(5近邻平均距离)、DNL(最近大岛距离)、NI(近邻指数)、B1/B3/B5(周边陆地占比)等10+核心指标
2. **双模式支持**：支持全岛屿计算（基于所有岛屿进行指标计算）和目标岛屿筛选计算（仅针对指定岛屿计算），灵活适配不同使用场景。
3. **灵活计算**：可独立设置 SDM、NI、NI’ 三项指标的计算范围（基于全岛屿或目标岛屿），满足个性化计算需求。
3. **内置数据集**：内置71个群岛+7大洲+中国沿海岛屿的已计算结果，支持唯一ID一键调取、关键词搜索
4. **高效计算**：基于空间索引优化，百万级岛屿也可快速计算，避免O(N²)复杂度
5. **多格式输出**：支持Excel/CSV/Shapefile格式输出，自动生成统计报告
6. **便捷调用**：支持 Python 脚本调用和命令行直接调用两种方式，无需编写复杂代码，上手门槛低。





## 安装方法
### 前置要求
- Python >= 3.8


## 标准安装
1.  适用于大多数环境，自动安装所有依赖并完成包配置，直接运行以下命令即可：
    ```bash
    pip install git+https://github.com/XY1019-GAO/islandattrs.git
    cd islandattrs
    ```
2.  版本升级：
    ```bash
    pip install --upgrade git+https://github.com/XY1019-GAO/islandattrs.git
    ```



## 快速开始
### 1. 内置数据集调取
```python
import islandattrs

# 1. 查看所有内置群岛的唯一ID列表
dataset_ids = islandattrs.list_built_in_datasets()
print("所有内置群岛ID：", dataset_ids)

# 2. 加载群岛信息总表（包含ID、中英文名称等基础信息）
archipelago_info = islandattrs.load_archipelago_info()
print("\n群岛信息总表：\n", archipelago_info.head())

# 3. 按ID加载已计算的群岛属性结果（示例：加载ID=1的群岛数据）
data = islandattrs.load_built_in_dataset(1)
print("\nID=1的群岛属性数据：\n", data.head())

# 4. 按关键词搜索群岛（示例：按中文名称搜索“锡利群岛”）
search_result = islandattrs.search_archipelago_info(
    keyword="锡利群岛",
    search_column="Chinese_Name"  # 搜索列：中文名称
)
print("\n搜索结果：\n", search_result)
```

### 2. 包内示例数据计算
无需准备数据，直接运行测试脚本：
```bash
python islandattrs/tests/test_internal_calc.py
```

### 3. 本地数据计算
```python
from islandattrs import IslandAttributeCalculator

# 初始化计算器（全岛屿计算模式，无需指定目标岛屿）
calculator = IslandAttributeCalculator(
    coastline_path="你的大陆海岸线.shp",  # 大陆海岸线文件路径
    islands_path="你的岛屿.shp",          # 岛屿图层文件路径
    output_dir="./output"                # 结果输出目录（自动创建）
)

# 计算所有支持的属性（全岛屿模式）
calculator.calculate_all_attributes(
    sdm_use_target_only=False,
    ni_use_target_only=False,
    ni_prime_use_target_only=False
)

# 保存结果（支持Excel、CSV、Shapefile格式）
calculator.save_results(
    output_format=["excel", "csv"],  # 选择输出格式
    filename_prefix="island_attributes",  # 结果文件前缀
    save_centroids=True,  # 保存岛屿质心信息
    save_all_islands=True  # 保存所有岛屿的计算结果
)
```

### 4. 命令行调用
```bash
# 1. 查看命令行帮助（了解所有可用参数）
islandattrs -h

# 2. 目标岛屿模式：计算所有属性，输出Excel格式
islandattrs --islands 你的岛屿.shp --coastline 大陆海岸线.shp --target-file 目标岛屿.xlsx --output ./output --all --sdm-target-only

# 3. 全岛屿模式：仅计算DM和SDM属性，输出Shapefile格式
islandattrs --islands 你的岛屿.shp --coastline 大陆海岸线.shp --output ./output --attributes DM SDM --save-formats shapefile
```

## 测试方法
### 测试1：内置数据集调取测试
```bash
python -m islandattrs.tests.test_built_in_datasets
```

### 测试2：包内数据计算测试
```bash
python -m islandattrs.tests.test_internal_calc
```

### 测试3：本地数据计算测试
```bash
# 先修改test_local_data.py中的本地路径，再运行
python -m islandattrs.tests.test_local_data
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

